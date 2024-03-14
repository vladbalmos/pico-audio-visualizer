#include "pico/stdlib.h"
#include "pico/util/queue.h"

#define FFT_ENGINE_READY 1

void fft_engine_init(queue_t *freq_levels_q);