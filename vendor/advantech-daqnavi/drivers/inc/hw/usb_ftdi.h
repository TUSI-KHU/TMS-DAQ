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

#ifndef _ADVANTECH_DAQ_USB_FTDI_PROTOCOL_DEFINE
#define _ADVANTECH_DAQ_USB_FTDI_PROTOCOL_DEFINE

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
   uint16  fifo_clock;
   uint16  power_attributes;
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
// MSG ID
#define MSG_NO_REPLY    0
#define MSG_NEED_REPLY  1

//
// USB packet size
#define LS_PKT_SIZE     512
#define LS_MSG_SIZE     (LS_PKT_SIZE - 8)

#define HS_PKT_SIZE     512
#define HS_MSG_SIZE     (HS_PKT_SIZE - 8)

#define NTF_PKT_SIZE    64

//
// Class/method: Global
#define CLAZZ_GLOBAL    0
#  define M_GLB_HEARTBEAT  0x00

//
// Class/method: Register
#define CLAZZ_REGISTER  0x1
#  define M_REG_BLK_OUTB   0x01
#  define M_REG_BLK_OUTW   0x11
#  define M_REG_BLK_OUTD   0x21
#  define M_REG_BLK_INW    0x12
#  define M_REG_BLK_IND    0x22

#  define M_REG_RDM_OUTB   0x03
#  define M_REG_RDM_OUTW   0x13
#  define M_REG_RDM_OUTD   0x23
#  define M_REG_RDM_INB    0x04
#  define M_REG_RDM_INW    0x14
#  define M_REG_RDM_IND    0x24

//
// Class/method: Device
#define CLAZZ_DEVICE    0x2
#  define M_DEV_AMSI_EXTCLK_SET   0x14
#  define M_DEV_AMSI_EXTCLK_GET   0x15
#  define M_DEV_AMSI_SLOT_SET     0x16
#  define M_DEV_HW_INFO_GET       0x17
#  define M_DEV_WDT_EN_SET        0x18
#  define M_DEV_WDT_EN_GET        0x19
#  define M_DEV_WDT_INFO_SET      0x1A
#  define M_DEV_WDT_INFO_GET      0x1B
#  define M_DEV_WDT_FLAG_CLR      0x1C

#  define M_DEV_SW_TRG_SET        0x28
#  define M_DEV_SW_TRG_GET        0x29

#  define M_DEV_ANA_TRG_SET       0x2A
#  define M_DEV_ANA_TRG_GET       0x2B
#  define M_DEV_TRG_OUT_SET       0x2C
#  define M_DEV_TRG_OUT_GET       0x2D

#  define M_DEV_CAL_SRC_SET       0x38
#  define M_DEV_CAL_SRC_GET       0x39
#  define M_DEV_CAL_CMD_WR        0x3A
#  define M_DEV_CAL_CMD_RD        0x3B

#  define M_DEV_TS_CNT_CLR        0x40
#  define M_DEV_TS_CNT_GET        0x41

#  define M_DEV_REF_CLK_SET       0x48
#  define M_DEV_REF_CLK_GET       0x49
#  define M_DEV_DDS_WR            0x4A

#  define M_DEV_TS_BFD_SAMP       0x80   // Return buffered time stamp sample
//
// Class/method: AI
#define CLAZZ_AI        0x0100
#  define M_AI_TRG_CFG_SET    0x08
#  define M_AI_TRG_CFG_GET    0x09
#  define M_AI_TRG_DLY_SET    0x0A
#  define M_AI_TRG_DLY_GET    0x0B
#  define M_AI_CLK_CFG_SET    0x0C
#  define M_AI_CLK_CFG_GET    0x0D

#  define M_AI_CH_EN_SET      0x18
#  define M_AI_CH_EN_GET      0x19
#  define M_AI_FIFO_THR_SET   0x1A
#  define M_AI_FIFO_THR_GET   0x1B
#  define M_AI_FIFO_CLR       0x1C
#  define M_AI_FIFO_CNT_GET   0x1D

#  define M_AI_ADC_WR         0x28
#  define M_AI_ADC_RD         0x29

#  define M_AI_CH_CFG_SET     0x30
#  define M_AI_CH_CFG_GET     0x31

#  define M_AI_SAMPLE_RD      0x33
#  define M_AI_FAULT_RD       0x35

#  define M_AI_BFD_SAMP       0x80   // Return buffered AI sample

//
// Class/method: AO
#define CLAZZ_AO        0x0200
#  define M_AO_TRG_CFG_SET    0x08
#  define M_AO_TRG_CFG_GET    0x09
#  define M_AO_TRG_DLY_SET    0x0A
#  define M_AO_TRG_DLY_GET    0x0B
#  define M_AO_CLK_CFG_SET    0x0C
#  define M_AO_CLK_CFG_GET    0x0D

#  define M_AO_CH_EN_SET      0x18
#  define M_AO_CH_EN_GET      0x19
#  define M_AO_FIFO_THR_SET   0x1A
#  define M_AO_FIFO_THR_GET   0x1B
#  define M_AO_FIFO_CLR       0x1C
#  define M_AO_FIFO_CNT_GET   0x1D

#  define M_AO_DAC_WR         0x28
#  define M_AO_DAC_RD         0x29
#  define M_AO_DAC_CLK_SET    0x2A
#  define M_AO_DAC_CLK_GET    0x2B

#  define M_AO_INTPL_FCTR_SET 0x2A
#  define M_AO_INTPL_FCTR_GET 0x2B

#  define M_AO_CH_CFG_SET     0x30
#  define M_AO_CH_CFG_GET     0x31
#  define M_AO_SAMPLE_WR      0x32
#  define M_AO_SAMPLE_RD      0x33
#  define M_AO_FAULT_RD       0x35

#  define M_AO_BFD_SAMP       0x80   // Write buffered AO sample

//
// Class/method: DIO
#define CLAZZ_DIO        0x0300
#  define M_DI_EVT_ENABLE        0x04
#  define M_DI_EVT_EDGE_SET      0x05
#  define M_DI_EVT_TYPE_SET      0x06

//#  define M_DO_PORT_WRITE        0x10 // Phase out ???
//#  define M_DI_PORT_READ         0x11 // Phase out ???
//#  define M_DO_PORT_READ         0x12 // Phase out ???

#  define M_DI_TRG_CFG_SET       0x18
#  define M_DI_TRG_CFG_GET       0x19
#  define M_DI_TRG_DLY_SET       0x1A
#  define M_DI_TRG_DLY_GET       0x1B
#  define M_DI_CLK_CFG_SET       0x1C
#  define M_DI_CLK_CFG_GET       0x1D

#  define M_DI_CH_EN_SET         0x28
#  define M_DI_CH_EN_GET         0x29
#  define M_DI_FIFO_THR_SET      0x2A
#  define M_DI_FIFO_THR_GET      0x2B
#  define M_DI_FIFO_CLR          0x2C
#  define M_DI_FIFO_CNT_GET      0x2D

#  define M_DI_PORT_CFG_SET      0x30
#  define M_DI_PORT_CFG_GET      0x31

#  define M_DI_SAMPLE_RD         0x33
#  define M_DI_FAULT_RD          0x35

#  define M_DO_TRG_CFG_SET       0x48
#  define M_DO_TRG_CFG_GET       0x49
#  define M_DO_TRG_DLY_SET       0x4A
#  define M_DO_TRG_DLY_GET       0x4B
#  define M_DO_CLK_CFG_SET       0x4C
#  define M_DO_CLK_CFG_GET       0x4D

#  define M_DO_CH_EN_SET         0x58
#  define M_DO_CH_EN_GET         0x59
#  define M_DO_FIFO_THR_SET      0x5A
#  define M_DO_FIFO_THR_GET      0x5B
#  define M_DO_FIFO_CLR          0x5C
#  define M_DO_FIFO_CNT_GET      0x5D

#  define M_DO_SAMPLE_WR         0x62
#  define M_DO_SAMPLE_RD         0x63
#  define M_DO_FAULT_RD          0x65

#  define M_DI_BFD_SAMP          0x80   // Return buffered DI sample
#  define M_DO_BFD_SAMP          0x81   // Write buffered DO sample

//
// Class/method: Counter
#define CLAZZ_CTR         0x0400
#  define M_CTR_SIG_CFG_SET      0x08
#  define M_CTR_SIG_CFG_GET      0x09
                                
#  define M_CTR_MODE_SET         0x18
#  define M_CTR_MODE_GET         0x19
#  define M_CTR_FIFO_THR_SET     0x1A
#  define M_CTR_FIFO_THR_GET     0x1B
#  define M_CTR_FIFO_CLR         0x1C
#  define M_CTR_FIFO_CNT_GET     0x1D
                                
#  define M_CTR_NUM_SET          0x30
#  define M_CTR_NUM_GET          0x31
                                
#  define M_CTR_VAL_GET          0x33

#  define M_CT0_BFD_IN           0x80   // Return buffered counter input sample for channel 0
#  define M_CT0_BFD_OUT          0x81   // Write buffered counter output sample for channel 0
#  define M_CT1_BFD_IN           0x82   // Return buffered counter input sample for channel 1
#  define M_CT1_BFD_OUT          0x83   // Write buffered counter output sample for channel 1
#  define M_CT2_BFD_IN           0x84   // Return buffered counter input sample for channel 2
#  define M_CT2_BFD_OUT          0x85   // Write buffered counter output sample for channel 2
#  define M_CT3_BFD_IN           0x86   // Return buffered counter input sample for channel 3
#  define M_CT3_BFD_OUT          0x87   // Write buffered counter output sample for channel 3

//----------------------------------------------------------------------
// Structure for USB communication

//----------------------------------------------------------------------
// DAQ USB Protocol: FIFO 1, Low-speed data request/response(EP: 0x2/0x82)
//----------------------------------------------------------------------
//
// Packet Header of Low-Speed Data Request and Response
typedef struct _daq_ls_hdr {
   uint16 msg_size; // Size of packet excluding header information (first 8 bytes). This is always 504.
   uint8  msg_id;   
   uint8  method;
   uint16 clazz;
   uint16 object;
} daq_ls_hdr_t;

typedef struct _daq_trg_cfg {
   uint8 src: 7; // trigger source
   uint8 edg: 1; // active edge
} daq_trg_cfg_t;

//--------------------------------------------
// CLAZZ: Device
//--------------------------------------------
typedef struct _daq_dev_pkt {
   daq_ls_hdr_t header;

   union {    
      // DevGetHWInfo: Get hardware information
      struct {
         uint32 board_id : 4;
         uint32     resv : 4;
         uint32  pcb_ver : 24;

         uint32 pld_ver;
         uint32 primary_addr;
         uint32 golden_addr;
         uint32 flash_size;
      } hw_info;

      // 
      // Set/Get WdtEnable: Set/get fail-safe output enable and timeout period 
      struct {
         uint8  ao_en[8];
         uint8  do_en[16];
         uint8  ct_en;
         uint8  timeout;
      } wdt_enable;

      // 
      // Set/Get WdtInfo: Set/get fail-safe output values
      struct {
         uint8  ao_val[8];     
         uint8  do_val[16];
         uint8  ct_val;
         uint8  fs_flg; // for response:  it becomes set after a fail-safe event occurs.
      } wdt_info;

      //
      // DevClrWdtFlag: Clear fail-safe output event indicator
      struct {
         uint32 dummy;
      } wdt_flag;
      
      // 
      // Set/Get SwTrig: Generate software triggers
      struct {
         uint8 trigger; // Writing 1 to these registers generates the corresponding software triggers.
      } sw_trg;

      //
      // Set/Get ATrgCfg: Set analog trigger configuration
      struct {
         uint32 thrs;           // trigger threshold
         uint32 hyst : 24;      // trigger hysteresis
         uint32 src  : 7;       // trigger source
         uint32 edge : 1;       // trigger active edge
      } ana_trg[2];

      // 
      // Set/get TrigOutCfg: Set/get trigger output configuration
      struct {
         uint8 src : 7;  // Trigger output source 
         uint8 inv : 1;  // Trigger output logic inversion
      } trg_out[2];

      //
      // Set/get CalSrc: calibration source configuration
      struct {
         uint8  cal_src;         // Calibration source select
         uint8  resv[3];
         uint8  ai_cal_en[8];    // Calibration enable for each AI channel.
         uint8  ao_cal_en[8];    // Calibration enable for each AO channel.
      } cal_cfg;

      // 
      // DevWriteCalCmd/DevReadCalCmd: Calibration write/read command
      struct {
         uint32 cmd : 8;
         uint32 data: 24;
      } cal_cmd;

      //
      // DevClrTsCnt: Clear time stamp counter
      struct {
         uint32 dummy;
      } ts_cnt_clr;

      //
      // DevGetTsCnt: Get time stamp counter value
      struct {
         uint32 lo;
         uint32 hi : 24;
      } ts_cnt;

      // 
      // Set/get RefClkSrc: reference clock source
      struct {
         uint8 src : 1; // Reference clock source select
      } ref_clk;

      //
      // DevWriteDds: Write DDS registers
      struct {
         uint16 cmd;
      } dds_wr;

      // 
      // padding to LS_PKT_SIZE bytes packet
      uint8 pad[LS_MSG_SIZE];
   };
} daq_dev_pkt_t;

//--------------------------------------------
// CLAZZ: AI
//--------------------------------------------
typedef struct _daq_ai_pkt {
   daq_ls_hdr_t header;

   union {    
      //
      // Set/get TrigCfg: Set/get AI trigger configuration
      struct {
         uint8         retrg   : 1;  // AI re-trigger enable
         uint8         resv0   : 3;
         uint8         sta_fd  : 1;  // ADC filter group delay enable for start trigger
         uint8         stp_fd  : 1;  // ADC filter group delay enable for stop trigger.
         uint8         resv1   : 1;
         uint8         flt_dly : 1;  // AI trigger filter delay
         uint8         resv2[3];

         daq_trg_cfg_t start[2];     // start trigger
         daq_trg_cfg_t stop[2];      // stop trigger
         daq_trg_cfg_t index[2];     // index trigger
      } trg_cfg;

      //
      // Set/get DlyNum: Set/get AI delay to start/stop sample number
      struct {
         uint32 sta_dly;  // AI delay to start number
         uint32 stp_dly;  // AI delay to stop number

         // for response
         uint32 sta_cnt;  // AI delay to start counter
         uint32 stp_cnt;  // AI delay to stop counter
      } delay;

      //
      // Set/get ClkCfg: Set/get AI clock configuration
      struct {
         uint8 cck_src : 7; // AI conversion clock source and active edge
         uint8 cck_edg : 1; // AI conversion clock active edge
         uint8 sck_src : 7; // AI scan clock source and active edge
         uint8 sck_edg : 1; // AI scan clock active edge
         uint16    resv;

         uint32 sck_div;    // Internal time-base divisor for AI scan clock
         uint32 cck_div;    // Internal time-base divisor for AI conversion clock
         uint32 iter_num;   // AI iteration number

         // for response
         uint32 iter_cnt;   // AI iteration counter
         uint32 sck_cnt;    // AI scan clock counter
      } clk_cfg;

      //
      // Set/get ChEnable: Set/get AI channel enable
      struct {
         uint8 ch_sta;        // AI start channel number (for channel scanning type)
         uint8 ch_stp;        // AI stop channel number (for channel scanning type)
         uint8 ch_cur;        // for response only, AI current channel number (for channel scanning type)
         uint8 chsc_ffen : 1; // AI FIFO enable (for channel scanning type)
         uint8 simu_ffen[8];  // AI FIFO enable (for simultaneous sampling type)
      } ch_en;

      //
      // Set/get FifoThr: Set/get AI data FIFO threshold value
      struct {
         uint8 threshold;     // AI data FIFO threshold value
      } fifo_thr;

      //
      // ClrFifo: Clear AI data FIFO
      struct {
         uint32 dummy;
      } fifo_clr;

      //
      // GetFifoCnt: Get AI data FIFO sample count
      struct {
         // for response only
         uint16 count;        // AI data FIFO sample count
      } fifo_cnt;

      //
      // Write/Read ADC: Write/read ADC registers
      struct {
         uint32 adc_sel;       // ADC select for writing/reading registers
         uint32 addr;          // ADC write/read address
         uint32 data;          // ADC write/read data
      } adc_rw;

      //
      // Set/get ChCfg: Set/get AI channel configuration
      struct {
         uint8 gain;
         uint8 psu_diff : 1; // Pseudo-differential mode enabled
         uint8 dc_cpl   : 1; // DC coupling enable
         uint8 iepe     : 1; // Integrated Electronics Piezo-Electric (IEPE) enable
         uint8 resv[2];
      } ch_cfg[64];

      //
      // ReadSamples: Read instant AI samples
      struct {
         // for response only
         uint32 data[64];
      } ch_samp;

      //
      // ReadFault: Read AI fault indicators
      struct {
         // for response only
         uint32 fault[64];     // channel fault indicators
      } ch_fault;

      // 
      // padding to LS_PKT_SIZE bytes packet
      uint8 pad[LS_MSG_SIZE];
   };
} daq_ai_pkt_t;

//--------------------------------------------
// CLAZZ: AO
//--------------------------------------------
typedef struct _daq_ao_pkt {
   daq_ls_hdr_t header;

   union {    
      //
      // Set/get TrigCfg: Set/get AO trigger configuration
      struct {
         uint8         retrg  : 1;  // AO re-trigger enable
         uint8         resv1[3];
         daq_trg_cfg_t start[2];     // start trigger
         daq_trg_cfg_t stop[2] ;     // stop trigger
         daq_trg_cfg_t index[2];     // index trigger
      } trg_cfg;

      //
      // Set/get DlyNum: Set/get AO delay to start/stop sample number
      struct {
         uint32 sta_dly;  // AO delay to start number
         uint32 stp_dly;  // AO delay to stop number

         // for response
         uint32 sta_cnt;  // AO delay to start counter
         uint32 stp_cnt;  // AO delay to stop counter
      } delay;

      //
      // Set/get ClkCfg: Set/get AO clock configuration
      struct {
         uint8  cck_src : 7; // AO conversion clock source and active edge
         uint8  cck_edg : 1; // AO conversion clock active edge
         uint8  resv[7];
         uint32 cck_div;     // Internal time-base divisor for AO conversion clock
      } clk_cfg;

      //
      // Set/get Intrpl: Set/get AO interpolation factor
      struct {
         uint8 factor;
      } intpl;

      //
      // Set/get ChEnable: Set/get AO channel enable
      struct {
         uint8 resv[4];
         uint8 fifo_en[8];  // AO FIFO enable (for simultaneous sampling type)
      } ch_en;

      //
      // Set/get FifoThr: Set/get AO data FIFO threshold value
      struct {
         uint16 threshold;     // AO data FIFO threshold value
      } fifo_thr;

      //
      // ClrFifo: Clear AO data FIFO
      struct {
         uint32 dummy;
      } fifo_clr;

      //
      // GetFifoCnt: Get AO data FIFO sample count
      struct {
         // for response only
         uint16 count;        // AO data FIFO sample count
      } fifo_cnt;

      //
      // Write/Read DAC: Write/read DAC registers
      struct {
         uint32 dac_sel;       // DAC select for writing/reading registers
         uint32 addr;          // DAC write/read address
         uint32 data;          // DAC write/read data
      } dac_rw;

      //
      // Set/get DACClk
      struct {
         uint8 sys_clk;       // DAC system clock frequency configuration
         uint8 bit_clk;       // DAC bit clock frequency configuration
      } dac_clk;              

      //
      // Set/get ChCfg: Set/get AO channel configuration
      struct {
         uint32 out_en;          // Output enable for all AO channels
         struct {
            uint8 gain;
            uint8 psu_diff : 1; // Pseudo-differential mode enabled
				uint8 clsl : 1;	  // Clear select for each AO channel
            uint8 resv[2];
         } cfg[64];
      } ch_cfg;

      //
      // Write/Read Samples: Write/Read instant AO samples
      struct {
         uint32 data[64];
      } ch_samp;

      //
      // ReadFault: Read AO fault indicators
      struct {
         // for response only
         uint32 fault[64];     // channel fault indicators
      } ch_fault;

      // 
      // padding to LS_PKT_SIZE bytes packet
      uint8 pad[LS_MSG_SIZE];
   };
} daq_ao_pkt_t;

//--------------------------------------------
// CLAZZ: DIO
//--------------------------------------------
typedef struct _daq_dio_pkt {
   daq_ls_hdr_t header;

   union {    
      //
      // EventEnable: Set DI interrupt enable
      struct {
         uint8 enable[16]; // DI interrupt enable
      } int_en;

      //
      // EventConfigEdge: Set DI interrupt edge
      struct {
         uint8 edge[16]; // DI interrupt edge
      } int_edge;

      //
      // EventConfig: Set DI interrupt configuration(int type)
      struct {
         uint8 type[16]; // DI interrupt configuration: 0: edge; 1: change of status; 2: pattern match
      } int_type;

      //
      // Set/get TrigCfg: Set/get DI/DO trigger configuration
      struct {
         uint8         retrig  : 1;  // DI/DO re-trigger enable
         uint8         resv1[3];
         daq_trg_cfg_t start[2];     // start trigger
         daq_trg_cfg_t stop[2] ;     // stop trigger
         daq_trg_cfg_t index[2];     // index trigger
      } trg_cfg;

      //
      // Set/get DlyNum: Set/get DI/DO delay to start/stop sample number
      struct {
         uint32 sta_dly;  // DI/DO delay to start number
         uint32 stp_dly;  // DI/DO delay to stop number

         // for response
         uint32 sta_cnt;  // DI/DO delay to start counter
         uint32 stp_cnt;  // DI/DO delay to stop counter
      } delay;

      //
      // Set/get ClkCfg: Set/get DI/DO clock configuration
      struct {
         uint8  cck_src : 7; // DI/DO conversion clock source and active edge
         uint8  cck_edg : 1; // DI/DO conversion clock active edge
         uint8  resv[7];
         uint32 cck_div;     // Internal time-base divisor for AO conversion clock
      } clk_cfg;

      //
      // Set/get ChEnable: Set/get DI/DO channel enable
      struct {
         uint8 resv[4];
         uint8 fifo_en;  // DI/DO FIFO enable (in DWORD)
      } ch_en;

      //
      // Set/get FifoThr: Set/get DI/DO data FIFO threshold value
      struct {
         uint8 threshold;     // DI/DO data FIFO threshold value
      } fifo_thr;
      
      //
      // ClrFifo: Clear DI/DO data FIFO
      struct {
         uint32 dummy;
      } fifo_clr;

      //
      // GetFifoCnt: Get DI/DO data FIFO sample count
      struct {
         // for response only
         uint16 count;        // DI/DO data FIFO sample count
      } fifo_cnt;

      //
      // Set/get PortCfg: Set/get DI port configuration
      struct {
         uint8 flt_dur;  // digital filter duration
         uint8 flt_en;   // digital filter enable
         uint8 ris_en;   // rising edge detection enable
         uint8 fal_en;   // falling edge detection enable
      } port_cfg[16];      

      //
      // Write/Read Samples: Write/Read instant DI/DO samples
      struct {
         uint8 data[16];
      } port_samp;

      //
      // ReadFault: Read AO fault indicators
      struct {
         uint8 resv[4];

         // for response only
         uint8 fault[16];     // port fault indicators
      } fault_rd;

      // 
      // padding to LS_PKT_SIZE bytes packet
      uint8 pad[LS_MSG_SIZE];
   };
} daq_dio_pkt_t;

//--------------------------------------------
// CLAZZ: CT (Counter)
//--------------------------------------------
typedef struct _daq_ctr_pkt {
   daq_ls_hdr_t header;

   union {    
      //
      // Set/get SigCfg: Set/get counter signal configuration
      struct {
         uint8 clk_src : 7;  // Counter clock source and active edge
         uint8 clk_edg : 1; 
         uint8 resv0[2];
         uint8 arm_src : 7;  // Counter arm source and active edge
         uint8 arm_edg : 1;

         uint8 sck_src : 7;  // Counter sample clock source and active edge
         uint8 sck_edg : 1; 
         uint8 resv1[3];

         uint8 flt_dur;      // Counter digital filter duration
         uint8 flt_clk : 1;  // Digital filter enable for counter clock signal.
         uint8 resv2   : 2;
         uint8 flt_arm : 1;  // Digital filter enable for counter arm signal
         uint8 flt_sck : 1;  // Digital filter enable for counter sample clock signal.
         uint8 resv3[2];

         uint8 resv4[4];
      } sig_cfg[8];

      //
      // Set/get Mode: Set/get counter operation mode
      struct {
         uint8 mode;         // Counter operation mode
         uint8 resv[2];
         uint8 type;         // Counter data type: No buffer or Sample clock buffered
      } ctr_cfg[8];

      //
      // Set/get FifoThr: Set/get counter data FIFO threshold value
      struct {
         uint32 thr;         // Counter input data FIFO threshold value
      } fifo_thr[8];

      //
      // ClrFifo: Clear counter data FIFO
      struct {
         uint32 clr;         // Counter input data FIFO clear
      } fifo_clr;

      //
      // GetFifoCnt: Get counter FIFO sample count
      struct {
         // for response only
         uint32 cnt;      // Counter input data FIFO sample count
      } fifo_cnt[8];

      //
      // Set/get Nums: Set/get counter numbers
      struct {
         uint32 reload;      // Counter reload number
         uint32 primary;     // Counter primary number
         uint32 secondary;   // Counter secondary number
         uint32 pulse;       // Counter pulse number
      } ctr_num[8];

      //
      // GetVals: Get counter values
      struct {
         uint32 primary;     // Counter primary value
         uint32 secondary;   // Counter secondary value
         uint32 emb_ct;      // Counter embedded counter value
         uint32 value;       // Counter value
      } ctr_val[8];

      // 
      // padding to LS_PKT_SIZE bytes packet
      uint8 pad[LS_MSG_SIZE];
   };
} daq_ctr_pkt_t;

//----------------------------------------------------------------------
// DAQ USB Protocol: FIFO 2, High-speed, Notification (EP: 0x83)
//----------------------------------------------------------------------
//
// DAQ usb event notification
typedef struct _daq_ntf_pkt {
   struct _ntf {
      uint8  di_state[16];
      uint8  di_data[16];

      union {
         uint16 state;
         struct {
            uint16 resv0  : 1;
            uint16 ff_full: 1;
         };
      } ai;

      union {
         uint16 state;
         struct {
            uint16 ff_thr : 1; // AO FIFO threshold detected interrupt flag
            uint16 ff_ept : 1; // AO FIFO empty interrupt flag
         };
      } ao;
   } ntf;

   // 
   // padding to NTF_PKT_SIZE bytes packet
   uint8  pad[NTF_PKT_SIZE - sizeof(struct _ntf)];
} daq_ntf_pkt_t;

//----------------------------------------------------------------------
// DAQ USB Protocol: FIFO 3, High-speed data transition (EP: 0x4/0x84)
//----------------------------------------------------------------------
//
// Packet Header of Low-Speed Data Request and Response
typedef struct _daq_hs_hdr {
   uint16 clazz;
   uint8  msg_id;   
   uint8  method;
   uint32 msg_size; // Size of packet excluding header information (first 8 bytes) and padding bytes. 
} daq_hs_hdr_t;

typedef struct _daq_hs_pkt {
   daq_hs_hdr_t header;

   union {
      //
      // DevTsBufSamples: Return buffered time stamp sample
      struct {
         uint32 ts_lo;  // Time stamp value
         uint32 ts_hi;

         uint8 ai_sta : 1;
         uint8 ai_stp : 1;
         uint8 ai_idx : 1;
         uint8 resv0  : 1;

         uint8 ao_sta : 1;
         uint8 ao_stp : 1;
         uint8 ao_idx : 1;
         uint8 resv1  : 1;

         uint8 di_sta : 1;
         uint8 di_stp : 1;
         uint8 di_idx : 1;
         uint8 resv2  : 1;

         uint8 do_sta : 1;
         uint8 do_stp : 1;
         uint8 do_idx : 1;
         uint8 resv3  : 1;
      } ts_samp;

      //
      // General: Variable length array for buffered samples (AI/AO/DIO/CTR, etc.)
      uint32 bfd_samp[1]; 

      // 
      // padding to HS_PKT_SIZE bytes packet
      uint8 pad[HS_MSG_SIZE];
   };
} daq_hs_pkt_t; 

//----------------------------------------------------------------------
// DAQ USB Protocol: FIFO 4, High-speed, Flash update (EP: 0x5/0x85)
//----------------------------------------------------------------------
typedef union _daq_flh_pkt {
   struct {
      uint8  cmd    : 2;  // Flash update command
      uint8  resv0  : 5;
      uint8  crcc   : 1;  // Response only, checksum matched indicator 
      uint8  resv1[3];

      // Flash update start address, the lowest 8bit must be zero (the address must be 256bytes aligned).
      uint32 addr;
      uint32 length : 9;  // Flash update length, bit0~8
      uint32 crc;         // Flash update checksum

      //
      // Variable length array for flash data
      uint8  data[1];
   } flash;

   // 
   // padding to HS_PKT_SIZE bytes packet
   uint8 pad[HS_PKT_SIZE];   
} daq_flh_pkt_t; 

#endif  // _ADVANTECH_DAQ_USB_FTDI_PROTOCOL_DEFINE

