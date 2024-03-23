#include <math.h>
#include "pico/stdlib.h"
#include "frequencies_bins.h"

#define FB_TOTAL 3
#define FB_MAX_FFT_VALUES 1025

static uint16_t sampling_freq = 0;
static uint16_t fft_count = 0;
static float ref_mag = 0;
static uint16_t freq_indexes[FB_MAX_FFT_VALUES] = {};

#ifdef EMA_ENABLED
static float ema_alpha = 0.5;
#endif


uint16_t bins[FB_TOTAL][3] = {
    {16, 250, -60},
    {251, 2000, -60},
    {2001, 20000, -60}
};

float bins_max[FB_TOTAL] = {-INFINITY};

void fb_init(uint16_t _sampling_freq, uint16_t _fft_count, float _ref_mag) {
    sampling_freq = _sampling_freq;
    fft_count = _fft_count;
    ref_mag = _ref_mag;
    
    if (fft_count > FB_MAX_FFT_VALUES) {
        panic("Max allowed FFT values: %d. Requested: %d\n", FB_MAX_FFT_VALUES, fft_count);
    }
    
    for (uint16_t i = 0; i < fft_count; i++) {
        uint16_t freq = (uint16_t) i * sampling_freq / fft_count;
        freq_indexes[i] = freq;
    }
}

void fb_add_mag(uint16_t freq_index, float magnitude) {
    uint16_t freq = freq_indexes[freq_index];
    uint16_t low = 0;
    uint16_t high = 0;
    float max;
    
    for (uint8_t i = 0; i < FB_TOTAL; i++) {
        low = bins[i][0];
        high = bins[i][1];
        
        if (freq >= low && freq <= high) {
            max = bins_max[i];

            if (magnitude > max) {
                bins_max[i] = magnitude;
            }
        }
    }
}

void fb_get_levels(float *levels) {
    float dbFS;
#ifdef EMA_ENABLED
    float ema;
#endif

    for (uint16_t i = 0; i < FB_TOTAL; i++) {
#ifdef HANN_ENABLED
        dbFS = 20 * log10((bins_max[i] / ref_mag) * 0.7071);
#else
        dbFS = 20 * log10(bins_max[i] / ref_mag);
#endif
        
#ifdef EMA_ENABLED
        ema = bins[i][2];
        ema = (dbFS * ema_alpha) + (ema * (1 - ema_alpha));
        bins[i][2] = ema;
        levels[i] = ema;
#else
        levels[i] = dbFS;
#endif
    }
}

uint8_t fb_get_total() {
    return FB_TOTAL;
}

void fb_reset() {
    for (uint8_t i = 0; i < FB_TOTAL; i++) {
        bins_max[i] = -INFINITY;
    }
}