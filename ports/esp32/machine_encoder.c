/*
 * This file is part of the Micro Python project, http://micropython.org/
 * This file was generated by micropython-extmod-generator https://github.com/prusnak/micropython-extmod-generator
 * from Python stab file pcnt.py
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2020-2021 Ihor Nehrutsa
 * Copyright (c) 2021 Jonathan Hogg
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

/*
ESP32 Pulse Counter
https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/pcnt.html
Wrapped around
https://github.com/espressif/esp-idf/blob/master/components/driver/include/driver/pcnt.h
https://github.com/espressif/esp-idf/blob/master/components/hal/include/hal/pcnt_types.h
https://github.com/espressif/esp-idf/blob/master/components/driver/pcnt.c
See also
https://github.com/espressif/esp-idf/tree/master/examples/peripherals/pcnt/pulse_count_event
*/

/*
ESP32 Quadrature Counter based on Pulse Counter(PCNT)
Based on
https://github.com/madhephaestus/ESP32Encoder
https://github.com/bboser/MicroPython_ESP32_psRAM_LoBo/blob/quad_decoder/MicroPython_BUILD/components/micropython/esp32/machine_dec.c
See also
https://github.com/espressif/esp-idf/tree/master/examples/peripherals/pcnt/rotary_encoder
*/

#include "py/runtime.h"
#include "mphalport.h"
#include "modmachine.h"

#if MICROPY_PY_MACHINE_PCNT

#include "driver/pcnt.h"
#include "soc/pcnt_struct.h"
#include "esp_err.h"

#include "machine_encoder.h"

#define GET_INT mp_obj_get_int_truncated
// #define GET_INT mp_obj_get_ll_int // need PR: py\obj.c: Get 64-bit integer arg. #80896

static pcnt_isr_handle_t pcnt_isr_handle = NULL;
static mp_pcnt_obj_t *pcnts[PCNT_UNIT_MAX] = {};

/* Decode what PCNT's unit originated an interrupt
 * and pass this information together with the event type
 * the main program using a queue.
 */
#if CONFIG_IDF_TARGET_ESP32S2 || CONFIG_IDF_TARGET_ESP32S3
#define H_LIM_LAT cnt_thr_h_lim_lat_un
#define L_LIM_LAT cnt_thr_l_lim_lat_un
#define THRES0_LAT cnt_thr_thres0_lat_un
#define THRES1_LAT cnt_thr_thres0_lat_un
#define ZERO_LAT cnt_thr_zero_lat_un
#else
#define H_LIM_LAT h_lim_lat
#define L_LIM_LAT l_lim_lat
#define THRES0_LAT thres0_lat
#define THRES1_LAT thres1_lat
#define ZERO_LAT zero_lat
#endif
STATIC void IRAM_ATTR pcnt_intr_handler(void *arg) {
    for (int id = 0; id < PCNT_UNIT_MAX; ++id) {
        if (PCNT.int_st.val & (1 << id)) {
            mp_pcnt_obj_t *self = pcnts[id];

            if (PCNT.status_unit[id].H_LIM_LAT) {
                self->counter += INT16_ROLL;
            } else if (PCNT.status_unit[id].L_LIM_LAT) {
                self->counter -= INT16_ROLL;
            }

            if (PCNT.status_unit[id].THRES1_LAT) {
                if (self->counter == self->counter_match1) {
                    mp_sched_schedule(self->handler_match1, MP_OBJ_FROM_PTR(self));
                }
            }
            if (PCNT.status_unit[id].THRES0_LAT) {
                if (self->counter == self->counter_match2) {
                    mp_sched_schedule(self->handler_match2, MP_OBJ_FROM_PTR(self));
                }
            }
            if (PCNT.status_unit[id].ZERO_LAT) {
                if (self->counter == 0) {
                    mp_sched_schedule(self->handler_zero, MP_OBJ_FROM_PTR(self));
                }
            }

            PCNT.int_clr.val |= 1 << id; // clear the interrupt
        }
    }
}

STATIC void register_isr_handler(void) {
    if (pcnt_isr_handle == NULL) {
        check_esp_err(pcnt_isr_register(pcnt_intr_handler, (void *)0, (int)0, (pcnt_isr_handle_t *)&pcnt_isr_handle));
        if (pcnt_isr_handle == NULL) {
            mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("wrap interrupt failed"));
        }
    }
}

/* Calculate the filter parameters based on an ns value
   1 / 80MHz = 12.5ns - min filter period
   12.5ns * FILTER_MAX = 12.5ns * 1023 = 12787.5ns - max filter period */
#define ns_to_filter(ns) ((ns * (APB_CLK_FREQ / 1000000) + 500) / 1000)
#define filter_to_ns(filter) (filter * 1000 / (APB_CLK_FREQ / 1000000))

STATIC uint16_t get_filter_value_ns(pcnt_unit_t unit) {
    uint16_t value;
    check_esp_err(pcnt_get_filter_value(unit, &value));

    return filter_to_ns(value);
}

STATIC void set_filter_value(pcnt_unit_t unit, int16_t value) {
    /*
    if ((value < 0) || (value > FILTER_MAX)) {
        mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("correct filter value is 0..%d ns"), filter_to_ns(FILTER_MAX));
    }
    */
    if (value < 0) {
        value = 0;
    } else if (value > FILTER_MAX) {
        value = FILTER_MAX;
    }

    check_esp_err(pcnt_set_filter_value(unit, value));
    if (value) {
        check_esp_err(pcnt_filter_enable(unit));
    } else {
        check_esp_err(pcnt_filter_disable(unit));
    }
}

STATIC void pcnt_disable_events(mp_pcnt_obj_t *self) {
    if (self->handler_match2 != MP_OBJ_NULL) {
        check_esp_err(pcnt_event_disable(self->unit, PCNT_EVT_THRES_0));
        self->handler_match2 = MP_OBJ_NULL;
    }
    if (self->handler_match1 != MP_OBJ_NULL) {
        check_esp_err(pcnt_event_disable(self->unit, PCNT_EVT_THRES_1));
        self->handler_match1 = MP_OBJ_NULL;
    }
    if (self->handler_zero != MP_OBJ_NULL) {
        check_esp_err(pcnt_event_disable(self->unit, PCNT_EVT_ZERO));
        self->handler_zero = MP_OBJ_NULL;
    }
}

STATIC void pcnt_deinit(mp_pcnt_obj_t *self) {
    check_esp_err(pcnt_counter_pause(self->unit));

    check_esp_err(pcnt_event_disable(self->unit, PCNT_EVT_L_LIM));
    check_esp_err(pcnt_event_disable(self->unit, PCNT_EVT_H_LIM));
    pcnt_disable_events(self);

    check_esp_err(pcnt_set_pin(self->unit, PCNT_CHANNEL_0, PCNT_PIN_NOT_USED, PCNT_PIN_NOT_USED));
    check_esp_err(pcnt_set_pin(self->unit, PCNT_CHANNEL_1, PCNT_PIN_NOT_USED, PCNT_PIN_NOT_USED));

    pcnts[self->unit] = NULL;

    m_del_obj(mp_pcnt_obj_t, self); // ???
}

// This called from Ctrl-D soft reboot
void machine_encoder_deinit_all(void) {
    for (int id = 0; id < PCNT_UNIT_MAX; ++id) {
        pcnt_deinit(pcnts[id]);
    }
    if (pcnt_isr_handle != NULL) {
        check_esp_err(pcnt_isr_unregister(pcnt_isr_handle));
        pcnt_isr_handle = NULL;
    }
}

// =================================================================
// Common classes methods
STATIC mp_obj_t machine_PCNT_deinit(mp_obj_t self_obj) {
    pcnt_deinit(MP_OBJ_TO_PTR(self_obj));
    return MP_ROM_NONE;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(machine_PCNT_deinit_obj, machine_PCNT_deinit);

// -----------------------------------------------------------------
STATIC mp_obj_t machine_PCNT_filter(size_t n_args, const mp_obj_t *args) {
    mp_pcnt_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_int_t value = get_filter_value_ns(self->unit);
    if (n_args > 1) {
        set_filter_value(self->unit, ns_to_filter(mp_obj_get_int(args[1])));
    }
    return MP_OBJ_NEW_SMALL_INT(value);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(machine_PCNT_filter_obj, 1, 2, machine_PCNT_filter);

// -----------------------------------------------------------------
STATIC mp_obj_t machine_PCNT_count(size_t n_args, const mp_obj_t *args) {
    mp_pcnt_obj_t *self = MP_OBJ_TO_PTR(args[0]);

    int16_t count;
    check_esp_err(pcnt_get_counter_value(self->unit, &count));
    int64_t counter = self->counter;

    if (n_args > 1) {
        uint64_t new_counter = GET_INT(args[1]);
        if (new_counter) {
            self->counter = new_counter - count;
        } else {
            self->counter = 0;
        }
    }
    return mp_obj_new_int_from_ll(counter + count);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(machine_PCNT_count_obj, 1, 2, machine_PCNT_count);

// -----------------------------------------------------------------
STATIC mp_obj_t machine_PCNT_get_count(mp_obj_t self_obj) {
    mp_pcnt_obj_t *self = MP_OBJ_TO_PTR(self_obj);

    int16_t count;
    pcnt_get_counter_value(self->unit, &count); // no error checking to speed up

    return mp_obj_new_int_from_ll(self->counter + count);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(machine_PCNT_get_count_obj, machine_PCNT_get_count);

// -----------------------------------------------------------------
STATIC mp_obj_t machine_PCNT_scaled(size_t n_args, const mp_obj_t *args) {
    mp_pcnt_obj_t *self = MP_OBJ_TO_PTR(args[0]);

    int64_t counter = self->counter;
    int16_t count;
    check_esp_err(pcnt_get_counter_value(self->unit, &count));
    if (n_args > 1) {
        int64_t new_counter = mp_obj_get_float_to_f(args[1]) / self->scale;
        self->counter = new_counter - count;
    }
    return mp_obj_new_float_from_f(self->scale * (counter + count));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(machine_PCNT_scaled_obj, 1, 2, machine_PCNT_scaled);

// -----------------------------------------------------------------
STATIC mp_obj_t machine_PCNT_pause(mp_obj_t self_obj) {
    mp_pcnt_obj_t *self = MP_OBJ_TO_PTR(self_obj);

    check_esp_err(pcnt_counter_pause(self->unit));

    return MP_ROM_NONE;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(machine_PCNT_pause_obj, machine_PCNT_pause);

// -----------------------------------------------------------------
STATIC mp_obj_t machine_PCNT_resume(mp_obj_t self_obj) {
    mp_pcnt_obj_t *self = MP_OBJ_TO_PTR(self_obj);

    check_esp_err(pcnt_counter_resume(self->unit));

    return MP_ROM_NONE;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(machine_PCNT_resume_obj, machine_PCNT_resume);

// -----------------------------------------------------------------
STATIC mp_obj_t machine_PCNT_id(mp_obj_t self_obj) {
    mp_pcnt_obj_t *self = MP_OBJ_TO_PTR(self_obj);
    return MP_OBJ_NEW_SMALL_INT(self->unit);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(machine_PCNT_id_obj, machine_PCNT_id);

// -----------------------------------------------------------------
STATIC mp_obj_t machine_PCNT_irq(mp_uint_t n_pos_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_handler, ARG_trigger };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_handler, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_trigger, MP_ARG_INT, {.u_int = PCNT_EVT_THRES_0 | PCNT_EVT_THRES_1 | PCNT_EVT_ZERO} },
    };

    mp_pcnt_obj_t *self = pos_args[0];
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_pos_args - 1, pos_args + 1, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    mp_obj_t handler = args[ARG_handler].u_obj;
    mp_uint_t trigger = args[ARG_trigger].u_int;

    if (trigger & ~(PCNT_EVT_THRES_1 | PCNT_EVT_THRES_0 | PCNT_EVT_ZERO)) {
        mp_raise_ValueError(MP_ERROR_TEXT("trigger"));
    }

    if (handler != mp_const_none) {
        if (trigger & PCNT_EVT_THRES_0) {
            self->handler_match2 = handler;
            pcnt_event_enable(self->unit, PCNT_EVT_THRES_0);
        } else {
            pcnt_event_disable(self->unit, PCNT_EVT_THRES_0);
        }
        if (trigger & PCNT_EVT_THRES_1) {
            self->handler_match1 = handler;
            pcnt_event_enable(self->unit, PCNT_EVT_THRES_1);
        } else {
            pcnt_event_disable(self->unit, PCNT_EVT_THRES_1);
        }
        if (trigger & PCNT_EVT_ZERO) {
            self->handler_zero = handler;
            pcnt_event_enable(self->unit, PCNT_EVT_ZERO);
        } else {
            pcnt_event_disable(self->unit, PCNT_EVT_ZERO);
        }
    } else {
        pcnt_disable_events(self);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(machine_PCNT_irq_obj, 1, machine_PCNT_irq);

// =================================================================
// class Counter(object):
STATIC void attach_Counter(mp_pcnt_obj_t *self) {
    // Prepare configuration for the PCNT unit
    pcnt_config_t r_enc_config;
    r_enc_config.pulse_gpio_num = self->aPinNumber; // Pulses
    r_enc_config.ctrl_gpio_num = self->bPinNumber; // Direction

    r_enc_config.unit = self->unit;
    r_enc_config.channel = PCNT_CHANNEL_0;

    // What to do on the positive / negative edge of pulse input?
    if (self->edge & FALLING) {
        r_enc_config.pos_mode = PCNT_COUNT_INC; // Count up on the positive edge
    } else {
        r_enc_config.pos_mode = PCNT_COUNT_DIS; // Keep the counter value on the positive edge
    }
    if (self->edge & RISING) {
        r_enc_config.neg_mode = PCNT_COUNT_INC; // Count up on the negative edge
    } else {
        r_enc_config.neg_mode = PCNT_COUNT_DIS; // Keep the counter value on the negative edge

    }
    // What to do when control input is low or high?
    r_enc_config.lctrl_mode = PCNT_MODE_REVERSE; // Reverse counting direction if low
    r_enc_config.hctrl_mode = PCNT_MODE_KEEP; // Keep the primary counter mode if high

    // Set the maximum and minimum limit values to watch
    r_enc_config.counter_h_lim = INT16_ROLL;
    r_enc_config.counter_l_lim = -INT16_ROLL;

    check_esp_err(pcnt_unit_config(&r_enc_config));
    check_esp_err(pcnt_counter_pause(self->unit));

    // Filter out bounces and noise
    set_filter_value(self->unit, self->filter); // Filter Runt Pulses

    // Enable events on maximum and minimum limit values
    check_esp_err(pcnt_event_enable(self->unit, PCNT_EVT_H_LIM));
    check_esp_err(pcnt_event_enable(self->unit, PCNT_EVT_L_LIM));

    check_esp_err(pcnt_counter_clear(self->unit));
    self->counter = 0;

    pcnts[self->unit] = self;

    // Enable interrupts for PCNT unit
    check_esp_err(pcnt_intr_enable(self->unit));
}

STATIC void mp_machine_Counter_init_helper(mp_pcnt_obj_t *self, size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    check_esp_err(pcnt_counter_pause(self->unit));

    enum { ARG_src, ARG_direction, ARG_edge, ARG_filter, ARG_scale, ARG_match1, ARG_match2 };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_src, MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_direction, MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_edge, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = -1} },
        { MP_QSTR_filter_ns, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = -1} },
        { MP_QSTR_scale, MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_match1, MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_match2, MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    mp_obj_t src = args[ARG_src].u_obj;
    if (src != MP_OBJ_NULL) {
        self->aPinNumber = machine_pin_get_id(src);
    }

    mp_obj_t direction = args[ARG_direction].u_obj;
    if (direction != MP_OBJ_NULL) {
        if (mp_obj_is_type(direction, &mp_type_int)) {
            mp_obj_get_int(direction); // TODO
        } else {
            self->bPinNumber = machine_pin_get_id(direction);
        }
    }
    check_esp_err(pcnt_set_pin(self->unit, PCNT_CHANNEL_0, self->aPinNumber, self->bPinNumber));

    if (args[ARG_edge].u_int != -1) {
        self->edge = args[ARG_edge].u_int;
    }

    if (args[ARG_filter].u_int != -1) {
        self->filter = ns_to_filter(args[ARG_filter].u_int);
        set_filter_value(self->unit, self->filter);
    }

    if (args[ARG_scale].u_obj != MP_OBJ_NULL) {
        if (mp_obj_is_type(args[ARG_scale].u_obj, &mp_type_float)) {
            self->scale = mp_obj_get_float_to_f(args[ARG_scale].u_obj);
        } else if (mp_obj_is_type(args[ARG_scale].u_obj, &mp_type_int)) {
            self->scale = mp_obj_get_int(args[ARG_scale].u_obj);
        } else {
            mp_raise_TypeError(MP_ERROR_TEXT("scale argument muts be a number"));
        }
    }

    if (args[ARG_match1].u_obj != MP_OBJ_NULL) {
        self->match1 = GET_INT(args[ARG_match1].u_obj);
        self->counter_match1 = self->match1 % INT16_ROLL;
        check_esp_err(pcnt_set_event_value(self->unit, PCNT_EVT_THRES_1, (int16_t)self->counter_match1));
        self->counter_match1 = self->match1 - self->counter_match1;
    }
    if (args[ARG_match2].u_obj != MP_OBJ_NULL) {
        self->match2 = GET_INT(args[ARG_match2].u_obj);
        self->counter_match2 = self->match2 % INT16_ROLL;
        check_esp_err(pcnt_set_event_value(self->unit, PCNT_EVT_THRES_0, (int16_t)self->counter_match2));
        self->counter_match2 = self->match2 - self->counter_match2;
    }
    check_esp_err(pcnt_counter_resume(self->unit));
}

STATIC mp_obj_t machine_Counter_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    register_isr_handler();

    mp_arg_check_num(n_args, n_kw, 1, 5, true);

    // create Counter object for the given unit
    mp_pcnt_obj_t *self = m_new_obj(mp_pcnt_obj_t);
    self->base.type = &machine_Counter_type;

    self->unit = mp_obj_get_int(args[0]);
    if ((self->unit < 0) || (self->unit >= PCNT_UNIT_MAX)) {
        mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("id must be from 0 to %d"), PCNT_UNIT_MAX - 1);
    }
    if (pcnts[self->unit] != NULL) {
        mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("already used"));
    }

    self->aPinNumber = PCNT_PIN_NOT_USED;
    if (n_args >= 2) {
        self->aPinNumber = machine_pin_get_id(args[1]);
    }
    if (self->aPinNumber == PCNT_PIN_NOT_USED) {
        mp_raise_TypeError(MP_ERROR_TEXT("'src' argument required, either pos or kw arg are allowed"));
    }

    self->bPinNumber = PCNT_PIN_NOT_USED;
    if (n_args >= 3) {
        self->bPinNumber = machine_pin_get_id(args[2]);
    }
    self->edge = RISING;
    self->scale = 1.0;
    self->filter = 0;

    self->match1 = 0;
    self->match2 = 0;
    self->counter_match1 = 0;
    self->counter_match2 = 0;

    attach_Counter(self);

    // Process the remaining parameters
    mp_map_t kw_args;
    mp_map_init_fixed_table(&kw_args, n_kw, args + n_args);
    //mp_machine_Counter_init_helper(self, n_args - n_args, args + n_args, &kw_args);
    mp_machine_Counter_init_helper(self, n_args - 1, args + 1, &kw_args);

    return MP_OBJ_FROM_PTR(self);
}

STATIC void common_print_pin(const mp_print_t *print, mp_pcnt_obj_t *self) {
    mp_printf(print, "%u, Pin(%u)", self->unit, self->aPinNumber);
    if (self->bPinNumber != PCNT_PIN_NOT_USED) {
        mp_printf(print, ", Pin(%u)", self->bPinNumber);
    }
}

STATIC void common_print_kw(const mp_print_t *print, mp_pcnt_obj_t *self) {
    mp_printf(print, ", filter_ns=%u", get_filter_value_ns(self->unit));
    mp_printf(print, ", scale=%f", self->scale);
    mp_printf(print, ", match1=%ld", self->match1);
    mp_printf(print, ", match2=%ld", self->match2);
}

STATIC void machine_Counter_print(const mp_print_t *print, mp_obj_t self_obj, mp_print_kind_t kind) {
    mp_pcnt_obj_t *self = MP_OBJ_TO_PTR(self_obj);

    mp_printf(print, "Counter(");
    common_print_pin(print, self);
    mp_printf(print, ", edge=%s", self->edge == 1 ? "RISING" : self->edge == 2 ? "FALLING" : "RISING | FALLING");
    common_print_kw(print, self);
    mp_printf(print, ")");
}

STATIC mp_obj_t machine_Counter_init(size_t n_args, const mp_obj_t *args, mp_map_t *kw_args) {
    mp_machine_Counter_init_helper(args[0], n_args - 1, args + 1, kw_args);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_KW(machine_Counter_init_obj, 1, machine_Counter_init);

// Register class methods
#define COMMON_METHODS \
    { MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&machine_PCNT_deinit_obj) }, \
    { MP_ROM_QSTR(MP_QSTR_value), MP_ROM_PTR(&machine_PCNT_count_obj) }, \
    { MP_ROM_QSTR(MP_QSTR_get_value), MP_ROM_PTR(&machine_PCNT_get_count_obj) }, \
    { MP_ROM_QSTR(MP_QSTR_scaled), MP_ROM_PTR(&machine_PCNT_scaled_obj) }, \
    { MP_ROM_QSTR(MP_QSTR_filter_ns), MP_ROM_PTR(&machine_PCNT_filter_obj) }, \
    { MP_ROM_QSTR(MP_QSTR_pause), MP_ROM_PTR(&machine_PCNT_pause_obj) }, \
    { MP_ROM_QSTR(MP_QSTR_resume), MP_ROM_PTR(&machine_PCNT_resume_obj) }, \
    { MP_ROM_QSTR(MP_QSTR_irq), MP_ROM_PTR(&machine_PCNT_irq_obj) }, \
    { MP_ROM_QSTR(MP_QSTR_id), MP_ROM_PTR(&machine_PCNT_id_obj) }

#define COMMON_CONSTANTS \
    { MP_ROM_QSTR(MP_QSTR_IRQ_ZERO), MP_ROM_INT(PCNT_EVT_ZERO) }, \
    { MP_ROM_QSTR(MP_QSTR_IRQ_MATCH1), MP_ROM_INT(PCNT_EVT_THRES_1) }, \
    { MP_ROM_QSTR(MP_QSTR_IRQ_MATCH2), MP_ROM_INT(PCNT_EVT_THRES_0) }

STATIC const mp_rom_map_elem_t machine_Counter_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&machine_Counter_init_obj) },
    COMMON_METHODS,
    COMMON_CONSTANTS,
    { MP_ROM_QSTR(MP_QSTR_RISING), MP_ROM_INT(RISING) },
    { MP_ROM_QSTR(MP_QSTR_FALLING), MP_ROM_INT(FALLING) },
};
STATIC MP_DEFINE_CONST_DICT(machine_Counter_locals_dict, machine_Counter_locals_dict_table);

// Create the class-object itself
const mp_obj_type_t machine_Counter_type = {
    { &mp_type_type },
    .name = MP_QSTR_Counter,
    .make_new = machine_Counter_make_new,
    .print = machine_Counter_print,
    .locals_dict = (mp_obj_dict_t *)&machine_Counter_locals_dict,
};

// =================================================================
// class Encoder(object):
STATIC void attach_Encoder(mp_pcnt_obj_t *self) {
    // Set up encoder PCNT configuration
    pcnt_config_t r_enc_config;
    r_enc_config.pulse_gpio_num = self->aPinNumber; // Rotary Encoder Chan A
    r_enc_config.ctrl_gpio_num = self->bPinNumber; // Rotary Encoder Chan B

    r_enc_config.unit = self->unit;
    r_enc_config.channel = PCNT_CHANNEL_0;

    r_enc_config.pos_mode = (self->x124 != 1) ? PCNT_COUNT_DEC : PCNT_COUNT_DIS; // Count Only On Rising-Edges // X1
    r_enc_config.neg_mode = PCNT_COUNT_INC; // Discard Falling-Edge

    r_enc_config.lctrl_mode = PCNT_MODE_KEEP; // Rising A on HIGH B = CW Step
    r_enc_config.hctrl_mode = PCNT_MODE_REVERSE; // Rising A on LOW B = CCW Step

    // Set the maximum and minimum limit values to watch
    r_enc_config.counter_h_lim = INT16_ROLL;
    r_enc_config.counter_l_lim = -INT16_ROLL;

    check_esp_err(pcnt_unit_config(&r_enc_config));

    if (self->x124 == 4) { // X4
        // set up second channel for full quad
        r_enc_config.pulse_gpio_num = self->bPinNumber; // make prior control into signal
        r_enc_config.ctrl_gpio_num = self->aPinNumber; // and prior signal into control

        r_enc_config.unit = self->unit;
        r_enc_config.channel = PCNT_CHANNEL_1; // channel 1

        r_enc_config.pos_mode = PCNT_COUNT_DEC; // Count Only On Rising-Edges
        r_enc_config.neg_mode = PCNT_COUNT_INC; // Discard Falling-Edge

        r_enc_config.lctrl_mode = PCNT_MODE_REVERSE; // prior high mode is now low
        r_enc_config.hctrl_mode = PCNT_MODE_KEEP; // prior low mode is now high

        r_enc_config.counter_h_lim = INT16_ROLL;
        r_enc_config.counter_l_lim = -INT16_ROLL;

        check_esp_err(pcnt_unit_config(&r_enc_config));
    } else { // make sure channel 1 is not set when not full quad
        r_enc_config.pulse_gpio_num = self->bPinNumber; // make prior control into signal
        r_enc_config.ctrl_gpio_num = self->aPinNumber; // and prior signal into control

        r_enc_config.unit = self->unit;
        r_enc_config.channel = PCNT_CHANNEL_1; // channel 1

        r_enc_config.pos_mode = PCNT_COUNT_DIS; // disabling channel 1
        r_enc_config.neg_mode = PCNT_COUNT_DIS; // disabling channel 1

        r_enc_config.lctrl_mode = PCNT_MODE_DISABLE; // disabling channel 1
        r_enc_config.hctrl_mode = PCNT_MODE_DISABLE; // disabling channel 1

        r_enc_config.counter_h_lim = INT16_ROLL;
        r_enc_config.counter_l_lim = -INT16_ROLL;

        check_esp_err(pcnt_unit_config(&r_enc_config));
    }
    check_esp_err(pcnt_counter_pause(self->unit));

    // Filter out bounces and noise
    set_filter_value(self->unit, self->filter); // Filter Runt Pulses

    // Enable events on maximum and minimum limit values
    check_esp_err(pcnt_event_enable(self->unit, PCNT_EVT_H_LIM));
    check_esp_err(pcnt_event_enable(self->unit, PCNT_EVT_L_LIM));

    check_esp_err(pcnt_counter_clear(self->unit));
    self->counter = 0;

    pcnts[self->unit] = self;

    check_esp_err(pcnt_intr_enable(self->unit));
    check_esp_err(pcnt_counter_resume(self->unit));
}

STATIC void mp_machine_Encoder_init_helper(mp_pcnt_obj_t *self, size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_phase_a, ARG_phase_b, ARG_x124, ARG_filter, ARG_scale, ARG_match1, ARG_match2 };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_phase_a, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_phase_b, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_x124, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = -1} },
        { MP_QSTR_filter_ns, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = -1} },
        { MP_QSTR_scale, MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_match1, MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_match2, MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
    };

    check_esp_err(pcnt_set_pin(self->unit, PCNT_CHANNEL_0, self->aPinNumber, self->bPinNumber));
    check_esp_err(pcnt_set_pin(self->unit, PCNT_CHANNEL_1, self->bPinNumber, self->aPinNumber));

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    if (args[ARG_x124].u_int != -1) {
        if ((args[ARG_x124].u_int == 1) || (args[ARG_x124].u_int == 2) || (args[ARG_x124].u_int == 4)) {
            self->x124 = args[ARG_x124].u_int;
        } else {
            mp_raise_ValueError(MP_ERROR_TEXT(MP_ERROR_TEXT("x124 must be 1, 2, 4")));
        }
    }


    if (args[ARG_filter].u_int != -1) {
        self->filter = ns_to_filter(args[ARG_filter].u_int);
        set_filter_value(self->unit, self->filter);
    }

    if (args[ARG_scale].u_obj != MP_OBJ_NULL) {
        if (mp_obj_is_type(args[ARG_scale].u_obj, &mp_type_float)) {
            self->scale = mp_obj_get_float_to_f(args[ARG_scale].u_obj);
        } else if (mp_obj_is_type(args[ARG_scale].u_obj, &mp_type_float)) {
            self->scale = mp_obj_get_int(args[ARG_scale].u_obj);
        } else {
            mp_raise_TypeError(MP_ERROR_TEXT("scale argument muts be a number"));
        }
    }
}

STATIC mp_obj_t machine_Encoder_make_new(const mp_obj_type_t *t_ype, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    register_isr_handler();

    mp_arg_check_num(n_args, n_kw, 1, 5, true);

    // create Encoder object for the given unit
    mp_pcnt_obj_t *self = m_new_obj(mp_pcnt_obj_t);
    self->base.type = &machine_Encoder_type;

    self->unit = mp_obj_get_int(args[0]);
    if ((self->unit < 0) || (self->unit >= PCNT_UNIT_MAX)) {
        mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("id must be from 0 to %d"), PCNT_UNIT_MAX - 1);
    }
    if (pcnts[self->unit] != NULL) {
        mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("already used"));
    }

    self->x124 = 4;
    self->scale = 1.0;
    self->filter = 0;

    self->match1 = 0;
    self->match2 = 0;
    self->counter_match1 = 0;
    self->counter_match2 = 0;

    self->aPinNumber = PCNT_PIN_NOT_USED;
    self->bPinNumber = PCNT_PIN_NOT_USED;
    if (n_args >= 2) {
        self->aPinNumber = machine_pin_get_id(args[1]);
    }
    if (n_args >= 3) {
        self->bPinNumber = machine_pin_get_id(args[2]);
    }
    if (self->aPinNumber == PCNT_PIN_NOT_USED) {
        mp_raise_TypeError(MP_ERROR_TEXT("'phase_a' argument required, either pos or kw arg are allowed"));
    }
    if (self->bPinNumber == PCNT_PIN_NOT_USED) {
        mp_raise_TypeError(MP_ERROR_TEXT("'phase_b' argument required, either pos or kw arg are allowed"));
    }

    // Process the remaining parameters
    mp_map_t kw_args;
    mp_map_init_fixed_table(&kw_args, n_kw, args + n_args);
    // mp_machine_Encoder_init_helper(self, n_args - n_args, args + n_args, &kw_args);
    mp_machine_Encoder_init_helper(self, n_args - 1, args + 1, &kw_args);

    attach_Encoder(self);

    return MP_OBJ_FROM_PTR(self);
}

STATIC mp_obj_t machine_Encoder_init(size_t n_args, const mp_obj_t *args, mp_map_t *kw_args) {
    mp_machine_Encoder_init_helper(args[0], n_args - 1, args + 1, kw_args);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_KW(machine_Encoder_init_obj, 1, machine_Encoder_init);

STATIC void machine_Encoder_print(const mp_print_t *print, mp_obj_t self_obj, mp_print_kind_t kind) {
    mp_pcnt_obj_t *self = MP_OBJ_TO_PTR(self_obj);

    mp_printf(print, "Encoder(");
    common_print_pin(print, self);
    mp_printf(print, ", x124=%d", self->x124);
    common_print_kw(print, self);
    mp_printf(print, ")");
}

// Register class methods
STATIC const mp_rom_map_elem_t machine_Encoder_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&machine_Encoder_init_obj) },
    COMMON_METHODS,
    COMMON_CONSTANTS
};
STATIC MP_DEFINE_CONST_DICT(machine_Encoder_locals_dict, machine_Encoder_locals_dict_table);

// Create the class-object itself
const mp_obj_type_t machine_Encoder_type = {
    { &mp_type_type },
    .name = MP_QSTR_Encoder,
    .print = machine_Encoder_print,
    .make_new = machine_Encoder_make_new,
    .locals_dict = (mp_obj_dict_t *)&machine_Encoder_locals_dict,
};

#endif // MICROPY_PY_MACHINE_PCNT
