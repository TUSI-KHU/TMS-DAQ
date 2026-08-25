/*
 * pciex_dma.c
 *
 *  Created on: 2019-8-12
 *      Author: rocky
 */
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/init.h>
#include <linux/types.h>
#include <linux/spinlock.h>
#include <linux/sched.h>
#include <linux/slab.h>
#include <linux/mm.h>
#include <linux/pagemap.h>
#include <linux/vmalloc.h>
#include <asm/io.h>

#include <bdaq_def.h>
#include <bdaq_kern.h>
#include <pciex_dma.h>

#ifndef EXPORT_SYMTAB
#define EXPORT_SYMTAB
#endif

//*************************************************************************
// daq_pciex_calc_sgl_length
//     Calculate the buffer length needed for S/G DMA operation according with
// the sample count and section size.
// return value: 
//    S/G List buffer size(bytes)
//************************************************************************* 
uint32 daq_pciex_calc_sgl_length(uint32 data_len, uint32 sect_len)
{
	uint32 count = 0;

	if (sect_len >= PAGE_SIZE) {
		count = data_len / PAGE_SIZE + ((data_len % PAGE_SIZE) != 0);
		if (sect_len % PAGE_SIZE) {
			count += data_len / sect_len;
		}
	} else {
		uint32 i, remains = 0;
		if (PAGE_SIZE % sect_len) {
			for (i = 0; i < data_len / PAGE_SIZE; i++) {
				count   += remains != 0;
				count   += (PAGE_SIZE - remains) / sect_len;
				remains  = (PAGE_SIZE - remains) % sect_len ;
				count   += remains != 0;
				remains  = sect_len - remains;
			}
		} else {
			count = (data_len / PAGE_SIZE) * (PAGE_SIZE / sect_len);
		}

		count    += (remains != 0);
		data_len %= PAGE_SIZE;
		if (data_len > remains) {
			data_len -= remains;
			remains   = data_len % sect_len;
			count    += data_len / sect_len + (remains != 0);
		}
	}

	return count  * sizeof(PCIEx_SGL_ENTRY);
}

/************************************************************************
daq_pciex_alloc_sgl_mem/daq_pciex_free_sgl_mem 
    allocate/free the memory of DMA scatter/gather list. 
************************************************************************/
int daq_pciex_alloc_sgl_mem(uint32 sgl_len, daq_pciex_sgl_t *sgl_mem)
{
   struct page **pages;
   int           nr_pages;
   int           i;

   BUG_ON(!sgl_mem);

   if (!sgl_len || sgl_mem->pages) {
      return -EINVAL;
   }

   memset(sgl_mem, 0, sizeof(*sgl_mem));

   nr_pages = (sgl_len + ~PAGE_MASK) >> PAGE_SHIFT;
   pages    = kmalloc(nr_pages * sizeof(void *), GFP_KERNEL);
   if (pages == NULL) {
      return -ENOMEM;
   }

   for (i = 0; i < nr_pages; ++i) {
      pages[i] = alloc_page(GFP_KERNEL);
      if (pages[i] == 0){
         break;
      }
   }

   if (i == nr_pages) {
      sgl_mem->start = vmap(pages, nr_pages, VM_MAP, PAGE_KERNEL);
      if (sgl_mem->start != NULL) {
         sgl_mem->nr_pages = nr_pages;
         sgl_mem->pages    = pages;
         sgl_mem->count    = sgl_len / sizeof(PCIEx_SGL_ENTRY);
         sgl_mem->daddr    = page_to_phys(pages[0]);
         return 0;
      }
   }

   while (--i >= 0) {
      __free_page(pages[i]);
   }

   kfree(pages);
   return -ENOMEM;
}

void daq_pciex_free_sgl_mem(daq_pciex_sgl_t *sgl_mem)
{
   int i;

   BUG_ON(!sgl_mem || (sgl_mem->nr_pages && !sgl_mem->pages));

   if (sgl_mem->nr_pages) {
      vunmap(sgl_mem->start);

      for (i = 0; i < sgl_mem->nr_pages; ++i){
         __free_page(sgl_mem->pages[i]);
      }

      kfree(sgl_mem->pages);
      memset(sgl_mem, 0, sizeof(*sgl_mem));
   }
}

/************************************************************************
daq_pciex_alloc_sgl_entry
    allocate a s/g entry. 
Return: 
    pointer to the allocated entry.
************************************************************************/
static PCIEx_SGL_ENTRY * daq_pciex_alloc_sgl_entry(daq_pciex_sgl_t *sgl_mem, uint32 *index)
{
   PCIEx_SGL_ENTRY *entry = NULL;
   unsigned   pg_num;
   unsigned   pg_off;
   dma_addr_t next_paddr;

   if (*index < sgl_mem->count) {
      entry   = &sgl_mem->start[*index];
      *index += 1;

      pg_num = (*index * sizeof(PCIEx_SGL_ENTRY)) >> PAGE_SHIFT;
      pg_off = (*index * sizeof(PCIEx_SGL_ENTRY)) &  ~PAGE_MASK;
      if (pg_num >= sgl_mem->nr_pages) {
         pg_num = pg_off = 0;
      }

      next_paddr = page_to_phys(sgl_mem->pages[pg_num]) + pg_off;
      PCIEx_SET_NDPR_ADDR(entry, next_paddr);
   }

   return entry;
}

/************************************************************************
daq_pciex_build_sgl
   Build the scatter/gather list for Bus-Master DMA. 
************************************************************************/
int daq_pciex_build_sgl(daq_user_mem_t *data_mem, uint32 data_len, uint32 sect_len, uint32 ele_size, daq_pciex_sgl_t *sgl_mem)
{
   struct page    **data_pages = data_mem->pages;
   PCIEx_SGL_ENTRY *entry      = NULL;
   unsigned         index      = 0;
   unsigned         bp         = sect_len;
   unsigned         curLen;
   dma_addr_t       curPA;

#  define DUMP_SGL_ENTRY(entry)   \
   daq_trace((KERN_INFO "entry(%lx): %d, 0x%x:0x%x, 0x%x:0x%x\n", \
      (unsigned long)entry, entry->size, entry->addr_hi, entry->addr_lo, entry->ndpr_hi, entry->ndpr_lo));

   BUG_ON(!sgl_mem  || !sgl_mem->nr_pages  || !sgl_mem->pages);
   BUG_ON(!data_mem || !data_mem->nr_pages || !data_mem->pages);

   while (data_len) {
      curPA     = page_to_phys(*data_pages++);
      curLen    = x_min((unsigned)PAGE_SIZE, data_len);
      data_len -= curLen;

      while (curLen) {
         entry = daq_pciex_alloc_sgl_entry(sgl_mem, &index);
         if (!entry) {
            return -EINVAL;
         }

         // fill in the entry
         PCIEx_SET_PCI_ADDR(entry, curPA);

         if (curLen >= bp) {
            entry->size     = bp;
            entry->done_int = 1;

            curPA += bp;
            bp     = sect_len;
         } else {
            entry->size = curLen;
            bp         -= curLen;
         }

         curLen -= entry->size;

         // Convert the 'size' field from bytes to specified unit
         entry->size /= ele_size; 
      }
   }

   //
   // Fix up the last entry
   PCIEx_SET_NDPR_ADDR(entry, sgl_mem->daddr); //chain the last entry to first one.
   entry->last_dpr = TRUE;
   entry->done_int = TRUE;

   // Record the last entry info, the caller might need it.
   sgl_mem->end = entry;

   return 0;
}

EXPORT_SYMBOL_GPL(daq_pciex_calc_sgl_length);
EXPORT_SYMBOL_GPL(daq_pciex_alloc_sgl_mem);
EXPORT_SYMBOL_GPL(daq_pciex_free_sgl_mem);
EXPORT_SYMBOL_GPL(daq_pciex_build_sgl);
