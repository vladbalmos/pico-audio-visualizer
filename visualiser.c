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

queue_t freq_levels_q;

void core1_main() {
    fft_engine_init(&freq_levels_q, 60);
}


int main() {
    uint8_t fb_total = fb_get_total();
    float *levels = malloc(fb_total * sizeof(float));
    uint8_t second_core_signal;
    // const uint LED_PIN = CYW43_WL_GPIO_LED_PIN;
    uint8_t leds_state[] = {0, 0, 0};
    
    // set_sys_clock_khz(200000, true);

    stdio_init_all();
    if (cyw43_arch_init()) {
        printf("Cyw43 arch init failed\n");
        return -1;
    }
    
    printf("Initializing renderer\n");
    renderer_init(1000);
    renderer_update_state(leds_state);
    renderer_start();
    
    printf("Initializing FFT engine\n");
    queue_init(&freq_levels_q, sizeof(uint8_t), FREQ_LEVELS_Q_MAX_ELEMENTS);
    multicore_launch_core1(core1_main);
    
    queue_remove_blocking(&freq_levels_q, &second_core_signal);

    printf("Ready\n");
    fflush(stdout);

    // renderer_demo_start(60);
    while (true) {
        // cyw43_arch_gpio_put(LED_PIN, 1);
        // sleep_ms(100);
        // cyw43_arch_gpio_put(LED_PIN, 0);
        // sleep_ms(100);

        // printf("Got samples\n");
        queue_remove_blocking(&freq_levels_q, &second_core_signal);

        // Get max level for each frequency bin in dbFS
        // fb_get_levels(levels);

        // for (int i = 0; i < fb_total; i++) {
        //     if (levels[i] >= -6.5) {
        //         leds_state[i] = 8;
        //     } else if (levels[i] >= -9) {
        //         leds_state[i] = 7;
        //     } else if (levels[i] >= -12) {
        //         leds_state[i] = 6;
        //     } else if (levels[i] >= -15) {
        //         leds_state[i] = 5;
        //     } else if (levels[i] >= -18) {
        //         leds_state[i] = 4;
        //     } else if (levels[i] >= -21) {
        //         leds_state[i] = 3;
        //     } else if (levels[i] >= -24) {
        //         leds_state[i] = 2;
        //     } else if (levels[i] >= -27) {
        //         leds_state[i] = 1;
        //     } else {
        //         leds_state[i] = 0;
        //     }
        //     renderer_update_state(leds_state);
        //     // printf("%f ", levels[i]);
        // }
        // printf("\n");
        
        // if (!renderer_demo_is_running()) {
        //     renderer_demo_start(60);
        // }
    }
}