cmake_minimum_required(VERSION 3.13)
include(pico_sdk_import.cmake)

project(pico-audio-visualizer VERSION 0.1 LANGUAGES C CXX ASM)
set(PICO_BOARD pico_w)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
# set(CYW43_ARCH_DEBUG_ENABLED 0)


pico_sdk_init()


add_compile_options(-Wall
        -Wno-format          # int != int32_t as far as the compiler is concerned because gcc has int32_t as long int
        -Wno-unused-function # we have some for the docs that aren't called
        -Wno-maybe-uninitialized
        )
    

add_executable(visualiser
    fft_engine.c
    renderer.c
    visualiser.c
)
# ADC_AVG_ENABLED - average ADC samples
# HANN_ENABLED - apply Hann windowing function before FFT analysis
# EMA_ENABLED - apply EMA to dbFS for each frequency band
target_compile_definitions(visualiser PRIVATE
                                    FREQ_BINS=3
                                    ADC_AVG_ENABLED=1
                                    HANN_ENABLED=1 
                                    EMA_ENABLED=1)

set(KISSFFT_STATIC ON)
set(KISSFFT_TEST OFF)
set(KISSFFT_TOOLS OFF)
set(KISSFFT_DATATYPE int16_t)
add_subdirectory(kissfft)

pico_enable_stdio_usb(visualiser 0)
pico_enable_stdio_uart(visualiser 1)

# pull in common dependencies
target_link_libraries(visualiser
    pico_stdlib
    pico_malloc
    pico_cyw43_arch_none
    pico_multicore
    hardware_adc
    hardware_dma
    hardware_clocks
    kissfft
    )


pico_add_extra_outputs(visualiser)