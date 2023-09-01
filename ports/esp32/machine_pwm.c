/*
 * This file is part of the MicroPython project, http://micropython.org/
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2016-2021 Damien P. George
 * Copyright (c) 2018 Alan Dragomirecky
 * Copyright (c) 2020 Antoine Aubert
 * Copyright (c) 2021, 2023 Ihor Nehrutsa
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#include <math.h>

#include "py/runtime.h"
#include "py/mphal.h"

#include "hal/ledc_hal.h"
#include "driver/ledc.h"
#include "esp_err.h"
#include "soc/gpio_sig_map.h"

#define MP_PRN_LEVEL 3
#include "py/mpprint.h"

typedef struct _chan_t {
    // Which channel has which GPIO pin assigned?
    // (-1 if not assigned)
    gpio_num_t pin;
    // Which channel has which timer assigned?
    // (-1 if not assigned)
    int timer;
} chan_t;

// List of PWM channels
STATIC chan_t chans[LEDC_SPEED_MODE_MAX][LEDC_CHANNEL_MAX];

// List of timer configs
STATIC ledc_timer_config_t timers[LEDC_SPEED_MODE_MAX][LEDC_TIMER_MAX];

// Params for PWM operation
// 5khz is default frequency
#define PWM_FREQ (5000)

// 10-bit resolution (compatible with esp8266 PWM)
#define PWM_RES_10_BIT (LEDC_TIMER_10_BIT)

// Maximum duty value on 10-bit resolution
#define MAX_DUTY_U10 (1 << PWM_RES_10_BIT)
// https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/ledc.html#supported-range-of-frequency-and-duty-resolutions
// duty() uses 10-bit resolution or less
// duty_u16() and duty_ns() use 16-bit resolution or less

// Duty resolution of user interface in `duty_u16()` and `duty_u16` parameter in constructor/initializer
#define UI_RES_16_BIT (16)
// Maximum duty value on highest user interface resolution
#define UI_MAX_DUTY (1 << UI_RES_16_BIT)

#if defined(SOC_LEDC_TIMER_BIT_WIDTH)
#  if SOC_LEDC_TIMER_BIT_WIDTH < 16
#    define HIGHEST_PWM_RES (LEDC_TIMER_BIT_MAX - 1)
#  else
#    define HIGHEST_PWM_RES (LEDC_TIMER_16_BIT) // 20 bit for ESP32, but 16 bit is used
#  endif
#elif defined(SOC_LEDC_TIMER_BIT_WIDE_NUM)
#  if SOC_LEDC_TIMER_BIT_WIDE_NUM < 16
#    define HIGHEST_PWM_RES (LEDC_TIMER_BIT_MAX - 1)
#  else
#    define HIGHEST_PWM_RES (LEDC_TIMER_16_BIT) // 20 bit for ESP32, but 16 bit is used
#  endif
#else
#  error HIGHEST_PWM_RES
#endif

#if SOC_LEDC_SUPPORT_REF_TICK
// If the PWM frequency is less than EMPIRIC_FREQ, then LEDC_REF_CLK_HZ(1 MHz) source is used, else LEDC_APB_CLK_HZ(80 MHz) source is used
#define EMPIRIC_FREQ (10) // Hz
#endif

// Config of timer upon which we run all PWM'ed GPIO pins
STATIC bool pwm_inited = false;

// MicroPython PWM object struct
typedef struct _machine_pwm_obj_t {
    mp_obj_base_t base;
    gpio_num_t pin;
    int mode;
    int channel;
    int timer;
    int duty_x;       // PWM_RES_10_BIT if duty(), HIGHEST_PWM_RES if duty_u16(), -HIGHEST_PWM_RES if duty_ns()
    int duty;         // saved values from previous duty setters
    int channel_duty; // saved values from previous duty setters calculated to raw channel_duty
    uint8_t output_invert;
} machine_pwm_obj_t;

STATIC void register_channel(int mode, int channel, int pin, int timer) {
    if ((mode >= 0) && (mode < LEDC_SPEED_MODE_MAX)
    && (channel >= 0) && (channel < LEDC_CHANNEL_MAX)) {
        MP_PRN(2, "register_channel:mode=%d, channel=%d, pin=%d, timer=%d", mode, channel, pin, timer);
        chans[mode][channel].pin = pin;
        chans[mode][channel].timer = timer;
    }
}

STATIC void unregister_channel(int mode, int channel) {
    if ((mode >= 0) && (mode < LEDC_SPEED_MODE_MAX)
    && (channel >= 0) && (channel < LEDC_CHANNEL_MAX)) {
        MP_PRN(2, "unregister_channel:mode=%d, channel=%d", mode, channel);
        chans[mode][channel].pin = -1;
        chans[mode][channel].timer = -1;
    }
}

STATIC void pwm_init(void) {
    // Initial condition: no channels assigned
    for (int mode = 0; mode < LEDC_SPEED_MODE_MAX; ++mode) {
        for (int channel = 0; channel < LEDC_CHANNEL_MAX; ++channel) {
            unregister_channel(mode, channel);
        }

        // Prepare all timers config
        // Initial condition: no timers assigned
        for (int timer = 0; timer < LEDC_TIMER_MAX; ++timer) {
            timers[mode][timer].duty_resolution = HIGHEST_PWM_RES;
            timers[mode][timer].freq_hz = 0; // unset timer is 0
            timers[mode][timer].speed_mode = mode;
            timers[mode][timer].timer_num = timer;
            timers[mode][timer].clk_cfg = LEDC_AUTO_CLK; // will reinstall later according to the EMPIRIC_FREQ
        }
    }
}

// Returns true if the timer is in use in addition to current channel
STATIC bool is_timer_in_use(int mode, int current_channel, int timer) {
    MP_PRN(6, "is_timer_in_use(mode=%d, current_channel=%d, timer=%d)", mode, current_channel, timer);
    for (int channel = 0; channel < LEDC_CHANNEL_MAX; ++channel) {
        if ((channel != current_channel) && (chans[mode][channel].timer == timer)) {
            MP_PRN(3, " is_timer_in_use(channel=%d, timer=%d)->true", channel, timer);
            return true;
        }
    }
    MP_PRN(3, " is_timer_in_use()->false");
    return false;
}

// Deinit channel and timer if the timer is unused, detach pin
STATIC void pwm_deinit(int mode, int channel) {
    MP_PRN(6, "pwm_deinit(mode=%d, channel=%d)", mode, channel);
    // Is valid channel?
    if ((mode >= 0) && (mode < LEDC_SPEED_MODE_MAX) && (channel >= 0) && (channel < LEDC_CHANNEL_MAX)) {
        // Clean up timer if necessary
        int timer = chans[mode][channel].timer;
        if (timer >= 0) {
            if (!is_timer_in_use(mode, channel, timer)) {
                check_esp_err(ledc_timer_rst(mode, timer));
                // Flag it unused
                timers[mode][timer].freq_hz = 0;
            }
        }

        int pin = chans[mode][channel].pin;
        if (pin >= 0) {
            // Mark it unused, and tell the hardware to stop routing
            check_esp_err(ledc_stop(mode, channel, 0));
            /*
            // Disable ledc signal for the pin
            if (mode == LEDC_LOW_SPEED_MODE) {
                esp_rom_gpio_connect_out_signal(pin, LEDC_LS_SIG_OUT0_IDX + channel, false, false);
            } else {
                #if SOC_LEDC_SUPPORT_HS_MODE
                esp_rom_gpio_connect_out_signal(pin, LEDC_HS_SIG_OUT0_IDX + channel, false, false);
                #endif
            }
            // reconfigure as GPIO
            //gpio_set_direction(pin, GPIO_MODE_INPUT_OUTPUT);
            */
        }
        unregister_channel(mode, channel);
    }
}

// This called from Ctrl-D soft reboot
void machine_pwm_deinit_all(void) {
    if (pwm_inited) {
        for (int mode = 0; mode < LEDC_SPEED_MODE_MAX; ++mode) {
            for (int channel = 0; channel < LEDC_CHANNEL_MAX; ++channel) {
                pwm_deinit(mode, channel);
            }
        }
        pwm_inited = false;
    }
}

STATIC void configure_channel(machine_pwm_obj_t *self) {
    MP_PRN(3, "configure_channel(mode=%d, channel=%d, timer=%d, pin=%d)", self->mode, self->channel, self->timer, self->pin);
    ledc_channel_config_t cfg = {
        .channel = self->channel,
        .duty = self->channel_duty,
        .gpio_num = self->pin,
        .intr_type = LEDC_INTR_DISABLE,
        .speed_mode = self->mode,
        .timer_sel = self->timer,
        .flags.output_invert = self->output_invert,
    };
    ledc_timer_config_t *timer = &timers[self->mode][self->timer];
    int max_duty = 1 << timer->duty_resolution;
    if (self->channel_duty == max_duty) {
        cfg.duty = 0;
        cfg.flags.output_invert = self->output_invert ^ 1;
    }
    check_esp_err(ledc_channel_config(&cfg));

    // reconfigure PWM output for Counter input
    gpio_set_direction(self->pin, GPIO_MODE_INPUT_OUTPUT);
    if (self->mode == LEDC_LOW_SPEED_MODE) {
        esp_rom_gpio_connect_out_signal(self->pin, LEDC_LS_SIG_OUT0_IDX + self->channel, self->output_invert, false);
    #if SOC_LEDC_SUPPORT_HS_MODE
    } else if (self->mode == LEDC_HIGH_SPEED_MODE) {
        esp_rom_gpio_connect_out_signal(self->pin, LEDC_HS_SIG_OUT0_IDX + self->channel, self->output_invert, false);
    #endif
    }
    /*
    test.py:
    ```
    import machine
    pin = machine.Pin(17)
    counter = machine.Counter(0, pin)  # must be first !!!
    pwm = machine.PWM(pin)             # must be second !!!

    print(pwm)
    print(counter)
    print("counter.value()=", counter.value())
    print("counter.value()=", counter.value())
    print("counter.value()=", counter.value())
    print("counter.value()=", counter.value())
    print("counter.value()=", counter.value())
    print("counter.value()=", counter.value())
    print("counter.value()=", counter.value())
    ```

    Output is:
    PWM(Pin(17), freq=5000, duty_u16=32768)
    Counter(0, src=Pin(17), direction=Counter.UP, edge=Counter.RISING, filter_ns=0)
    counter.value()= 92
    counter.value()= 94
    counter.value()= 95
    counter.value()= 95
    counter.value()= 142
    counter.value()= 142
    counter.value()= 143
    */
}

STATIC void pwm_is_active(machine_pwm_obj_t *self) {
    if (self->timer < 0) {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PWM is inactive"));
    }
}

// Calculate the duty parameters based on an ns value
STATIC int ns_to_duty(machine_pwm_obj_t *self, int ns) {
    ledc_timer_config_t *timer = &timers[self->mode][self->timer];
    int64_t duty = ((int64_t)ns * UI_MAX_DUTY * timer->freq_hz + 500000000LL) / 1000000000LL;
    if ((ns > 0) && (duty == 0)) {
        duty = 1;
    } else if (duty > UI_MAX_DUTY) {
        duty = UI_MAX_DUTY;
    }
    return duty;
}

STATIC int duty_to_ns(machine_pwm_obj_t *self, int duty) {
    ledc_timer_config_t *timer = &timers[self->mode][self->timer];
    int64_t ns = ((int64_t)duty * 1000000000LL + (int64_t)timer->freq_hz * UI_MAX_DUTY / 2) / ((int64_t)timer->freq_hz * UI_MAX_DUTY);
    return ns;
}

#define get_duty_raw(self) ledc_get_duty(self->mode, self->channel)

STATIC uint32_t get_duty_u16(machine_pwm_obj_t *self) {
    ledc_timer_config_t *timer = &timers[self->mode][self->timer];
    int max_duty = 1 << timer->duty_resolution;
    if (self->channel_duty == max_duty) {
        return UI_MAX_DUTY;
    } else {
        int resolution = timers[self->mode][self->timer].duty_resolution;
        if (resolution <= UI_RES_16_BIT) {
            return get_duty_raw(self) << (UI_RES_16_BIT - resolution);
        } else {
            return get_duty_raw(self) >> (resolution - UI_RES_16_BIT);
        }
    }
}

STATIC uint32_t get_duty_u10(machine_pwm_obj_t *self) {
    return get_duty_u16(self) >> (UI_RES_16_BIT - PWM_RES_10_BIT); // Scale down from 16 bit to 10 bit resolution
}

STATIC uint32_t get_duty_ns(machine_pwm_obj_t *self) {
    return duty_to_ns(self, get_duty_u16(self));
}

STATIC void set_duty_u16(machine_pwm_obj_t *self, int duty) {
    if ((duty < 0) || (duty > UI_MAX_DUTY)) {
        mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("duty_u16 must be from 0 to %d"), UI_MAX_DUTY);
    }

    ledc_timer_config_t *timer = &timers[self->mode][self->timer];
    int channel_duty;
    if (timer->duty_resolution <= UI_RES_16_BIT) {
        channel_duty = duty >> (UI_RES_16_BIT - timer->duty_resolution);
    } else {
        channel_duty = duty << (timer->duty_resolution - UI_RES_16_BIT);
    }
    int max_duty = 1 << timer->duty_resolution;
    if (channel_duty < 0) {
        channel_duty = 0;
    } else if (channel_duty > max_duty) {
        channel_duty = max_duty;
    }
    check_esp_err(ledc_set_duty(self->mode, self->channel, channel_duty));
    check_esp_err(ledc_update_duty(self->mode, self->channel));

    self->duty_x = HIGHEST_PWM_RES;
    self->duty = duty;
    self->channel_duty = channel_duty;
}

STATIC void set_duty_u10(machine_pwm_obj_t *self, int duty) {
    if ((duty < 0) || (duty > MAX_DUTY_U10)) {
        mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("duty must be from 0 to %u"), MAX_DUTY_U10);
    }
    set_duty_u16(self, duty << (UI_RES_16_BIT - PWM_RES_10_BIT));
    self->duty_x = PWM_RES_10_BIT;
    self->duty = duty;
}

STATIC void set_duty_ns(machine_pwm_obj_t *self, int ns) {
    if ((ns < 0) || (ns > duty_to_ns(self, UI_MAX_DUTY))) {
        mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("duty_ns must be from 0 to %d ns"), duty_to_ns(self, UI_MAX_DUTY));
    }
    set_duty_u16(self, ns_to_duty(self, ns));
    self->duty_x = -HIGHEST_PWM_RES;
    self->duty = ns;
}

STATIC void set_duty(machine_pwm_obj_t *self) {
    if (self->duty_x == HIGHEST_PWM_RES) {
        set_duty_u16(self, self->duty);
    } else if (self->duty_x == PWM_RES_10_BIT) {
        set_duty_u10(self, self->duty);
    } else if (self->duty_x == -HIGHEST_PWM_RES) {
        set_duty_ns(self, self->duty);
    }
}

// Set timer frequency
STATIC void set_freq(machine_pwm_obj_t *self, unsigned int freq) {
    ledc_timer_config_t *timer = &timers[self->mode][self->timer];
    if (timer->freq_hz != freq) {
        MP_PRN(3, "set_freq(mode=%d, timer=%d, freq=%d)", self->mode, self->timer, freq);
        // Find the highest bit resolution for the requested frequency
        uint32_t src_clk_freq = APB_CLK_FREQ; // 80 MHz
        #if SOC_LEDC_SUPPORT_REF_TICK
        if (freq < EMPIRIC_FREQ) {
            src_clk_freq = REF_CLK_FREQ; // 1 MHz
        }
        #endif
        uint32_t i = src_clk_freq;

        #if ESP_IDF_VERSION < ESP_IDF_VERSION_VAL(4, 4, 0)
        // original code
        i /= freq;
        #else
        // See https://github.com/espressif/esp-idf/issues/7722
        unsigned divider = (i + freq / 2) / freq; // rounded
        if (divider == 0) {
            divider = 1;
        }
        float f = (float)i / divider; // actual frequency
        if (f <= 1.0) {
            f = 1.0;
        }
        i = (unsigned int)roundf((float)i / f);
        #endif

        unsigned int res = 0;
        for (; i > 1; i >>= 1) {
            ++res;
        }

        // res = ledc_calc_duty_resolution(src_clk_freq, freq);

        if (res == 0) {
            res = 1;
        } else if (res > HIGHEST_PWM_RES) {
            // Limit resolution to HIGHEST_PWM_RES to match units of our duty
            res = HIGHEST_PWM_RES;
        }

        // Configure the new resolution and frequency
        timer->duty_resolution = res;
        timer->freq_hz = freq;
        timer->clk_cfg = LEDC_USE_APB_CLK;
        #if SOC_LEDC_SUPPORT_REF_TICK
        if (freq < EMPIRIC_FREQ) {
            timer->clk_cfg = LEDC_USE_REF_TICK;
        }
        #endif

        // Configure timer - Set frequency
        MP_PRN(3, " Configure timer - Set frequency: self->mode=%d, self->timer=%d, timer->freq_hz=%d", self->mode, self->timer, timer->freq_hz);
        check_esp_err(ledc_timer_config(timer));
        // Reset the timer if low speed
        if (self->mode == LEDC_LOW_SPEED_MODE) {
            check_esp_err(ledc_timer_rst(self->mode, self->timer));
        }

        // Save the same duty cycle when frequency is changed
        set_duty(self);
    }
}

STATIC bool is_free_channels(int mode, int pin) {
    MP_PRN(3, "is_free_channels(mode=%d, pin=%d)", mode, pin);
    for (int channel = 0; channel < LEDC_CHANNEL_MAX; ++channel) {
        if ((chans[mode][channel].pin < 0) || (chans[mode][channel].pin == pin)) {
            MP_PRN(3, " is_free_channels(mode=%d, pin=%d)->true", mode, pin);
            return true;
        }
    }
    MP_PRN(3, " is_free_channels()->false");
    return false;
}

// Find self channel or free channel in the mode
STATIC int find_channel(int mode, int pin) {
    MP_PRN(3, "find_channel(mode=%d, pin=%d)", mode, pin);
    int avail_channel = -1;
    for (int channel = 0; channel < LEDC_CHANNEL_MAX; ++channel) {
        if (chans[mode][channel].pin == pin) {
            MP_PRN(3, " find_channel(mode=%d, pin=%d)->channel=%d", mode, pin, channel);
            return channel;
        }
        if ((avail_channel < 0) && (chans[mode][channel].pin < 0)) {
            avail_channel = channel;
        }
    }
    MP_PRN(3, " find_channel(mode=%d, pin=%d)->avail_channel=%d", mode, pin, avail_channel);
    return avail_channel;
}

// Returns timer with the same mode and frequency, freq == 0 means free timer
STATIC int find_timer(int mode, unsigned int freq) {
    MP_PRN(3, "find_timer(mode=%d, freq=%d)", mode, freq);
    for (int timer = 0; timer < LEDC_TIMER_MAX; ++timer) {
        if (timers[mode][timer].freq_hz == freq) {
            MP_PRN(3, " find_timer(mode=%d, freq=%d)->timer=%d", mode, freq, timer);
            return timer;
        }
    }
    MP_PRN(3, " find_timer(mode=%d, freq=%d)->timer=-1", mode, freq);
    return -1;
}

// Try to find a timer with the same frequency in the current mode, otherwise in the next mode.
// If no existing timer and channel was found, then try to find free timer in any mode.
// If the mode or channel is changed, release the channel and select(bind) a new channel in the next mode.
STATIC void select_a_timer(machine_pwm_obj_t *self, int freq) {
    MP_PRN(2, "select_a_timer(freq=%d)", freq);
    if ((freq <= 0) || (freq > 40000000)) {
        mp_raise_ValueError(MP_ERROR_TEXT("frequency must be from 1Hz to 40MHz"));
    }

    // mode, channel, timer may be -1(not defined) or actual values
    int save_mode = self->mode;
    int save_channel = self->channel;
    // int save_timer = self->timer;

    int mode = MAX(self->mode, 0);

    // Check if an already running timer with the required frequency is running in the current mode
    int timer = -1;
    if (is_free_channels(mode, self->pin)) {
        timer = find_timer(mode, freq);
    }
    // If no existing timer and channel was found in the current mode, then find a new one in another mode
    if (timer < 0) {
        // Calc next mode
        int mode_ = mode;
        if (mode > 0) {
            --mode;
        } else if (mode < (LEDC_SPEED_MODE_MAX - 1)) {
            ++mode;
        }

        if (mode_ != mode) {
            if (is_free_channels(mode, self->pin)) {
                timer = find_timer(mode, freq);
            }
        }
    }
    // If the timer is found, then bind and set the duty
    if ((timer >= 0)
    && (timers[mode][timer].freq_hz != 0)
    && (timers[mode][timer].freq_hz != freq)
    && (self->channel >= 0)
    && (self->mode >= 0)) {
        // Bind the channel to the timer
        self->mode = mode;
        self->timer = timer;
        check_esp_err(ledc_bind_channel_timer(self->mode, self->channel, self->timer));
        register_channel(self->mode, self->channel, self->pin, self->timer);
        set_duty(self);
    } else {
        timer = -1;
    }

    if (timer < 0) {
        // Try to reuse self timer
        MP_PRN(2, " Try to reuse self timer:self->mode=%d, self->timer=%d, self->channel=%d, self->pin=%d", self->mode, self->timer, self->channel, self->pin);
        if ((self->mode >= 0) && (self->channel >= 0)) {
            if (!is_timer_in_use(self->mode, self->channel, self->timer)) {
                mode = self->mode;
                timer = self->timer;
            }
        }
        MP_PRN(2, " Try to reuse self timer:mode=%d, timer=%d", mode, timer);
        // If no existing timer and channel was found, then try to find free timer in any mode
        if (timer < 0) {
            mode = -1;
            while ((timer < 0) && (mode < (LEDC_SPEED_MODE_MAX - 1))) {
                ++mode;
                if (is_free_channels(mode, self->pin)) {
                    timer = find_timer(mode, 0); // find free timer
                }
            }
            if (timer < 0) {
                mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("out of PWM timers:%d"), LEDC_SPEED_MODE_MAX * LEDC_TIMER_MAX);
            }
        }
        self->mode = mode;
        self->timer = timer;
    }
    if ((save_mode != self->mode) || (save_channel != self->channel)) {
        unregister_channel(save_mode, save_channel);
    }
}

/******************************************************************************/
// MicroPython bindings for PWM

STATIC void mp_machine_pwm_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    machine_pwm_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_printf(print, "PWM(Pin(%u)", self->pin);
    if (self->timer >=0) {
        mp_printf(print, ", freq=%u", ledc_get_freq(self->mode, self->timer));

        if (self->duty_x == PWM_RES_10_BIT) {
            mp_printf(print, ", duty=%d", get_duty_u10(self));
        } else if (self->duty_x == -HIGHEST_PWM_RES) {
            mp_printf(print, ", duty_ns=%d", get_duty_ns(self));
        } else {
            mp_printf(print, ", duty_u16=%d", get_duty_u16(self));
        }
        if (self->output_invert) {
            mp_printf(print, ", invert=%d", self->output_invert);
        }
        mp_printf(print, ")");
        #if 1
        int resolution = timers[self->mode][self->timer].duty_resolution;
        mp_printf(print, "  # resolution=%d", resolution);

        mp_printf(print, ", (duty=%.2f%%, resolution=%.6f%%)", 100.0 * get_duty_raw(self) / (1 << resolution), 100.0 * 1 / (1 << resolution)); // percents

        mp_printf(print, ", mode=%d, channel=%d, timer=%d", self->mode, self->channel, self->timer);
        #endif
    } else {
        mp_printf(print, ")");
    }
}

// This called from pwm.init() method
/*
Check the current mode.
If the frequency is changed, try to find a timer with the same frequency
in the current mode, otherwise in the new mode.
If the mode is changed, release the channel and select a new channel in the new mode.
Then set the frequency with the same duty.
*/
STATIC void mp_machine_pwm_init_helper(machine_pwm_obj_t *self,
    size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    MP_PRN(6, "mp_machine_pwm_init_helper()");

    enum { ARG_freq, ARG_duty, ARG_duty_u16, ARG_duty_ns, ARG_invert };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_freq, MP_ARG_INT, {.u_int = -1} },
        { MP_QSTR_duty, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = -1} },
        { MP_QSTR_duty_u16, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = -1} },
        { MP_QSTR_duty_ns, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = -1} },
        { MP_QSTR_invert, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0}},
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, pos_args, kw_args,
        MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    int duty = args[ARG_duty].u_int;
    int duty_u16 = args[ARG_duty_u16].u_int;
    int duty_ns = args[ARG_duty_ns].u_int;
    /*
    if (((duty != -1) && (duty_u16 != -1)) || ((duty != -1) && (duty_ns != -1)) || ((duty_u16 != -1) && (duty_ns != -1))) {
        mp_raise_ValueError(MP_ERROR_TEXT("only one of parameters 'duty', 'duty_u16' or 'duty_ns' is allowed"));
    }
    */
    /*
    if ((duty < 0) && (duty_u16 < 0) && (duty_ns < 0)) {
        mp_raise_ValueError(MP_ERROR_TEXT("one of parameters 'duty', 'duty_u16', or 'duty_ns' is required"));
    }
    */
    if (duty_u16 >= 0) {
        self->duty_x = HIGHEST_PWM_RES;
        self->duty = duty_u16;
    } else if (duty_ns >= 0) {
        self->duty_x = -HIGHEST_PWM_RES;
        self->duty = duty_ns;
    } else if (duty >= 0) {
        self->duty_x = PWM_RES_10_BIT;
        self->duty = duty;
    } else if (self->duty_x == 0) {
        self->duty_x = HIGHEST_PWM_RES;
        self->duty = (1 << HIGHEST_PWM_RES) / 2; // 50%
    }

    self->output_invert = args[ARG_invert].u_int == 0 ? 0 : 1;

    int save_mode = self->mode;
    int save_channel = self->channel;
    int save_timer = self->timer;

    // Check the current mode and channel
    int mode = -1;
    int channel = -1;
    while ((channel < 0) &&  (mode < (LEDC_SPEED_MODE_MAX - 1))) {
        ++mode;
        channel = find_channel(mode, self->pin);
    }
    if (channel < 0) {
        mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("out of PWM channels:%d"), LEDC_SPEED_MODE_MAX * LEDC_CHANNEL_MAX); // in all modes
    }
    self->mode = mode;
    self->channel = channel;

    int freq = args[ARG_freq].u_int;
    // Check if freq wasn't passed as an argument
    if ((freq == -1) && (mode >= 0) && (channel >= 0)) {
        // Check if already set, otherwise use the default freq.
        // It is possible in case:
        // pwm = PWM(pin, freq=1000, duty=256)
        // pwm = PWM(pin, duty=128)
        if (chans[mode][channel].timer >= 0) {
            freq = timers[mode][chans[mode][channel].timer].freq_hz;
        }
        if (freq <= 0) {
            freq = PWM_FREQ;
        }
    }

    select_a_timer(self, freq);
    set_freq(self, freq);

    // New PWM assignment
    if ((chans[mode][channel].pin < 0)
    || ((save_mode != self->mode))
    || ((save_channel != self->channel))
    || ((save_timer != self->timer))) {
        configure_channel(self);
        register_channel(self->mode, self->channel, self->pin, self->timer);
    }
}

// This called from PWM() constructor
STATIC mp_obj_t mp_machine_pwm_make_new(const mp_obj_type_t *type,
    size_t n_args, size_t n_kw, const mp_obj_t *args) {
    MP_PRN(3, "mp_machine_pwm_make_new()");
    mp_arg_check_num(n_args, n_kw, 1, 2, true);
    gpio_num_t pin_id = machine_pin_get_id(args[0]);

    // create PWM object from the given pin
    machine_pwm_obj_t *self = mp_obj_malloc(machine_pwm_obj_t, &machine_pwm_type);
    self->pin = pin_id;
    self->mode = -1;
    self->channel = -1;
    self->timer = -1;
    self->duty_x = 0;
    self->duty = 0;
    self->channel_duty = 0;
    self->output_invert = 0;

    // start the PWM subsystem if it's not already running
    if (!pwm_inited) {
        pwm_init();
        pwm_inited = true;
    }

    // start the PWM running for this channel
    mp_map_t kw_args;
    mp_map_init_fixed_table(&kw_args, n_kw, args + n_args);
    mp_machine_pwm_init_helper(self, n_args - 1, args + 1, &kw_args);

    return MP_OBJ_FROM_PTR(self);
}

// This called from pwm.deinit() method
STATIC void mp_machine_pwm_deinit(machine_pwm_obj_t *self) {
    MP_PRN(6, "mp_machine_pwm_deinit()");
    pwm_deinit(self->mode, self->channel);
    self->mode = -1;
    self->channel = -1;
    self->timer = -1;
    self->duty_x = 0;
    self->duty = 0;
    self->channel_duty = 0;
    self->output_invert = 0;
}

// Set and get methods of PWM class

STATIC mp_obj_t mp_machine_pwm_freq_get(machine_pwm_obj_t *self) {
    if (self->timer < 0) {
        return MP_OBJ_NEW_SMALL_INT(0);
    } else {
        return MP_OBJ_NEW_SMALL_INT(ledc_get_freq(self->mode, self->timer));
    }
}

STATIC void mp_machine_pwm_freq_set(machine_pwm_obj_t *self, mp_int_t freq) {
    pwm_is_active(self);
    if (freq == timers[self->mode][self->timer].freq_hz) {
        return;
    }
    // Set new PWM frequency
    select_a_timer(self, freq);
    set_freq(self, freq);
}

STATIC mp_obj_t mp_machine_pwm_duty_get(machine_pwm_obj_t *self) {
    if (self->timer < 0) {
        return MP_OBJ_NEW_SMALL_INT(0);
    } else {
        return MP_OBJ_NEW_SMALL_INT(get_duty_u10(self));
    }
}

STATIC void mp_machine_pwm_duty_set(machine_pwm_obj_t *self, mp_int_t duty) {
    pwm_is_active(self);
    set_duty_u10(self, duty);
}

STATIC mp_obj_t mp_machine_pwm_duty_get_u16(machine_pwm_obj_t *self) {
    if (self->timer < 0) {
        return MP_OBJ_NEW_SMALL_INT(0);
    } else {
        return MP_OBJ_NEW_SMALL_INT(get_duty_u16(self));
    }
}

STATIC void mp_machine_pwm_duty_set_u16(machine_pwm_obj_t *self, mp_int_t duty) {
    pwm_is_active(self);
    set_duty_u16(self, duty);
}

STATIC mp_obj_t mp_machine_pwm_duty_get_ns(machine_pwm_obj_t *self) {
    if (self->timer < 0) {
        return MP_OBJ_NEW_SMALL_INT(0);
    } else {
        return MP_OBJ_NEW_SMALL_INT(get_duty_ns(self));
    }
}

STATIC void mp_machine_pwm_duty_set_ns(machine_pwm_obj_t *self, mp_int_t duty) {
    pwm_is_active(self);
    set_duty_ns(self, duty);
}
