#include "pico/stdlib.h"

void fb_init(uint16_t sampling_freq, uint16_t fft_count, float ref_magnitude);
uint8_t fb_get_total();
void fb_add_mag(uint16_t freq_index, float magnitude);
void fb_get_levels(float *levels);
void fb_reset();