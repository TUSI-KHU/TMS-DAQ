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

//
// PCIe-X DMA format definition for PCIe-1812,PCIe-1813, PCIe-1803, etc.
// 

#ifndef _PCIEx_DMA_DEFINE
#define _PCIEx_DMA_DEFINE

//-----------------------------------------------------------------------------   
// Maximum DMA transfer size (in bytes).
//
//-----------------------------------------------------------------------------   
#define PCIEx_MAXIMUM_TRANSFER_LENGTH    (-1) // unlimited

//-----------------------------------------------------------------------------   
// The DMA_TRANSFER_ELEMENTS (the PCIEx's hardware scatter/gather list element)
// must be aligned on a 32-byte boundary to avoid a SGL entry span over two pages.
//-----------------------------------------------------------------------------   
#define PCIEx_DTE_ALIGNMENT_32  0x1F 

//-----------------------------------------------------------------------------   
// DMA-64 enabled
//-----------------------------------------------------------------------------
#if defined(_WIN64)
#   define PCIEx_DMA_ADDR_64    1
#endif

#if defined(__linux__)
#  if defined(CONFIG_HIGHMEM64G) || defined(CONFIG_X86_64) || defined(CONFIG_ARCH_DMA_ADDR_T_64BIT)
#     define PCIEx_DMA_ADDR_64  1
#  endif
#endif
 
//-----------------------------------------------------------------------------
// DMA Transfer Element (DTE)
//-----------------------------------------------------------------------------   
#define PCIEx_DESC_PTR_ADDR_SHIFT (2)
#define PCIEx_DESC_PTR_ADDR(a)    (((uint32)(a)) >> PCIEx_DESC_PTR_ADDR_SHIFT)

#if defined(PCIEx_DMA_ADDR_64)

#  define PCIEx_SET_PCI_ADDR(entry, phys) \
   do {\
      (entry)->addr_lo = (uint32)(phys); \
      (entry)->addr_hi = (uint32)((phys) >> 32); \
   } while(0)

#  define PCIEx_SET_NDPR_ADDR(entry, phys) \
   do {\
      (entry)->ndpr_lo = (uint32)(phys); \
      (entry)->ndpr_hi = (uint32)((phys) >> 32); \
   } while(0)

#else

#  define PCIEx_SET_PCI_ADDR(entry, phys) \
   do {\
      (entry)->addr_lo = (uint32)(phys); \
      (entry)->addr_hi = 0; \
   } while(0)

#  define PCIEx_SET_NDPR_ADDR(entry, phys) \
   do {\
      (entry)->ndpr_lo = (uint32)(phys); \
      (entry)->ndpr_hi = 0; \
   } while(0)

#endif

//
// PCIE-x scatter/gather list entry
typedef struct _PCIEx_SGL_ENTRY {   
   union {
      uint32    size;
      struct {
         uint32 size_dw : 12;
         uint32 sge_idx : 20;   // Driver Defined Value, index of this descriptor in the SG table
      };
   };

   uint32        addr_lo;
   uint32        addr_hi;

   union {
      uint32     ndpr_lo;
      struct {
         uint32  last_dpr : 1;
         uint32  done_int : 1;
      };
   };
   uint32        ndpr_hi;

   uint32        koffset;       // Driver Defined Value, offset of this descriptor in the data buffer

   // Padding to 32bytes alignment to avoid a SGL entry span over two pages
   uint32        __pad[2];  
} PCIEx_SGL_ENTRY, * PPCIEx_SGL_ENTRY;

#endif // _PCIEx_DMA_DEFINE
