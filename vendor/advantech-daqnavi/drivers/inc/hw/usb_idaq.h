// ############################################################################
// ****************************************************************************
//                 Copyright (c) 2018, Advantech Co. Ltd.
//      THIS IS AN UNPUBLISHED WORK CONTAINING CONFIDENTIAL AND PROPRIETARY
//         INFORMATION WHICH IS THE PROPERTY OF ADVANTECH AUTOMATION CORP.
//
//    ANY DISCLOSURE, USE, OR REPRODUCTION, WITHOUT WRITTEN AUTHORIZATION FROM
//               ADVANTECH AUTOMATION CORP., IS STRICTLY PROHIBITED.
// ****************************************************************************
// ############################################################################
//
// File:        usb_idaq.h
// Environment: Kernel mode only
// Reference:   Microsoft WDK 6000
//
// Abstract:
//    This module contains the usb/iDAQ protocol definition.
//
// Author: Rocky.Ji
// ----------------------------------------------------------------------------

#ifndef _ADVANTECH_DAQ_USB_IDAQ_PROTOCOL_DEFINE
#define _ADVANTECH_DAQ_USB_IDAQ_PROTOCOL_DEFINE

//
// USB Interface index
typedef enum {
   IFACE_FTDI = 0,
   IFACE_DAQ  = 1,
} IFACE_INDEX;

#define BUILDEDIN_IFACE_NUM   2

//
// EP Number
typedef enum {
   // interface 0: FTDI
   EP_FTDI_OUT  = 0x1,
   EP_FTDI_IN   = 0x81,

   // interface 1: DAQ
   // FIFO 1: low-speed request/response
   EP_CMD_OUT   = 0x2,
   EP_CMD_IN    = 0x82,

   // FIFO 2: high-speed, notification
   __RESVED     = 0x3,
   EP_NTF_IN    = 0x83,

   // FIFO 3: high-speed, buffered samples
   EP_BFD_OUT   = 0x4,
   EP_BFD_IN    = 0x84,

   // FIFO 4: Flash update
   EP_FLH_OUT   = 0x5,
   EP_FLH_IN    = 0x85,
} EP_NUMBER;

#define FTDI_EP_NUM      2
#define DAQ_EP_NUM       8
#define BUILDEDIN_EP_NUM (FTDI_EP_NUM + DAQ_EP_NUM)

//----------------------------------------------------------------------
// 
//----------------------------------------------------------------------
//
// EP Index
typedef enum  {
   // interface 0: FTDI
   IDX_FTDI_OUT  = 0,
   IDX_FTDI_IN,

   // interface 1: DAQ
   // FIFO 1: low-speed request/response
   IDX_CMD_OUT,
   IDX_CMD_IN,

   // FIFO 2: high-speed, notification
   IDX_RESVED,
   IDX_NTF_IN,

   // FIFO 3: high-speed, buffered samples
   IDX_BFD_OUT,
   IDX_BFD_IN,

   // FIFO 4: Flash update
   IDX_FLH_OUT,
   IDX_FLH_IN,
} EP_IDX;

//----------------------------------------------------------------------
// FTDI command
//----------------------------------------------------------------------
#define  FTDI_STOP             0x0
#define  FTDI_START            0x1
#define  FTDI_START_AUTOREPEAT 0x2
#define  FTDI_FLUSH            0x3
#define  FTDI_GPIO             0x10 

// For compatible
#define  FTDI_START_AUTORESET  FTDI_START_AUTOREPEAT  

//
// FTDI session 
typedef struct _ftdi_session { // From FTDI spec.
   uint8  ep_num;             
   uint8  cmd_id;              
   uint8  reserve0;             
   uint8  reserve1;             
   uint32 sess_len_lo;           
   uint32 sess_len_hi;          
} ftdi_session_t;

// single session transaction
typedef struct _ftdi_ss_trans { 
   uint32          cmd_sn;
   ftdi_session_t  session;
   uint32          zero_term;
} ftdi_ss_trans_t;

typedef struct _ftdi_config {
   uint16 vendor_id;
   uint16 product_id;
} ftdi_config_t;

typedef struct _ftdi_60x_cfg {  //from FTDI spec.
   // Device Descriptor
   uint16 vendor_id;
   uint16 product_id;

   // String Descriptors
   uint8  descriptors[128];

   // Configuration Descriptor
   uint8  reserved1;
   uint8  power_attributes;
   uint16 power_consumption;

   // Data Transfer Configuration
   uint8  reserved2;
   uint8  fifo_clock;
   uint8  fifo_mode;
   uint8  channel_config;

   // Optional Feature Support
   uint16 optional_feat_supp;
   uint8  battery_charging_gpio_config;
   uint8  flash_eeprom_detection; 

   // MSIO and GPIO Configuration
   uint32 msio_control;
   uint32 gpio_control;
} ftdi_60x_cfg_t;

//----------------------------------------------------------------------
// DAQ USB Protocol
//----------------------------------------------------------------------
//

//
// Note about Method ID:
// The highest 2bits is pipe id of the command send to, which is required by HW.
// The lower 14bit is the actual method id.
// Due to driver has no interesting about the pipe id, here we just define one
// field to hold these two parts.
//
#define PIPE1_MTH_ID(n)     ((0 << 14) | n)   
#define PIPE3_MTH_ID(n)     ((2 << 14) | n)   
#define PIPE4_MTH_ID(n)     ((3 << 14) | n)   

//
// Note about Event ID (Notification packet of PIPE#1):
// The highest 2bits is pipe id of the command send to, which is required by HW.
// The lower 14bit is the actual method id.
// Due to driver has no interesting about the pipe id, here we just define one
// field to hold these two parts.
//
// 2025/5/28:
// Using an unique event id (32bits) to conveniently identify the event reported by HW.
// The unique event id is combined from 16bits event id and 4bits class id.
#define PIPE2_EVT_ID(n, cls)      ((((1 << 14) | n) << 16) | ((cls) << 8))

//
// Class/method: System
#define CLAZZ_SYSTEM    0x0

// Method Ids(PIPE#1)
#  define MTH_SYS_MB_HEARTBEAT    PIPE1_MTH_ID(0x0000)   // Heartbeat packet, required by iDAQ-964

#  define MTH_SYS_MB_STAT_GET     PIPE1_MTH_ID(0x0001)

#  define MTH_SYS_MOD_PRSNT_GET   PIPE1_MTH_ID(0x0003)
#  define MTH_SYS_MOD_FAULT_CLR   PIPE1_MTH_ID(0x0004)
#  define MTH_SYS_MOD_FAULT_GET   PIPE1_MTH_ID(0x0005)
#  define MTH_SYS_MOD_RESET_SET   PIPE1_MTH_ID(0x0006)
#  define MTH_SYS_MOD_RESET_GET   PIPE1_MTH_ID(0x0007)

#  define MTH_SYS_MOD_SIG_SET     PIPE1_MTH_ID(0x0010)
#  define MTH_SYS_MOD_SIG_GET     PIPE1_MTH_ID(0x0011)
#  define MTH_SYS_PFP_CFG_SET     PIPE1_MTH_ID(0x0012)
#  define MTH_SYS_PFP_CFG_GET     PIPE1_MTH_ID(0x0013)
#  define MTH_SYS_PFP_STA_GET     PIPE1_MTH_ID(0x0015)

#  define MTH_SYS_LED_CFG_SET     PIPE1_MTH_ID(0x0016)
#  define MTH_SYS_LED_CFG_GET     PIPE1_MTH_ID(0x0017)
#  define MTH_SYS_LED_OUT_SET     PIPE1_MTH_ID(0x0018)
#  define MTH_SYS_LED_OUT_GET     PIPE1_MTH_ID(0x0019)

#  define MTH_SYS_ACQ_EN_SET      PIPE1_MTH_ID(0x0020)
#  define MTH_SYS_ACQ_EN_GET      PIPE1_MTH_ID(0x0021)

#  define MTH_SYS_ACQ_CFG_SET     PIPE1_MTH_ID(0x0022)
#  define MTH_SYS_ACQ_CFG_GET     PIPE1_MTH_ID(0x0023)
                                                     
#  define MTH_SYS_CLK_CFG_SET     PIPE1_MTH_ID(0x0030)
#  define MTH_SYS_CLK_CFG_GET     PIPE1_MTH_ID(0x0031)

#  define MTH_SYS_SW_TRG_SET      PIPE1_MTH_ID(0x0040)
#  define MTH_SYS_SW_TRG_GET      PIPE1_MTH_ID(0x0041)

#  define MTH_SYS_TS_CNT_CLR      PIPE1_MTH_ID(0x0050)
#  define MTH_SYS_TS_CNT_GET      PIPE1_MTH_ID(0x0051)

#  define MTH_SYS_WDT_CFG_SET     PIPE1_MTH_ID(0x0060)
#  define MTH_SYS_WDT_CFG_GET     PIPE1_MTH_ID(0x0061)
#  define MTH_SYS_WDT_FLAG_CLR    PIPE1_MTH_ID(0x0062)
#  define MTH_SYS_WDT_FLAG_GET    PIPE1_MTH_ID(0x0063)
                                                     
#  define MTH_SYS_CLK_GEN_WR      PIPE1_MTH_ID(0x0100)
#  define MTH_SYS_CLK_GEN_RD      PIPE1_MTH_ID(0x0101)
                                                     
// Event Ids(PIPE#2)                       
#  define EVT_SYS_MB_STAT         PIPE2_EVT_ID(0x0000, CLAZZ_SYSTEM)                   
#  define EVT_SYS_MOD_ISRT        PIPE2_EVT_ID(0x0002, CLAZZ_SYSTEM)                   
#  define EVT_SYS_MOD_RMOV        PIPE2_EVT_ID(0x0003, CLAZZ_SYSTEM)                   
#  define EVT_SYS_MOD_FAULT_0     PIPE2_EVT_ID(0x0010, CLAZZ_SYSTEM) 
#  define EVT_SYS_MOD_FAULT_15    PIPE2_EVT_ID(0x001F, CLAZZ_SYSTEM) 
#  define EVT_SYS_TIMESTAMP       PIPE2_EVT_ID(0x0020, CLAZZ_SYSTEM)

//
// Class/method: Module
#define CLAZZ_MODULE    0x1

// Method Ids (PIPE#1)
#  define MTH_MOD_HWINFO_GET      PIPE1_MTH_ID(0x0001)

#  define MTH_MOD_CAL_WR          PIPE1_MTH_ID(0x0020)
#  define MTH_MOD_CAL_RD          PIPE1_MTH_ID(0x0021)

#  define MTH_MOD_CAL_CFG_SET     PIPE1_MTH_ID(0x0022)
#  define MTH_MOD_CAL_CFG_GET     PIPE1_MTH_ID(0x0023)

#  define MTH_MOD_FIFO_CLR        PIPE1_MTH_ID(0x0030)
#  define MTH_MOD_FIFO_STAT_GET   PIPE1_MTH_ID(0x0031)
#  define MTH_MOD_FIFO_CNT_GET    PIPE1_MTH_ID(0x0033)
#  define MTH_MOD_FIFO_THR_SET    PIPE1_MTH_ID(0x0034)
#  define MTH_MOD_FIFO_THR_GET    PIPE1_MTH_ID(0x0035)
#  define MTH_MOD_SW_TRG_SET      PIPE1_MTH_ID(0x0042)
#  define MTH_MOD_TRG_OUT_SET     PIPE1_MTH_ID(0x0040)
#  define MTH_MOD_TRG_OUT_GET     PIPE1_MTH_ID(0x0041)
                                  
#  define MTH_MOD_EVT_EN_SET      PIPE1_MTH_ID(0x0070)
#  define MTH_MOD_EVT_EN_GET      PIPE1_MTH_ID(0x0071)
#  define MTH_MOD_SIG_CFG_SET     PIPE1_MTH_ID(0x0010)
#  define MTH_MOD_SIG_CFG_GET     PIPE1_MTH_ID(0x0011)

// Event Ids(PIPE#2)  
#  define EVT_MOD_ACQ_STAT        PIPE2_EVT_ID(0x0000, CLAZZ_MODULE) 
#  define EVT_MOD_FIFO_STAT       PIPE2_EVT_ID(0x0002, CLAZZ_MODULE) 

// Method Ids(PIPE#3)
#  define MTH_MOD_OUT_FIFO_0      PIPE3_MTH_ID(0x2000)
#  define MTH_MOD_IN_FIFO_0       PIPE3_MTH_ID(0x2001)
#  define MTH_MOD_OUT_FIFO_1      PIPE3_MTH_ID(0x2002)
#  define MTH_MOD_IN_FIFO_1       PIPE3_MTH_ID(0x2003)
#  define MTH_MOD_OUT_FIFO_2      PIPE3_MTH_ID(0x2004)
#  define MTH_MOD_IN_FIFO_2       PIPE3_MTH_ID(0x2005)
#  define MTH_MOD_OUT_FIFO_3      PIPE3_MTH_ID(0x2006)
#  define MTH_MOD_IN_FIFO_3       PIPE3_MTH_ID(0x2007)
#  define MTH_MOD_IN_FIFO_0_CF    PIPE3_MTH_ID(0x2011)
#  define MTH_MOD_IN_FIFO_0_CFO   PIPE3_MTH_ID(0x2019)
#  define MTH_MOD_OUT_FIFO_0_DDL  PIPE3_MTH_ID(0x2020) //in double data length
#  define MTH_MOD_IN_FIFO_0_DDL   PIPE3_MTH_ID(0x2021) //in double data length
#  define MTH_MOD_IN_DATA_END     PIPE3_MTH_ID(0x2081)

// Method Ids(PIPE#4)
#  define MTH_MOD_FLH_WR          PIPE4_MTH_ID(0x0000) 
#  define MTH_MOD_FLH_RD          PIPE4_MTH_ID(0x0001)

//
// Class/method: AI
#define CLAZZ_AI        0x2

// Method Ids (PIPE#1)
#  define MTH_AI_BFD_ACQ_SET      PIPE1_MTH_ID(0x0000)
#  define MTH_AI_BFD_ACQ_GET      PIPE1_MTH_ID(0x0001)

#  define MTH_AI_CNV_MOD_SET      PIPE1_MTH_ID(0x0002)
#  define MTH_AI_CNV_MOD_GET      PIPE1_MTH_ID(0x0003)
                                             
#  define MTH_AI_CH_CFG_SET       PIPE1_MTH_ID(0x0020)
#  define MTH_AI_CH_CFG_GET       PIPE1_MTH_ID(0x0021)
                                                     
#  define MTH_AI_ATRG_CFG_SET     PIPE1_MTH_ID(0x0030)
#  define MTH_AI_ATRG_CFG_GET     PIPE1_MTH_ID(0x0031)

#  define MTH_AI_EVT_EN_SET       PIPE1_MTH_ID(0x0070)
#  define MTH_AI_EVT_EN_GET       PIPE1_MTH_ID(0x0071)

#  define MTH_AI_SAMPLE_GET       PIPE1_MTH_ID(0x0081)
#  define MTH_AI_FAULT_IND_GET    PIPE1_MTH_ID(0x0083)
                                                     
#  define MTH_AI_ADC_WR           PIPE1_MTH_ID(0x0100)
#  define MTH_AI_ADC_RD           PIPE1_MTH_ID(0x0101)

// Event Ids(PIPE#2)  
#  define EVT_AI_FAULT_0          PIPE2_EVT_ID(0x0000, CLAZZ_AI)
#  define EVT_AI_FAULT_1          PIPE2_EVT_ID(0x0001, CLAZZ_AI)

//
// Class/method: AO
#define CLAZZ_AO        0x3

// Method Ids (PIPE#1)
#  define MTH_AO_BFD_ACQ_SET      PIPE1_MTH_ID(0x0000)
#  define MTH_AO_BFD_ACQ_GET      PIPE1_MTH_ID(0x0001)

#  define MTH_AO_CH_CFG_SET       PIPE1_MTH_ID(0x0020)
#  define MTH_AO_CH_CFG_GET       PIPE1_MTH_ID(0x0021)
                                                     
#  define MTH_AO_ATRG_CFG_SET     PIPE1_MTH_ID(0x0030)
#  define MTH_AO_ATRG_CFG_GET     PIPE1_MTH_ID(0x0031)

#  define MTH_AO_FS_CFG_SET       PIPE1_MTH_ID(0x0040)
#  define MTH_AO_FS_CFG_GET       PIPE1_MTH_ID(0x0041)

#  define MTH_AO_SAMPLE_SET       PIPE1_MTH_ID(0x0080)
#  define MTH_AO_SAMPLE_GET       PIPE1_MTH_ID(0x0081)
#  define MTH_AO_FAULT_IND_GET    PIPE1_MTH_ID(0x0083)
                                                     
#  define MTH_AO_DAC_WR           PIPE1_MTH_ID(0x0100)
#  define MTH_AO_DAC_RD           PIPE1_MTH_ID(0x0102)

// Event Ids(PIPE#2)  
//#  define EVT_AO_FAULT_0          PIPE2_EVT_ID(0x0000, CLAZZ_AO) 

//
// Class/method: DI
#define CLAZZ_DI        0x4

// Method Ids (PIPE#1)
#  define MTH_DI_BFD_ACQ_SET      PIPE1_MTH_ID(0x0000)
#  define MTH_DI_BFD_ACQ_GET      PIPE1_MTH_ID(0x0001)
                                                     
#  define MTH_DI_EDG_EN_SET       PIPE1_MTH_ID(0x0010)
#  define MTH_DI_EDG_EN_GET       PIPE1_MTH_ID(0x0011)
#  define MTH_DI_PM_CFG_SET       PIPE1_MTH_ID(0x0012)
#  define MTH_DI_PM_CFG_GET       PIPE1_MTH_ID(0x0013)

#  define MTH_DI_LAT_STAT_GET     PIPE1_MTH_ID(0x001F)
                                  
#  define MTH_DI_FLT_CFG_SET      PIPE1_MTH_ID(0x0022)
#  define MTH_DI_FLT_CFG_GET      PIPE1_MTH_ID(0x0023)
                                                     
#  define MTH_DI_DTRG_CFG_SET     PIPE1_MTH_ID(0x0030)
#  define MTH_DI_DTRG_CFG_GET     PIPE1_MTH_ID(0x0031)

#  define MTH_DI_SAMPLE_GET       PIPE1_MTH_ID(0x0081)
#  define MTH_DI_FAULT_IND_GET    PIPE1_MTH_ID(0x0083)

// Event Ids(PIPE#2)  
#  define EVT_DI_RIS              PIPE2_EVT_ID(0x0010, CLAZZ_DI) 
#  define EVT_DI_FAL              PIPE2_EVT_ID(0x0011, CLAZZ_DI) 
#  define EVT_DI_PM               PIPE2_EVT_ID(0x0012, CLAZZ_DI) 

//
// Class/method: DO
#define CLAZZ_DO        0x5

// Method Ids (PIPE#1)
#  define MTH_DO_BFD_ACQ_SET      PIPE1_MTH_ID(0x0000)
#  define MTH_DO_BFD_ACQ_GET      PIPE1_MTH_ID(0x0001)
                                                     
#  define MTH_DO_OUT_TYPE_SET     PIPE1_MTH_ID(0x0020)
#  define MTH_DO_OUT_TYPE_GET     PIPE1_MTH_ID(0x0021)

#  define MTH_DO_ENABLE_SET       PIPE1_MTH_ID(0x0022)
#  define MTH_DO_ENABLE_GET       PIPE1_MTH_ID(0x0023)

#  define MTH_DO_FS_CFG_SET       PIPE1_MTH_ID(0x0040)
#  define MTH_DO_FS_CFG_GET       PIPE1_MTH_ID(0x0041)

#  define MTH_DO_SAMPLE_SET       PIPE1_MTH_ID(0x0080)
#  define MTH_DO_SAMPLE_GET       PIPE1_MTH_ID(0x0081)
#  define MTH_DO_FAULT_IND_GET    PIPE1_MTH_ID(0x0083)

// Event Ids(PIPE#2)  
//#  define EVT_DO_FAULT_0          PIPE2_EVT_ID(0x0000, CLAZZ_DO) 

//                                                   
// Class/method: Counter
#define CLAZZ_CTR       0x6

// Method Ids (PIPE#1)
#  define MTH_CTR_BFD_ACQ_SET     PIPE1_MTH_ID(0x0000)
#  define MTH_CTR_BFD_ACQ_GET     PIPE1_MTH_ID(0x0001)
                                                     
#  define MTH_CTR_SIG_SET         PIPE1_MTH_ID(0x0010)
#  define MTH_CTR_SIG_GET         PIPE1_MTH_ID(0x0011)
#  define MTH_CTR_OP_MOD_SET      PIPE1_MTH_ID(0x0020)
#  define MTH_CTR_OP_MOD_GET      PIPE1_MTH_ID(0x0021)
#  define MTH_CTR_FLT_CFG_SET     PIPE1_MTH_ID(0x0022)
#  define MTH_CTR_FLT_CFG_GET     PIPE1_MTH_ID(0x0023)
                                                     
#  define MTH_CTR_VAL_GET         PIPE1_MTH_ID(0x0035)
#  define MTH_CTR_NUM_SET         PIPE1_MTH_ID(0x0032)
#  define MTH_CTR_NUM_GET         PIPE1_MTH_ID(0x0033)
                                                     
#  define MTH_CTR_EVT_EN_SET      PIPE1_MTH_ID(0x0070)
#  define MTH_CTR_EVT_EN_GET      PIPE1_MTH_ID(0x0071)

// Event Ids(PIPE#2)  
//#  define EVT_CTR_FAULT_0         PIPE2_EVT_ID(0x0000, CLAZZ_CTR) 

#  define EVT_CTR_OP_FIN          PIPE2_EVT_ID(0x0010, CLAZZ_CTR) 
#  define EVT_CTR_UDF             PIPE2_EVT_ID(0x0011, CLAZZ_CTR) 
#  define EVT_CTR_OVF             PIPE2_EVT_ID(0x0012, CLAZZ_CTR) 
#  define EVT_CTR_IDX             PIPE2_EVT_ID(0x0013, CLAZZ_CTR) 
#  define EVT_CTR_SPL             PIPE2_EVT_ID(0x0014, CLAZZ_CTR) 
                                                     
//----------------------------------------------------------------------
// Structure for USB communication
//----------------------------------------------------------------------
// Common part: packet header of request and response packet
//----------------------------------------------------------------------
typedef union _daq_pkt_hdr {
   uint32 xval;
   struct {
      uint8  siz_dw;        // Total size of the packet, in DWORD.
      uint8  clazz : 4;
      uint8  slot  : 4;   

      union {
         uint16 method;     // method id, the highest two bits is pipe id.
         uint16 eid_hi;     // Highest 16bit of Event id, for notification packet, the highest two bits is pipe id.
      };
   };
} daq_pkt_hdr_t;

//
// USB packet size
#define LS_PKT_SIZE     256
#define LS_MSG_SIZE     (LS_PKT_SIZE - sizeof(daq_pkt_hdr_t))

#define NTF_PKT_SIZE    16
#define NTF_MSG_SIZE    (NTF_PKT_SIZE - sizeof(daq_pkt_hdr_t))

#define HS_PKT_SIZE     512
#define HS_MSG_SIZE     (HS_PKT_SIZE - sizeof(daq_pkt_hdr_t))

#define HS_FIFO_SIZE    1024
#define HS_USB_PKT_SIZE (32 * 1024)    

#define FLH_PKT_SIZE    512
#define FLH_MSG_SIZE    (FLH_PKT_SIZE - sizeof(daq_pkt_hdr_t))

#define BYTES_TO_DWORD(size)  ((((uint32)(size) + 3) & (~3)) >> 2)

#define PKT_HDR_RESET(pkt)    (((daq_pkt_hdr_t*)pkt)->xval = 0) // Zero the packet header

#define PKT_EVT_ID_GET(pkt)   (((daq_pkt_hdr_t*)pkt)->xval & 0xffff0f00)

#define IS_EVT_PKT(pkt)       ((((daq_pkt_hdr_t*)pkt)->method & (3 << 14)) == (1 << 14))

#define PKT_INIT_NOT_ZERO_DATA(pkt, cls, slt, mth, data_size) \
   do {\
      (pkt)->header.siz_dw = BYTES_TO_DWORD(sizeof(daq_pkt_hdr_t) + data_size);\
      (pkt)->header.clazz  = cls;\
      (pkt)->header.slot   = slt;\
      (pkt)->header.method = mth;\
   } while (0)

#define PKT_INIT_AND_ZERO_DATA(pkt, cls, slt, mth, data_size) \
   do {\
      PKT_INIT_NOT_ZERO_DATA(pkt, cls, slt, mth, data_size);\
      memset((pkt)->pad, 0, data_size);  \
   } while (0)

#define SYS_PKT_INIT(pkt, mth, data_size)         PKT_INIT_AND_ZERO_DATA(pkt, CLAZZ_SYSTEM, 0xF, mth, data_size)
#define MOD_PKT_INIT(pkt, slt, mth, data_size)    PKT_INIT_AND_ZERO_DATA(pkt, CLAZZ_MODULE, slt, mth, data_size)
#define AI_PKT_INIT( pkt, slt, mth, data_size)    PKT_INIT_AND_ZERO_DATA(pkt, CLAZZ_AI,     slt, mth, data_size)
#define AO_PKT_INIT( pkt, slt, mth, data_size)    PKT_INIT_AND_ZERO_DATA(pkt, CLAZZ_AO,     slt, mth, data_size)
#define DI_PKT_INIT( pkt, slt, mth, data_size)    PKT_INIT_AND_ZERO_DATA(pkt, CLAZZ_DI,     slt, mth, data_size)
#define DO_PKT_INIT( pkt, slt, mth, data_size)    PKT_INIT_AND_ZERO_DATA(pkt, CLAZZ_DO,     slt, mth, data_size)
#define CTR_PKT_INIT(pkt, slt, mth, data_size)    PKT_INIT_AND_ZERO_DATA(pkt, CLAZZ_CTR,    slt, mth, data_size)

//----------------------------------------------------------------------
// Common part: helper structures & macros
//----------------------------------------------------------------------
//
// System
#define SYS_MOD_CNT      14
#define SYS_CLK_CNT      SYS_MOD_CNT
#define SYS_ACQ_CNT      SYS_MOD_CNT
#define SYS_CLK_GEN_CNT  8
#define SYS_FAULT_CNT    16
#define SYS_PFP_CNT      2

#define SYS_SLOT_NUM     0xF

//
// Module
#define MOD_FIFO_CNT     4
#define MOD_EVT_CNT      256 

#define MOD_FLH_ADDR_SHIFT 4
#define MOD_FLH_ADDR(a)    (((uint32)(a)) >> MOD_FLH_ADDR_SHIFT)

// Trigger
#define MOD_TRG_OUT_CNT  2

// 
// AI
#define AI_CH_CNT_MAX    32
#define AI_ADC_CNT_MAX   8
#define AI_EVT_CNT       256 

// 
// AO
#define AO_CH_CNT_MAX    32
#define AO_DAC_CNT_MAX   8
#define AO_EVT_CNT       256 

//
// DIO
#define DIO_PT_CNT_MAX   8
#define DIO_EVT_CNT      256 
#define DIO_PT_PER_GP    4    // One group have 4 dio ports
#define DIO_GP_CNT_MAX   2    

// 
// Counter
#define CTR_CH_CNT_MAX   8

//----------------------------------------------------------------------
// DAQ USB Protocol: PIPE#1, Low-speed data transition (EP: 0x2/0x82)
//----------------------------------------------------------------------
//--------------------------------------------
// CLAZZ: SYSTEM
//--------------------------------------------
//
// device clock setting
typedef struct _daq_clk_cfg {
   uint32 src;        // ClkDividerJunction
   uint32 dsr;
} daq_clk_cfg_t;

typedef struct _daq_pfp_cfg {
   uint8 flt_en;      // bit#0: Programmable function pin input debounce filter enable
   uint8 flt_dur;     // Programmable function pin input debounce filter duration

   uint8 out_en;      // bit#0: Programmable function pin output enable
   uint8 out_src : 7; // Programmable function pin output source select and inversion
   uint8 out_inv : 1; 
} daq_pfp_cfg_t;

//
// module signal setting
typedef struct _daq_mod_sig {
   // MOD_n_SIG_0: ConvClkJunction
   uint8 conv_clk_src : 7;
   uint8 conv_clk_inv : 1;

   // MOD_n_SIG_1: SyncJunction
   uint8 sync_sig_src : 7;
   uint8 sync_sig_inv : 1;

   // MOD_n_SIG_2: AcqStateJunction
   uint8 acq_stat_src : 7;
   uint8 acq_stat_inv : 1;

   // MOD_n_SIG_3: reserved
   uint8 reserved;
} daq_mod_sig_t;

//
// device acquisition setting
typedef struct _daq_acq_cfg {
   // Acquisition enable & re-trigger enable    
   uint32 rtrg_en : 1;  
   uint32 type    : 1;

   uint32 __resv  : 6;

   // Start trigger source select and inversion
   uint32  sta_trg_src : 7;   // TrgStaJunction
   uint32  sta_trg_inv : 1; 

   // Stop trigger source select and inversion
   uint32  stp_trg_src : 7;   // TrgStpJunction
   uint32  stp_trg_inv : 1; 

   // Sample clock source select and inversion
   uint32  spl_clk_src : 7;
   uint32  spl_clk_inv : 1;

   // Start/Stop trigger delay number
   uint32 sta_trg_dly;
   uint32 stp_trg_dly;

   // Sample count
   uint32 spl_num;
} daq_acq_cfg_t;

typedef struct _daq_sys_pkt {
   daq_pkt_hdr_t header;

   union {    
      // System get main-board status
      struct {
         uint32 us_ss : 1; //Upstream port SuperSpeed and Hi-Speed indicator
         uint32 us_hs : 1;
      } mb_stat;

      // 
      // System get module present
      struct {
         uint16 present;  // Module present indicators, each bit for a module
         uint16 power_en; // Module power enable indicators, each bit for a module
      } mod_stat;

      // 
      // System clear/get module fault indicator
      struct {
         uint16 over_curr;                   // Module over-current indicator, each bit for a module
         uint16 fault[SYS_FAULT_CNT - 1];  // Module fault 0~15, each bit for a module
      } mod_fault;

      //
      // System get/set module reset
      struct {
         uint16 reset;  // Module reset, each bit for a module
      } mod_reset;

      // 
      // System get/set module signal configuration
      daq_mod_sig_t mod_sig[SYS_MOD_CNT];
      
      //
      // System get/set programmable function pin configuration
      daq_pfp_cfg_t pfp_cfg[SYS_PFP_CNT];

      struct {
         uint32 pfp0 : 1;  // 0: PFP is low, 1: PFP is high
         uint32 pfp1 : 1;
      } pfp_sta;

      // 
      // System get/set LED SW control 
      struct {
         uint32 led0 : 2; // bit0: green, bit1: red
         uint32 led1 : 2; // bit0: green, bit1: yellow
         uint32 led2 : 2; // bit0: green, bit1: red
      } led_ctl;

      // 
      // System get/set LED output 
      // 0 -- LED is off, 1 -- LED is on
      struct {
         uint32 led0 : 2; // bit0: green, bit1: red
         uint32 led1 : 2; // bit0: green, bit1: yellow
         uint32 led2 : 2; // bit0: green, bit1: red
      } led_out;

      // 
      // System enable acquisition
      struct {
         uint32 enable; // enable acquisition
      } acq_en;

      // 
      // System get/set acquisition configuration
      daq_acq_cfg_t acq_cfg[SYS_ACQ_CNT];

      //
      // System get/set clock divider
      daq_clk_cfg_t clk_cfg[SYS_CLK_CNT];

      // 
      // System assert software trigger
      struct {
         uint32 asrt; // Each bit for a SW trigger source
         uint32 __resv;
      } sw_trg;

      //
      // System clear/get time stamp counter(56bit)
      struct {
         uint32 lo;
         uint32 hi;
      } ts_cnt;

      //
      // System get/set watchdog timer configuration
      struct {
         uint8 timeout; // Watchdog timer time-out period
      } wdt_cfg;

      //
      // System get watchdog timer time-out flag
      struct {
         uint8 flag; // Watchdog timer time-out flag
      } wdt_flag;

      // 
      // System write/read clock generator
      struct {
         // Clock generator access/busy and read/write indicator
         uint32 acc_busy : 1; // ACC for write, BUSY for read.
         uint32 rw_sel   : 1;
         uint32 __resv   : 6;

         // Clock generator read/write address
         uint32 addr     : 24;

         // Clock generator data
         uint32 data;
      } clk_gen[SYS_CLK_GEN_CNT];

      // 
      // padding to LS_PKT_SIZE bytes packet
      uint8 pad[LS_MSG_SIZE];
   };
} daq_sys_pkt_t;

//--------------------------------------------
// CLAZZ: MODULE
//--------------------------------------------
typedef struct _daq_mod_pkt {
   daq_pkt_hdr_t header;

   union {    
      // Module get hardware version
      struct {
         uint32 dev_id;

         uint32 cid     : 4;   // Chassis ID
         uint32 __resv  : 4;
         uint32 pcb_ver : 24;  // PCB version        
         uint32 pld_ver;       // PLD version
      } hw_info;

      //
      // Module read/write calibration command
      struct {
         uint32 cmd    : 8;
         uint32 __resv : 23;
         uint32 busy   : 1;    // for read response packet only!
         uint32 data;
      } cal_rw;

      //
      // Module enable/disable calibration
      struct {
         uint32 enable;
         uint32 __resv;
      } cal_cfg;

      // 
      // Module clear FIFO
      struct {
         uint8 in_fifo : 1;
         uint8 resv: 3;
         uint8 out_fifo: 1;
      } fifo_clr[MOD_FIFO_CNT];

      // 
      // Module get FIFO status
      struct {
         uint8 in_emp : 1;
         uint8 in_ful : 1;
         uint8 __resv : 2;
         uint8 out_emp: 1;         
         uint8 out_ful: 1;         
         uint8 out_dct: 1;         
      } fifo_stat[MOD_FIFO_CNT];

      //
      // Module get FIFO data count
      struct {
         uint16 in;
         uint16 out;
      } fifo_cnt[MOD_FIFO_CNT];

      //
      // Module get/set FIFO threshold value
      struct {
         uint16 in_fifo;
         uint16 out_fifo;
      } fifo_thr[MOD_FIFO_CNT];

      //
      // Module get/set trigger out
      struct {
         uint32 src : 7;
         uint32 edg : 1;
         uint32 act : 24;
         uint32 thr;
         uint32 hys;
      } trg_out[MOD_TRG_OUT_CNT];

      //
      // Module get/set event enable
      struct {
         uint32 acq_stat  : 1;
         uint32 __resv0   : 1;
         uint32 fifo_stat : 1;

         uint32 others[MOD_EVT_CNT/32 - 1];
      } evt_en;
      
      struct {
         uint32 strg;
      }strg_en;

      struct {
         uint32 out_src : 7;
         uint32 out_inv : 1;
      }sig_cfg;
      // 
      // padding to LS_PKT_SIZE bytes packet
      uint8 pad[LS_MSG_SIZE];
   };
} daq_mod_pkt_t;

//--------------------------------------------
// CLAZZ: AI
//--------------------------------------------
typedef struct _daq_ai_pkt {
   daq_pkt_hdr_t header;

   union {    
      //
      // Analog input get/set buffered acquisition configuration
      struct {
         uint32 ch_en; // Analog input buffered acquisition enable
      } bfd_acq;

      //
      // Analog input get/set output data rate
      struct {
         uint32 mod   : 8;
         uint32 rate  : 24;
      } conv_mode;
      
      //
      // Analog input get/set channel configuration
      struct {
         uint8 gain;
         uint8 type     : 4;
         uint8 psu_diff : 1; // Pseudo-differential mode enabled
         uint8 dc_cpl   : 1; // DC coupling enable
         uint8 iepe     : 2; // Integrated Electronics Piezo-Electric (IEPE) enable
         uint8 flt      : 1; // Anti-aliasing filter -3 dB bandwidth
         uint8 resv1    : 7;
         uint8 resv2;
      } ch_cfg[AI_CH_CNT_MAX];

      //
      // Analog input get/set analog trigger configuration
      struct {
         uint32 src     : 7;
         uint32 edg     : 1;
         uint32 resv0   : 24;
         uint32 thrs;          // trigger threshold
         uint32 hyst;          // trigger hysteresis
      } ana_trg;

      //
      // Analog input get sample
      struct {
         uint32 val;
      } ch_data[AI_CH_CNT_MAX];
      
      //
      // Analog input get fault indicator
      struct {
         uint32 chan;     // channel fault indicators
      } fault[SYS_FAULT_CNT];

      //
      // Analog input write ADC
      struct {
         uint32 acc_busy : 1;  // ADC access(for write)/busy(for read) indicator
         uint32 rw_sel   : 1;  // ADC select for writing/reading registers
         uint32 __resv   : 6;
         uint32 addr     : 24; // ADC write/read address
         uint32 data;          // ADC data, for ADC write only!
      } adc_rw[AI_ADC_CNT_MAX];

      //
      // Analog input get/set event enable
      struct {
         uint32 burn_out;
      } evt_en;

      // 
      // padding to LS_PKT_SIZE bytes packet
      uint8 pad[LS_MSG_SIZE];
   };
} daq_ai_pkt_t;

//--------------------------------------------
// CLAZZ: AO
//--------------------------------------------
typedef struct _daq_ao_pkt {
   daq_pkt_hdr_t header;

   union {    
      //
      // Analog output get/set buffered acquisition configuration
      struct {
         uint32 ch_en; // Analog output buffered acquisition enable
      } bfd_acq;

      //
      // Analog output get/set channel configuration
      struct {
         uint32 gain : 8;
         uint32 other: 24; 
      } ch_cfg[AO_CH_CNT_MAX];

      //
      // Analog output get/set analog trigger configuration
      struct {
         uint32 src   : 5;
         uint32 thrs;           // trigger threshold
         uint32 hyst;           // trigger hysteresis
      } ana_trg;

      //
      // Analog output get/set fail-safe output configuration
      struct {
         uint32 fs_en;                 // Fail-safe output enable for analog output
         uint32 fs_val[AO_CH_CNT_MAX]; // Fail-safe output value for analog output
      } fs_cfg;

      //
      // Analog output get/set sample
      struct {
         uint32 val;
      } ch_data[AO_CH_CNT_MAX];

      //
      // Analog output get fault indicator
      struct {
         uint32 chan;     // channel fault indicators
      } fault[SYS_FAULT_CNT];

      //
      // Analog output write DAC
      struct {
         uint32 acc_busy : 1;  // DAC access(for write)/busy(for read) indicator
         uint32 rw_sel   : 1;  // DAC select for writing/reading registers
         uint32 __resv   : 6;
         uint32 addr     : 24; // DAC write/read address
         uint32 data;          // DAC data, for ADC write only!
      } dac_rw[AO_DAC_CNT_MAX];

      // 
      // padding to LS_PKT_SIZE bytes packet
      uint8 pad[LS_MSG_SIZE];
   };
} daq_ao_pkt_t;

//--------------------------------------------
// CLAZZ: DIO
//--------------------------------------------
// DIO sample struct, in DWORDs.
typedef struct _daq_dio_spl {
   uint8 port[DIO_PT_PER_GP];
} daq_dio_spl_t;

//DIO port count is greater than 4(e.g idaq-751)
typedef struct _daq_dio_spl_ex {
   uint8 port[DIO_PT_CNT_MAX];
} daq_dio_spl_ex_t;

typedef struct _daq_dio_pkt {
   daq_pkt_hdr_t header;

   union {    
      //
      // Digital input/output get/set buffered acquisition configuration
      struct {
         uint8 port_en[DIO_PT_CNT_MAX]; 
      } bfd_acq;
      
      //
      // Digital input get/set edge detect enable
      struct {
         uint8 ris; 
         uint8 fal;
      } edg_en[DIO_PT_CNT_MAX];

      //
      // Digital input get/set pattern match detect configuration
      struct {
         uint8 en;   
         uint8 pat;  
      } pm_cfg[DIO_PT_CNT_MAX];

      //
      // Digital input get latched state
      daq_dio_spl_t    lat_stat; 

      daq_dio_spl_ex_t lat_stat_ex;
      //
      // Digital input get/set de-bounce filter configuration
      struct {
         uint8 en;
         uint8 dur;
         uint8 __resv[2];
      } flt_cfg[DIO_PT_CNT_MAX];

      //
      // Digital input get/set digital trigger configuration
      struct {
         uint32 src : 6;
      } dtrg_cfg;

      //
      // Digital input/output get/set sample
      daq_dio_spl_t    dio_spl;

      daq_dio_spl_ex_t dio_spl_ex;

      //
      // Digital output get/set output type
      struct {
         uint8 type;
      } do_type[DIO_PT_CNT_MAX];
      
      //
      // Digital output get/set enable
      struct {
         uint8 en;
      } do_en[DIO_PT_CNT_MAX];

      //
      // Digital output get/set fail-safe output configuration
      struct {
         uint8 fs_en[DIO_PT_PER_GP];  // bit#0: Fail-safe output enable for digital output
         uint8 fs_val[DIO_PT_PER_GP]; // Fail-safe output value for digital output
      } fs_cfg[DIO_GP_CNT_MAX];      
      // 
      // padding to LS_PKT_SIZE bytes packet
      uint8 pad[LS_MSG_SIZE];
   };
} daq_dio_pkt_t;

//--------------------------------------------
// CLAZZ: CT (Counter)
//--------------------------------------------
typedef union _daq_ctr_sig {
   uint32 xval[3];

   struct{
      uint8 clk_src : 7;  // Counter clock source and active edge
      uint8 clk_inv : 1;

      uint8 gat_src : 7;  // Counter gate source and active level
      uint8 gat_inv : 1;

      uint8 aux_src : 7;  // Counter aux source and active edge
      uint8 aux_inv : 1;

      uint8 arm_src : 7;  // Counter arm source and active edge
      uint8 arm_inv : 1;

      uint8 sck_src : 7;  // Counter sample clock source and active edge
      uint8 sck_inv : 1; 

      uint8 resv0   : 7;
      uint8 out_inv : 1;

      uint8 resv1;

      uint8 rld_src: 7;
      uint8 rld_inv: 1;
   };
} daq_ctr_sig_t;

typedef struct _daq_ctr_flt {
   union{
      uint8 en_val;

      struct{
         uint8 clk:     1;
         uint8 gate:    1;
         uint8 aux:     1;
         uint8 arm:     1;
         uint8 sclk:    1;
         uint8 resv:    3;
      } en;
   };

   uint8 dur;
   uint8 __resv[2];
} daq_ctr_flt_t;

typedef union _daq_ctr_opm {
   uint32 xval;
   struct{
      uint8 mode;
      uint8 dir;
      uint8 gmode;
      uint8 type;
   };
} daq_ctr_opm_t;

typedef struct _daq_ctr_evt {
   uint8 op_fin;      // operation finished event enable.
   uint8 underflow;   // underflow event enable.
   uint8 overflow;    // overflow event enable.
   uint8 idx_en;      // index event enable.
   uint8 spl_en;      // sample indicator event enable.
   uint8 resv[3];
} daq_ctr_evt_t;

typedef struct _daq_ctr_num {
   uint32 reload;      // Counter reload number
   uint32 pulse;       // Counter pulse number
   uint32 primary;     // Counter primary number
   uint32 secondary;   // Counter secondary number
} daq_ctr_num_t;

typedef struct _daq_ctr_val {
   uint32 primary;    // Counter primary value
   uint32 secondary;  // Counter secondary value
   uint32 emb_val;    // Counter embedded counter value
   uint32 value;      // Counter value
} daq_ctr_val_t;

typedef struct _daq_ctr_pkt {
   daq_pkt_hdr_t header;

   union {    
      //
      // Counter get/set buffered acquisition configuration
      struct {
         uint8 mod; 
         uint8 __resv[3];
      } bfd_mod[CTR_CH_CNT_MAX];

      //
      // Set/get SigCfg: Set/get counter signal configuration
      daq_ctr_sig_t sig_cfg[CTR_CH_CNT_MAX];

      //
      // Counter get/set operation mode
      daq_ctr_opm_t op_mod[CTR_CH_CNT_MAX];

      //
      // Counter get/set filter configuration
      daq_ctr_flt_t flt_cfg[CTR_CH_CNT_MAX];

      //
      // Counter get value
      daq_ctr_val_t ctr_val[CTR_CH_CNT_MAX];

      //
      // Set/get Nums: Set/get counter numbers
      daq_ctr_num_t ctr_num[CTR_CH_CNT_MAX];

      //
      // Counter get/set event enable
      daq_ctr_evt_t ctr_evt;

      //
      // Counter get/set arm signal
      struct {
         uint32 arm;
      } ctr_arm [CTR_CH_CNT_MAX];


      // 
      // padding to LS_PKT_SIZE bytes packet
      uint8 pad[LS_MSG_SIZE];
   };
} daq_ctr_pkt_t;

//----------------------------------------------------------------------
// DAQ USB Protocol: PIPE 2, High-speed, Notification (EP: 0x83)
//----------------------------------------------------------------------
//
// DAQ USB event notification
typedef struct _daq_ntf_pkt {
   daq_pkt_hdr_t header;

   union {
      //
      // System module insertion
      uint32 mod_isrt;  // Each bit for a module 

      //
      // System module removal
      uint32 mod_rmov; // Each bit for a module 

      //
      // System module fault 0
      uint32 mod_ovc;    // Module over-current indicator, each bit for a module 
      uint32 mod_fault;  // Module other faults(1 ~ 15)

      //
      // System time stamp FIFO data
      struct {
         uint32 ts_lo;  // Time stamp value
         uint32 ts_hi;

         // Acquisition status indicators
         union {
            uint32 acq_ind;
            struct {
               uint8 acq0_sta : 1;
               uint8 acq0_stp : 1;

               uint8 acq1_sta : 1;
               uint8 acq1_stp : 1;

               uint8 acq2_sta : 1;
               uint8 acq2_stp : 1;

               uint8 acq3_sta : 1;
               uint8 acq3_stp : 1;
            };
         };
      } ts_data;

      //
      // Module acquisition status
      struct {
         uint32 fin : 1;
      } acq_stat;

      //
      // Module FIFO status
      struct {
         uint8 __resv0 : 1;
         uint8 in_ful  : 1;         // Input FIFO is full.
         uint8 __resv1 : 2;

         uint8 out_emp : 1;         // Output FIFO is empty.
         uint8 __resv2 : 1;         
         uint8 out_dct : 1;         // Output FIFO data count threshold point detected.
      } fifo_stat[MOD_FIFO_CNT];

      //
      // Analog input fault 0~15
      uint32 ai_fault;  // Each bit for a channel

      //
      // Analog output fault 0~15
      uint32 ao_fault;  // Each bit for a channel

      //
      // Digital input fault 0~15
      uint32 di_fault;  // Each bit for a channel

      //
      // Digital input rising/falling edge
      uint8 di_ris[DIO_PT_CNT_MAX];
      uint8 di_fal[DIO_PT_CNT_MAX];

      //
      // Digital input pattern match
      uint8 di_pm[DIO_PT_CNT_MAX];

      //
      // Digital output fault 0~15
      uint32 do_fault;  // Each bit for a channel

      //
      // Counter fault 0~15
      uint32 ctr_fault;  // Each bit for a channel

      //
      // Counter operation finished
      uint32 ctr_op_fin; // Each bit for a channel

      //
      // Counter output rising edge
      uint32 ctr_idx; // Each bit for a channel

      //
      // Counter overflow
      uint32 ctr_ovf; // Each bit for a channel

      //
      // Counter underflow
      uint32 ctr_udf; // Each bit for a channel

      // 
      // padding to NTF_PKT_SIZE bytes packet
      uint8  pad[NTF_MSG_SIZE];
   };
} daq_ntf_pkt_t;

//----------------------------------------------------------------------
// DAQ USB Protocol: PIPE 3, High-speed data transition (EP: 0x4/0x84)
//----------------------------------------------------------------------
//
// DAQ USB High-speed data transition
typedef struct _daq_hs_pkt {
   daq_pkt_hdr_t header;

   union {      
      //
      // DIO buffered samples, in DWORDs.
      daq_dio_spl_t    dio_spl[1];

      daq_dio_spl_ex_t dio_spl_ex[1];

      //
      // General: Variable length array for buffered samples (AI/AO/DIO/CTR, etc.)
      uint32 bfd_data[1]; 

      // 
      // padding to HS_PKT_SIZE bytes packet
      uint8 pad[HS_MSG_SIZE];
   };
} daq_hs_pkt_t; 

//----------------------------------------------------------------------
// DAQ USB Protocol: PIPE 4, High-speed, Flash update (EP: 0x5/0x85)
//----------------------------------------------------------------------
//
#define FLH_CMD_WRITE 0
#define FLH_CMD_READ  1
#define FLH_CMD_ERASE 2

typedef struct _daq_flh_pkt {
   daq_pkt_hdr_t header;

   union {
      //
      // Module write flash
      struct {
         uint32 cmd  : 4;
         uint32 addr : 28;    // Flash update start address, Must be 16-bytes aligned
         uint16 len;          // Flash update length, Must be 8-bytes aligned
         uint8  busy;         // bit#7: Flash update busy indicator(for Read)
         uint8  crcc;         // bit#7: Checksum matched indicator(for Read)
         uint32 crc;          // Flash update checksum
         uint8  data[1];      // Variable length array for flash data
      } flh_rw;

      // 
      // padding to HS_PKT_SIZE bytes packet
      uint8 pad[FLH_MSG_SIZE];   
   };   
} daq_flh_pkt_t; 


#endif
