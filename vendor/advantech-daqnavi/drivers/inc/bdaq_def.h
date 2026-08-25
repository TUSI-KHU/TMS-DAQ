/*******************************************************************************
                  Copyright (c) 1983-2009 Advantech Co., Ltd.
********************************************************************************
THIS IS AN UNPUBLISHED WORK CONTAINING CONFIDENTIAL AND PROPRIETARY INFORMATION
WHICH IS THE PROPERTY OF ADVANTECH CORP., ANY DISCLOSURE, USE, OR REPRODUCTION,
WITHOUT WRITTEN AUTHORIZATION FROM ADVANTECH CORP., IS STRICTLY PROHIBITED. 

================================================================================
REVISION HISTORY
--------------------------------------------------------------------------------
$Log: /Project/BionicDAQ/Windows/Public/Inc/BDaqDef.h $
 
 Revision: 1   Date: 2009-09-25 06:50:28Z   User: kang.ning 
 Baseline 
--------------------------------------------------------------------------------
$NoKeywords:  $
*/

/****************************************************************************
*                                                                           *
* BDaqDef.h -- Bionic DAQ Type Definitions                                  *
*                                                                           *
****************************************************************************/
#ifndef DAQNAVI_TYPE_DEF_H
#define DAQNAVI_TYPE_DEF_H

#undef _BDAQ_NO_NAMESPACE
#undef _BDAQ_TYPES_ONLY

#define _BDAQ_NO_NAMESPACE
#define _BDAQ_TYPES_ONLY
#include "bdaqctrl.h"

#ifdef _WIN32
#  define BDAQ_NO_VTABLE __declspec(novtable)
#else
#  define BDAQ_NO_VTABLE
#endif

#ifndef x_max
#define x_max(a,b)    (((a) > (b)) ? (a) : (b))
#endif

#ifndef x_min
#define x_min(a,b)    (((a) < (b)) ? (a) : (b))
#endif

#ifndef IN
#  define IN        // Place holder indicates an input parameter
#endif
#ifndef OUT
#  define OUT       // Place holder indicates a output parameter
#endif
#ifndef OPTIONAL    // Place holder indicates an optional parameter,
#  define OPTIONAL  // which value can be zero or NULL, depends on the parameter type.
#endif

#ifndef FALSE
#  define FALSE   0
#endif

#ifndef TRUE
#  define TRUE    1
#endif

#ifndef ARRAY_SIZE
#  define ARRAY_SIZE(x)  (sizeof(x)/sizeof(x[0]))
#endif

#ifndef offset_of
#  ifdef __compiler_offsetof
#     define offset_of(TYPE,MEMBER) __compiler_offsetof(TYPE,MEMBER)
#  else
#     define offset_of(TYPE, MEMBER) ((size_t)&((TYPE *)0)->MEMBER)
#  endif
#endif

#ifndef container_of
#  ifdef __linux__
#     define container_of(ptr, type, member) ({         \
         const typeof(((type *)0)->member) *__mptr = (ptr);  \
         (type *)((char *)__mptr - offset_of(type,member));})
#  else
#     define container_of(ptr, type, member)\
         ((type *)((char*)(ptr) - offset_of(type,member)))
#  endif
#endif

#ifndef x_round_down
/**
 * x_round_down - round down to next specified multiple
 * @x: the value to round
 * @y: multiple to round down to
 *
 * Rounds @x down to next multiple of @y. If @y will always be a power
 * of 2, consider using the faster x_round_down_pw2().
 */
#  define x_round_down(x, y)  ((x) - ((x) % (y)))
#endif

#ifndef x_round_down_pw2
/**
 * x_round_down_pw2 - round down to next specified power of 2
 * @x: the value to round
 * @y: multiple to round down to (must be a power of 2)
 *
 * Rounds @x down to next multiple of @y (which must be a power of 2).
 * To perform arbitrary rounding down, use x_round_down() 
 */
#  define x_round_mask(y)         ((y)-1))
#  define x_round_down_pw2(x, y)  ((x) & ~x_round_mask(y))
#endif

#ifndef BDAQ_API
#  define BDAQ_API
#endif

#define DBGIO_STACKBUF_THR       32
#define DBGIO_MAX_LENGTH         4096

#define DAQ_ACQ_FINITE_SYNC      0x0
#define DAQ_ACQ_FINITE_ASYNC     0x1
#define DAQ_ACQ_INFINITE         0x2
#define DAQ_XFER_INT             0x0
#define DAQ_XFER_DMA             0x100

#define DAQ_FN_IDLE              0
#define DAQ_FN_READY             1
#define DAQ_FN_RUNNING           2
#define DAQ_FN_STOPPED           3
#define DAQ_FN_PASSED            4

#define DAQ_IN_DATAREADY                0x001
#define DAQ_IN_BUF_OVERRUN              0x002
#define DAQ_IN_BUF_FULL                 0x004
#define DAQ_IN_CACHE_OVERFLOW           0x008
#define DAQ_IN_BURN_OUT                 0x010
#define DAQ_IN_TSTAMP_OVERRUN           0x020
#define DAQ_IN_TSTAMP_CACHE_OVERFLOW    0x040
#define DAQ_IN_MARK_OVERRUN             0x080
#define DAQ_IN_REC_END                  0x100
#define DAQ_IN_XFER_STOP                0x200
#define DAQ_IN_CONV_STOP                0x400

#define DAQ_IN_MUST_STOP(state, mode)   ((state & DAQ_IN_BUF_FULL) && !(mode == DAQ_ACQ_INFINITE))

#define DAQ_OUT_TRANSMITTED      0x1
#define DAQ_OUT_BUF_UNDERRUN     0x2
#define DAQ_OUT_TRANSSTOPPED     0x4
#define DAQ_OUT_CACHE_EMPTY      0x8

//
// Convert the system time(since Jan 1, 1601, in 100-nanoseconds) to epoch(since Jan 1, 1970, in microseconds)
#define EPOCH_SYSTIME_US              0x295E9648864000ULL  // system time of EPOCH, in microsecond.
#define SYSTIME_TO_EPOCH_US(sys_time) ((sys_time) / 10 - EPOCH_SYSTIME_US)

//
// For compatible with old version
#define pullHighAllPort PullHigh
#define pullLowAllPort  PullLow

//
// Helpers for Bit operations used by user/kernel drivers
#define BIT_SET(x, bit)          (x) |= 1 << (bit)
#define BIT_CLR(x, bit)          (x) &= ~(1 << (bit))
#define BIT_TEST(x, bit)         ((x) & (1 << (bit)))

//
// Header part of the structure: DEVICE_SHARED
// Usage:
// typedef struct xxxxx {
//    kshr_header Header;
//    ......
// } xxx;
//
typedef struct kshr_header {
   uint32 size;         // size of the whole 'DEVICE_SHARED' structure, this is used to identify the different version of the structure.
   uint32 prod_id;      // Device Type
   uint32 dev_number;   // Zero-based device number
} kshr_header;

#endif /* DAQNAVI_TYPE_DEF_H */
