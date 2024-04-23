#include <math.h>
#include <stdio.h>
#include <malloc.h>
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "pico/util/queue.h"
#include "pico/cyw43_arch.h"
#include "hardware/clocks.h"
#include "renderer.h"
#include "frequencies_bins.h"
#include "fft_engine.h"

#define FREQ_LEVELS_Q_MAX_ELEMENTS 16

#ifdef ENABLE_LED_HEARTBEAT
#define HEARTBEAT_LED_PIN CYW43_WL_GPIO_LED_PIN
#endif

queue_t freq_levels_q;
repeating_timer_t heartbeat_timer;
uint8_t default_led_state = 0;

#ifndef ENABLE_DEMO_MODE
void core1_main() {
    fft_engine_init(&freq_levels_q, 60);
}
#endif

#ifdef ENABLE_LED_HEARTBEAT
bool toggle_default_led(repeating_timer_t *t) {
    default_led_state = !default_led_state;
    cyw43_arch_gpio_put(HEARTBEAT_LED_PIN, default_led_state);
    return true;
}

void enable_led_heartbeat() {
    add_repeating_timer_ms(100, toggle_default_led, NULL, &heartbeat_timer);
}
#endif


int main() {
    uint8_t leds_state[] = {0, 0, 0};

#ifndef ENABLE_DEMO_MODE
    uint8_t fb_total = fb_get_total();
    float *levels = malloc(fb_total * sizeof(float));
    uint8_t second_core_signal;
#endif
    
    // set_sys_clock_khz(200000, true);
    stdio_init_all();
    
#ifdef ENABLE_LED_HEARTBEAT
    if (cyw43_arch_init()) {
        printf("Cyw43 arch init failed\n");
        return -1;
    }
    enable_led_heartbeat();
#endif
    
    printf("Initializing renderer\n");
    renderer_init(1000);
    renderer_update_state(leds_state);
    renderer_start();
    
#ifndef ENABLE_DEMO_MODE
    printf("Initializing FFT engine\n");
    queue_init(&freq_levels_q, sizeof(uint8_t), FREQ_LEVELS_Q_MAX_ELEMENTS);
    multicore_launch_core1(core1_main);
    
    queue_remove_blocking(&freq_levels_q, &second_core_signal);

    printf("Ready\n");
    fflush(stdout);
    int32_t start_time;
    int32_t last_time = time_us_32();
    int32_t time_diff;
#else
    renderer_demo_start(60);
#endif

    while (true) {
#ifndef ENABLE_DEMO_MODE
        // printf("Got samples\n");
        queue_remove_blocking(&freq_levels_q, &second_core_signal);
        start_time = time_us_32();

        // Get max level for each frequency bin in dbFS
        fb_get_levels(levels);

        time_diff = start_time - last_time;
        
        if (time_diff >= 500000) {
            for (int i = 0; i < fb_total; i++) {
                printf("%f ", levels[i]);
            }
            printf("\n");
            last_time = start_time;
        }

        for (int i = 0; i < fb_total; i++) {
            if (levels[i] >= -6) {
                leds_state[i] = 8;
            } else if (levels[i] >= -9) {
                leds_state[i] = 7;
            } else if (levels[i] >= -12) {
                leds_state[i] = 6;
            } else if (levels[i] >= -15) {
                leds_state[i] = 5;
            } else if (levels[i] >= -18) {
                leds_state[i] = 4;
            } else if (levels[i] >= -21) {
                leds_state[i] = 3;
            } else if (levels[i] >= -24) {
                leds_state[i] = 2;
            } else if (levels[i] >= -30) {
                leds_state[i] = 1;
            } else {
                leds_state[i] = 0;
            }
            renderer_update_state(leds_state);
        }
#else 
        if (!renderer_demo_is_running()) {
            renderer_demo_start(60);
            sleep_ms(100);
        }
#endif
    }
}