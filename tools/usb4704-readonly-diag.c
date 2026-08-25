#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

#define BDAQ_DEV_MAGIC 'a'
#define BDAQ_AI_MAGIC  'b'
#define BDAQ_DIO_MAGIC 'd'

#define IOCTL_DEVICE_GET_DESC          _IO(BDAQ_DEV_MAGIC, 1)
#define IOCTL_DEVICE_GET_BOARD_VER     _IO(BDAQ_DEV_MAGIC, 2)
#define IOCTL_DEVICE_GET_LOCATION_INFO _IO(BDAQ_DEV_MAGIC, 4)
#define IOCTL_AI_READ_SAMPLES          _IO(BDAQ_AI_MAGIC, 2)
#define IOCTL_DIO_READ_DI_PORTS        _IO(BDAQ_DIO_MAGIC, 6)
#define IOCTL_DIO_READ_DO_PORTS        _IO(BDAQ_DIO_MAGIC, 8)

#define USB4704_AI_CHANNELS 8U

/* These ABI layouts are the DAQNavi 3-compatible structures consumed by
 * drivers/usb4702_usb4704/src/lnx_ko/{ai,dio}.c. */
struct ai_read_samples {
    uint32_t phy_chan_start;
    uint32_t log_chan_count;
    void *data;
};

struct dio_rw_ports {
    uint32_t port_start;
    uint32_t port_count;
    uint8_t *data;
};

struct range {
    uint16_t min;
    uint16_t max;
};

static void usage(const char *program)
{
    fprintf(stderr, "Usage: %s [device] [iterations] [interval-ms]\n", program);
    fprintf(stderr, "Defaults: /dev/daq0 10 100\n");
}

static int parse_unsigned(const char *text, unsigned int *value)
{
    char *end = NULL;
    unsigned long parsed;

    errno = 0;
    parsed = strtoul(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || parsed > UINT_MAX) {
        return -1;
    }

    *value = (unsigned int)parsed;
    return 0;
}

static int read_text(int fd, unsigned long request, char *buffer, size_t size,
                     const char *label)
{
    memset(buffer, 0, size);
    if (ioctl(fd, request, buffer) < 0) {
        fprintf(stderr, "%s ioctl: %s\n", label, strerror(errno));
        return -1;
    }
    return 0;
}

static int read_ai(int fd, uint16_t samples[USB4704_AI_CHANNELS])
{
    struct ai_read_samples request = {
        .phy_chan_start = 0,
        .log_chan_count = USB4704_AI_CHANNELS,
        .data = samples,
    };

    if (ioctl(fd, IOCTL_AI_READ_SAMPLES, &request) < 0) {
        fprintf(stderr, "AI read ioctl: %s\n", strerror(errno));
        return -1;
    }
    return 0;
}

static int read_port(int fd, unsigned long request, uint8_t *value,
                     const char *label)
{
    struct dio_rw_ports ports = {
        .port_start = 0,
        .port_count = 1,
        .data = value,
    };

    if (ioctl(fd, request, &ports) < 0) {
        fprintf(stderr, "%s ioctl: %s\n", label, strerror(errno));
        return -1;
    }
    return 0;
}

static void sleep_milliseconds(unsigned int milliseconds)
{
    struct timespec delay = {
        .tv_sec = milliseconds / 1000U,
        .tv_nsec = (long)(milliseconds % 1000U) * 1000000L,
    };

    while (nanosleep(&delay, &delay) < 0 && errno == EINTR) {
    }
}

int main(int argc, char **argv)
{
    const char *device = "/dev/daq0";
    unsigned int iterations = 10;
    unsigned int interval_ms = 100;
    struct range ranges[USB4704_AI_CHANNELS];
    uint8_t last_di = 0;
    unsigned int di_changes = 0;
    unsigned int failures = 0;
    char description[64];
    char firmware[64];
    char location[64];
    int fd;

    if (argc > 4) {
        usage(argv[0]);
        return 2;
    }
    if (argc > 1) {
        device = argv[1];
    }
    if (argc > 2 && parse_unsigned(argv[2], &iterations) < 0) {
        fprintf(stderr, "Invalid iterations: %s\n", argv[2]);
        return 2;
    }
    if (argc > 3 && parse_unsigned(argv[3], &interval_ms) < 0) {
        fprintf(stderr, "Invalid interval-ms: %s\n", argv[3]);
        return 2;
    }
    if (iterations == 0) {
        fprintf(stderr, "iterations must be at least 1\n");
        return 2;
    }

    fd = open(device, O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        fprintf(stderr, "open(%s): %s\n", device, strerror(errno));
        return 1;
    }

    if (read_text(fd, IOCTL_DEVICE_GET_DESC, description, sizeof(description),
                  "description") < 0 ||
        read_text(fd, IOCTL_DEVICE_GET_BOARD_VER, firmware, sizeof(firmware),
                  "firmware") < 0 ||
        read_text(fd, IOCTL_DEVICE_GET_LOCATION_INFO, location, sizeof(location),
                  "location") < 0) {
        close(fd);
        return 1;
    }

    printf("device=%s description=%s firmware=%s location=%s\n", device,
           description, firmware, location);
    printf("AI values are raw 14-bit ADC codes; this program never writes AO or DO.\n");

    for (unsigned int iteration = 0; iteration < iterations; ++iteration) {
        uint16_t samples[USB4704_AI_CHANNELS] = {0};
        uint8_t di = 0;
        uint8_t do_state = 0;
        int ai_ok = read_ai(fd, samples) == 0;
        int di_ok = read_port(fd, IOCTL_DIO_READ_DI_PORTS, &di, "DI read") == 0;
        int do_ok = read_port(fd, IOCTL_DIO_READ_DO_PORTS, &do_state, "DO readback") == 0;

        if (!ai_ok || !di_ok || !do_ok) {
            ++failures;
            fprintf(stderr, "iteration %u: I/O failure\n", iteration + 1U);
        } else {
            if (iteration == 0) {
                last_di = di;
                for (unsigned int channel = 0; channel < USB4704_AI_CHANNELS; ++channel) {
                    ranges[channel].min = samples[channel];
                    ranges[channel].max = samples[channel];
                }
            } else {
                if (di != last_di) {
                    ++di_changes;
                    last_di = di;
                }
                for (unsigned int channel = 0; channel < USB4704_AI_CHANNELS; ++channel) {
                    if (samples[channel] < ranges[channel].min) {
                        ranges[channel].min = samples[channel];
                    }
                    if (samples[channel] > ranges[channel].max) {
                        ranges[channel].max = samples[channel];
                    }
                }
            }

            printf("%04u AI=", iteration + 1U);
            for (unsigned int channel = 0; channel < USB4704_AI_CHANNELS; ++channel) {
                printf("%s%5u", channel == 0 ? "" : ",", samples[channel]);
            }
            printf(" DI=0x%02x DO=0x%02x\n", di, do_state);
        }

        if (iteration + 1U < iterations && interval_ms != 0) {
            sleep_milliseconds(interval_ms);
        }
    }

    if (failures == 0) {
        printf("summary: %u successful iterations, DI changes=%u\n", iterations,
               di_changes);
        for (unsigned int channel = 0; channel < USB4704_AI_CHANNELS; ++channel) {
            printf("AI%u min=%u max=%u\n", channel, ranges[channel].min,
                   ranges[channel].max);
        }
    } else {
        printf("summary: %u/%u iterations had I/O failures\n", failures, iterations);
    }

    close(fd);
    return failures == 0 ? 0 : 1;
}
