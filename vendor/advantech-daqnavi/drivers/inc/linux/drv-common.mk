#--------------------------------------------------------------------------------
# Driver Makefile common part
#    Common part of drivers Makefile for various kernel versions and ARCHs.
#
# Note: DONOT use this makefile directly
#
#--------------------------------------------------------------------------------

# KBuild part of makefile--------------------------------------------------------
ifneq ($(KERNELRELEASE),)

	ccflags-y += -DDN4_DRIVER -I$(src)/../../../../inc -I$(src)/../../../../inc/hw -I$(src)/../../../../inc/linux
	ccflags-y += -Wno-unused-function -Wno-missing-prototypes -Wno-missing-declarations 
	ccflags-y += -Wno-cast-function-type -Wno-enum-int-mismatch -Wno-vla -Wno-vla-larger-than

	KBUILD_EXTRA_SYMBOLS += $(src)/../../../../lib/Module.symvers

	# DEBUG Version
	ifneq ($(DEBUG),)
		ccflags-y += -DDAQ_TRACING
	endif

# Normal makefile----------------------------------------------------------------
else

KVER ?= $(shell uname -r)
KSRC ?= /lib/modules/$(KVER)/build
KMOD ?= /lib/modules/$(KVER)/kernel/drivers/daqnavi

all:
	@cp $(DRV_ROOT)/lib/Module.symvers ./ && $(MAKE) -C $(KSRC) M=$(CURDIR) modules && cp $(DRV_NAME).ko $(DRV_ROOT)/bin/

install:
	@echo -n "Intalling '$(DRV_NAME)', please wait ...... "
	$(shell mkdir -p $(KMOD) && cp -f ./$(DRV_NAME).ko $(KMOD)/;\
	if [ $(KVER) = $(shell uname -r) ]; then \
		depmod && modprobe $(DRV_NAME) 1>/dev/null; \
	else \
	  	[ -f /boot/System.map-$(KVER) ] && depmod -a $(KVER) -F "/boot/System.map-$(KVER)" || depmod -a $(KVER); \
	fi)	
	@echo "Done"

uninstall:
	$(shell if grep $(DRV_NAME) /proc/modules >/dev/null ; then rmmod $(DRV_NAME) ; fi)
	rm -f $(KMOD)/$(DRV_NAME).ko && depmod

clean:
	@$(MAKE) -C $(KSRC) M=$(CURDIR) clean
	@-rm -rf *.o *~ .depend .*.cmd *.ko *.mod.c .tmp_versions modules.* Module.*

.PHONY: all clean

endif
