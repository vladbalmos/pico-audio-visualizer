#include <stdio.h>
#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"
#include "kissfft/kiss_fft.h"
#include "renderer.h"

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