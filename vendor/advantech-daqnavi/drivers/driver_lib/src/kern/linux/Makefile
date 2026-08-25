#--------------------------------------------------------------------------------
# DAQNavi4 Makefile, VER 4.1
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
DRV_NAME := biokernbase
DRV_PATH := daqnavi

# KBuild part of makefile--------------------------------------------------------
ifneq ($(KERNELRELEASE),)

obj-m := $(DRV_NAME).o
$(DRV_NAME)-objs := main.o event.o usbreader.o memory.o misc.o isa.o pciex_dma.o dnl.o

ccflags-y += -DDN4_DRIVER -I$(src)/../../../../inc -I$(src)/../../../../inc/hw -I$(src)/../../../../inc/linux
ccflags-y += -Wno-undef -Wno-missing-prototypes -Wno-missing-declarations

# to enable diagnostic messages for DNL
# ccflags-y += -DLIB_DNL_SYS_TRACE

# Normal makefile----------------------------------------------------------------
else
KVER ?= $(shell uname -r)
KSRC ?= /lib/modules/$(KVER)/build
KMOD ?= /lib/modules/$(KVER)/kernel/drivers/$(DRV_PATH)

DRV_BIN := ../../../../bin
DRV_LIB := ../../../../lib
UDEV_PATH := /etc/udev/rules.d

all:
	$(MAKE) -C $(KSRC) M=$(CURDIR) modules
	mkdir -p $(DRV_BIN) && cp $(DRV_NAME).ko $(DRV_BIN)/
	mkdir -p $(DRV_LIB) && cp Module.symvers $(DRV_LIB)/

install:
	@echo -n "Intalling '$(DRV_NAME)', please wait ...... "
	@cp 71-bionic-daq.rules $(UDEV_PATH)/
	@udevadm control --reload-rules
	@udevadm trigger
	$(shell mkdir -p $(KMOD) && cp -f ./$(DRV_NAME).ko $(KMOD)/;\
	if [ $(KVER) = $(shell uname -r) ]; then \
		depmod && modprobe $(DRV_NAME); \
	else \
	  	[ -f /boot/System.map-$(KVER) ] && depmod -a $(KVER) -F "/boot/System.map-$(KVER)" || depmod -a $(KVER); \
	fi;\
	[ -f /dev/daq255 ] && chmod a+rw /dev/daq255)
	@echo "Done"

uninstall:
	$(shell if grep $(DRV_NAME) /proc/modules > /dev/null ; then rmmod $(DRV_NAME) ; fi)
	rm -f $(KMOD)/$(DRV_NAME).ko && depmod
	rm $(UDEV_PATH)/71-bionic-daq.rules

clean:
	@$(MAKE) -C $(KSRC) M=$(CURDIR) clean
	@-rm -rf *.o *.o.* *~ .depend .*.cmd *.ko *.mod.c .tmp_versions modules.* Module.*

.PHONY: all clean

endif
