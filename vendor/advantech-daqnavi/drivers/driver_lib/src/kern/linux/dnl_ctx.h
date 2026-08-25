#ifndef DNL_CTX_H_INCLUDED
#define DNL_CTX_H_INCLUDED

#include <linux/spinlock.h>

typedef struct dnl_ctx
{
    ulong      ready;
    spinlock_t lock;
    ulong      capacity;
    ulong      size;
    char*      buffer;
} dnl_ctx_t, *dnl_ctx_ptr;

int  dnl_ctx_init(dnl_ctx_ptr);
void dnl_ctx_destroy(dnl_ctx_ptr);

u32 dnl_get_logger_registry_size(void);
u32 dnl_get_log_cache_size(void);

void dnl_test_logger_registry(u16);
void dnl_test_log_cache(u32);
void dnl_test_register_logger(void);
void dnl_test_write_log(u32);
void dnl_test_unregister_logger(void);

extern dnl_ctx_t dnl_ctx;

#endif /* DNL_CTX_H_INCLUDED */
