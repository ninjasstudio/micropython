/*
 * This file is part of the Micro Python project, http://micropython.org/
 *
 * The MIT License (MIT)
 *
  * Copyright (c) 2018 B. Boser (https://github.com/loboris)
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

#include <stdio.h>
#include "driver/pcnt.h"
#include "esp_err.h"

#include "py/nlr.h"
#include "py/runtime.h"
#include "modmachine.h"
#include "mphalport.h"

typedef struct _mod_quad_QUAD_obj_t {
    mp_obj_base_t base;
    pcnt_config_t unit_a;
    pcnt_config_t unit_b;
} mod_quad_QUAD_obj_t;

//-------------------------------------------------------------------------------------------------------------
STATIC mp_obj_t mod_quad_QUAD_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 2, 3, true);
    int unit = mp_obj_get_int(args[0]);
    gpio_num_t pin_a = machine_pin_get_gpio(args[1]);
    gpio_num_t pin_b = PCNT_PIN_NOT_USED;
    if (n_args == 3)
        pin_b = machine_pin_get_gpio(args[2]);

    if (unit < 0 || unit > PCNT_UNIT_MAX)
        nlr_raise(mp_obj_new_exception_msg_varg(&mp_type_ValueError, "Bad timer number %d", unit));

    // create dec object for the given unit
    mp_obj_QUAD_t *self = m_new_obj(mod_quad_QUAD_obj_t);
    self->base.type = &mod_quad_QUAD_type;

    // configure timer channel 0
    self->unit_a.channel = PCNT_CHANNEL_0;
    self->unit_a.pulse_gpio_num = pin_a;    // reverse from channel 1
    self->unit_a.ctrl_gpio_num = pin_b;
    self->unit_a.unit = unit;
    self->unit_a.pos_mode = PCNT_COUNT_DEC;
    self->unit_a.neg_mode = PCNT_COUNT_INC;
    self->unit_a.lctrl_mode = PCNT_MODE_KEEP;
    self->unit_a.hctrl_mode = PCNT_MODE_REVERSE;
    self->unit_a.counter_h_lim =  INT16_MAX;    // don't care if interrupt is not used?
    self->unit_a.counter_l_lim = -INT16_MAX;

    // configure timer channel 1
    self->unit_b.channel = PCNT_CHANNEL_1;
    self->unit_b.pulse_gpio_num = pin_b;    // reverse from channel 0
    self->unit_b.ctrl_gpio_num = pin_a;
    self->unit_b.unit = unit;
    self->unit_b.pos_mode = PCNT_COUNT_DEC;
    self->unit_b.neg_mode = PCNT_COUNT_INC;
    self->unit_b.lctrl_mode = PCNT_MODE_REVERSE;
    self->unit_b.hctrl_mode = PCNT_MODE_KEEP;
    self->unit_b.counter_h_lim =  INT16_MAX;    // don't care if interrupt is not used?
    self->unit_b.counter_l_lim = -INT16_MAX;

    if (n_args == 2) {
        // not sure if all this is required, but I've played long enough
        self->unit_a.pos_mode = PCNT_COUNT_INC;
        self->unit_a.hctrl_mode = PCNT_MODE_KEEP;

        self->unit_b.channel = PCNT_CHANNEL_1;
        self->unit_b.ctrl_gpio_num = pin_b;
        self->unit_b.pos_mode = PCNT_COUNT_DIS;
        self->unit_b.neg_mode = PCNT_COUNT_DIS;
        self->unit_b.hctrl_mode = PCNT_MODE_KEEP;
    }

    pcnt_unit_config(&(self->unit_a));
    pcnt_unit_config(&(self->unit_b));
    pcnt_filter_disable(unit);

    // init / start the counter
    pcnt_counter_pause(unit);
    pcnt_counter_clear(unit);
    pcnt_counter_resume(unit);

    // not sure what this is for or if it's needed
    mp_map_t kw_args;
    mp_map_init_fixed_table(&kw_args, n_kw, args + n_args);

    return MP_OBJ_FROM_PTR(self);
}

//------------------------------------------------------------------------------------------
STATIC void mod_quad_QUAD_print(const mp_print_t *print, mp_obj_t self_obj, mp_print_kind_t kind)
{
    mp_obj_QUAD_t *self = MP_OBJ_TO_PTR(self_obj);
    mp_printf(print, "QUAD(%u, Pin(%u)", self->unit_a.unit, self->unit_a.pulse_gpio_num);
    if (self->unit_a.ctrl_gpio_num != PCNT_PIN_NOT_USED) mp_printf(print, ", Pin(%u)", self->unit_a.ctrl_gpio_num);
    mp_printf(print, ")");
}

//-----------------------------------------------------------------
// def QUAD.clear(self)
STATIC mp_obj_t mod_quad_QUAD_clear(mp_obj_t self_obj) {
    mp_obj_QUAD_t *self = MP_OBJ_TO_PTR(self_obj);
    pcnt_counter_clear(self->unit_a.unit);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_quad_QUAD_clear_obj, mod_quad_QUAD_clear);

//-----------------------------------------------------------------
// def QUAD.count(self) -> int
STATIC mp_obj_t mod_quad_QUAD_count(mp_obj_t self_obj) {
    mp_obj_QUAD_t *self = MP_OBJ_TO_PTR(self_obj);

    int16_t count;
    pcnt_get_counter_value(self->unit_a.unit, &count);
    return MP_OBJ_NEW_SMALL_INT(count);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_quad_QUAD_count_obj, mod_quad_QUAD_count);

//-----------------------------------------------------------------
// def QUAD.count_and_clear(self)
STATIC mp_obj_t mod_quad_QUAD_count_and_clear(mp_obj_t self_obj) {
    mp_obj_QUAD_t *self = MP_OBJ_TO_PTR(self_obj);

    int16_t count;
    pcnt_get_counter_value(self->unit_a.unit, &count);
    pcnt_counter_clear(self->unit_a.unit);
    return MP_OBJ_NEW_SMALL_INT(count);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_quad_QUAD_count_and_clear_obj, mod_quad_QUAD_count_and_clear);

//-----------------------------------------------------------------
// def QUAD.pause(self)
STATIC mp_obj_t mod_quad_QUAD_pause(mp_obj_t self_obj) {
    mp_obj_QUAD_t *self = MP_OBJ_TO_PTR(self_obj);
    pcnt_counter_pause(self->unit_a.unit);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_quad_QUAD_pause_obj, mod_quad_QUAD_pause);

//-----------------------------------------------------------------
// def QUAD.resume(self)
STATIC mp_obj_t mod_quad_QUAD_resume(mp_obj_t self_obj) {
    mp_obj_QUAD_t *self = MP_OBJ_TO_PTR(self_obj);
    pcnt_counter_resume(self->unit_a.unit);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_quad_QUAD_resume_obj, mod_quad_QUAD_resume);

//==============================================================
STATIC const mp_rom_map_elem_t mod_quad_QUAD_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_mod_quad_QUAD_attach_single_edge), MP_ROM_PTR(&mod_quad_QUAD_attach_single_edge_obj) },
    { MP_ROM_QSTR(MP_QSTR_mod_quad_QUAD_attach_half_quad), MP_ROM_PTR(&mod_quad_QUAD_attach_half_quad_obj) },
    { MP_ROM_QSTR(MP_QSTR_mod_quad_QUAD_attach_full_quad), MP_ROM_PTR(&mod_quad_QUAD_attach_full_quad_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_count), MP_ROM_PTR(&mod_quad_QUAD_set_count_obj) },
    { MP_ROM_QSTR(MP_QSTR_count_raw), MP_ROM_PTR(&mod_quad_QUAD_count_raw_obj) },
    { MP_ROM_QSTR(MP_QSTR_count), MP_ROM_PTR(&mod_quad_QUAD_count_obj) },
    { MP_ROM_QSTR(MP_QSTR_count_and_clear), MP_ROM_PTR(&mod_quad_QUAD_count_and_clear_obj) },
    { MP_ROM_QSTR(MP_QSTR_clear), MP_ROM_PTR(&mod_quad_QUAD_clear_obj) },
    { MP_ROM_QSTR(MP_QSTR_pause), MP_ROM_PTR(&mod_quad_QUAD_pause_obj) },
    { MP_ROM_QSTR(MP_QSTR_resume), MP_ROM_PTR(&mod_quad_QUAD_resume_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_filter), MP_ROM_PTR(&mod_quad_QUAD_set_filter_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_quad_QUAD_locals_dict, mod_quad_QUAD_locals_dict_table);

//======================================
STATIC const mp_obj_type_t mod_quad_QUAD_type = {
    { &mp_type_type },
    .name = MP_QSTR_QUAD,
    .print = mod_quad_QUAD_print,
    .make_new = mod_quad_QUAD_make_new,
    .locals_dict = (mp_obj_dict_t*)&mod_quad_QUAD_locals_dict,
};
