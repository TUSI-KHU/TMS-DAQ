#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define BDAQ_DEV_MAGIC 'a'
#define IOCTL_DEVICE_GET_DESC _IO(BDAQ_DEV_MAGIC, 1)

int main(int argc, char **argv)
{
    const char *device = argc > 1 ? argv[1] : "/dev/daq0";
    char description[64] = {0};
    int fd = open(device, O_RDWR | O_CLOEXEC);

    if (fd < 0) {
        fprintf(stderr, "open(%s): %s\n", device, strerror(errno));
        return 1;
    }

    if (ioctl(fd, IOCTL_DEVICE_GET_DESC, description) < 0) {
        fprintf(stderr, "USB-4704 description ioctl: %s\n", strerror(errno));
        close(fd);
        return 1;
    }

    printf("device=%s description=%s\n", device, description);
    close(fd);
    return 0;
}
