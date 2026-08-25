/*******************************************************************************
Copyright (c) 1983-2009 Advantech Co., Ltd.
********************************************************************************
THIS IS AN UNPUBLISHED WORK CONTAINING CONFIDENTIAL AND PROPRIETARY INFORMATION
WHICH IS THE PROPERTY OF ADVANTECH CORP., ANY DISCLOSURE, USE, OR REPRODUCTION,
WITHOUT WRITTEN AUTHORIZATION FROM ADVANTECH CORP., IS STRICTLY PROHIBITED. 

================================================================================
REVISION HISTORY
--------------------------------------------------------------------------------
$Log:  $
$NoKeywords:  $
*/

#ifndef _I8237_DEFINE
#define _I8237_DEFINE

#define MAX_DMA_LENGTH 0x100000    //1M, 1024*1024

//////////////////////////////////////////////////////////////////////////
//DMA Controller register for x86 Platform
typedef enum _I8237DmaAddr{
   DmaCh0AddrReg = 0,
   DmaCh1AddrReg = 2,
   DmaCh2AddrReg = 4,
   DmaCh3AddrReg = 6,
   DmaCh4AddrReg = 0xC0,
   DmaCh5AddrReg = 0xC4,
   DmaCh6AddrReg = 0xC8,
   DmaCh7AddrReg = 0xCC,
}I8237DmaAddr;

typedef enum _I8237DmaCount{
   DmaCh0CountReg = 1,
   DmaCh1CountReg = 3,
   DmaCh2CountReg = 5,
   DmaCh3CountReg = 7,
   DmaCh4CountReg = 0xC2,
   DmaCh5CountReg = 0xC6,
   DmaCh6CountReg = 0xCA,
   DmaCh7CountReg = 0xCE,
}I8237DmaCount;

typedef enum _I8237DmaPage{
   DmaCh0PageReg = 0x87,
   DmaCh1PageReg = 0x83,
   DmaCh2PageReg = 0x81,
   DmaCh3PageReg = 0x82,
}I8237DmaPage;

typedef union _DMA_CMD_ISA
{
   uint8 Value;
   struct{
      uint8 Enable       : 1; // 0:disable, 1: enable
      uint8 AddrHoldEn   : 1; // Channel0 address hold, 0: disable, 1: enable
      uint8 ControllerEn : 1; // control enable
      uint8 Timing       : 1; // 0: normal timing, 1: compressed timing
      uint8 Priority     : 1; // 0: fixed priority, 1:rotating priority
      uint8 WriteSelect  : 1; // 0: late write selection, 1:Extended write selection
      uint8 DreqActLevel : 1; // DREQ sense active level, 0: high, 0:low
      uint8 DackActLevel : 1; // DACK sense active level, 0: low, 1: high
   };
}DMA_CMD_ISA, *PDMA_CMD_ISA;
#define DmaCommandReg      0x8
#define DmaCommandRegChip2 0xD0

typedef union _DMA_STATUS_ISA
{
   uint8 Value;
   struct{
      uint8 ChxTC  : 4; //Channel x Terminal count, each channel use a bit
      uint8 ChxReq : 4; //Channel x request
   };
}DMA_STATUS_ISA, *PDMA_STATUS_ISA;
#define DmaStatusReg      0x8
#define DmaStatusRegChip2 0xD0

typedef union _DMA_REQUEST
{
   uint8 Value;
   struct{
      uint8 Channel   : 2; //DMA channel
      uint8 Request   : 1; //0: Reset request bit, 1: Set request bit
      uint8 Reserved  : 5; //NC
   };
}DMA_REQUEST, *PDMA_REQUEST;
#define DmaRequestReg      0x9
#define DmaRequestRegChip2 0xD2

//////////////////////////////////////////////////////////////////////////
// Define the DMA-mode register structure.
typedef union _DMA_MASK_ISA
{
   uint8 Value;
   struct{
      uint8 Channel   : 2; //DMA channel
      uint8 Request   : 1; //0: Reset request bit, 1: Set request bit
      uint8 Reserved  : 5; //NC
   };
}DMA_MASK_ISA, *PDMA_MASK_ISA;
#define DmaMaskReg      0xA
#define DmaMaskRegChip2 0xD4

// Because the Plx905x.h have a union defiend as DMA_MODE, here add _ISA for distinguish
typedef union _DMA_MODE_ISA
{
   uint8 Value;
   struct{
      uint8 Channel          : 2; //DMA channel
      uint8 TransferType     : 2; //Transfer type, 0: Verify transfer, 1: Write transfer, 2: Read Transfer, 3: illegal
      uint8 AutoInitialize   : 1; //Auto initialize setting, 0: disable, 1: enable 
      uint8 AddressDecrement : 1; //Address decrement, 0: increment, 1: decrement
      uint8 RequestMode      : 2; //Request mode, 0:demand mode, 1:Single mode, 2:Block mode, 3:Cascade mode
   };
} DMA_MODE_ISA, *PDMA_MODE_ISA;
#define DmaModeReg      0xB
#define DmaModeRegChip2 0xD6

// Define TransferType values.
#define VERIFY_TRANSFER         0x00
#define WRITE_TRANSFER          0x01    // Write to the memory
#define READ_TRANSFER           0x02    // Read from the memory

// Define RequestMode values.
#define DEMAND_REQUEST_MODE     0x0
#define SINGLE_REQUEST_MODE     0x1
#define BLOCK_REQUEST_MODE      0x2
#define CASCADE_REQUEST_MODE    0x3

// Software Command
#define SoftCmdClearFlipFlop           0xC
#define SoftCmdClearFlipFlopChip2      0xD8

#define SoftCmdMasterClear             0xD
#define SoftCmdMasterClearChip2        0xDA

#define SoftCmdClearMaskRegister       0xE
#define SoftCmdClearMaskRegisterChip2  0xDC

typedef union _DMA_MASK_ALL
{
   uint8 Value;
   struct{
      uint8 Channel   : 2; //DMA channel
      uint8 Request   : 1; //0: Reset request bit, 1: Set request bit
      uint8 Reserved  : 5; //NC
   };
}DMA_MASK_ALL, *PDMA_MASK_ALL;
#define DmaMaskAllReg            0xF
#define DmaMaskAllRegChip2       0xDE

#endif
