#pragma once

#include <driver/gpio.h>
#include "driver/pcnt.h"

#define MAX_ESP32_ENCODERS (PCNT_UNIT_MAX)
#define _INT16_MAX (32766)
#define _INT16_MIN (-32766)

enum encType {
    SINGLE,
    HALF,
    FULL
};

enum puType {
    NONE,
    DOWN,
    UP
};

#pragma once
