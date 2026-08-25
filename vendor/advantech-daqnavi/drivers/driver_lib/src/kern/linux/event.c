/*
 * event.c
 *
 *  Created on: 2011-9-27
 *      Author: rocky
 */
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/types.h>
#include <linux/spinlock.h>
#include <linux/sched.h>
#include <linux/slab.h>

#include <bdaq_def.h>
#include <bdaq_kern.h>

#ifndef EXPORT_SYMTAB
#define EXPORT_SYMTAB
#endif

#define STACK_BUF_THRESHOLD 6

#ifndef EVENT_NAME_LEN_MAX
#  define EVENT_NAME_LEN_MAX  31
#endif

/************************************************************************
 * Private Types
 ************************************************************************/
struct daq_event{
   struct kref      kref;
   struct list_head wait_list;
   int              signal_state;

   /*For named event*/
   struct list_head named_node;
   char             name[EVENT_NAME_LEN_MAX + 1];
};

typedef struct daq_wait_item{
   struct list_head    list_entry;
   struct daq_wait_ctx *wait_ctx;
} daq_wait_item_t;

typedef struct daq_wait_ctx{
   void            *wait_task;
   daq_wait_item_t *wait_items;
   int             item_count;
   int             wait_result;
} daq_wait_ctx_t;

/************************************************************************
 * Private Data
 ************************************************************************/
static DEFINE_SPINLOCK(s_event_dispatch_lock);

static LIST_HEAD(s_named_event_list);

/************************************************************************
 * Private Method
 ************************************************************************/
static
int daq_event_probe(unsigned count, daq_event_t *event[])
{
   unsigned long flags;
   int i;

   spin_lock_irqsave(&s_event_dispatch_lock, flags);
   for (i = 0; i < count; ++i){
      if (event[i]->signal_state > 0){
         event[i]->signal_state = 0;
         break;
      }
   }
   spin_unlock_irqrestore(&s_event_dispatch_lock, flags);

   return i < count ? i : -1;
}

static
void daq_event_release(struct kref *kref)
{
   daq_event_t *event = container_of(kref, daq_event_t, kref);

   if (event->name[0]) { /*Named event, remove it from the named event list*/
      list_del(&event->named_node);
   }

   kfree(event);
}

/************************************************************************
 * KLib Public Methods
 *************************************************************************/
daq_event_t * daq_event_create_named(char *name)
{
   daq_event_t *event;

   if (name && name[0]) { /*Search the event in the named event list*/
      list_for_each_entry(event, &s_named_event_list, named_node){
         if (strncmp(event->name, name, EVENT_NAME_LEN_MAX) == 0){
            kref_get(&event->kref);
            return event;
         }
      }
   }

   /*Create a new event*/
   event = kmalloc(sizeof(*event), GFP_KERNEL);
   if (event != NULL){
      kref_init(&event->kref);
      INIT_LIST_HEAD(&event->wait_list);
      event->signal_state = 0;

      INIT_LIST_HEAD(&event->named_node);
      event->name[0] = event->name[EVENT_NAME_LEN_MAX] = 0;      
      if (name && name[0]) {
         strncpy(event->name, name, EVENT_NAME_LEN_MAX);
         list_add(&event->named_node, &s_named_event_list);   
      }
   }

   return event;
}

daq_event_t * daq_event_create()
{
   return daq_event_create_named(NULL);
}

void daq_event_add_ref(daq_event_t *event)
{
   if (event != NULL) {
      kref_get(&event->kref);
   }
}

void daq_event_close(daq_event_t *event)
{
   if (event != NULL){
      kref_put(&event->kref, daq_event_release);
   }
}

void daq_event_set(daq_event_t *event)
{
   daq_wait_item_t *curr, *next;
   daq_wait_ctx_t  *ctx;
   unsigned long   flags;

   if (event == NULL){
      return;
   }

   spin_lock_irqsave(&s_event_dispatch_lock, flags);
   if (event->signal_state == 0){
      event->signal_state = 1;
      list_for_each_entry_safe(curr, next, &event->wait_list, list_entry){
         list_del_init(&curr->list_entry);

         ctx = curr->wait_ctx;
         if (ctx->wait_result == -1) {
            event->signal_state = 0;
            ctx->wait_result = curr - ctx->wait_items;
            wake_up_process(ctx->wait_task);
         }
      }
   }
   spin_unlock_irqrestore(&s_event_dispatch_lock, flags);
}

void daq_event_reset(daq_event_t *event)
{
   unsigned long flags;

   if (event != NULL){
      spin_lock_irqsave(&s_event_dispatch_lock, flags);
      event->signal_state = 0;
      spin_unlock_irqrestore(&s_event_dispatch_lock, flags);
   }
}

int daq_event_wait(
   unsigned     count,
   daq_event_t *events[],
   int          waitAll,
   unsigned     timeout)
{
   daq_wait_ctx_t  ctx;
   daq_wait_item_t stack_buf[STACK_BUF_THRESHOLD];
   unsigned long   flags;
   int i;

   if (count > MAX_WAIT_OBJECTS){
      return -EINVAL;
   }

   for (i = 0; i < count; ++i){
      if (events[i] == NULL){
         return -EINVAL;
      }
   }

   if (!timeout){
      return daq_event_probe(count, events);
   }

   ctx.wait_task   = current;
   ctx.wait_result = -1;
   ctx.item_count  = count;
   if (count <= STACK_BUF_THRESHOLD){
      ctx.wait_items = stack_buf;
   } else {
      ctx.wait_items = kmalloc(sizeof(daq_wait_item_t) * count, GFP_KERNEL);
      if (ctx.wait_items == NULL){
         return -ENOMEM;
      }
   }

   spin_lock_irqsave(&s_event_dispatch_lock, flags);
   for (i = 0; i < count; ++i){
      if (events[i]->signal_state > 0) {
          events[i]->signal_state = 0;
          ctx.wait_result = i;
          break;
      }
      kref_get(&events[i]->kref);
      ctx.wait_items[i].wait_ctx = &ctx;
      list_add(&ctx.wait_items[i].list_entry, &events[i]->wait_list);
   }

   if (ctx.wait_result < 0){
      timeout = msecs_to_jiffies(timeout);
      do {
         if (test_tsk_thread_flag(current, TIF_SIGPENDING)){
            ctx.wait_result = -EINTR;
            break;
         }
         set_current_state(TASK_INTERRUPTIBLE);
         spin_unlock_irqrestore(&s_event_dispatch_lock, flags);
         timeout = schedule_timeout(timeout);
         spin_lock_irqsave(&s_event_dispatch_lock, flags);
      } while (ctx.wait_result < 0 && timeout);
      __set_current_state(TASK_RUNNING);
   }

   while (--i >= 0){
      list_del(&ctx.wait_items[i].list_entry);
      kref_put(&events[i]->kref, daq_event_release);
   }
   spin_unlock_irqrestore(&s_event_dispatch_lock, flags);

   if (count > STACK_BUF_THRESHOLD){
      kfree(ctx.wait_items);
   }

   return ctx.wait_result;
}
EXPORT_SYMBOL_GPL(daq_event_create_named);
EXPORT_SYMBOL_GPL(daq_event_create);
EXPORT_SYMBOL_GPL(daq_event_add_ref);
EXPORT_SYMBOL_GPL(daq_event_close);
EXPORT_SYMBOL_GPL(daq_event_set);
EXPORT_SYMBOL_GPL(daq_event_reset);
EXPORT_SYMBOL_GPL(daq_event_wait);

