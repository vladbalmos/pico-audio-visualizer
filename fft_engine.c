#include <stdio.h>
#include "pico/util/queue.h"
#include "pico/stdlib.h"
#include <math.h>
#include "fft_engine.h"

queue_t *levels_q = NULL;
    
// TODO:
    // initialize ADC DMA
    // sample at 44.1 KHZ @ 12bit
    // process samples:
        // remove DC bias
        // convert each sample from unsigned to signed
    // every 16.6 ms:
        // apply Hanning on the last 32 ms samples
        // do FFT analysis
        // convert amplitudes to dbFS
        // apply EMA on resulting dbFS
        // scale the resulting amplitudes to LED states
        // push LED states to queue
    

void fft_engine_init(queue_t *freq_levels_q) {
    levels_q = freq_levels_q;
    uint32_t engine_ready = FFT_ENGINE_READY;
    
    queue_add_blocking(levels_q, &engine_ready);
}