#include <stdio.h>
#include <malloc.h>
#include "pico/stdlib.h"
#include "pico/time.h"
#include "renderer.h"

/**
 * Handles turning the LEDs on/off based on set state
 */

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

#define LED_COLS_COUNT 3

int64_t renderer_mux_delay_us;
repeating_timer_t mux_timer;

uint8_t demo_fps;
repeating_timer_t demo_timer;
demo_timer_data_t demo_timer_data = {NULL};

int8_t last_selected_led_col = -1;
uint8_t led_row_index = 0;
uint8_t led_state;

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

uint8_t leds_state[LED_COLS_COUNT][LED_PINS_COUNT];

void init_state() {
    uint8_t i, j;
    
    for (i = 0; i < LED_COLS_COUNT; i++) {
        for (j = 0; j < LED_PINS_COUNT; j++) {
            leds_state[i][j] = 0;
        }
    }
}

inline static void toggle_mux(uint8_t state) {
    gpio_put(MUX_ENABLE_PIN, !state);
}

void toggle_leds_column(uint8_t index) {
    toggle_mux(0);
    
    uint8_t mux_ctrl_a_value = (index >> 2);
    uint8_t mux_ctrl_b_value = (index >> 1) & 1;
    uint8_t mux_ctrl_c_value = index & 1;
    
    gpio_put(MUX_A_PIN, mux_ctrl_a_value);
    gpio_put(MUX_B_PIN, mux_ctrl_b_value);
    gpio_put(MUX_C_PIN, mux_ctrl_c_value);
    
    for (; led_row_index < LED_PINS_COUNT; led_row_index++) {
        led_state = leds_state[index][led_row_index];

        // TODO: replace this with gpio_set_mark
        gpio_put(led_pins[led_row_index], led_state);
    }
    led_row_index = 0;
    
    toggle_mux(1);
}

bool toggle_leds(repeating_timer_t *timer) {
    if (last_selected_led_col < 0 || last_selected_led_col >= (LED_COLS_COUNT - 1)) {
        last_selected_led_col = 0;
    } else {
        last_selected_led_col++;
    }
    toggle_leds_column(last_selected_led_col);
    return true;
}

bool render_demo_states(repeating_timer_t *timer) {
    demo_timer_data_t *data = (demo_timer_data_t *) timer->user_data;
    
    if (data->index >= (data->size - 1)) {
        data->is_running = 0;
        return false;
    }
    
    renderer_update_state(&data->states[data->index]);

    data->index += data->slice_size;
    return true;
}

void renderer_init(int64_t mux_delay_us) {
    renderer_mux_delay_us = mux_delay_us;

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
    
    init_state();
}

void renderer_update_state(const uint8_t *state_per_col) {
    for (uint8_t i = 0; i < LED_COLS_COUNT; i++) {
        // Holds the number of LEDs that must be light up for the current column
        uint8_t state = state_per_col[i];
        // printf("%d ", state);
        
        for (uint8_t j = 0; j < LED_PINS_COUNT; j++) {
            if (j < state) {
                leds_state[i][j] = 1;
            } else {
                leds_state[i][j] = 0;
            }
        }
    }
    // printf("\n-------------\n");
}

void renderer_start() {
    if (!add_repeating_timer_us(renderer_mux_delay_us, toggle_leds, NULL, &mux_timer)) {
        panic("Unable to start MUX timer\n");
    }
}

void renderer_demo_start(uint8_t fps) {
    renderer_demo_stop();
    // 1 animation per bar + three extra where all bars move at the same time
    uint16_t total_animations = LED_COLS_COUNT + 3;
    // light up LEDs from 0 to 8 and back to 1
    uint16_t states_per_animation = LED_PINS_COUNT * 2;
    int elements_per_state = LED_COLS_COUNT;
    
    size_t animation_size = (total_animations * states_per_animation * elements_per_state) + elements_per_state;
    uint8_t *animation_states = malloc(animation_size);
    uint8_t *mutable_states = animation_states;
    uint8_t led_state = 0;
    uint16_t elements_count = 0;
    
    // Generate animations states
    // Animate each band
    for (uint8_t i = 0; i < total_animations; i++) {
        // Generate each state
        for (uint8_t j = 0; j < states_per_animation; j++) {
            if (j <= LED_PINS_COUNT) {
                led_state = j;
            } else {
                led_state = states_per_animation - j;
            }

            for (uint8_t k = 0; k < elements_per_state; k++) {
                if (k == i || i >= LED_COLS_COUNT) {
                    *mutable_states++ = led_state;
                } else {
                    *mutable_states++ = 0;
                }
                elements_count++;
            }
        }
    }
    // Turn off after all animations
    *mutable_states++ = 0;
    *mutable_states++ = 0;
    *mutable_states++ = 0;
    elements_count += 3;
    
    int64_t demo_delay_us = 1000000 / fps;
    demo_timer_data.states = animation_states;
    demo_timer_data.size = animation_size;
    demo_timer_data.slice_size = elements_per_state;
    demo_timer_data.index = 0;
    demo_timer_data.is_running = 1;
    
    printf("Starting demo timer with %lldus delay\n", demo_delay_us / 1000);

    if (!add_repeating_timer_us(demo_delay_us, render_demo_states, &demo_timer_data, &demo_timer)) {
        panic("Unable to start DEMO timer\n");
    }
}

uint8_t renderer_demo_is_running() {
    return demo_timer_data.is_running;
}

void renderer_demo_stop() {
    printf("Stopping demo\n");
    cancel_repeating_timer(&demo_timer);
    if (demo_timer_data.states != NULL) {
        free(demo_timer_data.states);
        demo_timer_data.states = NULL;
        demo_timer_data.size = 0;
        demo_timer_data.slice_size = 0;
        demo_timer_data.index = 0;
        demo_timer_data.is_running = 0;
    }
}

void renderer_stop() {
    cancel_repeating_timer(&mux_timer);
}