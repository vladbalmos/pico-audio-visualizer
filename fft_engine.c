#include <stdio.h>
#include <malloc.h>
#include <string.h>
#include <math.h>
#include "pico/util/queue.h"
#include "pico/stdlib.h"
#include "fft_engine.h"

#define SCALE_FACTOR (1<<16)
#define ADC_SAMPLES_Q_MAX_ELEMENTS 8
#define ADC_SAMPLE_RATE_HZ 44100
#define ADC_CLOCK_SPEED_HZ 48.0 * 1000 * 1000

#define DC_BIAS 2048 // Half of max voltage (3.3V = 4096 for our 12bit ADC)

static int adc_dma_chan;
static int adc_dma_transfer_count;

static uint16_t *adc_samples_buf = NULL;
static uint16_t *adc_prev_samples_buf = NULL;
static int16_t *adc_averaged_samples_buf = NULL;
static int16_t *adc_samples_for_fft_buf = NULL;
static int16_t *tmp_buf = NULL;

static size_t adc_buf_size;
static uint adc_samples_for_fft_buf_size;

static uint8_t samples_ready = 0;
static queue_t *levels_q = NULL;

static uint8_t analysis_per_sec;

static inline int div_by_32(int n) {
    int remainder = n % 32;
    if (!remainder) {
        return n + 32;
    }
    
    return n + (32 - remainder);
}

static void __isr adc_dma_isr() {
    samples_ready = 1;
    // Since we're analyzing the last 32ms of audio, we need the last 16ms sample set
    // memcpy(adc_samples_for_fft_buf, adc_averaged_samples_buf, adc_buf_size);

    // tmp_buf = adc_averaged_samples_buf;
    
    // for (uint16_t i = 0; i < adc_dma_transfer_count; i++) {
    //     // Average each sample using the current and previous sample set
    //     // add the result to the `averaged` buffer
    //     *tmp_buf++ = (adc_samples_buf[i] + adc_prev_samples_buf[i]) / 2;
    // }
    // adc_prev_samples_buf = adc_samples_buf;
    
    // // Append the new sample set
    // memcpy(&adc_samples_for_fft_buf[adc_samples_for_fft_buf_size / 2], adc_averaged_samples_buf, adc_buf_size);
    
    // Restart DMA transfer
    dma_channel_set_write_addr(adc_dma_chan, &adc_samples_buf[0], true);
}

void init_adc_dma() {
    float adc_clock_div = ADC_CLOCK_SPEED_HZ / ADC_SAMPLE_RATE_HZ;
    float analysis_period = 1.0 / analysis_per_sec;
    float adc_capture_period = 1.0 / ADC_SAMPLE_RATE_HZ;

    adc_dma_transfer_count = div_by_32((int) (analysis_period / adc_capture_period));
    if (adc_dma_transfer_count <= 0) {
        panic("Invalid ADC DMA transfer count\n");
    }
    
    adc_buf_size = sizeof(uint16_t) * adc_dma_transfer_count;
    adc_samples_buf = malloc(adc_buf_size);
    if (adc_samples_buf == NULL) {
        panic("Unable to allocate %d bytes to 'adc_samples_buf'\n", adc_dma_transfer_count);
    }
    memset(adc_samples_buf, 0, adc_buf_size);

    adc_prev_samples_buf = malloc(adc_buf_size);
    if (adc_prev_samples_buf == NULL) {
        panic("Unable to allocate %d bytes to 'adc_prev_samples_buf'\n", adc_dma_transfer_count);
    }
    memset(adc_prev_samples_buf, 0, adc_buf_size);

    adc_samples_for_fft_buf = malloc(adc_buf_size);
    if (adc_samples_for_fft_buf == NULL) {
        panic("Unable to allocate %d bytes to 'adc_samples_for_fft_buf'\n", adc_buf_size);
    }
    memset(adc_samples_for_fft_buf, 0, adc_buf_size);

    adc_samples_for_fft_buf_size = sizeof(int16_t) * 2 * adc_dma_transfer_count;
    adc_averaged_samples_buf = malloc(adc_samples_for_fft_buf_size);
    if (adc_averaged_samples_buf == NULL) {
        panic("Unable to allocate %d bytes to 'adc_averaged_samples_buf'\n", adc_samples_for_fft_buf_size);
    }
    memset(adc_averaged_samples_buf, 0, adc_samples_for_fft_buf_size);
    

    // Setup ADC
    adc_init();
    adc_gpio_init(26);
    adc_select_input(0);
    adc_fifo_setup(true, true, 1, false, false);
    adc_set_clkdiv(adc_clock_div);


    // Setup DMA
    adc_dma_chan = dma_claim_unused_channel(true);
    dma_channel_set_irq0_enabled(adc_dma_chan, true);
    irq_set_exclusive_handler(DMA_IRQ_0, adc_dma_isr);
    irq_set_enabled(DMA_IRQ_0, true);

    dma_channel_config cfg = dma_channel_get_default_config(adc_dma_chan);
    channel_config_set_transfer_data_size(&cfg, DMA_SIZE_16);
    channel_config_set_read_increment(&cfg, false);
    channel_config_set_write_increment(&cfg, true);
    channel_config_set_dreq(&cfg, DREQ_ADC);
    
    dma_channel_configure(
        adc_dma_chan,
        &cfg,
        &adc_samples_buf[0],
        &adc_hw->fifo,
        adc_dma_transfer_count,
        true
    );
}

void fft_engine_init(queue_t *freq_levels_q, uint8_t runs_per_sec) {
    levels_q = freq_levels_q;
    uint32_t engine_ready = FFT_ENGINE_READY;
    int16_t *adc_samples = NULL;
    int32_t hann_window_value;
    int16_t sample;
    uint16_t adc_samples_count = 2 * adc_dma_transfer_count;
    
    analysis_per_sec = runs_per_sec;
    
    init_adc_dma();
    adc_run(true);
    
    queue_add_blocking(levels_q, &engine_ready);
    printf("In here yes\n");
    while (true) {
        printf("In here\n");
        if (!samples_ready) {
            __wfe();
            continue;
        }
        samples_ready = 0;
        __wfe();

        // for (uint16_t i = 0; i < adc_samples_count; i++) {
        //     // We need to remove the DC bias and scale the sample,
        //     // since the original signal is attenuated by half
        //     sample = (adc_samples_for_fft_buf[i] - DC_BIAS) * 2;
            
        //     // Apply Hann windowing function
        //     hann_window_value = (int32_t)(0.5 * (1 - cos(2 * M_PI * i / (adc_samples_count - 1))) * SCALE_FACTOR);
        //     sample = ((int32_t) sample) * hann_window_value / SCALE_FACTOR;
            
        //     adc_samples_for_fft_buf[i]  = (int16_t) sample;
        // }
        
        // printf("Got sample\n");

        // TODO:
            // do FFT analysis
            // convert amplitudes to dbFS
            // apply EMA on resulting dbFS
            // scale the resulting amplitudes to LED states
            // push LED states to queue
    }
}