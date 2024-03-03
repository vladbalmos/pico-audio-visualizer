/**
 * Copyright (c) 2020 Raspberry Pi (Trading) Ltd.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include <stdio.h>
#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"
#include "kissfft/kiss_fft.h"

#define MUX_ENABLE_PIN 15
#define MUX_A_PIN 12
#define MUX_B_PIN 11
#define MUX_C_PIN 10

#define LED_0_PIN 9
#define LED_1_PIN 8
#define LED_2_PIN 7
#define LED_3_PIN 6
#define LED_4_PIN 5
#define LED_5_PIN 4
#define LED_6_PIN 3
#define LED_7_PIN 2

#define LED_PINS_COUNT 8
#define MUX_CTRL_PINS_COUNT 3

const uint8_t led_pins[] = {
    LED_0_PIN,
    LED_1_PIN,
    LED_2_PIN,
    LED_3_PIN,
    LED_4_PIN,
    LED_5_PIN,
    LED_6_PIN,
    LED_7_PIN
};

const uint8_t mux_ctrl_pins[] = {
    MUX_A_PIN,
    MUX_B_PIN,
    MUX_C_PIN
};

typedef struct {
    int8_t last_led;
    uint8_t max_led;
} led_col_t;


bool repeating_timer_callback(repeating_timer_t *rt) {
    led_col_t *lct = (led_col_t *) rt->user_data;
    
    if (lct->last_led++ >= lct->max_led) {
        return false;
    }
    
    gpio_put(led_pins[lct->last_led], 1);
    return true;
}

void init_pins() {

    // Init LED pins
    for (uint8_t i = 0; i < LED_PINS_COUNT; i++) {
        gpio_init(led_pins[i]);
        gpio_set_dir(led_pins[i], GPIO_OUT);
        gpio_set_drive_strength(led_pins[i], GPIO_DRIVE_STRENGTH_12MA);
        gpio_put(led_pins[i], 0);
    }
    
    // Init mux pins
    gpio_init(MUX_ENABLE_PIN);
    gpio_set_dir(MUX_ENABLE_PIN, GPIO_OUT);
    gpio_put(MUX_ENABLE_PIN, 1);
    
    for (uint8_t i = 0; i < MUX_CTRL_PINS_COUNT; i++) {
        gpio_init(mux_ctrl_pins[i]);
        gpio_set_dir(mux_ctrl_pins[i], GPIO_OUT);
        gpio_set_drive_strength(mux_ctrl_pins[i], GPIO_DRIVE_STRENGTH_2MA);
        gpio_put(mux_ctrl_pins[i], 0);
    }
}

inline static void toggle_mux(uint8_t state) {
    gpio_put(MUX_ENABLE_PIN, !state);
}

void select_column(uint8_t index) {
    toggle_mux(0);
    
    uint8_t mux_ctrl_a_value = (index >> 2);
    uint8_t mux_ctrl_b_value = (index >> 1) & 1;
    uint8_t mux_ctrl_c_value = index & 1;
    // printf("Selected col: %d. A: %d B: %d C: %d\n", index, mux_ctrl_a_value, mux_ctrl_b_value, mux_ctrl_c_value);
    
    gpio_put(MUX_A_PIN, mux_ctrl_a_value);
    gpio_put(MUX_B_PIN, mux_ctrl_b_value);
    gpio_put(MUX_C_PIN, mux_ctrl_c_value);
    toggle_mux(1);
}

int main() {
    const uint LED_PIN = CYW43_WL_GPIO_LED_PIN;
    int8_t col_index = 0;
    int8_t col_incr = 1;
    
    led_col_t col;
    col.last_led = -1;
    col.max_led = 7;

    stdio_init_all();
    if (cyw43_arch_init()) {
        printf("Cyw43 arch init failed\n");
        return -1;
    }
    
    printf("Initializing pins\n");
    init_pins();
    
    select_column(0);
    gpio_put(LED_0_PIN, 1);
    gpio_put(LED_1_PIN, 1);
    gpio_put(LED_2_PIN, 1);
    gpio_put(LED_3_PIN, 1);
    gpio_put(LED_4_PIN, 1);
    gpio_put(LED_5_PIN, 1);
    gpio_put(LED_6_PIN, 1);
    gpio_put(LED_7_PIN, 1);
    
    
    // repeating_timer_t timer;
    // add_repeating_timer_ms(100, repeating_timer_callback, &col, &timer);
    
    
    while (true) {
        // cyw43_arch_gpio_put(LED_PIN, 1);
        // sleep_ms(100);
        // cyw43_arch_gpio_put(LED_PIN, 0);
        // sleep_ms(250);

        printf("Col: %d\n", col_index);
        select_column(col_index);
        
        if (col_index >= 2) {
            col_incr = -1;
        }
        
        if (col_index <= 0) {
            col_incr = 1;
        }

        col_index += col_incr;
        sleep_ms(125);
    }
}