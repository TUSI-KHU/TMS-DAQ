#--------------------------------------------------------------------------------
# DAQNavi3 Makefile, VER 3.1
#    This is a general purpose makefile for various kernel versions and ARCHs.
#
# To make driver for current running kernel:
#    make
#    sudo make install
#
# To make driver for other kernel version and ARCHs(cross-compiling), the kernel
# source(or kernel headers) and cross compiler prefix must be supplied:
#    make KSRC='kernel source' CROSS_COMPILE='cross-compiler prefix'
# Note: the make target 'install' and 'uninstall' are not available.
#
#--------------------------------------------------------------------------------

# Common part--------------------------------------------------------------------
DRV_NAME := bio4704
DRV_ROOT := ../../../

# KBuild part of makefile--------------------------------------------------------
ifneq ($(KERNELRELEASE),)

obj-m	:= $(DRV_NAME).o
$(DRV_NAME)-objs := init.o fops.o ai.o ao.o dio.o counter.o usbfunc.o

ccflags-y += -I$(src)/../../../inc -I$(src)/../../../inc/hw -I$(src)/../../../inc/linux
ccflags-y += -Wno-unused-function -Wno-missing-prototypes -Wno-vla

KBUILD_EXTRA_SYMBOLS += $(src)/../../../lib/Module.symvers

# Normal makefile----------------------------------------------------------------
else 

include ../../../inc/linux/drv-common.mk

endif