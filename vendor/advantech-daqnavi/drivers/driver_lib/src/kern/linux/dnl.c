/*
 * dnl.c
 *
 * Created on: 2023-9-5
 *    Author: li.zhe
 */

#include <linux/module.h>
#include <linux/slab.h>
#include <linux/time.h>
#include <linux/version.h>

#include "dnl_ctx.h"

#ifndef EXPORT_SYMTAB
#  define EXPORT_SYMTAB
#endif

#define DNL_LOGGER_NAME_LENGTH_MAX        (127 + 1)
#define DNL_LOG_MESSAGE_LENGTH_MAX        (259 + 1)
#define DNL_LOGGING_DIRECTORY_LENGTH_MAX  (259 + 1)
#define DNL_LOGGER_BLOCKING_LIST_SIZE_MAX (10)

#define DNL_LOG_LEVEL_FATAL   (0)
#define DNL_LOG_LEVEL_ERROR   (1)
#define DNL_LOG_LEVEL_WARNING (2)
#define DNL_LOG_LEVEL_TRACE   (3)
#define DNL_LOG_LEVEL_DEBUG   (4)

#define DNL_FILE_SIZE_CONSTRAINT_MIN     (1 * 0x1000)   /* 4 KiB */
#define DNL_FILE_SIZE_CONSTRAINT_DEFAULT (4 * 0x100000) /* 4 MiB */

#define DNL_LOG_ROTATION_ACTION_OVERWRITE (0)
#define DNL_LOG_ROTATION_ACTION_STOP      (1)

#define DNL_BUILDIN_DIAGNOSTIC_FILE "File"
#define DNL_BUILDIN_DIAGNOSTIC_LINE "Line"
#define DNL_BUILDIN_DIAGNOSTIC_FUNC "Function"

#define DNL_LOGGER_DEFAULT_ENABLED                                (0)
#define DNL_LOGGER_DEFAULT_DEBUGGING_ENABLED                      (1)
#define DNL_LOGGER_DEFAULT_DEBUGGING_FILTER                       (DNL_LOG_LEVEL_WARNING)
#define DNL_LOGGER_DEFAULT_LOGGING_ENABLED                        (0)
#define DNL_LOGGER_DEFAULT_LOGGING_FILTER                         (DNL_LOG_LEVEL_WARNING)
#define DNL_LOGGER_DEFAULT_LOGGING_DIRECTORY                      "/opt/advantech/logs/"
#define DNL_LOGGER_DEFAULT_LOGGING_FILE_SIZE_CONSTRAINT           DNL_FILE_SIZE_CONSTRAINT_DEFAULT
#define DNL_LOGGER_DEFAULT_LOGGING_ROTATION_BOUNDARY              (3 * DNL_LOGGER_DEFAULT_LOGGING_FILE_SIZE_CONSTRAINT)
#define DNL_LOGGER_DEFAULT_LOGGING_ROTATION_ACTION                (DNL_LOG_ROTATION_ACTION_OVERWRITE)
#define DNL_LOGGER_DEFAULT_REMOTING_ENABLED                       (0)
#define DNL_LOGGER_DEFAULT_REMOTING_FILTER                        (DNL_LOG_LEVEL_WARNING)
#define DNL_LOGGER_DEFAULT_REMOTING_TRANSPORT_COMPRESSION_ENABLED (1)

#pragma pack(push, 1)

typedef struct logger_registry
{
   struct
   {
      u8 reserved;

      struct
      {
         u32 descriptors;
         u32 registry;
      } size;

      u16 capacity;
      u16 registered;

      u8 dirty;
   } descriptor;

   char buffer[1];
} logger_registry_t, *logger_registry_ptr;

typedef struct logger
{
   char name[DNL_LOGGER_NAME_LENGTH_MAX];

   u8 enabled;

   struct
   {
      u8  enabled;
      u32 filter;
   } debugging;

   struct
   {
      u8  enabled;
      u32 filter;

      char directory[DNL_LOGGING_DIRECTORY_LENGTH_MAX];

      struct
      {
         u32 size;
      } file;

      struct
      {
         u64 boundary;
         u32 action;
      } rotation;
   } logging;

   struct
   {
      u8  enabled;
      u32 filter;

      struct
      {
         u8 compression_enabled;
      } transport;
   } remoting;

   struct
   {
      char file[DNL_LOGGER_NAME_LENGTH_MAX];
      u32  line;
   } blocking_list[DNL_LOGGER_BLOCKING_LIST_SIZE_MAX];
} logger_t, *logger_ptr;

typedef struct log_cache
{
   struct
   {
      u32 header;

      struct
      {
         u32 capacity;
         u32 unit;
      } cache;
   } size;

   u32 wp;
   u32 rp;

   char buffer[1];
} log_cache_t, *log_cache_ptr;

#pragma pack(pop)

static logger_registry_ptr _logger_registry = NULL;
static log_cache_ptr       _log_cache       = NULL;

#define LOGGER_REGISTRY_DESCRIPTOR_SIZE \
   (                \
      sizeof(u8)  + \
      sizeof(u32) + \
      sizeof(u32) + \
      sizeof(u16) + \
      sizeof(u16) + \
      sizeof(u8)    \
   )

typedef struct logger_descriptor
{
   ulong handle;
   void* address;
} logger_descriptor_t, *logger_descriptor_ptr;

#define LOGGER_COUNT_MAX (128)

static u32 get_logger_registry_header_size(void)
{
   /*
    * An integer multiple of PAGE_SIZE that is no smaller than
    * LOGGER_REGISTRY_DESCRIPTOR_SIZE + LOGGER_COUNT_MAX * sizeof(logger_descriptor_t)
    */

   static u32 size = 0;

   if (size == 0) {
      u32 sizeof_logger_descriptors = LOGGER_COUNT_MAX * sizeof(logger_descriptor_t);

      size = LOGGER_REGISTRY_DESCRIPTOR_SIZE + sizeof_logger_descriptors;
      size = ((size + ~PAGE_MASK) >> PAGE_SHIFT) * PAGE_SIZE;
   }

   return size;
}
#define LOGGER_REGISTRY_HEADER_SIZE get_logger_registry_header_size()

static u32 get_logger_registry_body_size(void)
{
   /*
    * An integer multiple of PAGE_SIZE that is no smaller than LOGGER_COUNT_MAX * sizeof(logger_t)
    */

   static u32 size = 0;

   if (size == 0) {
      size = LOGGER_COUNT_MAX * sizeof(logger_t);
      size = ((size + ~PAGE_MASK) >> PAGE_SHIFT) * PAGE_SIZE;
   }

   return size;
}
#define LOGGER_REGISTRY_BODY_SIZE get_logger_registry_body_size()

u32 dnl_get_logger_registry_size(void)
{
   static u32 size = 0;

   if (size == 0) {
      u32 header_size = 0;
      u32 body_size   = 0;

      header_size = get_logger_registry_header_size();
      BUG_ON(header_size == (u32)-1);

      body_size = get_logger_registry_body_size();
      BUG_ON(body_size == (u32)-1);

      BUG_ON((u32)-1 - header_size < body_size);
      size = header_size + body_size;
      BUG_ON(size == 0);

#  if LIB_DNL_SYS_TRACE
      printk(KERN_INFO "DNL kernel mode logger registry - size: %u", size);
#  endif
   }

   return size;
}
#define LOGGER_REGISTRY_SIZE dnl_get_logger_registry_size()

#define LOGGER_DESCRIPTOR_BASE \
   ((char*)_logger_registry + LOGGER_REGISTRY_DESCRIPTOR_SIZE)

#define LOGGER_DESCRIPTOR(i) \
   ((logger_descriptor_ptr)(LOGGER_DESCRIPTOR_BASE + (i) * sizeof(logger_descriptor_t)))

#define LOGGER_BASE \
   ((char*)_logger_registry + LOGGER_REGISTRY_HEADER_SIZE)

#define LOGGER(i) \
   ((logger_ptr)(LOGGER_BASE + (i) * sizeof(logger_t)))

#define FILE_NAME_LENGTH_MAX     (127 + 1)
#define FUNCTION_NAME_LENGTH_MAX (127 + 1)
#define DBG_MESSAGE_LENGTH_MAX   (511 + 1)

#define STRUCTURED_LOG_VERSION_1 (1)
#define STRUCTURED_LOG_VERSION   STRUCTURED_LOG_VERSION_1

#define LOG_SIZE_CONSTRAINT \
   (                               \
      sizeof(u16)                + \
      sizeof(u8)                 + \
      sizeof(u8)                 + \
      sizeof(u64)                + \
      sizeof(u16)                + \
      DNL_LOGGER_NAME_LENGTH_MAX + \
      sizeof(u32)                + \
      sizeof(u16)                + \
      DNL_LOG_MESSAGE_LENGTH_MAX + \
      sizeof(u16)                + \
      sizeof(u16)                + \
      FILE_NAME_LENGTH_MAX       + \
      sizeof(u32)                + \
      sizeof(u16)                + \
      FUNCTION_NAME_LENGTH_MAX     \
   )

#define LOG_CACHE_UNIT_SIZE (LOG_SIZE_CONSTRAINT + 1)

u32 dnl_get_log_cache_size(void)
{
   /*
    * An integer multiple of PAGE_SIZE, should be at least 20 bytes larger than an integer multiple of
    * LOG_CACHE_UNIT_SIZE
    */

   static u32 size = 0;

   BUG_ON(LOGGER_REGISTRY_SIZE >= 4 * 0x100000);

   if (size == 0) {
      size = 4 * 0x100000 - LOGGER_REGISTRY_SIZE;
      size = ((size + ~PAGE_MASK) >> PAGE_SHIFT) * PAGE_SIZE;

#  if LIB_DNL_SYS_TRACE
      printk(KERN_INFO "DNL kernel mode log cache - size: %u", size);
#  endif
   }

   return size;
}
#define LOG_CACHE_SIZE dnl_get_log_cache_size()

static u32 get_log_cache_header_size(void)
{
   static u32 size = 0;

   if (size == 0) {
      size = dnl_get_log_cache_size() % LOG_CACHE_UNIT_SIZE;
      while (size < 20) {
         size += LOG_CACHE_UNIT_SIZE;
      }

      BUG_ON(dnl_get_log_cache_size() <= size + LOG_CACHE_UNIT_SIZE);
   }

   return size;
}
#define LOG_CACHE_HEADER_SIZE get_log_cache_header_size()

#define LOG_CACHE_BODY_SIZE \
   (LOG_CACHE_SIZE - LOG_CACHE_HEADER_SIZE)

#define LOG_CACHE_BASE \
   ((char*)_log_cache + LOG_CACHE_HEADER_SIZE)

dnl_ctx_t dnl_ctx;

#if (LINUX_VERSION_CODE < KERNEL_VERSION(4, 18, 0))
static struct timespec _boot_time;
#else
static struct timespec64 _boot_time;
#endif

static u16 _logger_id = 0;

void logger_registry_init(void)
{
   u32 i = 0;

   BUG_ON(_logger_registry == NULL);
   memset(_logger_registry, 0, LOGGER_REGISTRY_SIZE);
   memset(_logger_registry, 0xFE, LOGGER_REGISTRY_HEADER_SIZE);

   _logger_registry->descriptor.reserved         = sizeof(void*) == sizeof(u32) ? 1 : 0;
   _logger_registry->descriptor.size.descriptors = LOGGER_REGISTRY_HEADER_SIZE - LOGGER_REGISTRY_DESCRIPTOR_SIZE;
   _logger_registry->descriptor.size.registry    = LOGGER_REGISTRY_BODY_SIZE;
   _logger_registry->descriptor.capacity         = LOGGER_COUNT_MAX;
   _logger_registry->descriptor.registered       = 0;
   _logger_registry->descriptor.dirty            = 0;

   for (; i < _logger_registry->descriptor.capacity; ++i) {
      logger_descriptor_ptr logger_descriptor = LOGGER_DESCRIPTOR(i);
      logger_descriptor->handle  = 0;
      logger_descriptor->address = LOGGER(i);
   }
}

void logger_cache_init(void)
{
   BUG_ON(_log_cache == NULL);
   memset(_log_cache, 0, LOG_CACHE_SIZE);
   memset(_log_cache, 0xFE, LOG_CACHE_HEADER_SIZE);

   _log_cache->size.header         = LOG_CACHE_HEADER_SIZE;
   _log_cache->size.cache.capacity = LOG_CACHE_BODY_SIZE;
   _log_cache->size.cache.unit     = LOG_CACHE_UNIT_SIZE;

   _log_cache->wp = 0;
   _log_cache->rp = 0;
}

int dnl_ctx_init(dnl_ctx_t* dnl_ctx)
{
   int   ret           = 0;
   u32   size          = 0;
   int   order         = 0;
   u64   capacity      = 0;
   u32   log_count_max = 0;
   ulong buffer        = 0;

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_ctx_init +");
#endif

#ifndef MAX_ORDER
#  define MAX_ORDER MAX_PAGE_ORDER
#endif

   do {
      if (unlikely(dnl_ctx == NULL)) {
         ret = -EINVAL;
         break;
      }

      memset(dnl_ctx, 0, sizeof(dnl_ctx_t));

      size = LOGGER_REGISTRY_SIZE + LOG_CACHE_SIZE;
      BUG_ON(size == 0 || size % PAGE_SIZE != 0);

      order = get_order(size);
      BUG_ON(order == 0 || order > MAX_ORDER);

      capacity      = (0x1 << order) * PAGE_SIZE;
      log_count_max = (LOG_CACHE_SIZE - LOG_CACHE_HEADER_SIZE) / LOG_SIZE_CONSTRAINT;
#  if LIB_DNL_SYS_TRACE
      printk(KERN_INFO "DNL - kernel mode memory usage - capacity         : %llu\n"
             "DNL - kernel mode memory usage - available        : %u\n"
             "DNL - kernel mode memory usage - maximum log count: %u",
             capacity, size, log_count_max);
#  endif

      buffer = __get_free_pages(GFP_KERNEL, order);
      if (buffer == 0) {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_ERR "DNL - __get_free_pages(GFP_KERNEL, %d) failed", order);
#     endif

         ret = -ECANCELED;
         break;
      }

      spin_lock_init(&dnl_ctx->lock);

      dnl_ctx->ready    = 1;
      dnl_ctx->capacity = order;
      dnl_ctx->size     = size;
      dnl_ctx->buffer   = (char*)buffer;

      _logger_registry = (logger_registry_ptr)dnl_ctx->buffer;
      logger_registry_init();

      _log_cache = (log_cache_ptr)(dnl_ctx->buffer + LOGGER_REGISTRY_SIZE);
      logger_cache_init();

#if (LINUX_VERSION_CODE < KERNEL_VERSION(4, 18, 0))
      getnstimeofday(&_boot_time);
#else
      ktime_get_real_ts64(&_boot_time);
#endif
   } while (false);

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_ctx_init -");
#endif

   return ret;
}

void dnl_ctx_destroy(dnl_ctx_t* dnl_ctx)
{
   ulong buffer = 0;
   ulong order  = 0;

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_ctx_destroy +");
#endif

   do {
      if (unlikely(dnl_ctx == NULL)) {
         break;
      }

      if (dnl_ctx->buffer == NULL) {
         BUG_ON(dnl_ctx->ready);

         break;
      }

      BUG_ON(dnl_ctx->capacity == 0);
      BUG_ON(dnl_ctx->size == 0 || dnl_ctx->size % PAGE_SIZE != 0);

      buffer = (ulong)dnl_ctx->buffer;
      order  = dnl_ctx->capacity;
      free_pages(buffer, order);

      memset(dnl_ctx, 0, sizeof(dnl_ctx_t));
   } while (false);

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_ctx_destroy -");
#endif
}

u16 get_registered_logger_count(void)
{
   BUG_ON(_logger_registry == NULL);

   return _logger_registry->descriptor.registered;
}

u16 get_logger_count_max(void)
{
   BUG_ON(_logger_registry == NULL);

   return _logger_registry->descriptor.capacity;
}

logger_descriptor_ptr get_logger_descriptor(u16 index)
{
   if (index >= get_logger_count_max()) {
      return NULL;
   }

   return LOGGER_DESCRIPTOR(index);
}

logger_ptr get_logger(u16 index)
{
   logger_ptr logger = NULL;

   do {
      logger_descriptor_ptr logger_descriptor = get_logger_descriptor(index);
      if (logger_descriptor == NULL) {
         break;
      }

      if (logger_descriptor->handle == 0) {
         break;
      }

      logger = (logger_ptr)logger_descriptor->address;
      BUG_ON(logger != LOGGER(index));
   } while (false);

   return logger;
}

bool find_logger(const char* name)
{
   bool found = false;
   u16  i     = 0;

   BUG_ON(_logger_registry == NULL);
   BUG_ON(name == NULL);

   for (; i < get_logger_count_max(); ++i) {
      logger_ptr logger = get_logger(i);
      if (logger == NULL) {
         continue;
      }

      if (strcmp(logger->name, name) != 0) {
         continue;
      }

      found = true;
      break;
   }

   return found;
}

u16 find_free_logger_descriptor(void)
{
   u16 i = 0;

   BUG_ON(_logger_registry == NULL);

   for (; i < get_logger_count_max(); ++i) {
      if (LOGGER_DESCRIPTOR(i)->handle != 0) {
         continue;
      }

      return i;
   }

   return (u16)-1;
}

logger_descriptor_ptr find_logger_descriptor(ulong logger_handle)
{
   logger_descriptor_ptr logger_descriptor = NULL;

   BUG_ON(_logger_registry == NULL);

   if (logger_handle == 0) {
      return NULL;
   }

   do {
      u16 index = (u16)(logger_handle & 0xFFFF);
      if (index >= LOGGER_COUNT_MAX) {
         break;
      }

      if (unlikely(LOGGER_DESCRIPTOR(index)->handle != logger_handle)) {
         break;
      }

      logger_descriptor = LOGGER_DESCRIPTOR(index);
      BUG_ON(logger_descriptor->address != LOGGER(index));
   } while (false);

   return logger_descriptor;
}

ulong dnl_register_logger(const char* name, u8** enabled)
{
   ulong                 logger_handle     = 0;
   logger_descriptor_ptr logger_descriptor = NULL;
   logger_ptr            logger            = NULL;

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_register_logger +");
#endif

   BUG_ON(enabled == NULL);

   if (enabled != NULL) {
      *enabled = NULL;
   }

   do {
      size_t length = 0;
      u16    index  = (u16)-1;

      if (get_registered_logger_count() == get_logger_count_max()) {
         break;
      }

      length = strlen(name);
      if (length >= DNL_LOGGER_NAME_LENGTH_MAX) {
         printk(KERN_ERR "DNL - the length limit for logger name is %d", DNL_LOGGER_NAME_LENGTH_MAX - 1);

         break;
      }

      if (find_logger(name)) {
         printk(KERN_WARNING "DNL - logger %s has already been registered", name);

         break;
      }

      index = find_free_logger_descriptor();
      if (index == (u16)-1) {
         break;
      }

      do {
         if (_logger_id == (u16)-1) {
            _logger_id = 0;
         }

         _logger_id += 1;

         logger_handle = (ulong)_logger_id << 16 | index;
         BUG_ON(logger_handle == 0);

         if (find_logger_descriptor(logger_handle) == NULL) {
            break;
         }
      } while (true);

      logger_descriptor = LOGGER_DESCRIPTOR(index);
      logger_descriptor->handle = logger_handle;

      logger = (logger_ptr)logger_descriptor->address;
      BUG_ON(logger == NULL);

      memset(logger, 0, sizeof(logger_t));

      memcpy(logger->name, name, length);

      length = strlen(DNL_LOGGER_DEFAULT_LOGGING_DIRECTORY);
      BUG_ON(length >= DNL_LOGGING_DIRECTORY_LENGTH_MAX);

      memcpy(logger->logging.directory, DNL_LOGGER_DEFAULT_LOGGING_DIRECTORY, length);

      logger->enabled                                = DNL_LOGGER_DEFAULT_ENABLED;
      logger->debugging.enabled                      = DNL_LOGGER_DEFAULT_DEBUGGING_ENABLED;
      logger->debugging.filter                       = DNL_LOGGER_DEFAULT_DEBUGGING_FILTER;
      logger->logging.enabled                        = DNL_LOGGER_DEFAULT_LOGGING_ENABLED;
      logger->logging.filter                         = DNL_LOGGER_DEFAULT_LOGGING_FILTER;
      logger->logging.file.size                      = DNL_LOGGER_DEFAULT_LOGGING_FILE_SIZE_CONSTRAINT;
      logger->logging.rotation.boundary              = DNL_LOGGER_DEFAULT_LOGGING_ROTATION_BOUNDARY;
      logger->logging.rotation.action                = DNL_LOGGER_DEFAULT_LOGGING_ROTATION_ACTION;
      logger->remoting.enabled                       = DNL_LOGGER_DEFAULT_REMOTING_ENABLED;
      logger->remoting.filter                        = DNL_LOGGER_DEFAULT_REMOTING_FILTER;
      logger->remoting.transport.compression_enabled = DNL_LOGGER_DEFAULT_REMOTING_TRANSPORT_COMPRESSION_ENABLED;

      _logger_registry->descriptor.registered += 1;
      _logger_registry->descriptor.dirty       = 1;

      if (enabled != NULL) {
         *enabled = &logger->enabled;
      }

#  if LIB_DNL_SYS_TRACE
      printk(KERN_INFO "DNL kernel mode logger registery - registered: %s [0x%08x]\n"
             "DNL kernel mode logger registery - state     : %u",
             name, (u32)logger_handle, _logger_registry->descriptor.dirty);
#  endif
   } while (false);

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_register_logger -");
#endif

   return logger_handle;
}

void dnl_unregister_logger(ulong logger_handle)
{
   logger_descriptor_ptr logger_descriptor = NULL;
   logger_ptr            logger            = NULL;

   char name[DNL_LOGGER_NAME_LENGTH_MAX];

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_unregister_logger +");
#endif

   do {
      logger_descriptor = find_logger_descriptor(logger_handle);
      if (logger_descriptor == NULL) {
         break;
      }

      BUG_ON(_logger_registry->descriptor.registered == 0);

      logger = (logger_ptr)logger_descriptor->address;
      BUG_ON(logger == NULL);

      memset(name, 0, DNL_LOGGER_NAME_LENGTH_MAX);
      memcpy(name, logger->name, DNL_LOGGER_NAME_LENGTH_MAX);

      memset(logger, 0, sizeof(logger_t));

      logger_descriptor->handle = 0;

      _logger_registry->descriptor.registered -= 1;
      _logger_registry->descriptor.dirty       = 1;

#  if LIB_DNL_SYS_TRACE
      printk(KERN_INFO "DNL kernel mode logger registery - unregistered: %s [0x%08x]\n"
             "DNL kernel mode logger registery - state       : %u",
             name, (u32)logger_handle, _logger_registry->descriptor.dirty);
#  endif
   } while (false);

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_unregister_logger -");
#endif
}

u64 get_timestamp(void)
{
#if (LINUX_VERSION_CODE < KERNEL_VERSION(4, 18, 0))
   struct timespec ts;
#else
   struct timespec64 ts;
#endif

   u32 s  = 0;
   u32 us = 0;

#if (LINUX_VERSION_CODE < KERNEL_VERSION(4, 18, 0))
   getnstimeofday(&ts);
#else
   ktime_get_real_ts64(&ts);
#endif

   WARN_ON(ts.tv_sec < _boot_time.tv_sec);
   ts.tv_sec -= _boot_time.tv_sec;
   WARN_ON(ts.tv_sec < 0);
   WARN_ON(ts.tv_sec > (u32)-1);

   WARN_ON(ts.tv_nsec >= 1000000000);
   ts.tv_nsec -= _boot_time.tv_nsec;

   if (ts.tv_nsec < 0) {
      WARN_ON(ts.tv_sec <= 0);
      ts.tv_sec -= 1;

      ts.tv_nsec += 1000000000;
   }

   s  = ts.tv_sec;
   us = ts.tv_nsec / 1000;

   return (u64)us << 32 | s;
}

u16 get_number_length(u32 number)
{
   u16 length = 0;

   while (number > 0) {
      number /= 10;
      length += 1;
   }

   return length;
}

void print_log(logger_ptr logger, u64 timestamp, u32 log_level, const char* log_message)
{
   u32    days         = 0;
   u32    hours        = 0;
   u32    minutes      = 0;
   u32    seconds      = 0;
   u32    microseconds = 0;
   size_t name_size    = 0;
   size_t message_size = 0;
   u32    size         = 0;
   char   level        = 0;
   char*  message      = NULL;
   int    count        = 0;

   BUG_ON(logger == NULL);
   BUG_ON(!logger->debugging.enabled);
   BUG_ON(logger->debugging.filter < log_level);
   BUG_ON(timestamp == 0);
   BUG_ON(log_message == NULL);

   seconds      = (u32)(timestamp & 0xFFFFFFFF);
   microseconds = (u32)(timestamp >> 32 & 0xFFFFFFFF);

   days = seconds / 86400;
   seconds %= 86400;

   hours = seconds / 3600;
   seconds %= 3600;

   minutes = seconds / 60;
   seconds %= 60;

   name_size = strlen(logger->name);
   BUG_ON(name_size == 0);

   message_size = strlen(log_message);
   BUG_ON(message_size == 0);

   BUG_ON(get_number_length(days) + 23 > 28);
   size += 28 + name_size + 4 + message_size;
   if (size >= DBG_MESSAGE_LENGTH_MAX) {
#  if LIB_DNL_SYS_TRACE
      printk(KERN_ERR "DNL - the kernel debugger can only transmit %u bytes of information at once",
             DBG_MESSAGE_LENGTH_MAX);
#  endif

      return;
   }

   switch (log_level) {
   case DNL_LOG_LEVEL_FATAL:
      level = 'F';
      break;
   case DNL_LOG_LEVEL_ERROR:
      level = 'E';
      break;
   case DNL_LOG_LEVEL_WARNING:
      level = 'W';
      break;
   case DNL_LOG_LEVEL_TRACE:
      level = 'T';
      break;
   default:
      level = 'D';
      break;
   }

   message = (char*)kmalloc(size + 1, GFP_KERNEL);
   if (message == NULL) {
#  if LIB_DNL_SYS_TRACE
      printk(KERN_ERR "DNL - kmalloc(%u) failed", size + 1);
#  endif

      return;
   }

   memset(message, 0, size + 1);

   count = snprintf(message, size + 1, "[%05u] %02u:%02u:%02u.%06u [%c] %s >> %s", days, hours, minutes,
                    seconds, microseconds, level, logger->name, log_message);
   BUG_ON(count != size);

   switch (log_level) {
   case DNL_LOG_LEVEL_FATAL:
      printk(KERN_CRIT "%s", message);
      break;
   case DNL_LOG_LEVEL_ERROR:
      printk(KERN_ERR "%s", message);
      break;
   case DNL_LOG_LEVEL_WARNING:
      printk(KERN_WARNING "%s", message);
      break;
   default:
      printk(KERN_INFO "%s", message);
      break;
   }

   kfree(message);
}

char* serialize_log(logger_ptr logger, u64 timestamp, u32 log_level, const char* log_message, u32* size)
{
   u16    name_size    = 0;
   u16    message_size = 0;
   u32    data_size    = 0;
   char*  data         = NULL;
   size_t offset       = 0;

   BUG_ON(_log_cache == NULL);
   BUG_ON(_log_cache->size.cache.unit == 0);
   BUG_ON(logger == NULL);
   BUG_ON(!logger->logging.enabled && !logger->remoting.enabled);
   BUG_ON(logger->logging.filter < log_level && logger->remoting.filter < log_level);
   BUG_ON(timestamp == 0);
   BUG_ON(log_message == NULL);

   if (size != NULL) {
      *size = 0;
   }

   name_size = strlen(logger->name);
   BUG_ON(name_size == 0);
   BUG_ON(name_size >= DNL_LOGGER_NAME_LENGTH_MAX);

   message_size = strlen(log_message);
   BUG_ON(message_size == 0);
   BUG_ON(message_size >= DNL_LOG_MESSAGE_LENGTH_MAX);

   data_size = sizeof(u16)                + /* Size        */
               sizeof(u8)                 + /* Version     */
               sizeof(u8)                 + /* Log type    */
               sizeof(u64)                + /* Timestamp   */
               sizeof(u16) + name_size    + /* Logger      */
               sizeof(u32)                + /* Log level   */
               sizeof(u16) + message_size + /* Log message */
               sizeof(u16);                 /* Diagnostics */
   if (data_size >= _log_cache->size.cache.unit) {
#  if LIB_DNL_SYS_TRACE
      printk(KERN_ERR "DNL - log (size: %u) blocked\n"
             "      log size constraint : %u",
             data_size, _log_cache->size.cache.unit - 1);
#  endif

      return NULL;
   }

   data = (char*)kmalloc(data_size, GFP_KERNEL);
   if (data == NULL) {
#  if LIB_DNL_SYS_TRACE
      printk(KERN_ERR "DNL - kmalloc(%u) failed", data_size);
#  endif

      return NULL;
   }

   memset(data, 0, data_size);

   *(u16*)(data + offset) = (u16)(data_size - sizeof(u16));

   offset += sizeof(u16);
   *(u8*)(data + offset) = STRUCTURED_LOG_VERSION;

   offset += sizeof(u8);
   *(u8*)(data + offset) = 0x10; /* Chronometer */

   offset += sizeof(u8);
   memcpy(data + offset, &timestamp, sizeof(u64));

   offset += sizeof(u64);
   *(u16*)(data + offset) = name_size;

   offset += sizeof(u16);
   memcpy(data + offset, logger->name, name_size);

   offset += name_size;
   *(u32*)(data + offset) = log_level;

   offset += sizeof(u32);
   *(u16*)(data + offset) = (u16)message_size;

   offset += sizeof(u16);
   memcpy(data + offset, log_message, message_size);

   offset += message_size;
   BUG_ON(*(u16*)(data + offset) != 0);

   offset += sizeof(u16);
   BUG_ON(offset != data_size);

   if (size != NULL) {
      *size = data_size;
   }

   return data;
}

void write_log_cache(const char* log, u32 log_size)
{
   char* cache      = NULL;
   u32   cache_size = 0;
   u32   wp         = 0;
   u32   rp         = 0;
   u32   writable   = 0;
   char* flag       = NULL;

   BUG_ON(_log_cache == NULL);
   BUG_ON(_log_cache->size.cache.unit == 0);
   BUG_ON(log == NULL);
   BUG_ON(log_size == 0);
   BUG_ON(log_size >= _log_cache->size.cache.unit);

   spin_lock(&dnl_ctx.lock);

   cache      = LOG_CACHE_BASE;
   cache_size = _log_cache->size.cache.capacity;
   wp         = _log_cache->wp;
   rp         = _log_cache->rp;
   BUG_ON(wp >= cache_size);
   BUG_ON(rp >= cache_size);

   writable = wp >= rp ? cache_size - wp + rp : rp - wp;
   BUG_ON(writable < _log_cache->size.cache.unit);
   BUG_ON(writable % _log_cache->size.cache.unit != 0);

   flag = cache + wp;

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL kernel mode log cache - WP [Before]  : %u\n"
          "DNL kernel mode log cache - wriable      : %u\n"
          "DNL kernel mode log cache - size to write: %u",
          wp, writable, log_size);
#endif

   *flag = 0; /* Reset the Data Ready flag */

   _log_cache->wp = (wp + _log_cache->size.cache.unit) % cache_size;

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL kernel mode log cache - WP [After]: %u", _log_cache->wp);
#endif

   spin_unlock(&dnl_ctx.lock);

   wp += 1;
   wp %= cache_size;

   if (wp + (_log_cache->size.cache.unit - 1) <= cache_size) {
      memset(cache + wp, 0xFE, (_log_cache->size.cache.unit - 1));
   }
   else {
      u32 tmp = cache_size - wp;

      memset(cache + wp, 0xFE, tmp);
      memset(cache, 0xFE, (_log_cache->size.cache.unit - 1) - tmp);
   }

   if (wp + log_size <= cache_size) {
      memcpy(cache + wp, log, log_size);
   }
   else {
      u32 tmp = cache_size - wp;

      memcpy(cache + wp, log, tmp);
      memcpy(cache, log + tmp, log_size - tmp);
   }

   *flag = 1; /* Set the Data Ready flag */
}

int dnl_print(ulong logger_handle, u32 log_level, const char* log_message, ...)
{
   int ret = 0;

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_print +");
#endif

   do {
      logger_descriptor_ptr logger_descriptor = NULL;
      logger_ptr            logger            = NULL;
      char*                 message           = NULL;
      int                   message_size      = 0;
      bool                  succeed           = false;

      if (log_level > DNL_LOG_LEVEL_DEBUG) {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_ERR "DNL - invalid log level : %u", log_level);
#     endif

         ret = -EINVAL;
         break;
      }

      if (log_message == NULL || strlen(log_message) == 0) {
         break;
      }

      logger_descriptor = find_logger_descriptor(logger_handle);
      if (logger_descriptor == NULL) {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_ERR "DNL - invalid logger handle: 0x%08x", (u32)logger_handle);
#     endif

         ret = -EINVAL;
         break;
      }

      logger = (logger_ptr)logger_descriptor->address;
      if (logger->enabled == 0) {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_WARNING "DNL - %s disabled\n", logger->name);
#     endif

         break;
      }

      if ((!logger->debugging.enabled || log_level > logger->debugging.filter) &&
          (!logger->logging.enabled   || log_level > logger->logging.filter)   &&
          (!logger->remoting.enabled  || log_level > logger->remoting.filter)) {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_WARNING "DNL - log (level: %u) blocked by %s\n"
                "      debugging mode enabled : %u, filter : %u\n"
                "      logging mode enabled   : %u, filter : %u\n"
                "      remoting mode enabled  : %u, filter : %u",
                log_level, logger->name, logger->debugging.enabled, logger->debugging.filter,
                logger->logging.enabled, logger->logging.filter, logger->remoting.enabled,
                logger->remoting.filter);
#     endif

         break;
      }

      message = (char*)kmalloc(DNL_LOG_MESSAGE_LENGTH_MAX, GFP_KERNEL);
      if (message == NULL) {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_ERR "DNL - kmalloc(%u) failed", DNL_LOG_MESSAGE_LENGTH_MAX);
#     endif

         ret = -ENOMEM;
         break;
      }

      memset(message, 0, DNL_LOG_MESSAGE_LENGTH_MAX);

      do {
         va_list arguments;
         va_start(arguments, log_message);

         message_size = vsnprintf(message, DNL_LOG_MESSAGE_LENGTH_MAX, log_message, arguments);

         va_end(arguments);

         if (message_size <= 0) {
#        if LIB_DNL_SYS_TRACE
            printk(KERN_ERR "DNL - vsnprintf() failed");
#        endif

            break;
         }

         if (message_size >= DNL_LOG_MESSAGE_LENGTH_MAX) {
#        if LIB_DNL_SYS_TRACE
            printk(KERN_ERR "DNL - the maximum length of log message is limited to %u bytes",
                   DNL_LOG_MESSAGE_LENGTH_MAX - 1);
#        endif

            break;
         }

#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - new log\n"
                "    %s -> %s",
                logger->name, message);
#     endif

         succeed = true;
      } while (false);

      if (succeed) {
         u64 timestamp = get_timestamp();

         if (logger->debugging.enabled && log_level <= logger->debugging.filter) {
            print_log(logger, timestamp, log_level, message);
         }

         if ((logger->logging.enabled  && log_level <= logger->logging.filter)  ||
             (logger->remoting.enabled && log_level <= logger->remoting.filter)) {
            u32 log_size = 0;
            char* log = serialize_log(logger, timestamp, log_level, message, &log_size);
            if (log != NULL) {
               BUG_ON(log_size == 0);

               write_log_cache(log, log_size);

               kfree(log);
            }
            else {
               ret = -ENOMEM;
            }
         }
      }
      else {
         ret = -EINVAL;
      }

      kfree(message);
   } while (false);

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_print -");
#endif

   return ret;
}

void print_log_ex(logger_ptr  logger,
                  u64         timestamp,
                  u32         log_level,
                  const char* log_message,
                  const char* file,
                  u32         line,
                  const char* function)
{
   u32    days          = 0;
   u32    hours         = 0;
   u32    minutes       = 0;
   u32    seconds       = 0;
   u32    microseconds  = 0;
   size_t name_size     = 0;
   size_t message_size  = 0;
   size_t file_size     = 0;
   size_t line_size     = 0;
   size_t function_size = 0;
   u32    size          = 0;
   char   level         = 0;
   char*  message       = NULL;
   int    count         = 0;

   BUG_ON(logger == NULL);
   BUG_ON(!logger->debugging.enabled);
   BUG_ON(logger->debugging.filter < log_level);
   BUG_ON(timestamp == 0);
   BUG_ON(log_message == NULL);
   BUG_ON(file == NULL);
   BUG_ON(function == NULL);

   seconds      = (u32)(timestamp & 0xFFFFFFFF);
   microseconds = (u32)(timestamp >> 32 & 0xFFFFFFFF);

   days = seconds / 86400;
   seconds %= 86400;

   hours = seconds / 3600;
   seconds %= 3600;

   minutes = seconds / 60;
   seconds %= 60;

   name_size = strlen(logger->name);
   BUG_ON(name_size == 0);

   message_size = strlen(log_message);
   BUG_ON(message_size == 0);

   file_size = strlen(file);
   BUG_ON(file_size == 0);
   BUG_ON(file_size >= FILE_NAME_LENGTH_MAX);

   line_size = get_number_length(line);
   BUG_ON(line_size == 0);

   function_size = strlen(function);
   BUG_ON(function_size == 0);
   BUG_ON(function_size >= FUNCTION_NAME_LENGTH_MAX);

   BUG_ON(get_number_length(days) + 23 > 28);
   size = 28 + name_size + 4 + message_size + 3 + function_size + 1 + file_size + 1 + line_size + 1;
   if (size >= DBG_MESSAGE_LENGTH_MAX) {
#  if LIB_DNL_SYS_TRACE
      printk(KERN_ERR "DNL - the kernel debugger can only transmit %u bytes of information at once",
             DBG_MESSAGE_LENGTH_MAX);
#  endif

      return;
   }

   switch (log_level) {
   case DNL_LOG_LEVEL_FATAL:
      level = 'F';
      break;
   case DNL_LOG_LEVEL_ERROR:
      level = 'E';
      break;
   case DNL_LOG_LEVEL_WARNING:
      level = 'W';
      break;
   case DNL_LOG_LEVEL_TRACE:
      level = 'T';
      break;
   default:
      level = 'D';
      break;
   }

   message = (char*)kmalloc(size + 1, GFP_KERNEL);
   if (message == NULL) {
#  if LIB_DNL_SYS_TRACE
      printk(KERN_ERR "DNL - kmalloc(%u) failed", size + 1);
#  endif

      return;
   }

   memset(message, 0, size + 1);

   count = snprintf(message, size + 1, "[%05u] %02u:%02u:%02u.%06u [%c] %s >> %s @ %s(%u):%s", days, hours,
                    minutes, seconds, microseconds, level, logger->name, log_message, file, line, function);
   BUG_ON(count != size);

   switch (log_level) {
   case DNL_LOG_LEVEL_FATAL:
      printk(KERN_CRIT "%s", message);
      break;
   case DNL_LOG_LEVEL_ERROR:
      printk(KERN_ERR "%s", message);
      break;
   case DNL_LOG_LEVEL_WARNING:
      printk(KERN_WARNING "%s", message);
      break;
   default:
      printk(KERN_INFO "%s", message);
      break;
   }

   kfree(message);
}

char* serialize_log_ex(logger_ptr  logger,
                       u64         timestamp,
                       u32         log_level,
                       const char* log_message,
                       const char* file,
                       u32         line,
                       const char* function,
                       u32*        size)
{
   u16    name_size     = 0;
   u16    message_size  = 0;
   u16    file_size     = 0;
   u16    function_size = 0;
   u32    data_size     = 0;
   char*  data          = NULL;
   size_t offset        = 0;

   BUG_ON(_log_cache == NULL);
   BUG_ON(_log_cache->size.cache.unit == 0);
   BUG_ON(logger == NULL);
   BUG_ON(!logger->logging.enabled && !logger->remoting.enabled);
   BUG_ON(logger->logging.filter < log_level && logger->remoting.filter < log_level);
   BUG_ON(timestamp == 0);
   BUG_ON(log_message == NULL);
   BUG_ON(file == NULL);
   BUG_ON(function == NULL);

   if (size != NULL) {
      *size = 0;
   }

   name_size = strlen(logger->name);
   BUG_ON(name_size == 0);
   BUG_ON(name_size >= DNL_LOGGER_NAME_LENGTH_MAX);

   message_size = strlen(log_message);
   BUG_ON(message_size == 0);
   BUG_ON(message_size >= DNL_LOG_MESSAGE_LENGTH_MAX);

   file_size = strlen(file);
   BUG_ON(file_size == 0);
   BUG_ON(file_size >= FILE_NAME_LENGTH_MAX);

   function_size = strlen(function);
   BUG_ON(function_size == 0);
   BUG_ON(function_size >= FUNCTION_NAME_LENGTH_MAX);

   data_size = sizeof(u16)                + /* Size                            */
               sizeof(u8)                 + /* Version                         */
               sizeof(u8)                 + /* Log type                        */
               sizeof(u64)                + /* Timestamp                       */
               sizeof(u16) + name_size    + /* Logger                          */
               sizeof(u32)                + /* Log level                       */
               sizeof(u16) + message_size + /* Log message                     */
               sizeof(u16)                + /* Diagnostics                     */
               sizeof(u16) + file_size    + /* DNL_BUILDIN_DIAGNOSTIC_FILE     */
               sizeof(u32)                + /* DNL_BUILDIN_DIAGNOSTIC_LINE     */
               sizeof(u16) + function_size; /* DNL_BUILDIN_DIAGNOSTIC_FUNCTION */
   if (data_size >= _log_cache->size.cache.unit) {
#  if LIB_DNL_SYS_TRACE
      printk(KERN_ERR "DNL - log (size: %u) blocked\n"
             "      log size constraint : %u",
             data_size, _log_cache->size.cache.unit - 1);
#  endif

      return NULL;
   }

   data = (char*)kmalloc(data_size, GFP_KERNEL);
   if (data == NULL) {
#  if LIB_DNL_SYS_TRACE
      printk(KERN_ERR "DNL - kmalloc(%u) failed", data_size);
#  endif

      return NULL;
   }

   memset(data, 0, data_size);

   *(u16*)(data + offset) = (u16)(data_size - sizeof(u16));

   offset += sizeof(u16);
   *(u8*)(data + offset) = STRUCTURED_LOG_VERSION;

   offset += sizeof(u8);
   *(u8*)(data + offset) = 0x10; /* Chronometer */

   offset += sizeof(u8);
   memcpy(data + offset, &timestamp, sizeof(u64));

   offset += sizeof(u64);
   *(u16*)(data + offset) = name_size;

   offset += sizeof(u16);
   memcpy(data + offset, logger->name, name_size);

   offset += name_size;
   *(u32*)(data + offset) = log_level;

   offset += sizeof(u32);
   *(u16*)(data + offset) = (u16)message_size;

   offset += sizeof(u16);
   memcpy(data + offset, log_message, message_size);

   offset += message_size;
   *(u16*)(data + offset) = 3;

   offset += sizeof(u16);
   *(u16*)(data + offset) = file_size;

   offset += sizeof(u16);
   memcpy(data + offset, file, file_size);

   offset += file_size;
   *(u32*)(data + offset) = line;

   offset += sizeof(u32);
   *(u16*)(data + offset) = (u16)function_size;

   offset += sizeof(u16);
   memcpy(data + offset, function, function_size);

   offset += function_size;
   BUG_ON(offset != data_size);

   if (size != NULL) {
      *size = data_size;
   }

   return data;
}

int dnl_print_ex(ulong       logger_handle,
                 u32         log_level,
                 const char* file,
                 u32         line,
                 const char* function,
                 const char* log_message,
                 ...)
{
   int ret = 0;

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_print_ex +");
#endif

   do {
      logger_descriptor_ptr logger_descriptor   = NULL;
      logger_ptr            logger              = NULL;
      char*                 message             = NULL;
      bool                  succeed             = false;
      int                   message_size        = 0;
      u32                   blocking_list_index = 0;
      bool                  blocked             = false;
      char*                 tmp                 = NULL;

      if (log_level > DNL_LOG_LEVEL_DEBUG) {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_ERR "DNL - invalid log level : %u", log_level);
#     endif

         ret = -EINVAL;
         break;
      }

      if (log_message == NULL || strlen(log_message) == 0) {
         break;
      }

      logger_descriptor = find_logger_descriptor(logger_handle);
      if (logger_descriptor == NULL) {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_ERR "DNL - invalid logger handle: 0x%08x", (u32)logger_handle);
#     endif

         ret = -EINVAL;
         break;
      }

      logger = (logger_ptr)logger_descriptor->address;
      if (logger->enabled == 0) {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_WARNING "DNL - %s disabled\n", logger->name);
#     endif

         break;
      }

      if ((!logger->debugging.enabled || log_level > logger->debugging.filter) &&
          (!logger->logging.enabled   || log_level > logger->logging.filter)   &&
          (!logger->remoting.enabled  || log_level > logger->remoting.filter)) {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_WARNING "DNL - log (level: %u) blocked by %s\n"
                "      debugging mode enabled : %u, filter : %u\n"
                "      logging mode enabled   : %u, filter : %u\n"
                "      remoting mode enabled  : %u, filter : %u",
                log_level, logger->name, logger->debugging.enabled, logger->debugging.filter,
                logger->logging.enabled, logger->logging.filter, logger->remoting.enabled,
                logger->remoting.filter);
#     endif

         break;
      }

      for (; blocking_list_index < DNL_LOGGER_BLOCKING_LIST_SIZE_MAX; ++blocking_list_index) {
         if (strlen(logger->blocking_list[blocking_list_index].file) == 0) {
            continue;
         }

         if (strlen(file) < strlen(logger->blocking_list[blocking_list_index].file)) {
            continue;
         }

         tmp = strstr(file, logger->blocking_list[blocking_list_index].file);
         if (tmp == NULL) {
            continue;
         }

         if (strcmp(tmp, logger->blocking_list[blocking_list_index].file) != 0) {
            continue;
         }

         blocked = logger->blocking_list[blocking_list_index].line == line;
         break;
      }

      if (blocked) {
         break;
      }

      message = (char*)kmalloc(DNL_LOG_MESSAGE_LENGTH_MAX, GFP_KERNEL);
      if (message == NULL) {
#     if LIB_DNL_SYS_TRACE
         printk(KERN_ERR "DNL - kmalloc(%u) failed", DNL_LOG_MESSAGE_LENGTH_MAX);
#     endif

         ret = -ENOMEM;
         break;
      }

      memset(message, 0, DNL_LOG_MESSAGE_LENGTH_MAX);

      do {
         va_list arguments;
         va_start(arguments, log_message);

         message_size = vsnprintf(message, DNL_LOG_MESSAGE_LENGTH_MAX, log_message, arguments);

         va_end(arguments);

         if (message_size <= 0) {
#        if LIB_DNL_SYS_TRACE
            printk(KERN_ERR "DNL - vsnprintf() failed");
#        endif

            break;
         }

         if (message_size >= DNL_LOG_MESSAGE_LENGTH_MAX) {
#        if LIB_DNL_SYS_TRACE
            printk(KERN_ERR "DNL - the maximum length of log message is limited to %u bytes",
                   DNL_LOG_MESSAGE_LENGTH_MAX - 1);
#        endif

            break;
         }

#     if LIB_DNL_SYS_TRACE
         printk(KERN_INFO "DNL - new log\n"
                "    %s -> %s",
                logger->name, message);
#     endif

         succeed = true;
      } while (false);

      if (succeed) {
         u64 timestamp = get_timestamp();

         if (logger->debugging.enabled && log_level <= logger->debugging.filter) {
            print_log_ex(logger, timestamp, log_level, message, file, line, function);
         }

         if ((logger->logging.enabled  && log_level <= logger->logging.filter)  ||
             (logger->remoting.enabled && log_level <= logger->remoting.filter)) {
            u32 log_size = 0;
            char* log = serialize_log_ex(logger, timestamp, log_level, message, file, line, function,
                                         &log_size);
            if (log != NULL) {
               BUG_ON(log_size == 0);

               write_log_cache(log, log_size);

               kfree(log);
            }
            else {
               ret = -ENOMEM;
            }
         }
      }
      else {
         ret = -EINVAL;
      }

      kfree(message);
   } while (false);

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_print_ex -");
#endif

   return ret;
}

void dnl_test_logger_registry(u16 id)
{
   logger_descriptor_ptr logger_descriptor = NULL;
   logger_ptr            logger            = NULL;
   size_t                length            = 0;

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_test_logger_registry +");
#endif

   BUG_ON(_logger_registry == NULL);
   BUG_ON(id == 0);

   logger_descriptor = LOGGER_DESCRIPTOR(0);
   logger            = LOGGER(0);
   BUG_ON(logger_descriptor->address != logger);

   logger_descriptor->handle = (ulong)id << 16 | 0;

   memset(logger, 0, sizeof(logger_t));

   memcpy(logger->name, "TEST", 4);

   length = strlen(DNL_LOGGER_DEFAULT_LOGGING_DIRECTORY);
   BUG_ON(length >= DNL_LOGGING_DIRECTORY_LENGTH_MAX);
   memcpy(logger->logging.directory, DNL_LOGGER_DEFAULT_LOGGING_DIRECTORY, length);

   logger->enabled                                = 1;
   logger->debugging.enabled                      = DNL_LOGGER_DEFAULT_DEBUGGING_ENABLED;
   logger->debugging.filter                       = DNL_LOGGER_DEFAULT_DEBUGGING_FILTER;
   logger->logging.enabled                        = DNL_LOGGER_DEFAULT_LOGGING_ENABLED;
   logger->logging.filter                         = DNL_LOGGER_DEFAULT_LOGGING_FILTER;
   logger->logging.file.size                      = DNL_LOGGER_DEFAULT_LOGGING_FILE_SIZE_CONSTRAINT;
   logger->logging.rotation.boundary              = DNL_LOGGER_DEFAULT_LOGGING_ROTATION_BOUNDARY;
   logger->logging.rotation.action                = DNL_LOGGER_DEFAULT_LOGGING_ROTATION_ACTION;
   logger->remoting.enabled                       = DNL_LOGGER_DEFAULT_REMOTING_ENABLED;
   logger->remoting.filter                        = DNL_LOGGER_DEFAULT_REMOTING_FILTER;
   logger->remoting.transport.compression_enabled = DNL_LOGGER_DEFAULT_REMOTING_TRANSPORT_COMPRESSION_ENABLED;

   _logger_registry->descriptor.registered = 1;
   _logger_registry->descriptor.dirty      = 1;

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_test_logger_registry -");
#endif
}

void dnl_test_log_cache(u32 data)
{
   char* cache      = NULL;
   u32   cache_size = 0;
   u32   wp         = 0;
   u32   rp         = 0;
   u32   data_size  = 0;
   u32   writable   = 0;

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_test_log_cache +");
#endif

   BUG_ON(_log_cache == NULL);

   cache      = LOG_CACHE_BASE;
   cache_size = _log_cache->size.cache.capacity;
   wp         = _log_cache->wp;
   rp         = _log_cache->rp;
   data_size  = sizeof(u32);
   writable   = wp >= rp ? cache_size - wp + rp : rp - wp;

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL kernel mode log cache - WP [Before]  : %u\n"
          "DNL kernel mode log cache - wriable      : %u\n"
          "DNL kernel mode log cache - size to write: %u",
          wp, writable, data_size);
#endif

   if (wp + data_size <= cache_size) {
      memcpy(cache + wp, &data, data_size);
   }
   else {
      u32 tmp = cache_size - wp;

      memcpy(cache + wp, &data, tmp);
      memcpy(cache, &data + tmp, data_size - tmp);
   }

   _log_cache->wp = (wp + data_size) % cache_size;

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL kernel mode log cache - WP [After]: %u", _log_cache->wp);
#endif

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_test_log_cache -");
#endif
}

static ulong _dnl_test_logger = 0;

void dnl_test_register_logger(void)
{
   logger_descriptor_ptr logger_descriptor = NULL;
   logger_ptr            logger            = NULL;
   u8*                   logger_enabled    = NULL;

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_test_register_logger +");
#endif

   if (_dnl_test_logger == 0) {
      _dnl_test_logger = dnl_register_logger("DNL-Testing", &logger_enabled);
      BUG_ON(_dnl_test_logger == 0);
      BUG_ON(logger_enabled == NULL);

      *logger_enabled = 1;
   }

   if (_dnl_test_logger != 0) {
      logger_descriptor = find_logger_descriptor(_dnl_test_logger);
      BUG_ON(logger_descriptor == NULL);

      logger = (logger_ptr)logger_descriptor->address;
      BUG_ON(!logger_enabled);
      BUG_ON(strlen(logger->blocking_list[0].file) != 0);
      BUG_ON(logger->blocking_list[0].line != 0);

      strcpy(logger->blocking_list[0].file, "dnl.c");
      logger->blocking_list[0].line = 1782;
   }

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_test_register_logger -");
#endif
}

#if (LINUX_VERSION_CODE < KERNEL_VERSION(4, 18, 0))
u32 get_elapsed(const struct timespec* start, const struct timespec* stop)
#else
s32 get_elapsed(const struct timespec64* start, const struct timespec64* stop)
#endif
{
    s32 sec  = 0;
    s32 nsec = 0;

    BUG_ON(start == NULL);
    BUG_ON(stop == NULL);

    sec = stop->tv_sec - start->tv_sec;
    BUG_ON(sec < 0);

    nsec = stop->tv_nsec - start->tv_nsec;
    if (nsec < 0) {
        BUG_ON(sec == 0);

        nsec += 1000000000;
        sec  -= 1;
    }

    return nsec;
}

void dnl_test_write_log(u32 flag)
{
#if (LINUX_VERSION_CODE < KERNEL_VERSION(4, 18, 0))
   struct timespec start, tmp, stop;
#else
   struct timespec64 start, tmp, stop;
#endif

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_test_write_log +");
#endif

   if (_dnl_test_logger != 0) {
      if (flag % 2 == 0) {
#     if (LINUX_VERSION_CODE < KERNEL_VERSION(4, 18, 0))
         getnstimeofday(&start);
#     else
         ktime_get_real_ts64(&start);
#     endif

         dnl_print_ex(_dnl_test_logger, DNL_LOG_LEVEL_ERROR, "dnl.c", 1782, "dnl_test_write_log",
                      "Testing log %u", flag);

#     if (LINUX_VERSION_CODE < KERNEL_VERSION(4, 18, 0))
         getnstimeofday(&tmp);
#     else
         ktime_get_real_ts64(&tmp);
#     endif

         dnl_print_ex(_dnl_test_logger, DNL_LOG_LEVEL_DEBUG, "dnl.c", 1791, "dnl_test_write_log",
                      "Testing log %u", flag);

#     if (LINUX_VERSION_CODE < KERNEL_VERSION(4, 18, 0))
         getnstimeofday(&stop);
#     else
         ktime_get_real_ts64(&stop);
#     endif

        printk(KERN_INFO "Blocked - %d ns", get_elapsed(&start, &tmp));
        printk(KERN_INFO "Filtered - %d ns", get_elapsed(&tmp, &stop));
      }
      else {
#     if (LINUX_VERSION_CODE < KERNEL_VERSION(4, 18, 0))
         getnstimeofday(&start);
#     else
         ktime_get_real_ts64(&start);
#     endif

         dnl_print_ex(_dnl_test_logger, DNL_LOG_LEVEL_ERROR, "dnl.c", 1810, "dnl_test_write_log",
                      "Testing log %u", flag);

#     if (LINUX_VERSION_CODE < KERNEL_VERSION(4, 18, 0))
         getnstimeofday(&stop);
#     else
         ktime_get_real_ts64(&stop);
#     endif

        printk(KERN_INFO "Passed - %d ns", get_elapsed(&start, &stop));
      }
   }

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_test_write_log -");
#endif
}

void dnl_test_unregister_logger(void)
{
#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_test_unregister_logger +");
#endif

   if (_dnl_test_logger != 0) {
      dnl_unregister_logger(_dnl_test_logger);

      _dnl_test_logger = 0;
   }

#if LIB_DNL_SYS_TRACE
   printk(KERN_INFO "DNL - dnl_test_unregister_logger -");
#endif
}

EXPORT_SYMBOL_GPL(dnl_register_logger);
EXPORT_SYMBOL_GPL(dnl_unregister_logger);
EXPORT_SYMBOL_GPL(dnl_print);
EXPORT_SYMBOL_GPL(dnl_print_ex);
