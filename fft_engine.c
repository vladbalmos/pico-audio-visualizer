#include <stdio.h>
#include "math.h"
#include "pico/util/queue.h"
#include "pico/stdlib.h"
#include <math.h>
#include "fft_engine.h"

#define ADC_SAMPLE_RATE_HZ 44100
#define ADC_CLOCK_SPEED_HZ 48.0 * 1000 * 1000

static int adc_dma_chan;
static int adc_dma_transfer_count;

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
    // push the buffer to queue
    // dma_channel_set_write_addr(adc_dma_chan, buffer, true);
}

    

void init_adc_dma() {
    float adc_clock_div = ADC_CLOCK_SPEED_HZ / ADC_SAMPLE_RATE_HZ;
    float analysis_period = 1.0 / analysis_per_sec;
    float adc_capture_period = 1.0 / ADC_SAMPLE_RATE_HZ;

    adc_dma_transfer_count = div_by_32((int) (analysis_period / adc_capture_period));

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
        NULL, // TODO: allocate memory for buffer
        &adc_hw->fifo,
        adc_dma_transfer_count,
        true
    );
    
}
void fft_engine_init(queue_t *freq_levels_q, uint8_t runs_per_sec) {
    levels_q = freq_levels_q;
    uint32_t engine_ready = FFT_ENGINE_READY;
    
    analysis_per_sec = runs_per_sec;

    init_adc_dma();
    
    queue_add_blocking(levels_q, &engine_ready);
    
    while (true) {
        // TODO:
            // pop adc samples from queue
            // process samples:
                // remove DC bias
                // convert each sample from unsigned to signed
            // every 16.6 ms:
                // apply Hanning on the last 32 ms samples
                // do FFT analysis
                // convert amplitudes to dbFS
                // apply EMA on resulting dbFS
                // scale the resulting amplitudes to LED states
                // push LED states to queue
    
        
        __wfe();
    }
}