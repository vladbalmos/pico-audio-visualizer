#include <stdio.h>
#include <malloc.h>
#include <string.h>
#include <math.h>
#include "pico/util/queue.h"
#include "pico/stdlib.h"
#include "fft_engine.h"
#include "kissfft/kiss_fftr.h"

#define ADC_SAMPLES_COUNT 736
#define ADC_SAMPLES_FOR_FFT_COUNT (2 * ADC_SAMPLES_COUNT)
#define MAX_FFT_VALUES (ADC_SAMPLES_COUNT + 1)

#ifdef HANN_ENABLED
#define SCALE_FACTOR (1<<16)
#endif

#define ADC_SAMPLES_Q_MAX_ELEMENTS 8
#define ADC_SAMPLE_RATE_HZ 44100
#define ADC_CLOCK_SPEED_HZ 48.0 * 1000 * 1000

#define DC_BIAS 2048 // Half of max voltage (3.3V = 4096 for our 12bit ADC)

int adc_dma_chan;

int16_t adc_buf[ADC_SAMPLES_FOR_FFT_COUNT] = {0};
int16_t adc_samples_buf[ADC_SAMPLES_COUNT] = {0};
int16_t adc_prev_samples_buf[ADC_SAMPLES_COUNT] = {0};
    
#ifdef HANN_ENABLED
    int16_t hann_window_lookup[ADC_SAMPLES_FOR_FFT_COUNT] = {0};
#endif

#ifdef ADC_AVG_ENABLED
int16_t adc_averaged_samples_buf[ADC_SAMPLES_COUNT] = {0};
#endif

int16_t adc_samples_for_fft_buf[ADC_SAMPLES_FOR_FFT_COUNT] = {0};
int32_t now = 0;
int32_t last_called = 0;
int32_t isr_duration = 0;

queue_t samples_ready_q;
uint8_t isr_samples_ready_flag = 1;
queue_t *levels_q = NULL;

void __isr adc_dma_isr() {
    now = time_us_32();
    isr_duration = now - last_called;
    last_called = now;
    int32_t sample;

    // Since we're analyzing the last 32ms of audio, we need the last 16ms sample set
#ifdef ADC_AVG_ENABLED
    memcpy(adc_samples_for_fft_buf, adc_averaged_samples_buf, ADC_SAMPLES_COUNT * sizeof(int16_t));
    
    for (uint16_t i = 0; i < ADC_SAMPLES_COUNT; i++) {
        // We need to remove the DC bias and scale the sample,
        // since the original signal is attenuated by half
        adc_samples_buf[i] = adc_samples_buf[i] - DC_BIAS;
        // Average each sample using the current and previous sample set
        // add the result to the `averaged` buffer
        adc_averaged_samples_buf[i] = (adc_samples_buf[i] + adc_prev_samples_buf[i]) / 2;
    }
    
    memcpy(adc_prev_samples_buf, adc_samples_buf, ADC_SAMPLES_COUNT * sizeof(int16_t));
    
    // Append the new sample set
    memcpy(&adc_samples_for_fft_buf[ADC_SAMPLES_COUNT], adc_averaged_samples_buf, ADC_SAMPLES_COUNT * sizeof(int16_t));
#else
    memcpy(adc_samples_for_fft_buf, adc_prev_samples_buf, ADC_SAMPLES_COUNT * sizeof(int16_t));

    for (uint16_t i = 0; i < ADC_SAMPLES_COUNT; i++) {
        // We need to remove the DC bias and scale the sample,
        // since the original signal is attenuated by half
        adc_samples_buf[i] = adc_samples_buf[i] - DC_BIAS;
    }

    memcpy(adc_prev_samples_buf, adc_samples_buf, ADC_SAMPLES_COUNT * sizeof(int16_t));

    // Append the new sample set
    memcpy(&adc_samples_for_fft_buf[ADC_SAMPLES_COUNT], adc_samples_buf, ADC_SAMPLES_COUNT * sizeof(int16_t));
#endif
    
    
#ifdef HANN_ENABLED
        // Apply Hann windowing function
        for (uint16_t i = 0; i < ADC_SAMPLES_FOR_FFT_COUNT; i++) {
            sample = adc_samples_for_fft_buf[i];
            sample = (int32_t) sample * hann_window_lookup[i];
            adc_samples_for_fft_buf[i]  = (int16_t) (sample >> 16);
        }
#endif

    // Restart DMA transfer
    dma_hw->ints0 = 1u << adc_dma_chan;
    dma_channel_set_write_addr(adc_dma_chan, adc_samples_buf, true);

    // Notify event loop that samples are ready
    queue_try_add(&samples_ready_q, &isr_samples_ready_flag);
}

void init_adc_dma() {
    float adc_clock_div = ADC_CLOCK_SPEED_HZ / ADC_SAMPLE_RATE_HZ;

    // Setup ADC
    adc_init();
    adc_gpio_init(26);
    adc_select_input(0);
    adc_fifo_setup(true, true, 1, false, false);
    adc_set_clkdiv(adc_clock_div);

    // Setup DMA
    adc_dma_chan = dma_claim_unused_channel(true);

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
        ADC_SAMPLES_COUNT,
        true
    );
    dma_channel_set_irq1_enabled(adc_dma_chan, true);
    irq_set_exclusive_handler(DMA_IRQ_1, adc_dma_isr);
    irq_set_enabled(DMA_IRQ_1, true);
}

void fft_engine_init(queue_t *freq_levels_q, uint8_t runs_per_sec) {
    levels_q = freq_levels_q;

    uint32_t engine_ready = FFT_ENGINE_READY;
    int16_t sample;
    uint8_t samples_ready_flag = 0;
    float mag;
    uint32_t freq;
    uint32_t freq_multiplier = ADC_SAMPLE_RATE_HZ / MAX_FFT_VALUES;
    float dbFS;
    kiss_fftr_cfg fft_cfg = kiss_fftr_alloc(ADC_SAMPLES_FOR_FFT_COUNT, 0, NULL, NULL);
    kiss_fft_cpx fft_output[MAX_FFT_VALUES];

    queue_init(&samples_ready_q, sizeof(uint8_t), ADC_SAMPLES_Q_MAX_ELEMENTS);

    init_adc_dma();

#ifdef HANN_ENABLED
    // Create Hann lookup table
    for (int i = 0; i < ADC_SAMPLES_FOR_FFT_COUNT; i++) {
        double hann_value = 0.5 * (1 - cos(2 * M_PI * i / (ADC_SAMPLES_FOR_FFT_COUNT - 1)));
        hann_window_lookup[i] = (int16_t) (hann_value * SCALE_FACTOR);
    }
#endif

    adc_run(true);

    queue_add_blocking(levels_q, &engine_ready);
    int32_t t = time_us_32();
    int32_t d;
    
#ifdef ADC_AVG_ENABLED
    printf("ADC AVG enabled\n");
#endif
#ifdef HANN_ENABLED
    printf("Hann windowing enabled\n");
#endif


    while (true) {
        queue_remove_blocking(&samples_ready_q, &samples_ready_flag);
        memcpy(adc_buf, adc_samples_for_fft_buf, ADC_SAMPLES_FOR_FFT_COUNT * sizeof(int16_t));

        uint32_t start_time = time_us_32();
        d = start_time - t;
        kiss_fftr(fft_cfg, adc_buf, fft_output);

        // TODO: finish computing magnitude & convert to dbFS
        for (uint16_t i = 0;  i < MAX_FFT_VALUES; i++) {
            mag = sqrt(fft_output[i].r * fft_output[i].r + fft_output[i].i * fft_output[i].i);
            freq = i * freq_multiplier;
            dbFS = 20 * log10(mag / 2048);
        }
        
        if (d > 250000) {
            uint32_t end_time = time_us_32();
            printf("FFT: %d. ISR: %d. Diff since last_called: %d\n", end_time - start_time, isr_duration, end_time - last_called);
            t = start_time;
        }

        queue_add_blocking(levels_q, &engine_ready);

        // TODO:
            // implement ADC calibration
            // convert amplitudes to dbFS
            // apply EMA on resulting dbFS
            // scale the resulting amplitudes to LED states
            // push LED states to queue
    }
}