/*
 * Ioctls.h
 *
 *  Created on: 2011-8-29
 *      Author: rocky
 */

#ifndef DAQNAVI_IOCTL_DEFINITION
#define DAQNAVI_IOCTL_DEFINITION

#include <linux/ioctl.h>

#ifdef DN4_DRIVER

//******************************************************************************************
//                                                                                         *
// IOCTL for DAQNAVI 4                                                                     *
//                                                                                         *
//******************************************************************************************

// Magic Number of IOCTLs
#define IOCTL_MAGIC_KLIB              'k'
#define IOCTL_MAGIC_DEV               'a'
#define IOCTL_MAGIC_AI                'b'
#define IOCTL_MAGIC_AO                'c'
#define IOCTL_MAGIC_DIO               'd'
#define IOCTL_MAGIC_CT                'e'
#define IOCTL_MAGIC_DNL               'l'

#define DAQCTL_RD(magic, number)      _IO(magic, number)
#define DAQCTL_WR(magic, number)      _IO(magic, number)
#define DAQCTL_NB(magic, number)      _IO(magic, number)

#define SIZEOF_VLST(st, field, vlen)  (offset_of(st, field) + (vlen) * sizeof(((st*)0)->field[0]))

#define DECL_64COMPAT(type, name)     union { type name; int64 _pad##name; }

//******************************************************************************************
//                                                                                         *
// IOCTL for klib operation                                                                *
//                                                                                         *
//******************************************************************************************
// Input: <None>
// Output: Handle of event
#define IOCTL_KLIB_CREATE_EVENT        DAQCTL_RD(IOCTL_MAGIC_KLIB, 1)

// Input: Handle of event
// Output: <None>
#define IOCTL_KLIB_CLOSE_EVENT         DAQCTL_RD(IOCTL_MAGIC_KLIB, 2)

// Input: Handle of event
// Output: <None>
#define IOCTL_KLIB_SET_EVENT           DAQCTL_RD(IOCTL_MAGIC_KLIB, 3)

// Input: Handle of event
// Output: <None>
#define IOCTL_KLIB_RESET_EVENT         DAQCTL_RD(IOCTL_MAGIC_KLIB, 4)

// Input: KLIB_WAIT_EVENT.
// Output: <None>
typedef struct KLIB_WAIT_EVENT {
   int32  Result;
   uint32 Timeout;
   int32  WaitAll;
   uint32 Count;
   DECL_64COMPAT(HANDLE*, Events);
} KLIB_WAIT_EVENT, *PKLIB_WAIT_EVENT;

#define IOCTL_KLIB_WAIT_EVENT          DAQCTL_RD(IOCTL_MAGIC_KLIB, 5)

#ifndef ISA_NAME_MAX_LEN
#define ISA_NAME_MAX_LEN  32
#endif

// Input: pointer of structure ISA_DEV_INFO
// Output: <None>
typedef struct ISA_DEV_INFO {
   char   DriverName[ISA_NAME_MAX_LEN];
   char   DeviceName[ISA_NAME_MAX_LEN];
   uint32 IoBase;
   uint32 Irq;
   uint32 Dma;
} ISA_DEV_INFO, *PISA_DEV_INFO;

// Input:
// Output:
#define IOCTL_KLIB_ADD_DEV             DAQCTL_RD(IOCTL_MAGIC_KLIB, 6)
#define IOCTL_KLIB_REMOVE_DEV          DAQCTL_RD(IOCTL_MAGIC_KLIB, 7)

// Input: Event name
// Output: Handle of event
#define EVENT_NAME_LEN_MAX  31

typedef struct NAMED_EVENT {
   char Name[EVENT_NAME_LEN_MAX + 1];
   DECL_64COMPAT(HANDLE, Handle);
} NAMED_EVENT, *PNAMED_EVENT;

#define IOCTL_KLIB_CREATE_EVENT_NAMED  DAQCTL_RD(IOCTL_MAGIC_KLIB, 8)


//******************************************************************************************
//                                                                                         *
// IOCTL for device operation                                                              *
//                                                                                         *
//******************************************************************************************

// input:  an array of struct USER_EVENT_INFO.
// output: <none>
typedef struct EVENT_INFO {
   DECL_64COMPAT(uint32, Id);
   DECL_64COMPAT(HANDLE, Handle);
} EVENT_INFO, *PEVENT_INFO;

#define IOCTL_DEV_REGISTER_EVENT       DAQCTL_RD(IOCTL_MAGIC_DEV, 1)
#define IOCTL_DEV_UNREGISTER_EVENT     DAQCTL_RD(IOCTL_MAGIC_DEV, 2)

// Input buffer:  uint32, EventID
// Output buffer: <None>
#define IOCTL_DEV_TRIGGER_EVENT        DAQCTL_WR(IOCTL_MAGIC_DEV, 3)

// Input: <None>
// Output: CHAR[64], device location information
#define IOCTL_DEV_GET_LOCATION         DAQCTL_RD(IOCTL_MAGIC_DEV, 4)

// Input: <None>
// Output: CHAR[64], board version( firmware version )
#define IOCTL_DEV_GET_BOARD_VER        DAQCTL_RD(IOCTL_MAGIC_DEV, 5)

// Input: <None>
// Output: <None>
#define IOCTL_DEV_LOCATE_DEVICE        DAQCTL_RD(IOCTL_MAGIC_DEV, 6)

// Input: the uint32 type boardID to be set to device
// Output: <None>
// Add these ioctrl code to manage the boardID problem of USB device.
#define IOCTL_DEV_SET_BOARDID          DAQCTL_WR(IOCTL_MAGIC_DEV, 7)

// Input buffer: <None>
// Output buffer: uint32[16], bool value, each element indicates whether a board id is freed or not.
#define IOCTL_DEV_GET_FREED_BOARDID    DAQCTL_RD(IOCTL_MAGIC_DEV, 8)

// Set WDT mode
// Input buffer: uint32, the WDT Mode to be set to device
// Output Buffer:  <None>
#define IOCTL_DEV_SET_WDT_MODE         DAQCTL_WR(IOCTL_MAGIC_DEV, 9)

// Update the firmware of H/W
// Input buffer:  <depends on device>
// Output buffer: <depends on device>
typedef struct FW_DOWNLOAD {
   uint32 Length;
   DECL_64COMPAT(void*, Data);
   DECL_64COMPAT(uint32*, Result);
} FW_DOWNLOAD, *PFW_DOWNLOAD;

#define IOCTL_DEV_DOWNLOAD_FW          DAQCTL_WR(IOCTL_MAGIC_DEV, 10)

// Input:  uint32
// Output: uint8 []
#define IOCTL_DEV_READ_PRV_RGN         DAQCTL_RD(IOCTL_MAGIC_DEV, 11)
#define IOCTL_DEV_WRITE_PRV_RGN        DAQCTL_WR(IOCTL_MAGIC_DEV, 12)

// -------------------------------------------------------------------/
// ///////////////////////////////////////////////////////////////////
// For debug and calibration only !!!!!!!!!!!!!!!!!!
typedef struct DBG_REG_IO {
   uint64 Addr;
   uint32 Length;
   uint32 Value;
} DBG_REG_IO, *PDBG_REG_IO;

#define IOCTL_DEV_DBG_REG_IN           DAQCTL_RD(IOCTL_MAGIC_DEV, 13)
#define IOCTL_DEV_DBG_REG_OUT          DAQCTL_WR(IOCTL_MAGIC_DEV, 14)

typedef struct DBG_USB_IO {
   uint16  MajorCmd;
   uint16  MinorCmd;
   uint32  Result;
   uint32  Length;
   uint8   Data[ ];
} DBG_USB_IO, *PDBG_USB_IO;

#define IOCTL_DEV_DBG_USB_IN           DAQCTL_WR(IOCTL_MAGIC_DEV, 15)
#define IOCTL_DEV_DBG_USB_OUT          DAQCTL_WR(IOCTL_MAGIC_DEV, 16)
// \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\/
// ------------------------------------------------------------------/

// Input buffer:   <None>
// Output Buffer:  a pointer to DEVICE_EXT_SHRED which had been mapped into caller process.
#define IOCTL_DEV_GET_KSHARED          DAQCTL_RD(IOCTL_MAGIC_DEV, 17)

// Input buffer:  <None>
// Output Buffer: a pointer to DEV_MEM_BAR which had been mapped into caller process.
#define IOCTL_DEV_GET_MEM_MAPPED       DAQCTL_RD(IOCTL_MAGIC_DEV, 18)

// Input buffer:   bool, shared writing allowed.
// Output Buffer:  <none>
#define IOCTL_DEV_MAKE_SHARED          DAQCTL_RD(IOCTL_MAGIC_DEV, 19)

// Input buffer:   <none>
// Output Buffer:  kernel driver version, ansi chars.
#define IOCTL_DEV_GET_DRV_VER          DAQCTL_RD(IOCTL_MAGIC_DEV, 20)

// Input:   WDT_EXEC_CMD
// Output:  uint32 Status
#define WDT_SET_ENABLE                 0x0
#define WDT_GET_ENABLE                 0x1
#define WDT_SET_INFO                   0x2
#define WDT_GET_INFO                   0x3
#define WDT_CLR_FLAG                   0x4
typedef struct WDT_EXEC_CMD {
   uint32  Command;
   uint32  Time;     // How long can it off-line?
   uint32  Flag;     // whether or not have been off-line
   uint8   Data[ ];  // variable length array for AO / DO / Counter
} WDT_EXEC_CMD, *PWDT_EXEC_CMD;

#define IOCTL_DEV_WDT_CMD              DAQCTL_WR(IOCTL_MAGIC_DEV, 21)

// Set PFP direction
// Input buffer:   uint32[]
// Output Buffer:  <none>
#define IOCTL_DEV_SET_PFP_DIR          DAQCTL_WR(IOCTL_MAGIC_DEV, 22)

// Signal Routing table: Endpoint configuration
// Input buffer:   RT_EP_CFG
// Output Buffer:  <none>
typedef struct RT_EP_CFG {
   uint32 RepNum;
   uint32 SigSrc;
} RT_EP_CFG, *PRT_EP_CFG;

#define IOCTL_DEV_SET_REP_CFG          DAQCTL_WR(IOCTL_MAGIC_DEV, 23)

//***********************************************************************************************
// To compatible with DN3 driver, its code must '26'
// Get device hardware Information
#define DRVSPEC_DN3  3
#define DRVSPEC_DN4  4

#define DEVICEHWINFO_V1_FIELDS  \
   uint32  DeviceNumber;        /* -1 if it is DN4 driver */ \
   uint32  ProductId;           \
   uint32  BoardId;             \
   union {                      \
      uint32  BusSlot;          /* for PCI device, higher word: bus; lower word: slot */ \
      uint32  IoBase;           /* for ISA device, I/O base address */                   \
   };                           \
   uint32  DriverSpec;          /* driver spec version, currently we support two version: 3.0 and 4.0. */ \
   char    DriverName[32];      \
   char    DeviceName[32];      \

typedef struct DEVICE_HWINFO {
   DEVICEHWINFO_V1_FIELDS
} DEVICE_HWINFO, *PDEVICE_HWINFO;

typedef struct DEVICE_HWINFO_EX {
   DEVICEHWINFO_V1_FIELDS

   char Description[64];  // Driver customized Description
   char TreePath[64];     // Driver customized TreePath
} DEVICE_HWINFO_EX, *PDEVICE_HWINFO_EX;

#define IOCTL_DEV_GET_HWINFO           DAQCTL_RD(IOCTL_MAGIC_DEV, 26) //For compatible with DN3

// Get/Set device signal filter
// Input buffer:  DEV_SIG_FILTER
// Output buffer: DEV_SIG_FILTER
typedef struct DEV_SIG_FLT {
   uint32 IsSet;
   uint32 Enabled;
   uint32 BlkTime;
} DEV_SIG_FLT, *PDEV_SIG_FLT;

#define IOCTL_DEV_SIG_FLT_CFG          DAQCTL_WR(IOCTL_MAGIC_DEV, 27)

// Notify the kernel driver to update the timestamp counter, for USB series
typedef struct DEV_TMSTAMP {
   uint64 sys_time;
   uint64 dev_tick;
} DEV_TMSTAMP;

#define IOCTL_DEV_GET_TIMESTAMP         DAQCTL_RD(IOCTL_MAGIC_DEV, 28)

//******************************************************************************************
//                                                                                         *
// IOCTL for analog input operation                                                        *
//                                                                                         *
//******************************************************************************************
// Input:    AI_SET_CH
// Output:   <none>
#define AI_SET_SCTYPE                  0x1
#define AI_SET_GAIN                    0x2
#define AI_SET_COUPLING                0x4
#define AI_SET_IMPEDANCE               0x8
#define AI_SET_BANDWIDTH               0x10
#define AI_SET_IEPE                    0x20
#define AI_SET_CH_ALL                  (-1)
typedef struct AI_CH_CFG {
   uint8  SCType;          // single-ended or differential
   uint8  Gain;            // gain code of the channel.
   uint8  CplType;         // AC/DC coupling.
   uint8  ImpdType;        // Impedance
   uint8  Bandwidth;       // Bandwidth
   uint8  IepeType;        // IEPE type
} AI_CH_CFG, *PAI_CH_CFG;

typedef struct AI_SET_CH {
   uint32    SetWhich;    // set which
   uint32    PhyCHStart;  // Physical channel number of the start channel to configure.
   uint32    PhyCHCount;  // Physical channel count to configure.
   AI_CH_CFG CHCfg[ ];    // variable length array for channel data.
} AI_SET_CH, *PAI_SET_CH;

#define IOCTL_AI_SET_CH                DAQCTL_WR(IOCTL_MAGIC_AI, 1)

// Input:  AI_READ_CH.
// Output: an array of Binary data. The minimize size of the output buffer is
//         channel count to scan multiplies the size of each data.
typedef struct AI_READ_CH {
   uint32 PhyCHStart; // Physical channel number of the start channel
   uint32 LogCHCount; // logical channel count
   DECL_64COMPAT(void*, Data);
} AI_READ_CH, *PAI_READ_CH;

#define IOCTL_AI_READ_CH               DAQCTL_RD(IOCTL_MAGIC_AI, 2)

// Set CJC channel
#define IOCTL_AI_SET_CJC               DAQCTL_WR(IOCTL_MAGIC_AI, 3)

// Input:  <NONE>.
// Output: an array of Binary data.
typedef struct AI_CJC_VALUE {
   uint32 CjcError;      //CJC error
   uint32 CjcValCount;   //The count of CJC Value
   uint8  CjcValues[ ];  //variable length array for CJC value
} AI_CJC_VALUE, *PAI_CJC_VALUE;

#define IOCTL_AI_READ_CJC              DAQCTL_RD(IOCTL_MAGIC_AI, 4)

// Input:  AI_BURN_DETECT
// Output: uint32[]
typedef struct AI_BURN_DETECT {
   uint32 Command;
   uint32 CHStart;
   uint32 CHCount;
   DECL_64COMPAT(uint32*, Status);
} AI_BURN_DETECT, *PAI_BURN_DETECT;

#define IOCTL_AI_BURN_DETECT           DAQCTL_RD(IOCTL_MAGIC_AI, 5)

// Input:  AI_USB_CALI
// Output: <none>
typedef struct AI_USB_CALI {
   uint16 CaliCmd;
   uint16 Gain;
   DECL_64COMPAT(uint32*, Result);
} AI_USB_CALI, *PAI_USB_CALI;

#define IOCTL_AI_USB_CALI              DAQCTL_WR(IOCTL_MAGIC_AI, 6)

// Input:  FAI_FUNC_CFG.
// Output: <None>
#define IOCTL_FAI_SET_PARAM            DAQCTL_WR(IOCTL_MAGIC_AI, 7)

// Input:  <None>
// Output: pointer to FAI_BUFFER
#define IOCTL_FAI_SET_BUFFER           DAQCTL_NB(IOCTL_MAGIC_AI, 8)

// Input:  <None>
// Output: pointer to BUFFER
#define IOCTL_FAI_MAP_BUFFER           DAQCTL_NB(IOCTL_MAGIC_AI, 9)

// Input:  FAI_EXEC_ARG
// Output: <None>
#define FAI_CMD_START                  0x0
#define FAI_CMD_STOP                   0x1
#define FAI_CMD_RESUMEDMA              0x2

// For command 'stop'
#define FAI_FREE_RES                   0x1

typedef struct FAI_EXEC_ARG {
   uint32 Command;
   union {
      uint32 AcqMode;    // For 'start' command
      uint32 StopFlag;   // For 'stop' command
      uint32 ResumeInfo; // For 'resume' command
   };
} FAI_EXEC_ARG, *PFAI_EXEC_ARG;

#define IOCTL_FAI_EXEC                 DAQCTL_WR(IOCTL_MAGIC_AI, 10)


//******************************************************************************************
//                                                                                         *
// IOCTL for analog output operation                                                       *
//                                                                                         *
//******************************************************************************************
#define AO_SET_CHVRG                   0x1
#define AO_SET_EXTREFUNI               0x2
#define AO_SET_EXTREFBI                0x4
#define AO_SET_ALL                     (uint32)-1

typedef struct AO_SET_CH {
   uint32  SetWhich;
   double  ExtRefUnipolar;  // unipolar external reference value
   double  ExtRefBipolar;   // bipolar external reference value
   uint32  CHStart;         // channel number of the start channel to configure.
   uint32  CHCount;         // channel number of the end channel to configure.
   uint32  Gain[ ];         // variable length array for channels gain.
} AO_SET_CH, *PAO_SET_CH;

#define IOCTL_AO_SET_CH                DAQCTL_WR(IOCTL_MAGIC_AO, 1)

// Input:  AO_WRITE_SAMPLES.
// Output: <None>
typedef struct AO_WRITE_CH {
   uint32 CHStart;     // channel number of the start channel to write data to.
   uint32 CHCount;     // count of channel to write data to.
   uint8  Data[ ];     // variable length array for channel data. the array length should match the channel count.
} AO_WRITE_CH, *PAO_WRITE_CH;

#define IOCTL_AO_WRITE_CH              DAQCTL_WR(IOCTL_MAGIC_AO, 2)

// Input:  FAO_FUNC_CFG.
// Output: <None>
#define IOCTL_FAO_SET_PARAM            DAQCTL_WR(IOCTL_MAGIC_AO, 3)

// Input: pointer to user buffer
// Output: <None>
#define IOCTL_FAO_SET_BUFFER           DAQCTL_NB(IOCTL_MAGIC_AO, 4)

// Input: <NONE>
// Output: pointer to user buffer
#define IOCTL_FAO_MAP_BUFFER           DAQCTL_WR(IOCTL_MAGIC_AO, 5)

// Input: uint32 : acquisition mode: FINITE or INFINITE
// Output buffer: <None>
#define FAO_CMD_START                  0x0
#define FAO_CMD_STOP                   0x1

// For command 'stop'
#define FAO_FREE_RES                   0x1   // free resource or not: 0 -- do not free resource, 1 -- free resource.
#define FAO_BREAK_NOW                  0x2   // wait for the working buffer empty or not: 0 -- wait, 1 -- no wait, stop immediately,

typedef struct FAO_EXEC_ARG {
   uint32 Command;
   union {
      uint32 AcqMode;    // For 'start' command
      uint32 StopFlag;   // For 'stop' command
   };
} FAO_EXEC_ARG, *PFAO_EXEC_ARG;

#define IOCTL_FAO_EXEC                 DAQCTL_WR(IOCTL_MAGIC_AO, 6)

//******************************************************************************************
//                                                                                         *
// IOCTL for digital input/output operation                                                *
//                                                                                         *
//******************************************************************************************

// Input:   DIO_SET_PORT.
// Output:  <None>
#define DIO_SET_PORTDIR                0x1
#define DIFLT_SET_BLKINTVL             0x2
#define DIFLT_SET_CHENBED              0x3
#define DOCIR_SET_TYPE                 0x4
#define DI_SET_OPENSTATE               0x5
typedef struct DIO_SET_PORT {
   uint32 SetWhich;
   uint32 PortStart;
   uint32 PortCount;
   uint8  Buffer[ ];
} DIO_SET_PORT, *PDIO_SET_PORT;

#define IOCTL_DIO_SET_PORT             DAQCTL_WR(IOCTL_MAGIC_DIO, 1)

// Input:  DIO_READ_PORT.
// Output: uint8 [] of DI port data.
typedef struct DIO_READ_PORT {
   uint32 PortStart;
   uint32 PortCount;
   DECL_64COMPAT(uint8*, Data);
} DIO_READ_PORT, *PDIO_READ_PORT;

#define IOCTL_DIO_READ_DI_PORT        DAQCTL_RD(IOCTL_MAGIC_DIO, 2)

// Input:  DIO_WRITE_PORT.
// Output: <none>
typedef struct DIO_WRITE_PORT {
   uint32 PortStart;
   uint32 PortCount;
   uint8  Data[ ];
} DIO_WRITE_PORT, *PDIO_WRITE_PORT;

#define IOCTL_DIO_WRITE_DO_PORT       DAQCTL_WR(IOCTL_MAGIC_DIO, 3)

// Input:  DIO_READ_PORT.
// Output: uint8 [] of DO ports state.
#define IOCTL_DIO_READ_DO_PORT        DAQCTL_RD(IOCTL_MAGIC_DIO, 4)

// Input:  DIO_WRITE_BIT.
// Output: <none>
typedef struct DIO_WRITE_BIT {
   uint32 Port;
   uint32 Bit;
   uint8  State;
} DIO_WRITE_BIT, *PDIO_WRITE_BIT;

#define IOCTL_DIO_WRITE_DO_BIT  	      DAQCTL_WR(IOCTL_MAGIC_DIO, 5)

// Input:  DIO_SET_INT.
// Output: <None>
#define DIINT_SET_TRIGEDGE             0x1
#define DIINT_SET_RISING_EDGE          0x2
#define DIINT_SET_FALLING_EDGE         0x3
#define DIINT_SET_GATECTRL             0x4
#define DICOS_SET_CHENBED              0x5
#define DIPM_SET_PORTVAL               0x6
#define DIPM_SET_CHENBED               0x7
typedef struct DIO_SET_INT {
   uint32 SetWhich;
   uint32 SrcStart;    // start DI INT source to configure
   uint32 SrcCount;    // DI INT source count to configure
   uint8  Buffer[ ];   // variable length array of interrupt setting.
} DIO_SET_INT, *PDIO_SET_INT;

#define IOCTL_DIO_SET_INT              DAQCTL_WR(IOCTL_MAGIC_DIO, 6)

// Input:  DIO_EXEC_DISNAP.
// Output: <none>
#define DISNAP_CMD_START               0x0
#define DISNAP_CMD_STOP                0x1
typedef struct DIO_EXEC_DISNAP {
   uint32 Command;               // Start / stop the DI snap
   uint32 EventType;             // event type to trigger DI snap function
   uint32 PortStart;             // start DI port to scan when the event occurred.
   uint32 PortCount;             // ports count to scan when the event occurred.
} DIO_EXEC_DISNAP, *PDIO_EXEC_DISNAP;

#define IOCTL_DIO_EXEC_DISNAP          DAQCTL_WR(IOCTL_MAGIC_DIO, 7)

// Input:  uint32, 0 -- disable the function, 1 -- enable the function
// Output: <none>
#define DOFRZ_CMD_ENABLE               0x0
#define DOFRZ_CMD_DISABLE              0x1
#define DOFRZ_CMD_POLLSTATE            0x2
typedef struct DIO_EXEC_DOFRZ {
   uint32 Command;
   DECL_64COMPAT(uint32*, Result);
} DIO_EXEC_DOFRZ, *PDIO_EXEC_DOFRZ;

#define IOCTL_DIO_EXEC_DOFRZ           DAQCTL_WR(IOCTL_MAGIC_DIO, 8)

// Input:  DIO_SET_POCFG
// Output:  <None>
#define DIOPO_SET_PORTDIR              0x0
#define DIOPO_SET_DOSTATE              0x1
typedef struct DIO_SET_POCFG {
   uint32 SetWhich;
   uint8  Buffer[ ];
} DIO_SET_POCFG, *PDIO_SET_POCFG;

#define IOCTL_DIO_SET_POCFG            DAQCTL_WR(IOCTL_MAGIC_DIO, 9)

// Input:  DIO_EXEC_DOWTD.
// Output: <None>
#define DOWTD_CMD_SET_FEEDINTVL        0x1
#define DOWTD_CMD_SET_LOCKVALUE        0x2
#define DOWTD_CMD_START                0x3
#define DOWTD_CMD_STOP                 0x4
#define DOWTD_CMD_FEED                 0x5
typedef struct DIO_EXEC_DOWTD {
   uint32 Command;
   uint32 PortStart;
   uint32 PortCount;
   uint8  Buffer[ ];
} DIO_EXEC_DOWTD, *PDIO_EXEC_DOWTD;

#define IOCTL_DIO_EXEC_DOWTD           DAQCTL_WR(IOCTL_MAGIC_DIO, 10)

// Input:  FDI_FUNC_CFG.
// Output: <None>
#define IOCTL_FDI_SET_PARAM            DAQCTL_WR(IOCTL_MAGIC_DIO, 11)

// Input:  <None>
// Output: pointer to FDI_BUFFER
#define IOCTL_FDI_SET_BUFFER           DAQCTL_NB(IOCTL_MAGIC_DIO, 12)

// Input:  <None>
// Output: pointer to BUFFER
#define IOCTL_FDI_MAP_BUFFER           DAQCTL_NB(IOCTL_MAGIC_DIO, 13)

// Input:  FAI_EXEC_ARG
// Output: <None>
#define FDI_CMD_START                  0x0
#define FDI_CMD_STOP                   0x1
#define FDI_CMD_RESUMEDMA              0x2

// For command 'stop'
#define FDI_FREE_RES                   0x1

typedef struct FDI_EXEC_ARG {
   uint32 Command;
   union {
      uint32 AcqMode;    // For 'start' command
      uint32 StopFlag;   // For 'stop' command
      uint32 ResumeInfo; // For 'resume' command
   };
} FDI_EXEC_ARG, *PFDI_EXEC_ARG;

#define IOCTL_FDI_EXEC                 DAQCTL_WR(IOCTL_MAGIC_DIO, 14)

// Input:  FDO_FUNC_CFG.
// Output: <None>
#define IOCTL_FDO_SET_PARAM            DAQCTL_WR(IOCTL_MAGIC_DIO, 15)

// Input: pointer to user buffer
// Output: <None>
#define IOCTL_FDO_SET_BUFFER           DAQCTL_NB(IOCTL_MAGIC_DIO, 16)

// Input: <NONE>
// Output: pointer to user buffer
#define IOCTL_FDO_MAP_BUFFER           DAQCTL_WR(IOCTL_MAGIC_DIO, 17)

// Input: uint32 : acquisition mode: FINITE or INFINITE
// Output buffer: <None>
#define FDO_CMD_START                  0x0
#define FDO_CMD_STOP                   0x1

// For command 'stop'
#define FDO_FREE_RES                   0x1   // free resource or not: 0 -- do not free resource, 1 -- free resource.
#define FDO_BREAK_NOW                  0x2   // wait for the working buffer empty or not: 0 -- wait, 1 -- no wait, stop immediately,

typedef struct FDO_EXEC_ARG {
   uint32 Command;
   union {
      uint32 AcqMode;    // For 'start' command
      uint32 StopFlag;   // For 'stop' command
   };
} FDO_EXEC_ARG, *PFDO_EXEC_ARG;

#define IOCTL_FDO_EXEC                 DAQCTL_WR(IOCTL_MAGIC_DIO, 18)
//******************************************************************************************
//                                                                                         *
// IOCTL for Counter/Timer operation                                                       *
//                                                                                         *
//******************************************************************************************
//
// Input:  CT_SET_CFG
// Output: <None>
typedef struct CT_SET_CFG {
   uint32 PropID;
   uint32 Start;
   uint32 Count;
   uint8  Value[ ];
} CT_SET_CFG, *PCT_SET_CFG;

#define IOCTL_CT_SET_CFG               DAQCTL_WR(IOCTL_MAGIC_CT, 1)

// Input:  CT_START
// Output: <None>
typedef struct CT_START {
   uint32 Operation;
   uint32 Start;
   uint32 Count;
   uint8  Param[ ];
} CT_START, *PCT_START;

#define IOCTL_CT_START                 DAQCTL_WR(IOCTL_MAGIC_CT, 2)

// Input:  CT_READ
// Output: depending on device and the operation value.
typedef struct CT_READ {
   uint32 Operation;
   uint32 Start;
   uint32 Count;
   DECL_64COMPAT(void*, Data);
} CT_READ, *PCT_READ;

typedef struct CT_VALUE {
   uint32 CanRead;
   uint32 Overflow;
   uint32 Value;
} CT_VALUE, *PCT_VALUE;

#define IOCTL_CT_READ                  DAQCTL_RD(IOCTL_MAGIC_CT, 3)

// Input:  CT_RESET
// Output: <NONE>
#define CT_RESET_HW                    0x0
#define CT_RESET_VALUE                 0x1
typedef struct CT_RESET {
   uint32 Start;
   uint32 Count;
   uint32 Param;
} CT_RESET, *PCT_RESET;

#define IOCTL_CT_RESET                 DAQCTL_WR(IOCTL_MAGIC_CT, 4)

// Input:  CT_EXEC_SNAP.
// Output: <none>
#define CTSNAP_CMD_START               0x0
#define CTSNAP_CMD_STOP                0x1
typedef struct CT_EXEC_SNAP {
   uint32 Command;               // Start / stop  snap
   uint32 EventType;             // event type to trigger DI snap function
   uint32 CntrStart;             // start channel to scan when the event occurred.
   uint32 CntrCount;             // channel count to scan when the event occurred.
} CT_EXEC_SNAP, *PCT_EXEC_SNAP;

#define IOCTL_CT_EXEC_SNAP             DAQCTL_WR(IOCTL_MAGIC_CT, 5)

// Input:  CT_CCMP_CFG
// Output: <NONE>
#define CT_CCMP_SET_TABLE              0x1
#define CT_CCMP_SET_INTVL              0x2
#define CT_CCMP_ADD_TABLE              0x3
#define CT_CCMP_ADD_INTVL              0x4
#define CT_CCMP_CLEAR                  (-1)
typedef struct CT_CCMP_CFG {
   uint32 Command;
   uint32 Counter;
   union {
      struct {
         uint32 Start;
         int32  Step;
         uint32 Count;
      };
      struct {
         uint32 TblSize;
         uint32 TblData[ ];
      };
   };
} CT_CCMP_CFG, *PCT_CCMP_CFG;

#define IOCTL_CT_CCMP_CFG              DAQCTL_WR(IOCTL_MAGIC_CT, 6)

#define IOCTL_FCT_SET_PARAM            DAQCTL_WR(IOCTL_MAGIC_CT, 7)

// Input:  FCT_BUFFER
// Output: <NONE>
typedef struct FCT_BUFFER {
   uint32 Channel;
   uint32 Size;
   void  *Buffer;
} FCT_BUFFER, *PFCT_BUFFER;

#define IOCTL_FCT_SET_BUFFER           DAQCTL_NB(IOCTL_MAGIC_CT, 8)

// Start/Stop FCT.
// Input:  FCT_EXEC_ARG
// Output: <None>
#define FCT_CMD_START                  0x0
#define FCT_CMD_STOP                   0x1

// FCT Stop Behavior: 
#define FCT_BREAK_NOW                  0x1   // For buffered counter output 
#define FCT_FREE_RES                   0x2 

typedef struct FCT_EXEC_ARG {
   uint32 Command;
   uint32 Counters; 
   union {
      uint32 AcqMode;    // For 'start' command
      uint32 StopFlag;   // For 'stop' command
   };
} FCT_EXEC_ARG, *PFCT_EXEC_ARG;

#define IOCTL_FCT_EXEC                 DAQCTL_WR(IOCTL_MAGIC_CT, 9)

#define IOCTL_FCT_MAP_BUFFER           DAQCTL_NB(IOCTL_MAGIC_CT, 10)

//******************************************************************************************
//                                                                                         *
// IOCTL for DNL operation                                                       *
//                                                                                         *
//******************************************************************************************
#define IOCTL_DNL_GET_MAPPING_SIZE         _IOR(IOCTL_MAGIC_DNL, 1, u32*)
#define IOCTL_DNL_GET_LOGGER_REGISTRY_SIZE _IOR(IOCTL_MAGIC_DNL, 2, u32*)
#define IOCTL_DNL_TEST_LOGGER_REGISTRY     _IOW(IOCTL_MAGIC_DNL, 3, u16)
#define IOCTL_DNL_TEST_LOG_CACHE           _IOW(IOCTL_MAGIC_DNL, 4, u32)
#define IOCTL_DNL_TEST_REGISTER_LOGGER     _IOW(IOCTL_MAGIC_DNL, 5, u32)
#define IOCTL_DNL_TEST_WRITE_LOG           _IOW(IOCTL_MAGIC_DNL, 6, u32)
#define IOCTL_DNL_TEST_UNREGISTER_LOGGER   _IOW(IOCTL_MAGIC_DNL, 7, u32)

#else

//******************************************************************************************
//                                                                                         *
// IOCTL for DAQNAVI 3, For compatible ONLY!!!!!!!!!!!!!!!!!!!!!                           *
//                                                                                         *
//******************************************************************************************

// Magic Number of IOCTLs
#define BDAQ_DEV_MAGIC  'a'
#define BDAQ_AI_MAGIC   'b'
#define BDAQ_AO_MAGIC   'c'
#define BDAQ_DIO_MAGIC  'd'
#define BDAQ_CNTR_MAGIC 'e'
#define BDAQ_KLIB_MAGIC 'k'

// To compatible with 32bit and 64bit OS at same time,
// pointer(handle) type field of a structure should be declared like this:
// Compatible(<type>, <name>)
#define DECL_64COMPAT(type, name)      union { type name; int64 _pad##name; }

//******************************************************************************************
//                                                                                         *
// IOCTL for klib operation                                                                *
//                                                                                         *
//******************************************************************************************
// Input: <None>
// Output: Handle of event
#define IOCTL_KLIB_CREATE_EVENT               _IO(BDAQ_KLIB_MAGIC, 1)

// Input: Handle of event
// Output: <None>
#define IOCTL_KLIB_CLOSE_EVENT                _IO(BDAQ_KLIB_MAGIC, 2)

// Input: Handle of event
// Output: <None>
#define IOCTL_KLIB_SET_EVENT                  _IO(BDAQ_KLIB_MAGIC, 3)

// Input: Handle of event
// Output: <None>
#define IOCTL_KLIB_RESET_EVENT                _IO(BDAQ_KLIB_MAGIC, 4)

// Input: pointer to structure DIO_RW_PORTS.
// Output: <None>
typedef struct _KLIB_WAIT_EVENTS{
   int32  Result;
   int32  Timeout;
   int32  WaitAll;
   uint32 Count;
   HANDLE *Events;
}KLIB_WAIT_EVENTS;

#define IOCTL_KLIB_WAIT_EVENTS                _IO(BDAQ_KLIB_MAGIC, 5)

#ifndef ISA_NAME_MAX_LEN
#define ISA_NAME_MAX_LEN  32
#endif
// Input: pointer of structure ISA_DEV_INFO
// Output: <None>
typedef struct _ISA_DEV_INFO{
   char driver_name[ISA_NAME_MAX_LEN];
   char device_name[ISA_NAME_MAX_LEN];
   uint32 iobase;
   uint32 irq;
   uint32 dmachan;
}ISA_DEV_INFO;

// Input:
// Output:
#define IOCTL_KLIB_ADD_DEV                   _IO(BDAQ_KLIB_MAGIC, 6)
#define IOCTL_KLIB_REMOVE_DEV                _IO(BDAQ_KLIB_MAGIC, 7)

// Input: Event name
// Output: Handle of event
#define EVENT_NAME_LEN_MAX  31

typedef struct NAMED_EVENT {
   char Name[EVENT_NAME_LEN_MAX + 1];
   DECL_64COMPAT(HANDLE, Handle);
} NAMED_EVENT, *PNAMED_EVENT;

#define IOCTL_KLIB_CREATE_EVENT_NAMED  DAQCTL_RD(IOCTL_MAGIC_KLIB, 8)

//******************************************************************************************
//                                                                                         *
// IOCTL for device operation                                                              *
//                                                                                         *
//******************************************************************************************
// Input:  <None>
// Output: CHAR[64], device description
#define IOCTL_DEVICE_GET_DESC                _IO(BDAQ_DEV_MAGIC, 1)

// Input: <None>
// Output: CHAR[64], board version(firmware version)
#define IOCTL_DEVICE_GET_BOARD_VER           _IO(BDAQ_DEV_MAGIC, 2)

// Input: <None>
// Output: <None>
#define IOCTL_DEVICE_LOCATE_DEVICE           _IO(BDAQ_DEV_MAGIC, 3)

// Input: <None>
// Output: CHAR[64], device location information
#define IOCTL_DEVICE_GET_LOCATION_INFO       _IO(BDAQ_DEV_MAGIC, 4)

// Input: the uint32 type boardID to be set to device
// Output: <None>
// Add these ioctrl code to manage the boardID problem of USB device.
#define IOCTL_DEVICE_SET_BOARDID             _IO(BDAQ_DEV_MAGIC, 5)

/*------------------------------------------------------------------*/
// input:  an array of struct USER_EVENT_INFO.
// output: <none>
typedef struct _USER_EVENT_INFO{
   uint32  EventId;
   HANDLE  Handle;
}USER_EVENT_INFO;

#define IOCTL_DEVICE_REGISTER_USER_EVENT       _IO(BDAQ_DEV_MAGIC, 10)
#define IOCTL_DEVICE_UNREGISTER_USER_EVENT     _IO(BDAQ_DEV_MAGIC, 11)

// Input: pointer of EVENT_GET_STATUS
// Output: status in EVENT_GET_STATUS
typedef struct _EVENT_GET_STATUS{
   uint32 LParam;
   uint32 RParam;
}EVENT_GET_STATUS;

#define IOCTL_DEVICE_GET_EVENT_LAST_STATUS     _IO(BDAQ_DEV_MAGIC, 12)


// Input: pointer of structure EVENT_CLEAR_FLAG
// Output: <None>
typedef struct _EVENT_CLEAR_FLAG{
   uint32 EventId;
   uint32 LParam;
   uint32 RParam;
}EVENT_CLEAR_FLAG;

#define IOCTL_DEVICE_CLEAR_EVENT_FLAG          _IO(BDAQ_DEV_MAGIC, 13)

// Input:
// Output:
#define IOCTL_DEVICE_NOTIFY_PROP_CHGED         _IO(BDAQ_DEV_MAGIC, 14)

// Input: event id
// Output:
#define IOCTL_DEVICE_TRIGGER_EVENT             _IO(BDAQ_DEV_MAGIC, 15)

/*------------------------------------------------------------------*/
// -------------------------------------------------------------------
// Special!
// -------------------------------------------------------------------
// For debug and calibration only!!!!!!!!!!!!!!!!!!
typedef struct _DBG_REG_IO{
   uint64 Addr;
   uint32 Length;
   void   *Data;
}DBG_REG_IO;

#define IOCTL_DEVICE_DBG_REG_IN              _IO(BDAQ_DEV_MAGIC, 21)
#define IOCTL_DEVICE_DBG_REG_OUT             _IO(BDAQ_DEV_MAGIC, 22)

// For debug and calibration only!!!!!!!!!!!!!!!!!!
typedef struct _DBG_USB_IO{
   uint16  MajorCmd;
   uint16  MinorCmd;
   uint32  Length;
   void    *Data;
}DBG_USB_IO;

#define IOCTL_DEVICE_DBG_USB_IN              _IO(BDAQ_DEV_MAGIC, 23)
#define IOCTL_DEVICE_DBG_USB_OUT             _IO(BDAQ_DEV_MAGIC, 24)

#define IOCTL_DEVICE_MAKE_SHARED             _IO(BDAQ_DEV_MAGIC, 25)

#define DRVSPEC_DN3  3
#define DRVSPEC_DN4  4
typedef struct _DEVICE_HWINFO {
   uint32 DeviceNumber;  // -1 if it is DN4 driver
   uint32 ProductId;
   uint32 BoardId;
   union {
      uint32 BusSlot;
      uint32 IoBase;
   };
   uint32 DriverSpec;
   char   DriverName[32];
   char   DeviceName[32];
} DEVICE_HWINFO, *PDEVICE_HWINFO;

#define IOCTL_DEVICE_GET_HWINFO              _IO(BDAQ_DEV_MAGIC, 26)

//******************************************************************************************
//                                                                                         *
// IOCTL for analog input operation                                                        *
//                                                                                         *
//******************************************************************************************
// Input:    AI_SET_CHAN
// Output:   <none>
#define AI_SET_CHSCTYPE  0x1
#define AI_SET_CHGAIN    0x2
#define AI_SET_CH_ALL     (-1)

typedef struct _AI_CHAN_CFG{
   uint8  SCType;  // single-ended or differential
   uint8  Gain;    // gain code of the channel.
}AI_CHAN_CFG;

typedef struct _AI_SET_CHAN{
   uint32      SetWhich;      // set which
   uint32      PhyChanStart;  // Physical channel number of the start channel to configure.
   uint32      PhyChanCount;  // Physical channel count to configure.
   AI_CHAN_CFG *ChanCfg;      // variable length array for channel data.
}AI_SET_CHAN;

#define IOCTL_AI_SET_CHAN_CFG                _IO(BDAQ_AI_MAGIC, 1)

// Input:   AI_SCAN_CHL.
// Output:
//    an array of Binary data. The minimize size of the output buffer is
//    channel count to scan multiplies the size of each data.
typedef struct _AI_READ_SAMPLES{
   uint32 PhyChanStart; // Physical channel number of the start channel
   uint32 LogChanCount; // logical channel count
   void   *Data;
}AI_READ_SAMPLES;

#define IOCTL_AI_READ_SAMPLES                _IO(BDAQ_AI_MAGIC, 2)

// Input:  AI_READ_CJC_SAMPLES.
// Output: an array of Binary data.
typedef struct _AI_READ_CJC_SAMPLES{
   uint32 CjcError;    //CJC error
   uint32 CjcValCount; //The count of CJC Value
   void   *CjcValues;  //variable length array for CJC value
}AI_READ_CJC_SAMPLES;

#define IOCTL_AI_READ_CJC_SAMPLES            _IO(BDAQ_AI_MAGIC, 3)

// Get the channel's status of USB device
//    used for Burn Detect and calibration
#define IOCTL_AI_BURN_DETECT                 _IO(BDAQ_AI_MAGIC, 4)

// Input: pointer to structure FAI_PARAM.
// Output: <None>
#define IOCTL_FAI_SET_PARAM                  _IO(BDAQ_AI_MAGIC, 5)

// Input: pointer to user buffer
// Output: <None>
#define IOCTL_FAI_SET_BUFFER                 _IO(BDAQ_AI_MAGIC, 6)

// Input:  __u32, acquisition mode: FINITE or INFINITE
// Output: <None>
#define IOCTL_FAI_START                      _IO(BDAQ_AI_MAGIC, 7)

// Input: __u32, other flags.
// Output: <None>
#define FAI_STOP_FREE_RES  0x1   // free resource or not: 0 -- do not free resource, 1 -- free resource.
#define IOCTL_FAI_STOP                       _IO(BDAQ_AI_MAGIC, 8)

//******************************************************************************************
//                                                                                         *
// IOCTL for analog output operation                                                       *
//                                                                                         *
//******************************************************************************************
#define AO_SET_CHVRG      0x1
#define AO_SET_EXTREFUNI  0x2
#define AO_SET_EXTREFBI   0x4
#define AO_SET_ALL        (uint32)-1
typedef struct _AO_SET_CHAN{
   uint32  SetWhich;
   double  ExtRefUnipolar;        // unipolar external reference value
   double  ExtRefBipolar;         // bipolar external reference value
   uint32  ChanStart;             // channel number of the start channel to configure.
   uint32  ChanCount;             // channel number of the end channel to configure.
   uint32  *Gains;                // variable length array for channels gain.
}AO_SET_CHAN;

#define IOCTL_AO_SET_CHAN_CFG                _IO(BDAQ_AO_MAGIC, 1)

// Input:  AO_WRITE_SAMPLES.
// Output: <None>
typedef struct _AO_WRITE_SAMPLES{
   uint32 ChanStart;     // channel number of the start channel to write data to.
   uint32 ChanCount;     // count of channel to write data to.
   void   *Data;         // variable length array for channel data. the array length
                        // should match the channel count.
}AO_WRITE_SAMPLES;

#define IOCTL_AO_WRITE_SAMPLES               _IO(BDAQ_AO_MAGIC, 2)

// Input:  pointer to structure FAO_FUNC_CFG.
// Output: <None>
#define IOCTL_FAO_SET_PARAM                  _IO(BDAQ_AO_MAGIC, 3)

// Input: pointer to user buffer
// Output: <None>
#define IOCTL_FAO_SET_BUFFER                 _IO(BDAQ_AO_MAGIC, 4)

// Input: uint32 : acquisition mode: FINITE or INFINITE
// Output buffer: <None>
#define IOCTL_FAO_START                      _IO(BDAQ_AO_MAGIC, 5)

// Input: uint32, other flags.
// Output: <None>
#define FAO_STOP_FREE_RES  0x1   // free resource or not: 0 -- do not free resource, 1 -- free resource.
#define FAO_STOP_BREAK_NOW 0x2   // wait for the working buffer empty or not: 0 -- wait, 1 -- no wait, stop immediately,
#define IOCTL_FAO_STOP                       _IO(BDAQ_AO_MAGIC, 6)

//******************************************************************************************
//                                                                                         *
// IOCTL for digital input/output operation                                                *
//                                                                                         *
//******************************************************************************************

// Input:  pointer to structure DIO_SET_PORT_DIR.
// Output: <None>
typedef struct _DIO_SET_PORT_DIR {
   uint32 PortStart;           // start port to configure
   uint32 PortCount;           // ports count to configure
   uint8  *Dirs;               // array for port direction.
} DIO_SET_PORT_DIR;

#define IOCTL_DIO_SET_PORT_DIR               _IO(BDAQ_DIO_MAGIC, 1)

// Input:   pointer to structure DIO_SET_DIINT_CFG.
// Output:  <None>
#define DIINT_SET_TRIGEDGE     0x1
#define DIINT_SET_RISING_EDGE  0x2
#define DIINT_SET_FALLING_EDGE 0x3
#define DIINT_SET_GATECTRL     0xF
typedef struct _DIO_SET_DIINT_CFG {
   uint32 SetWhich;
   uint32 SrcStart;             // start DI INT source to configure
   uint32 SrcCount;             // DI INT source count to configure
   uint8  *Buffer;              // array for DI interrupt trigger edge / gate control.
} DIO_SET_DIINT_CFG;

#define IOCTL_DIO_SET_DIINT_CFG               _IO(BDAQ_DIO_MAGIC, 2)

// Input:  pointer to structure DIO_SET_DICOS_CFG
// Output: <None>
typedef struct _DIO_SET_DICOS_CFG {
   uint32 SrcStart;      // start DI CoS source to configure
   uint32 SrcCount;      // DI CoS source count to configure
   uint8  *ChanEnable;   // each bit specified whether enable/disable the for a DI channel. 0 -- disable, 1 -- enable.
} DIO_SET_DICOS_CFG;

#define IOCTL_DIO_SET_DICOS_CFG                _IO(BDAQ_DIO_MAGIC, 3)

// Input:  pointer to structure DIO_SET_DIPM.
// Output: <None>
#define DIPM_SET_PORTVAL  0x1
#define DIPM_SET_CHENBED  0xF
typedef struct _DIO_SET_DIPM_CFG {
   uint32 SetWhich;    // set which parameter
   uint32 SrcStart;    // start DI Pm source to configure
   uint32 SrcCount;    // DI Pm source count to configure
   uint8  *Buffer;  // variable length array: Port value or channel enabled map.
} DIO_SET_DIPM_CFG;

#define IOCTL_DIO_SET_DIPM_CFG                 _IO(BDAQ_DIO_MAGIC, 4)

// Input:  pointer to structure DIO_SET_DIINT_GATECTRL.
// Output: <None>
#define DIFLT_SET_BLKINTVL 0x1
#define DIFLT_SET_CHENBED  0x2
#define DIFLT_SET_ALL      -1
typedef struct _DIO_SET_DIFLT_CFG {
   uint32 SetWhich;
   uint32 BlkTime;          // di filter block interval value, in device unit.
   uint32 SrcStart;         // start port to configure
   uint32 SrcCount;         // port count to configure
   uint8  *ChanEnabled;     // each bit specified whether enable/disable the for a DI channel. 0 -- disable, 1 -- enable.
} DIO_SET_DIFLT_CFG;

#define IOCTL_DIO_SET_DIFLT_CFG                _IO(BDAQ_DIO_MAGIC, 5)

// Input: pointer to structure DIO_RW_PORTS.
// Output: DI port data, stored in DIO_RW_PORTS.PortData[].
typedef struct _DIO_RW_PORTS {
   uint32 PortStart;             // start port to configure
   uint32 PortCount;             // ports count to configure
   uint8  *Data;                 // variable length array of DO ports data to output.
} DIO_RW_PORTS;

#define IOCTL_DIO_READ_DI_PORTS                _IO(BDAQ_DIO_MAGIC, 6)

// Input: pointer to structure DIO_RW_PORTS.
// Output: <None>.
#define IOCTL_DIO_WRITE_DO_PORTS               _IO(BDAQ_DIO_MAGIC, 7)

// Input: pointer to structure DIO_RW_PORTS.
// Output: DO port data, stored in DIO_RW_PORTS.PortData[].
#define IOCTL_DIO_READ_DO_PORTS                _IO(BDAQ_DIO_MAGIC, 8)

// Input:   pointer to structure DIO_START_DI_SNAP.
// Output:  <none>
typedef struct _DIO_START_DI_SNAP{
   uint32 EventId;               // event type to trigger DI snap function
   uint32 PortStart;             // start DI port to scan when the event occurred.
   uint32 PortCount;             // ports count to scan when the event occurred.
} DIO_START_DI_SNAP;

#define IOCTL_DIO_START_DI_SNAP                _IO(BDAQ_DIO_MAGIC, 9)

// Input: uint32, the event type for which to stop the DI snap function.
// Output: <none>
#define IOCTL_DIO_STOP_DI_SNAP                 _IO(BDAQ_DIO_MAGIC, 10)

// Input:  uint32, 0 -- disable the function, 1 -- enable the function
// Output: <none>
#define IOCTL_DIO_ENABLE_DO_FREEZE             _IO(BDAQ_DIO_MAGIC, 11)

// Input:  <none>
// Output: uint32, freeze state: 0 -- the do channels are not frozen, 1 -- the do channels are frozen
#define IOCTL_DIO_POLL_DO_FREEZE_STATE         _IO(BDAQ_DIO_MAGIC, 12)

// Input:  uint8[], dio ports power on direction
// Output: <None>
#define IOCTL_DIO_SET_POWER_ON_DIR             _IO(BDAQ_DIO_MAGIC, 13)

// Input:  uint8[], do ports power on state
// Output: <None>
#define IOCTL_DIO_SET_DO_POWER_ON_STATE        _IO(BDAQ_DIO_MAGIC, 14)

// Input:  pointer to structure DIO_SET_DOWTD_CFG.
// Output: <None>
#define WDT_SET_INTERVAL      0x1
#define WDT_SET_LOCKVALUE     0x2
#define WDT_SET_ALL            -1
typedef struct _DIO_SET_WDT_CFG {
   uint32 SetWhich;
   uint32 Interval;
   uint32 SrcStart;         // start port to configure
   uint32 SrcCount;         // port count to configure
   uint8  *LockValue;       // variable length array, each element stands for one DO port's locked state
} DIO_SET_WDT_CFG;

#define IOCTL_DIO_SET_DOWDT_CFG                _IO(BDAQ_DIO_MAGIC, 15)

// Input:  uint32, the command to execute
// Output: <None>
#define WDT_CMD_START   0x0
#define WDT_CMD_STOP    0x1
#define WDT_CMD_FEED    0x2
#define IOCTL_DIO_EXEC_WDT_CMD                _IO(BDAQ_DIO_MAGIC, 16)

// Input: pointer to structure DIO_RW_BIT.
typedef struct _DIO_RW_BIT {
   uint32 Port;            // port to configure
   uint32 Bit;             // count to configure
   uint8  Data;            // variable of DO bit data to output.
} DIO_RW_BIT;
#define IOCTL_DIO_WRITE_DO_BIT                _IO(BDAQ_DIO_MAGIC, 17)
//******************************************************************************************
//                                                                                         *
// IOCTL for Counter/Timer operation                                                       *
//                                                                                         *
//******************************************************************************************
//

// Input: pointer to structure CNTR_SET_CFG
// Output: <None>
typedef struct _CNTR_SET_CFG{
   uint32 PropID;
   uint32 Start;
   uint32 Count;
   void   *Value;
}CNTR_SET_CFG;

#define IOCTL_CNTR_SET_CFG                     _IO(BDAQ_CNTR_MAGIC, 1)

// Input:  pointer to structure CNTR_START
// Output:  <None>
typedef struct _CNTR_START{
   uint32 Operation;
   uint32 Start;
   uint32 Count;
   void   *Param;
}CNTR_START;

#define IOCTL_CNTR_START                       _IO(BDAQ_CNTR_MAGIC, 2)

// Input:  pointer to structure CNTR_READ
// Output: depending on device and the operation value.
typedef struct _CNTR_READ{
   uint32 Start;
   uint32 Count;
   uint32 Operation;
   void   *Value;
}CNTR_READ;

typedef struct _CNTR_VALUE{
   uint16 CanRead;
   uint16 Overflow;
   uint32 Value;
}CNTR_VALUE;

#define IOCTL_CNTR_READ                        _IO(BDAQ_CNTR_MAGIC, 3)

// Input:  pointer to structure CNTR_RESET
// Output: <NONE>
typedef struct _CNTR_RESET{
   uint32 Start;
   uint32 Count;
}CNTR_RESET;

#define IOCTL_CNTR_RESET                       _IO(BDAQ_CNTR_MAGIC, 4)


// Input buffer:  pointer to structure CNTR_START_SNAP.
// Output buffer: <none>
typedef struct _CNTR_START_SNAP {
   uint32 EventType;             // event type to trigger DI snap function
   uint32 CntrStart;             // start DI port to scan when the event occurred.
   uint32 CntrCount;             // ports count to scan when the event occurred.
} CNTR_START_SNAP, *PCNTR_START_SNAP;

#define IOCTL_CNTR_START_SNAP                  _IO(BDAQ_CNTR_MAGIC, 5)


// Input buffer:  uint32, the event type for which to stop the DI snap function.
// Output buffer:  <none>
#define IOCTL_CNTR_STOP_SNAP                  _IO(BDAQ_CNTR_MAGIC, 6)

// Input buffer:  CNTR_CONTCMP_CFG
// Output buffer: <NONE>
#define CNTR_CONTCMP_TABLE     1
#define CNTR_CONTCMP_INTVL     2
#define CNTR_CONTCMP_ADD_TABLE 3
#define CNTR_CONTCMP_ADD_INTVL 4
typedef struct _CNTR_CONTCMP_CFG {
   uint32 Counter;
   uint32 Type;
   union {
      struct {
         uint32 Start;
         int32  Increment;
         uint32 Count;
      };
      struct {
         uint32 TblSize;
         uint32 *TblData;
      };
   };
} CNTR_CONTCMP_CFG, *PCNTR_CONTCMP_CFG;

#define IOCTL_CNTR_CONTCMP_CFG                  _IO(BDAQ_CNTR_MAGIC, 7)


// Input buffer:  uint32, the counter
// Output buffer: <NONE>
#define IOCTL_CNTR_CONTCMP_CLEAR                _IO(BDAQ_CNTR_MAGIC, 8)

// Input buffer:  CNTR_RESET
// Output buffer: <NONE>
#define IOCTL_CNTR_RESET_VALUE                  _IO(BDAQ_CNTR_MAGIC, 9)

#endif

#endif /* DAQNAVI_IOCTL_DEFINITION */
