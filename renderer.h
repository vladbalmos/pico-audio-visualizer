#include "pico/stdlib.h"

void renderer_init(int64_t mux_delay_us);
void renderer_update_state(const uint8_t *state_per_col);
void renderer_start();
void renderer_start_demo(uint8_t fps);
void renderer_stop_demo();
void renderer_stop();