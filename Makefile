SHELL := /bin/bash
.DELETE_ON_ERROR:

KERNEL_RELEASE ?= $(shell uname -r)
KERNEL_DIR ?= /lib/modules/$(KERNEL_RELEASE)/build
OUT_DIR ?= out/$(KERNEL_RELEASE)

DRIVERS_DIR := vendor/advantech-daqnavi/drivers
BASE_DIR := $(DRIVERS_DIR)/driver_lib/src/kern/linux
USB4704_DIR := $(DRIVERS_DIR)/usb4702_usb4704/src/lnx_ko

MODULE_MAKE_ARGS := KVER=$(KERNEL_RELEASE) KSRC=$(KERNEL_DIR)
ifneq ($(strip $(ARCH)),)
MODULE_MAKE_ARGS += ARCH=$(ARCH)
endif
ifneq ($(strip $(CROSS_COMPILE)),)
MODULE_MAKE_ARGS += CROSS_COMPILE=$(CROSS_COMPILE)
endif

.PHONY: all modules check clean

all: modules

check:
	@test -d "$(KERNEL_DIR)" || { echo "Kernel headers not found: $(KERNEL_DIR)" >&2; exit 1; }
	@test -f "$(BASE_DIR)/Makefile"
	@test -f "$(USB4704_DIR)/Makefile"
	@mkdir -p "$(DRIVERS_DIR)/bin" "$(DRIVERS_DIR)/lib" "$(OUT_DIR)"

modules: check
	$(MAKE) -C "$(BASE_DIR)" $(MODULE_MAKE_ARGS)
	$(MAKE) -C "$(USB4704_DIR)" $(MODULE_MAKE_ARGS)
	install -m 0644 "$(BASE_DIR)/biokernbase.ko" "$(OUT_DIR)/biokernbase.ko"
	install -m 0644 "$(USB4704_DIR)/bio4704.ko" "$(OUT_DIR)/bio4704.ko"

clean:
	@if test -d "$(KERNEL_DIR)"; then \
		$(MAKE) -C "$(USB4704_DIR)" $(MODULE_MAKE_ARGS) clean; \
		$(MAKE) -C "$(BASE_DIR)" $(MODULE_MAKE_ARGS) clean; \
	fi

