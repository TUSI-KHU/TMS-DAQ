/*
 * init.c
 *
 *  Created on: August 1, 2012
 *      Author: rocky
 */
#include <linux/module.h>
#include <linux/init.h>
#include <linux/fs.h>
#include "kdriver.h"

// device supported
static struct usb_device_id daq_device_ids[] = {
   { USB_DEVICE(ADVANTECH_VID, DEVICE_ID_4704) },
   { USB_DEVICE(ADVANTECH_VID, DEVICE_ID_4702) },
   { 0, }
};
MODULE_DEVICE_TABLE(usb, daq_device_ids);

/************************************************************************
* FILE OPERATIONS
************************************************************************/
static struct file_operations daq_fops = {
   .owner    = THIS_MODULE,
   .open     = daq_file_open,
   .release  = daq_file_close,
   .mmap     = daq_file_mmap,
   .unlocked_ioctl = daq_file_ioctl,
};

/************************************************************************
* device settings
************************************************************************/
static void daq_device_load_setting(daq_device_t  *daq_dev)
{
   DEVICE_SHARED *shared = &daq_dev->shared;
   int i;

   // AI
   for (i = 0; i < AI_CHL_COUNT; ++i){
      shared->AiChanType[i] = DEF_AI_CHTYPE;
      shared->AiChanGain[i] = DEF_AI_GAIN;
   }

   shared->FaiParam.PhyChanStart     = DEF_FAI_CHSTART;
   shared->FaiParam.LogChanCount     = DEF_FAI_CHCOUNT;
   shared->FaiParam.ConvClkSource    = DEF_FAI_CLKSRC;
   shared->FaiParam.ConvClkRatePerCH = AI_CLK_BASE / DEF_FAI_PACERDIVISOR;
   shared->FaiParam.SectionSize      = DEF_FAI_SECTSIZE;

   // AO
   for (i = 0; i < AO_CHL_COUNT; ++i){
      shared->AoChanGain[i]  = DEF_AO_GAIN;
      shared->AoChanState[i] = DEF_AO_STATE;
   }

   // DIO
   memset(shared->DoPortState, DEF_DO_STATE, DIO_PORT_COUNT);

   // Counter
   shared->CntrConfig.FmPeroid[0] = DEF_CNT_PERIOD;
}

/************************************************************************
* sysfs support routines
************************************************************************/
#include <sysfs_helper.h>

// ------------------------------------------------------------------
// Device initialize/de-initailize
// ------------------------------------------------------------------
static int __devinit daq_device_probe(struct usb_interface *interface, const struct usb_device_id *id)
{
   struct usb_host_interface      *iface_desc;
   struct usb_endpoint_descriptor *epd;
   dev_t         devid;
   daq_device_t  *daq_dev;
   DEVICE_SHARED *shared = NULL;
   size_t        mem_size;
   int           ret, i;
   char          fw_ver[64];

#define CHK_RESULT(_ok_, err, err_label)   if (!(_ok_)) { ret = err; goto err_label; }

   // allocate private data structure
   mem_size = (sizeof(daq_device_t) + PAGE_SIZE - 1) & PAGE_MASK;
   daq_dev = (daq_device_t*)kzalloc(mem_size, GFP_KERNEL);
   CHK_RESULT(daq_dev, -ENOMEM, err_alloc_dev)

   // get usb information
   mutex_init(&daq_dev->ctrl_pipe_lock);
   daq_dev->iface = interface;
   daq_dev->udev  = usb_get_dev(interface_to_usbdev(interface));
   CHK_RESULT(daq_dev->udev, -ENODEV, err_device)

   // endpoint information
   iface_desc = interface->cur_altsetting;
   for (i = 0; i < iface_desc->desc.bNumEndpoints; i++) {
      epd = &iface_desc->endpoint[i].desc;
      if (USB_EP_DIR(epd) == USB_DIR_IN
          && USB_EP_XFER_TYPE(epd) == USB_ENDPOINT_XFER_BULK) {
         daq_dev->xfer_epd = epd;
         break;
      }
   }

   // initialize the private data in the device
   shared               = &daq_dev->shared;
   shared->Size         = sizeof(*shared);
   shared->DeviceNumber = -1; // unknown
   shared->InitOnLoad   = DEF_INIT_ON_LOAD;

   switch(id->idProduct){
      case DEVICE_ID_4702: shared->ProductId = BD_USB4702; break;
      default:             shared->ProductId = BD_USB4704; break;
   }
   spin_lock_init(&daq_dev->dev_lock);

   spin_lock_init(&daq_dev->fai_lock);
   mutex_init(&daq_dev->fai_stop_lock);
   daq_dev->fai_hwflag_supported = 1;
   daq_dev->fai_next_hwflag_check = jiffies;
   init_waitqueue_head(&daq_dev->fai_queue);
   DAQ_INIT_WORK(&daq_dev->fai_check_work, daq_fai_check_work_func);
   DAQ_INIT_WORK(&daq_dev->fai_stop_work,  daq_fai_stop_work_func);

   DAQ_INIT_DELAYED_WORK(&daq_dev->cntr_fm_work, daq_cntr_update_state_work_func);
   INIT_LIST_HEAD(&daq_dev->file_ctx_list);
   daq_dev->file_ctx_pool_size = (mem_size - sizeof(daq_device_t)) / sizeof(daq_file_ctx_t);
   if (daq_dev->file_ctx_pool_size){
      daq_dev->file_ctx_pool = (daq_file_ctx_t *)(daq_dev + 1);
   } else {
      daq_dev->file_ctx_pool = NULL;
   }

   // get device information
   ret = daq_usb_dev_get_board_id_oscsd(daq_dev, &shared->BoardId, &shared->HwAiChType, &shared->Oscillator);
   CHK_RESULT(ret > 0, ret, err_no_res)

   ret = daq_usb_dev_get_firmware_ver(daq_dev, fw_ver, 64);
   CHK_RESULT(ret > 0, ret, err_no_res)

   shared->FirmwareVer = daq_ver_string_to_integer(fw_ver);

   /*Get dynamic device number*/
   devid = daq_devid_alloc(shared->ProductId, shared->BoardId, HW_BSPN(daq_dev->udev->bus->busnum, daq_dev->udev->portnum));
   CHK_RESULT(devid > (dev_t)0, -ENOSPC, err_no_res)

   /*register our device into kernel*/
   cdev_init(&daq_dev->cdev, &daq_fops);
   daq_dev->cdev.owner = THIS_MODULE;
   ret = cdev_add(&daq_dev->cdev, devid, 1);
   CHK_RESULT(ret == 0, ret, err_cdev_add)

   /* register our own device in sysfs, and this will cause udev to create corresponding device node */
   daq_dev->sysfs = daq_sysfs_dev_create(devid, daq_dev);
   CHK_RESULT(!IS_ERR(daq_dev->sysfs), PTR_ERR(daq_dev->sysfs), err_sysfs_reg)

   // link the info into the other structures
   usb_set_intfdata(daq_dev->iface, daq_dev);
   SetPageReserved(virt_to_page((unsigned long)daq_dev));

   // initialize the device
   daq_device_load_setting(daq_dev);
   daq_ai_initialize_hw(daq_dev);
   daq_ao_initialize_hw(daq_dev);
   daq_dio_initialize_hw(daq_dev);

   // Winning horn
   daq_trace((KERN_INFO "Add %s: major:%d, minor:%d\n", DEVICE_NAME_FROM_PID(shared->ProductId), MAJOR(devid), MINOR(devid)));
   return 0;

err_sysfs_reg:
   cdev_del(&daq_dev->cdev);

err_cdev_add:
   daq_devid_free(devid);

err_no_res:
   mutex_destroy(&daq_dev->ctrl_pipe_lock);
   usb_put_dev(interface_to_usbdev(interface));

err_device:
   kfree(daq_dev);

err_alloc_dev:
   daq_trace((KERN_ERR "Add %s failed. error = %d\n", DEVICE_NAME_FROM_PID(shared->ProductId), ret));
   return ret;
}

void daq_device_cleanup(daq_device_t * daq_dev)
{
   // Clean up any allocated resources and stuff here.
   daq_usb_reader_cleanup(&daq_dev->usb_reader);
   /* No queued callback may dereference daq_dev after kfree below. */
   cancel_work_sync(&daq_dev->fai_stop_work);
   cancel_work_sync(&daq_dev->fai_check_work);
   mutex_destroy(&daq_dev->fai_stop_lock);

   daq_sysfs_dev_destroy(daq_dev->sysfs);
   daq_devid_free(daq_dev->cdev.dev);
   cdev_del(&daq_dev->cdev);

   mutex_destroy(&daq_dev->ctrl_pipe_lock);

   // Free the device information structure
   ClearPageReserved(virt_to_page((unsigned long)daq_dev));
   kfree(daq_dev);
}

static void __devexit daq_device_remove(struct usb_interface *interface)
{
   daq_device_t *daq_dev = usb_get_intfdata(interface);

   daq_trace((KERN_INFO"Device removed!\n" ));

   mutex_lock(&daq_dev->ctrl_pipe_lock);
   usb_put_dev(interface_to_usbdev(interface));   // Disconnect from usb interface
   usb_set_intfdata(interface, NULL);
   daq_dev->udev = NULL;
   daq_dev->iface= NULL;
   mutex_unlock(&daq_dev->ctrl_pipe_lock);

   {
      unsigned long flags;
      spin_lock_irqsave(&daq_dev->dev_lock, flags);
      if (list_empty(&daq_dev->file_ctx_list)){
         spin_unlock_irqrestore(&daq_dev->dev_lock, flags);
         daq_device_cleanup(daq_dev);
      } else {
         spin_unlock_irqrestore(&daq_dev->dev_lock, flags);
      }
   }
}

// ------------------------------------------------------------------
// Driver initialize/de-initailize
// ------------------------------------------------------------------
static struct usb_driver usb_driver = {
   .name       = DRIVER_NAME,
   .probe      = daq_device_probe,
   .disconnect = __devexit_p(daq_device_remove),
   .id_table   = daq_device_ids,
};

static int __init daq_driver_init(void)
{
   return usb_register(&usb_driver);
}

static void __exit daq_driver_exit(void)
{
   usb_deregister(&usb_driver);
}

module_init(daq_driver_init);
module_exit(daq_driver_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Advantech DAQ Driver For USB-4702/04 series");
