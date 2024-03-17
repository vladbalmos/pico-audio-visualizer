#include <stdio.h>
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "pico/util/queue.h"
#include "pico/cyw43_arch.h"
// #include "kissfft/kiss_fft.h"
#include "renderer.h"
#include "fft_engine.h"

#define FREQ_LEVELS_Q_MAX_ELEMENTS 16

queue_t freq_levels_q;

void core1_main() {
    fft_engine_init(&freq_levels_q, 60);
}


int div_by_32(int n) {
    int remainder = n % 32;
    if (!remainder) {
        return n + 32;
    }
    
    return n + (32 - remainder);
}

int main() {
    const uint LED_PIN = CYW43_WL_GPIO_LED_PIN;
    const uint8_t leds_state[] = {0, 0, 0};

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
    queue_init(&freq_levels_q, sizeof(uint32_t), FREQ_LEVELS_Q_MAX_ELEMENTS);
    multicore_launch_core1(core1_main);
    
    uint32_t fft_engine_ready_flag = 0;
    queue_remove_blocking(&freq_levels_q, &fft_engine_ready_flag);

    // printf("Ready\n");

    renderer_demo_start(60);
    while (true) {
        cyw43_arch_gpio_put(LED_PIN, 1);
        sleep_ms(100);
        cyw43_arch_gpio_put(LED_PIN, 0);
        sleep_ms(100);
        
        if (!renderer_demo_is_running()) {
            renderer_demo_start(60);
        }
    }
}