/*
 * main.c
 *
 *  Created on: 2011-9-8
 *      Author: rocky
 */
#include <linux/kernel.h>
#include <linux/device.h>
#include <linux/mm.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/fs.h>
#include <linux/types.h>
#include <linux/spinlock.h>
#include <linux/slab.h>
#include <linux/uaccess.h>
#include <linux/cdev.h>
#include <linux/platform_device.h>

#include <bdaq_def.h>
#include <ioctls.h>
#include <bdaq_kern.h>

#include "dnl_ctx.h"

#ifndef EXPORT_SYMTAB
#define EXPORT_SYMTAB
#endif

/************************************************************************
 * Private Macros
 ************************************************************************/
#define KLIB_DEV_MINOR       255

/************************************************************************
 * Private Types
 ************************************************************************/
typedef struct daq_klib_device {
   struct cdev cdev;     // char device structure
} daq_klib_device_t;

typedef struct daq_klib_file_ctx {
   spinlock_t  lock;
   daq_event_t *events[(PAGE_SIZE - sizeof(spinlock_t))/sizeof(daq_event_t*)];
} daq_klib_file_ctx_t;

typedef struct dev_id_entry {
   u16 online;
   u16 prod_id;
   u16 board_id;
   u16 hw_bspn;  //Hardware bus + slot(PCI)/port(USB) number
} dev_id_entry_t;

/************************************************************************
 * Private data
 ************************************************************************/
static struct class     *daq_class;
static dev_t             daq_dev_id;

static DEFINE_SPINLOCK(dev_id_map_lock);
static dev_id_entry_t    dev_id_map[256];

#define DEV_ID_MAPLEN    ARRAY_SIZE(dev_id_map)

// The only device instance
static daq_klib_device_t daq_klib_dev;

// The only SYSFS device instance
struct device           *daq_klib_sysfs;

static struct platform_driver daq_klib_drv = {
   .driver = {
      .name = "biokernbase",
   }
};

/************************************************************************
 * KLib Public Methods
 *************************************************************************/
/*
 * Alloc a dev id. return (dev_t)0 if error.
 * */
dev_t daq_devid_alloc(unsigned prod_id, unsigned board_id, unsigned hw_bspn)
{
   dev_t    id = (dev_t)0;
   unsigned i  = DEV_ID_MAPLEN;

   spin_lock(&dev_id_map_lock);

   // 1. Find the previously allocated id if possible
   // 1.1 Find according to the board id
   if (board_id) {
      for (i = 0; i < DEV_ID_MAPLEN; ++i) {
         if ( !dev_id_map[i].online 
            && dev_id_map[i].prod_id  == prod_id 
            && dev_id_map[i].board_id == board_id) {
            break;
         }
      }
   }

   // 1.2 Find according to the HW Key: bus & slot for PCI, bus & port for USB
   if (i >= DEV_ID_MAPLEN) {
      for (i = 0; i < DEV_ID_MAPLEN; ++i) {
         if ( !dev_id_map[i].online
            && dev_id_map[i].prod_id == prod_id 
            && dev_id_map[i].hw_bspn == hw_bspn) {
            break;
         }
      }
   }

   // 2. Allocate a new id
   // 2.1 Find an blank ID at first
   if (i >= DEV_ID_MAPLEN) {
      for (i = 0; i < DEV_ID_MAPLEN; ++i) {
         if ( !dev_id_map[i].online 
            && dev_id_map[i].prod_id == 0) {
            break;
         }
      }
   }

   // 2.2 Find an free ID
   if (i >= DEV_ID_MAPLEN) {
      for (i = 0; i < DEV_ID_MAPLEN; ++i) {
         if (!dev_id_map[i].online) {
            break;
         }
      }
   }

   // AHA, we got it at last, record the device information
   if (i < DEV_ID_MAPLEN) {
      dev_id_map[i].prod_id = prod_id;
      dev_id_map[i].hw_bspn = hw_bspn;
      dev_id_map[i].board_id= board_id;
      dev_id_map[i].online = 1;

      id = MKDEV(MAJOR(daq_dev_id), i);
   }

   spin_unlock(&dev_id_map_lock);

   return id;
}

dev_t daq_devid_alloc_fixed(int minor)
{
   if (minor >= KLIB_DEV_MINOR) {
      return (dev_t)-1;
   }

   spin_lock(&dev_id_map_lock);
   if (dev_id_map[minor].online) {
      minor = -1;
   } else {
      dev_id_map[minor].online  = 1;
      dev_id_map[minor].prod_id = -1;
      dev_id_map[minor].hw_bspn = -1;
   }
   spin_unlock(&dev_id_map_lock);

   return minor == -1 ? (dev_t)-1 : MKDEV(MAJOR(daq_dev_id), minor);
}

/*
 * update the 'board id' information of a dev id
 * */
void daq_devid_update(dev_t id, unsigned prod_id, unsigned board_id)
{
   int ma = MAJOR(id);
   int mi = MINOR(id);

   if (ma != MAJOR(daq_dev_id) || ((u32)mi) >= KLIB_DEV_MINOR) {
      return;
   }

   spin_lock(&dev_id_map_lock);
   if (dev_id_map[mi].prod_id == prod_id) {
      dev_id_map[mi].board_id = board_id;
   }
   spin_unlock(&dev_id_map_lock);
}

/*
 * Free a dev id.
 * */
void daq_devid_free(dev_t id)
{
   int ma = MAJOR(id);
   int mi = MINOR(id);

   if (ma != MAJOR(daq_dev_id) || ((u32)mi) >= KLIB_DEV_MINOR) {
      return;
   }

   spin_lock(&dev_id_map_lock);
   dev_id_map[mi].online = 0;
   spin_unlock(&dev_id_map_lock);
}

/*
 * Get device class
 * */
struct class * daq_class_get(void)
{
   return daq_class;
}

/*
* Get device class driver
*/
struct device_driver * daq_class_drv_get(void)
{
   return &daq_klib_drv.driver;
}

/************************************************************************
 * File Operation Methods
 *************************************************************************/
static int daq_klib_file_open(struct inode *in, struct file *fp)
{
   daq_klib_file_ctx_t *ctx = (daq_klib_file_ctx_t *)kzalloc(sizeof(*ctx), GFP_KERNEL);

   if (ctx == NULL){
      return -ENOMEM;
   }

   spin_lock_init(&ctx->lock);
   fp->private_data = ctx;
   return 0;
}

static int daq_klib_file_close(struct inode *inode, struct file *filp)
{
   daq_klib_file_ctx_t *ctx =(daq_klib_file_ctx_t *)filp->private_data;
   int i;

   spin_lock(&ctx->lock);
   for (i = 0; i < ARRAY_SIZE(ctx->events); ++i){
      if (ctx->events[i]){
         daq_event_close(ctx->events[i]);
      }
   }
   memset(ctx->events, 0, sizeof(ctx->events));
   spin_unlock(&ctx->lock);

   kfree(ctx);
   filp->private_data = NULL;
   return 0;
}

static long daq_klib_file_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)
{
   switch(cmd)
   {
   case IOCTL_KLIB_CREATE_EVENT:
      {
         daq_klib_file_ctx_t *ctx = filp->private_data;
         void  *event;
         int   slot;

         event = daq_event_create();
         if (event == NULL){
            return -ENOMEM;
         }

         spin_lock(&ctx->lock);
         for (slot = 0; slot < ARRAY_SIZE(ctx->events); ++slot){
            if (!ctx->events[slot]){
               ctx->events[slot] = event;
               break;
            }
         }
         spin_unlock(&ctx->lock);

         if (slot >= ARRAY_SIZE(ctx->events)) {
            daq_event_close(event);
            return -EXFULL;
         }

         if (unlikely(put_user(event, (void **)arg)) < 0){
            ctx->events[slot] = NULL;
            daq_event_close(event);
            return -EFAULT;
         }
         return 0;
      }
      break;
   case IOCTL_KLIB_CREATE_EVENT_NAMED:
      {
         daq_klib_file_ctx_t *ctx = filp->private_data;
         NAMED_EVENT xbuf;
         void  *event;
         int   slot;

         if (unlikely(copy_from_user(&xbuf, (void *)arg, sizeof(xbuf)))){
            return -EFAULT;
         }

         event = daq_event_create_named(xbuf.Name);
         if (event == NULL){
            return -ENOMEM;
         }

         spin_lock(&ctx->lock);
         for (slot = 0; slot < ARRAY_SIZE(ctx->events); ++slot){
            if (!ctx->events[slot]){
               ctx->events[slot] = event;
               break;
            }
         }
         spin_unlock(&ctx->lock);

         if (slot >= ARRAY_SIZE(ctx->events)) {
            daq_event_close(event);
            return -EXFULL;
         }

         if (unlikely(put_user(event, &((NAMED_EVENT*)arg)->Handle)) < 0){
            ctx->events[slot] = NULL;
            daq_event_close(event);
            return -EFAULT;
         }
         return 0;
      }
      break;
   case IOCTL_KLIB_CLOSE_EVENT:
      {
         daq_klib_file_ctx_t *ctx = filp->private_data;
         int   slot;

         spin_lock(&ctx->lock);
         for (slot = 0; slot < ARRAY_SIZE(ctx->events); ++slot){
            if (ctx->events[slot] == (void *)arg){
               ctx->events[slot] = NULL;
            }
         }
         spin_unlock(&ctx->lock);

         daq_event_close((void *)arg);
         return 0;
      }
      break;
   case IOCTL_KLIB_SET_EVENT:
      {
         daq_event_set((void *)arg);
         return 0;
      }
      break;
   case IOCTL_KLIB_RESET_EVENT:
      {
         daq_event_reset((void *)arg);
         return 0;
      }
      break;
   case IOCTL_KLIB_WAIT_EVENT:
      {
         KLIB_WAIT_EVENT xbuf;
         daq_event_t    *events[MAX_WAIT_OBJECTS];

         if (unlikely(copy_from_user(&xbuf, (void *)arg, sizeof(xbuf)))){
            return -EFAULT;
         }

         if (xbuf.Count > MAX_WAIT_OBJECTS){
            return -EINVAL;
         }

         if (unlikely(copy_from_user(events, xbuf.Events, sizeof(void *) * xbuf.Count))){
            return -EFAULT;
         }

         xbuf.Result = daq_event_wait(xbuf.Count, events, xbuf.WaitAll, xbuf.Timeout);
         put_user(xbuf.Result, &((KLIB_WAIT_EVENT*)arg)->Result);
         return xbuf.Result < 0 ? xbuf.Result : 0;
      }
      break;
   case IOCTL_KLIB_ADD_DEV:
      {
         ISA_DEV_INFO xbuf;
         if (unlikely(copy_from_user(&xbuf, (void *)arg, sizeof(xbuf)))){
            return -EFAULT;
         }

         return daq_add_isa_device(xbuf.DeviceName, xbuf.DriverName, xbuf.IoBase, xbuf.Irq, xbuf.Dma);
      }
   case IOCTL_KLIB_REMOVE_DEV:
      {
         ISA_DEV_INFO xbuf;
         if (unlikely(copy_from_user(&xbuf, (void *)arg, sizeof(xbuf)))){
            return -EFAULT;
         }

         return daq_remove_isa_device(xbuf.DeviceName, xbuf.DriverName, xbuf.IoBase);
      }
   case IOCTL_DNL_GET_MAPPING_SIZE:
      {
         u32 __user *target = NULL;
         u32        value   = 0;
         long       err     = 0;

#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - IOCTL_DNL_GET_MAPPING_SIZE +\n");
#     endif

         target = (u32*)arg;
         value  = dnl_get_logger_registry_size() + dnl_get_log_cache_size();

         if (target == NULL || unlikely(copy_to_user(target, &value, sizeof(u32)))) {
#        if LIB_DNL_SYS_TRACE
            printk(KERN_ERR "DNL - copy_to_user() failed\n");
#        endif

            err = -EFAULT;
         }

#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - IOCTL_DNL_GET_MAPPING_SIZE -\n");
#     endif

         return err;
      }
   case IOCTL_DNL_GET_LOGGER_REGISTRY_SIZE:
      {
         u32 __user *target = NULL;
         u32        value   = 0;
         long       err     = 0;

#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - IOCTL_DNL_GET_LOGGER_REGISTRY_SIZE +\n");
#     endif

         target = (u32*)arg;
         value  = dnl_get_logger_registry_size();

         if (target == NULL || unlikely(copy_to_user(target, &value, sizeof(u32)))) {
#        if LIB_DNL_SYS_TRACE
            printk(KERN_ERR "DNL - copy_to_user() failed\n");
#        endif

            err = -EFAULT;
         }

#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - IOCTL_DNL_GET_LOGGER_REGISTRY_SIZE -\n");
#     endif

         return err;
      }
   case IOCTL_DNL_TEST_LOGGER_REGISTRY:
      {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - IOCTL_DNL_TEST_LOGGER_REGISTRY +\n");
#     endif

         dnl_test_logger_registry((u16)arg);

#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - IOCTL_DNL_TEST_LOGGER_REGISTRY -\n");
#     endif

         return 0;
      }
   case IOCTL_DNL_TEST_LOG_CACHE:
      {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - IOCTL_DNL_TEST_LOG_CACHE +\n");
#     endif

         dnl_test_log_cache((u32)arg);

#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - IOCTL_DNL_TEST_LOG_CACHE -\n");
#     endif

         return 0;
      }
   case IOCTL_DNL_TEST_REGISTER_LOGGER:
      {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - IOCTL_DNL_TEST_REGISTER_LOGGER +\n");
#     endif

         dnl_test_register_logger();

#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - IOCTL_DNL_TEST_REGISTER_LOGGER -\n");
#     endif

         return 0;
      }
   case IOCTL_DNL_TEST_WRITE_LOG:
      {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - IOCTL_DNL_TEST_WRITE_LOG +\n");
#     endif

         dnl_test_write_log((u32)arg);

#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - IOCTL_DNL_TEST_WRITE_LOG -\n");
#     endif

         return 0;
      }
   case IOCTL_DNL_TEST_UNREGISTER_LOGGER:
      {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - IOCTL_DNL_TEST_UNREGISTER_LOGGER +\n");
#     endif

         dnl_test_unregister_logger();

#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - IOCTL_DNL_TEST_UNREGISTER_LOGGER -\n");
#     endif

         return 0;
      }
   default:
      break;
   }

   return -ENOTTY;
}

int dnl_mmap(struct file *flip, struct vm_area_struct *vma)
{
   int ret = 0;

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_mmap +\n");
#endif

   do {
      ulong addr      = 0;
      ulong pfn       = 0;
      ulong size      = 0;
      int   remap_err = 0;

      addr = (ulong)vma->vm_start;
      size = vma->vm_end - vma->vm_start;
      pfn  = virt_to_phys(dnl_ctx.buffer) >> PAGE_SHIFT;

      if (!dnl_ctx.ready) {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_ERR "DNL - shared memory unavailable\n");
#     endif

         ret = -EPERM;
         break;
      }

      if (size != dnl_ctx.size) {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_ERR "DNL - invalid mapping size: %lu (%lu expected)\n", size, dnl_ctx.size);
#     endif

         ret = -EINVAL;
         break;
      }

      remap_err = remap_pfn_range(vma, addr, pfn, size, vma->vm_page_prot);
      if (remap_err != 0) {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_ERR "DNL - remap_pfn_range() failed, errno: %d\n", remap_err);
#     endif

         ret = -EAGAIN;
         break;
      }

      vm_flags_set(vma, VM_RESERVED);
   } while (false);

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_mmap -\n");
#endif

   return ret;
}

/************************************************************************
* fs support routines
************************************************************************/
static struct file_operations daq_klib_fops = {
   .owner          = THIS_MODULE,
   .open           = daq_klib_file_open,
   .release        = daq_klib_file_close,
   .unlocked_ioctl = daq_klib_file_ioctl,
   .mmap           = dnl_mmap,
};

/************************************************************************
* sysfs support routines
************************************************************************/
#define DEVICE_DESC      "Kernel Mode Library for BDAQNavi Linux drivers"
#define DRIVER_NAME      "biokernbase"
#include <sysfs_helper.h>

/************************************************************************
 * Private Methods
 *************************************************************************/
static int __init daq_klib_init(void)
{
   dev_t klib_devid   = 0;
   int   dev_inited   = 0;
   int   ret          = 0;
   int   dnl_init_err = 0;

   platform_driver_register(&daq_klib_drv);

   do{
      /* Allocate dynamic device number */
      if ((ret = alloc_chrdev_region(&daq_dev_id, 0, 256, "daq")) != 0) {
         daq_trace((KERN_ERR "failed to alloc device number.0x%x\n",ret));
         break;
      }

      /* This device using the minor number '255' */
      klib_devid = MKDEV(MAJOR(daq_dev_id), KLIB_DEV_MINOR);
      dev_id_map[KLIB_DEV_MINOR].online  = 1;
      dev_id_map[KLIB_DEV_MINOR].prod_id = -1;
      dev_id_map[KLIB_DEV_MINOR].hw_bspn = -1;

      /* Register our device class */
#ifdef class_create
      daq_class = class_create(THIS_MODULE, "daq");
#else
      daq_class = class_create("daq");
#endif
      if (IS_ERR(daq_class)){
         daq_trace((KERN_ERR "failed in creating device class.\n"));
         ret = PTR_ERR(daq_class);
         break;
      }

      /* Register the device into kernel */
      cdev_init(&daq_klib_dev.cdev, &daq_klib_fops);
      daq_klib_dev.cdev.owner = THIS_MODULE;
      if ((ret = cdev_add(&daq_klib_dev.cdev, klib_devid, 1)) != 0) {
         daq_trace((KERN_ERR "daq: register char device failed.0x%x\n", ret));
         break;
      }
      dev_inited = 1;


      /* Register the device into sysfs */
      daq_klib_sysfs = daq_sysfs_dev_create(klib_devid, &daq_klib_dev);
      if (IS_ERR(daq_klib_sysfs)){
         daq_trace( (KERN_INFO "Registered character device failed\n"));
         ret = PTR_ERR(daq_klib_sysfs);
         break;
      }

      /* Initialize DNL */
      dnl_init_err = dnl_ctx_init(&dnl_ctx);
      if (dnl_init_err != 0) {
         printk(KERN_ERR "DNL - dnl_ctx_init() failed, errno: %d\n", dnl_init_err);

         BUG_ON(dnl_ctx.ready);
         BUG_ON(dnl_ctx.buffer != NULL);
      }
      else {
         BUG_ON(!dnl_ctx.ready);
         BUG_ON(dnl_ctx.buffer == NULL);
      }
   } while(0);

   /* Some error occured, clean up now*/
   if (ret != 0) {
      BUG_ON(dnl_ctx.ready);

      if (daq_klib_sysfs != NULL && !IS_ERR(daq_klib_sysfs)) {
         daq_sysfs_dev_destroy(daq_klib_sysfs);
      }

      if (dev_inited) {
         cdev_del(&daq_klib_dev.cdev);
      }

      if (daq_class != NULL && !IS_ERR(daq_class)) {
         class_destroy(daq_class);
      }

      if (daq_dev_id != 0) {
         unregister_chrdev_region(daq_dev_id, 256);
      }

      platform_driver_unregister(&daq_klib_drv);
   }

   return ret;
}

/************************************************************************
 * static void __exit advdrv_cleanup(void)
 *
 * Description:  Close driver - Clean up remaining memory and unregister
 *                         the major.256
 *************************************************************************/
static void __exit daq_klib_exit(void)
{
   daq_trace((KERN_INFO "daq: klib uninitialized\n"));

   dnl_ctx_destroy(&dnl_ctx);

   daq_sysfs_dev_destroy(daq_klib_sysfs);

   cdev_del(&daq_klib_dev.cdev);

   class_destroy(daq_class);

   unregister_chrdev_region(daq_dev_id, 256);

   platform_driver_unregister(&daq_klib_drv);
}

module_init(daq_klib_init);
module_exit(daq_klib_exit);

EXPORT_SYMBOL_GPL(daq_devid_alloc);
EXPORT_SYMBOL_GPL(daq_devid_alloc_fixed);
EXPORT_SYMBOL_GPL(daq_devid_update);
EXPORT_SYMBOL_GPL(daq_devid_free);
EXPORT_SYMBOL_GPL(daq_class_get);
EXPORT_SYMBOL_GPL(daq_class_drv_get);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Advantech DAQ Driver Kernel Library");