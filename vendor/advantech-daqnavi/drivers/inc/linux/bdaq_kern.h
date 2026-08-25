/*******************************************************************************
              Copyright (c) 1983-2009 Advantech Co., Ltd.
********************************************************************************
THIS IS AN UNPUBLISHED WORK CONTAINING CONFIDENTIAL AND PROPRIETARY INFORMATION
WHICH IS THE PROPERTY OF ADVANTECH CORP., ANY DISCLOSURE, USE, OR REPRODUCTION,
WITHOUT WRITTEN AUTHORIZATION FROM ADVANTECH CORP., IS STRICTLY PROHIBITED.

================================================================================
REVISION HISTORY
--------------------------------------------------------------------------------
$Log: $
--------------------------------------------------------------------------------
$NoKeywords:  $
*/

#ifndef DAQNAVI_KERNEL_MODE_LIBRARY
#define DAQNAVI_KERNEL_MODE_LIBRARY

#include <linux/version.h>
#if (LINUX_VERSION_CODE < KERNEL_VERSION(2,6,0))
#  error "This driver needs kernel version >= 2.6.0."
#endif

#if (LINUX_VERSION_CODE < KERNEL_VERSION(2,6,18))
#include <linux/config.h>
#endif

// -------------------------------------------------------------------------------
// debug helper
// -------------------------------------------------------------------------------
#if defined(_DEBUG) || defined(DEBUG)
#  define DAQ_TRACING
#endif

#if defined(DAQ_TRACING)
#  define daq_trace( _x_ )  printk _x_
#else
#  define daq_trace( _x_ )  do{}while(0)
#endif

// -------------------------------------------------------------------------------
// MACROs to simplify read/write device register
// -------------------------------------------------------------------------------
// Access I/O Space
#define AdxIoInB(io_base, offset)           inb((io_base) + (offset))
#define AdxIoInW(io_base, offset)           inw((io_base) + (offset))
#define AdxIoInD(io_base, offset)           inl((io_base) + (offset))
#define AdxIoOutB(io_base, offset, data)    outb(( __u8)(data), (io_base) + (offset))
#define AdxIoOutW(io_base, offset, data)    outw((__u16)(data), (io_base) + (offset))
#define AdxIoOutD(io_base, offset, data)    outl((__u32)(data), (io_base) + (offset))

// Access Memory Space
#define AdxMemInB(mem_base, offset)         ioread8((mem_base) + (offset))
#define AdxMemInW(mem_base, offset)         ioread16((mem_base) + (offset))
#define AdxMemInD(mem_base, offset)         ioread32((mem_base) + (offset))
#define AdxMemOutB(mem_base, offset, data)  iowrite8 (( __u8)(data), (__u8*)(mem_base) + (offset))
#define AdxMemOutW(mem_base, offset, data)  iowrite16((__u16)(data), (__u8*)(mem_base) + (offset))
#define AdxMemOutD(mem_base, offset, data)  iowrite32((__u32)(data), (__u8*)(mem_base) + (offset))

// ------------------------------------------------------------------------
// For compatible
// ------------------------------------------------------------------------
#define x_list_for_each_entry(pos, head, member, xtype) list_for_each_entry(pos, head, member)

#define x_event_set(handle)             daq_event_set(handle)
#define x_event_set_inc(handle, x)      daq_event_set(handle)
#define x_event_reset(handle)           daq_event_reset(handle)

#define x_os_start_timer(tmr, delay)    schedule_delayed_work(tmr, usecs_to_jiffies(delay))
#define x_ms_to_os_tick(ms)             msecs_to_jiffies(ms)

static inline uint64 x_os_get_tick_count(void)
{
   return (uint64)jiffies;
}

static inline int64 x_os_get_time_ns(void)
{
   // kernel time in nano-second
#if (LINUX_VERSION_CODE < KERNEL_VERSION(4,18,0))
   struct timespec now;
   getnstimeofday(&now);
   return timespec_to_ns(&now);
#else
   struct timespec64 now;
   ktime_get_real_ts64(&now);
   return timespec64_to_ns(&now);
#endif
}

static inline int x_time_is_before(uint64 a, uint64 b)
{
   //return true if the time a is before b
   return (int64)a - (int64)b < 0;
}

static inline uint64 x_os_get_time_epoch_us(void)
{
   uint64 x = x_os_get_time_ns();
   do_div(x, 1000);
   return x;
}

static inline s64 x_current_kernel_time_ns(void)
{
#if (LINUX_VERSION_CODE < KERNEL_VERSION(4,18,0))
   struct timespec now = current_kernel_time();
   return timespec_to_ns(&now);
#else
   struct timespec64 now;
   ktime_get_coarse_real_ts64(&now);
   return timespec64_to_ns(&now);
#endif
}

// ATOMIC Operation Support, Using Linux Kernel built-in ATOMIC operations.
#define x_atomic_inc(ptr)                  atomic_inc((atomic_t *)ptr)
#define x_atomic_dec(ptr)                  atomic_dec((atomic_t *)ptr)

#define x_atomic_add(ptr, val)             atomic_add(val, (atomic_t *)ptr)
#define x_atomic_sub(ptr, val)             atomic_sub(val, (atomic_t *)ptr)

#define x_atomic_xchg(ptr, val)            atomic_xchg((atomic_t *)ptr, val)
#define x_atomic_cmpxchg(ptr, oval, nval)  atomic_cmpxchg((atomic_t *)ptr, oval, nval)

static inline uint32 x_atomic_and(volatile uint32 *ptr, uint32 val)
{
   uint32 old;
   do {
      old = *ptr;
   } while (x_atomic_cmpxchg(ptr, old, old & val) != old);
 
   return old;
}

static inline uint32 x_atomic_or(volatile uint32 *ptr, uint32 val)
{
   uint32 old;
   do {
      old = *ptr;
   } while (x_atomic_cmpxchg(ptr, old, old | val) != old);
 
   return old;
}

static inline uint32 x_atomic_xor(volatile uint32 *ptr, uint32 val)
{
   uint32 old;
   do {
      old = *ptr;
   } while (x_atomic_cmpxchg(ptr, old, old ^ val) != old);

   return old;
}

static inline uint32 x_atomic_limit_add(volatile uint32 *ptr, uint32 val, uint32 upLimit)
{
   uint32 old, nval;
   do {
      old = *ptr;
      nval= x_min(old + val, upLimit);
   } while (x_atomic_cmpxchg(ptr, old, nval) != old);

   return old;
}

static inline int32 x_atomic_limit_sub(volatile uint32 *ptr, uint32 val, uint32 loLimit)
{
   int32 old, nval;
   do {
      old  = (int32)*ptr;
      nval = x_max((int32)(old - val), (int32)loLimit);
   } while (x_atomic_cmpxchg(ptr, old, nval) != old);

   return old;
}

static inline uint32 x_mod_u64(uint64 n, uint32 b)
{
   return do_div(n, b);
}

static inline uint32 x_div_u64(uint64 n, uint32 b)
{
   return div_u64(n, b);
}

// -------------------------------------------------------------------------------
// device id and sysfs methods & macros
// -------------------------------------------------------------------------------
#define HW_BSPN(bus, slot_or_port)  (((unsigned)bus << 8) | (slot_or_port & 0xFF))

dev_t daq_devid_alloc(unsigned prod_id, unsigned board_id, unsigned hw_bspn);
dev_t daq_devid_alloc_fixed(int minor);
void  daq_devid_update(dev_t id, unsigned prod_id, unsigned board_id);
void  daq_devid_free(dev_t id);

struct class *         daq_class_get(void);
struct device_driver * daq_class_drv_get(void);

// -------------------------------------------------------------------------------
// event methods
// -------------------------------------------------------------------------------
#define MAX_WAIT_OBJECTS  64
typedef struct daq_event daq_event_t;

daq_event_t* daq_event_create(void);
daq_event_t* daq_event_create_named(char *name);
void daq_event_add_ref(daq_event_t *event);
void daq_event_close(daq_event_t* event);
void daq_event_set(daq_event_t* event);
void daq_event_reset(daq_event_t* event);
int  daq_event_wait(unsigned count, daq_event_t* events[], int waitAll, unsigned timeout);

// -------------------------------------------------------------------------------
// memory.c
// -------------------------------------------------------------------------------
#define ROUND_TO_PAGES(size) (((unsigned)(size) + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1))

typedef struct _daq_user_mem {
   unsigned    nr_pages;
   struct page **pages;
   void        *kaddr;
} daq_user_mem_t;

int  daq_user_mem_map(unsigned long uaddr, unsigned count, int write, daq_user_mem_t *mi);
int  daq_user_mem_get_pages(unsigned long uaddr, unsigned count, int write, daq_user_mem_t *mi);
int  daq_user_mem_map_pages(daq_user_mem_t *mi);
void daq_user_mem_unmap(daq_user_mem_t *mi);
int  daq_user_mem_alloc(unsigned count, daq_user_mem_t *mi, int dma32);
void daq_user_mem_free(daq_user_mem_t *mi);

#include <linux/device.h>

typedef struct _daq_dma_mem {
   unsigned size;
   void    *kaddr;
   uint64   daddr;
} daq_dma_mem_t;

int  daq_dma_mem_alloc(struct device *dev, unsigned size, daq_dma_mem_t *dmem);
void daq_dma_mem_free(struct device *dev, daq_dma_mem_t *dmem);
void daq_mem_reserve_pages(void *ptr, unsigned size, int reserve);

//
// for compatible : daq_umem
#define daq_umem_t          daq_user_mem_t
#define daq_umem_map        daq_user_mem_map
#define daq_umem_get_pages  daq_user_mem_get_pages
#define daq_umem_map_pages  daq_user_mem_map_pages
#define daq_umem_unmap      daq_user_mem_unmap
#define daq_umem_alloc      daq_user_mem_alloc
#define daq_umem_free       daq_user_mem_free

//
// for compatible : daq_dmem
#define daq_dmem_t          daq_dma_mem_t
#define daq_dmem_alloc      daq_dma_mem_alloc
#define daq_dmem_free       daq_dma_mem_free

// -------------------------------------------------------------------------------
// misc.c
// -------------------------------------------------------------------------------
unsigned daq_ai_calc_log_chan_count(unsigned char * chType, unsigned count);
unsigned daq_ai_calc_phy_chan_range(unsigned char * chType, unsigned count, unsigned phyStart, unsigned logCount);
static inline unsigned daq_ai_calc_phy_chan_range32(unsigned char * chType, unsigned count, unsigned phyStart, unsigned logCount)
{
   unsigned range = daq_ai_calc_phy_chan_range(chType, count, phyStart, logCount);
   return ((range & 0xff00) << 8) | (range & 0x00ff);
}


typedef struct _daq_plx_sgl {
   unsigned               nr_pages;
   struct page          **pages;
   struct _PLX_SGL_ENTRY *start;
   struct _PLX_SGL_ENTRY *end;
   unsigned               count;
   unsigned               startPA;
} daq_plx_sgl_t;

int      daq_plx9054_flush_fifo(unsigned bridge_base, int dma_chan);
unsigned daq_plx905x_calc_sgl_length(unsigned data_len, unsigned sect_len);
int      daq_plx905x_alloc_sgl_mem(unsigned sgl_len, daq_plx_sgl_t *sgl_mem);
void     daq_plx905x_free_sgl_mem(daq_plx_sgl_t *sgl_mem);
int      daq_plx905x_build_sgl(
            daq_user_mem_t *data_mem, unsigned data_len,    unsigned  sect_len,
            unsigned   dev_addr,  unsigned from_device, daq_plx_sgl_t *sgl_mem);

unsigned daq_ver_string_to_integer(char * ver_str);

// ------------------------------------------------------------------------
//  PCIe-X DMA format definition for PCIe-1812,PCIe-1813, PCIe-1803, etc.
//
// ------------------------------------------------------------------------
typedef struct _daq_pciex_sgl {
   unsigned                 nr_pages;
   struct page            **pages;
   struct _PCIEx_SGL_ENTRY *start;
   struct _PCIEx_SGL_ENTRY *end;
   uint64                   daddr;
   uint32                   count;
} daq_pciex_sgl_t;

uint32   daq_pciex_calc_sgl_length(uint32 data_len, uint32 sect_len);
int      daq_pciex_alloc_sgl_mem(uint32 sgl_len, daq_pciex_sgl_t *sgl_mem);
void     daq_pciex_free_sgl_mem(daq_pciex_sgl_t *sgl_mem);
int      daq_pciex_build_sgl(daq_user_mem_t *data_mem, uint32 data_len, uint32 sect_len, uint32 ele_size, daq_pciex_sgl_t *sgl_mem);

//
// Helper function used to queue a work item so that the callback function
// can be executed in the context of a system thread.
typedef void (*daq_work_func_t)(void *device, unsigned long arg1, unsigned long arg2);
int daq_dev_schedule_work(void *device, daq_work_func_t func, unsigned long arg1, unsigned long arg2);

// -------------------------------------------------------------------------------
// USB continuous reader methods.
// -------------------------------------------------------------------------------
#if 1
//#ifdef CONFIG_USB   //disbale this for debain

#include <linux/usb.h>

#define MAX_PENDING_PACKET_COUNT       4
#define USB_EP_DIR(epd)                (epd->bEndpointAddress & USB_ENDPOINT_DIR_MASK)
#define USB_EP_XFER_TYPE(epd)          (epd->bmAttributes & USB_ENDPOINT_XFERTYPE_MASK)

//
// return value of the call back function :
// DAQ_UR_CONTINUE : submit the URB again
// DAQ_UR_BREAK : don't submit the URB any more.
#define DAQ_UR_CONTINUE 0
#define DAQ_UR_BREAK    1
typedef int (*daq_usb_complete_t)(struct urb *urb, void *context);

#define is_reader_inited(reader) ((reader)->urb_count)
#define is_reader_running(reader) ((reader)->running)
typedef struct _daq_usb_reader{
   daq_usb_complete_t complete;
   void *context;
   int  running;
   int  urb_count;
   struct urb *urbs[MAX_PENDING_PACKET_COUNT];
}daq_usb_reader_t;

int daq_usb_reader_init(
      struct usb_device *udev,       const struct usb_endpoint_descriptor *epd,
      unsigned int      packet_size, unsigned int packet_count,
      daq_usb_complete_t on_read_complete, void *context, daq_usb_reader_t *reader);

int  daq_usb_reader_start(daq_usb_reader_t *reader);
void daq_usb_reader_stop(daq_usb_reader_t *reader);
void daq_usb_reader_cleanup(daq_usb_reader_t *reader);

#endif // CONFIG_USB

// -------------------------------------------------------------------------------
// ISA device.
// -------------------------------------------------------------------------------
extern struct list_head daq_isa_drivers;
struct daq_isa_device;

#define ISA_NAME_MAX_LEN         32

struct daq_isa_driver {
   struct list_head  isa_drivers;
   struct list_head  devices;
   const char *name;
   int (*probe)(struct daq_isa_device *dev);
   int (*remove)(struct daq_isa_device *dev);
   int (*match)(struct daq_isa_device *dev, struct daq_isa_driver * driver);
   int (*shutdown)(struct daq_isa_device *dev);
   int (*suspend)(struct daq_isa_device *dev);
   int (*resume)(struct daq_isa_device *dev);
};

struct daq_isa_device{
   struct list_head device_list;
   struct daq_isa_driver   *driver;
   const char device_name[ISA_NAME_MAX_LEN];
   const char driver_name[ISA_NAME_MAX_LEN];
   unsigned int iobase;
   unsigned int irq;
   unsigned int dmachan;
   struct  device dev;
};

int daq_isa_register_driver(struct daq_isa_driver *driver);
int daq_isa_unregister_driver(struct daq_isa_driver *driver);
int daq_isa_add_device(struct daq_isa_driver *driver, struct daq_isa_device *device);
int daq_isa_renove_device(struct daq_isa_driver *driver, struct daq_isa_device *device);
int daq_isa_match_obe_device(struct daq_isa_device *devuce, struct daq_isa_driver *driver);
int daq_add_isa_device(char *device_name, char * driver_name, unsigned int iobase, unsigned int irq, unsigned int dmabase);
int daq_remove_isa_device(char *device_name, char * driver_name, unsigned int iobase);

// -------------------------------------------------------------------------------
// MACROs for compatible with different kernel version
// -------------------------------------------------------------------------------
#if (LINUX_VERSION_CODE < KERNEL_VERSION(2,6,18))
#  ifdef CONFIG_PCI
#     include <linux/signal.h>
#     define IRQF_SHARED  SA_SHIRQ
#  endif
#endif

#if (LINUX_VERSION_CODE < KERNEL_VERSION(2,6,19))
   typedef irqreturn_t (*daq_irq_handler_t)(int, void *, struct pt_regs *);
#else
#  include <linux/irqreturn.h>
   typedef irqreturn_t (*daq_irq_handler_t)(int, void *);
#endif

#if (LINUX_VERSION_CODE < KERNEL_VERSION(2,6,20))
#  define delayed_work                        work_struct
#  define delayed_work_ptr(_work)             (_work)
#  define DAQ_INIT_WORK(_work, _func)         INIT_WORK(_work, (void (*)(void *))_func, _work)
#  define DAQ_INIT_DELAYED_WORK(_work, _func) INIT_WORK(_work, (void (*)(void *))_func, _work)
#else
#  define delayed_work_ptr(_work)             container_of(_work, struct delayed_work, work)
#  define DAQ_INIT_WORK(_work, _func)         INIT_WORK(_work, _func)
#  define DAQ_INIT_DELAYED_WORK(_work, _func) INIT_DELAYED_WORK(_work, _func)

#  if (LINUX_VERSION_CODE < KERNEL_VERSION(2,6,23))
   static inline int cancel_delayed_work_sync(struct delayed_work *dwork)
   {
      int ret = cancel_delayed_work(dwork);
      if (!ret) {
         cancel_work_sync(&dwork->work);
      }

      return ret;
   }
#  endif

#endif

#if (LINUX_VERSION_CODE < KERNEL_VERSION(2,6,26))
#  define time_is_before_jiffies(a) time_after(jiffies, a)
#endif

#if (LINUX_VERSION_CODE < KERNEL_VERSION(2,6,34))
#  define usb_alloc_coherent  usb_buffer_alloc
#  define usb_free_coherent   usb_buffer_free
#endif

#if (LINUX_VERSION_CODE >= KERNEL_VERSION(3,8,0))
#  define __devinit
#  define __devexit
#  define __devexit_p(a)     a
#endif

#ifndef VM_RESERVED
#  define VM_RESERVED  (VM_DONTEXPAND | VM_DONTDUMP)
#endif

#if (LINUX_VERSION_CODE < KERNEL_VERSION(4,17,0))
#  define vm_fault_ret int
#else
#  define vm_fault_ret vm_fault_t
#endif

#ifdef RHEL_RELEASE
#  if RHEL_RELEASE_CODE < 2309 // RHEL_RELEASE "503.14.1"
#     define vm_flags_set(vma, flags)   do { vma->vm_flags |= flags; } while(0)
#  else 
//    Using the OS defined 'vm_flags_set'
#  endif
#else
#  if (LINUX_VERSION_CODE < KERNEL_VERSION(6,3,0))
#     define vm_flags_set(vma, flags)   do { vma->vm_flags |= flags; } while(0)
#  else 
//    Using the OS defined 'vm_flags_set'
#  endif
#endif

// -------------------------------------------------------------------------------
// dnl.c
// -------------------------------------------------------------------------------

#include <linux/compiler.h>

ulong dnl_register_logger(const char* name,
                          u8**        enabled);

extern __printf(3, 4)
int dnl_print(ulong       logger_handle,
              u32         log_level,
              const char* log_message,
              ...);

extern __printf(6, 7)
int dnl_print_ex(ulong       logger_handle,
                 u32         log_level,
                 const char* file,
                 u32         line,
                 const char* function,
                 const char* log_message,
                 ...);

void  dnl_unregister_logger(ulong logger_handle);

#endif // DAQNAVI_KERNEL_MODE_LIBRARY
