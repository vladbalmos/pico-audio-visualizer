#include "pico/stdlib.h"

typedef struct {
    uint8_t *states;
    size_t size;
    uint8_t slice_size;
    uint16_t index;
    uint8_t is_running;
} demo_timer_data_t;

void renderer_init(int64_t mux_delay_us);
void renderer_update_state(const uint8_t *state_per_col);
void renderer_start();
void renderer_demo_start(uint8_t fps);
uint8_t renderer_demo_is_running();
void renderer_demo_stop();
void renderer_stop();