// Cycle a downstream USB hub port through the Linux usbfs control interface.
//
// This is intentionally tiny and dependency-free so the Pi installer can
// build it offline. It is used only by the root-only USB-4704 recovery helper
// after the acquisition service has stopped.

#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <linux/usb/ch11.h>
#include <linux/usb/ch9.h>
#include <linux/usbdevice_fs.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

static int parse_positive(const char *text, const char *name, int minimum, int maximum) {
    char *end = NULL;
    long value = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value < minimum || value > maximum) {
        fprintf(stderr, "%s must be an integer from %d to %d\n", name, minimum, maximum);
        return -1;
    }
    return (int)value;
}

static int set_port_power(int fd, unsigned char request, unsigned short port) {
    struct usbdevfs_ctrltransfer transfer = {
        .bRequestType = USB_DIR_OUT | USB_TYPE_CLASS | USB_RECIP_OTHER,
        .bRequest = request,
        .wValue = USB_PORT_FEAT_POWER,
        .wIndex = port,
        .wLength = 0,
        .timeout = 1000,
        .data = NULL,
    };
    if (ioctl(fd, USBDEVFS_CONTROL, &transfer) == 0) {
        return 0;
    }
    fprintf(stderr, "USB port power control failed: %s\n", strerror(errno));
    return -1;
}

static void sleep_milliseconds(int milliseconds) {
    struct timespec duration = {
        .tv_sec = milliseconds / 1000,
        .tv_nsec = (long)(milliseconds % 1000) * 1000000L,
    };
    while (nanosleep(&duration, &duration) != 0 && errno == EINTR) {
    }
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <hub-usbfs-node> <port> <off-ms>\n", argv[0]);
        return 2;
    }

    int port = parse_positive(argv[2], "port", 1, 255);
    int off_milliseconds = parse_positive(argv[3], "off-ms", 100, 10000);
    if (port < 0 || off_milliseconds < 0) {
        return 2;
    }

    int fd = open(argv[1], O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        fprintf(stderr, "cannot open %s: %s\n", argv[1], strerror(errno));
        return 1;
    }

    int status = 0;
    if (set_port_power(fd, USB_REQ_CLEAR_FEATURE, (unsigned short)port) != 0) {
        status = 1;
    } else {
        sleep_milliseconds(off_milliseconds);
        if (set_port_power(fd, USB_REQ_SET_FEATURE, (unsigned short)port) != 0) {
            status = 1;
        }
    }
    if (close(fd) != 0 && status == 0) {
        fprintf(stderr, "cannot close %s: %s\n", argv[1], strerror(errno));
        status = 1;
    }
    return status;
}
