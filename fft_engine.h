#include "pico/stdlib.h"
#include "pico/util/queue.h"
#include "hardware/dma.h"
#include "hardware/adc.h"

#define FFT_ENGINE_READY 1

void fft_engine_init(queue_t *freq_levels_q, uint8_t runs_per_sec);