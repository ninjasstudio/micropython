# step_motor_base.py

from utime import sleep_us, ticks_us, ticks_diff
from machine import Pin

PI2 = 3.14159265358979 * 2

STEP_PULSE_us = 10  # длительность импульса в мкс


class StepBase():
    def __init__(self, steps_per_rev):
        self.steps_per_rev = steps_per_rev

    def angle_to_steps(self, angle):
        return round(self.steps_per_rev * angle / 360)

    def steps_to_angle(self, steps):
        return steps * PI2 / self.steps_per_rev

    def radian_to_steps(self, angle):
        return round(self.steps_per_rev * angle / PI2)

    def steps_to_radian(self, steps):
        return steps * 360 / self.steps_per_rev

    def f_to_rps(self, f):  # rotates per second  # об/с
        return f / self.steps_per_rev

    def f_to_rpm(self, f):  # rotates per minute  # об/мин
        return self.f_to_rps(f) * 60

    def rps_to_f(self, rps):
        return rps * self.steps_per_rev

    def rpm_to_f(self, rpm):
        return rpm * self.steps_per_rev / 60


#     def us_to_steps(self, now_us, start_us):
#         return round(ticks_diff(now_us, start_us) / self.us_step_period)


class StepMotorBase(StepBase):
    def __init__(self, name, pin_step, pin_dir, steps_per_rev, max_limit=180, min_limit=-180):
        super().__init__(steps_per_rev)

        self.name = name
        self.steps_per_rev = steps_per_rev

        self.pin_step = pin_step
        self.pin_dir = Pin(pin_dir, Pin.OUT, value=1)
        self.reverse_direction = 0  # развернуть направление вращения мотора

        self.direction = 0  # (-1, 0, 1) текущее направление вращения, устанавливается в dir()

        self.max_limit = max_limit  # физические механические ограничения конструкции
        self.min_limit = min_limit

        self.us_prev_step = ticks_us()

        self._on_correct_handler = None  # call back function for correct external angles

    def __repr__(self):
        return "StepMotorBase('{}', step={}, dir={}, steps_per_rev={})".format(self.name, self.pin_step, self.pin_dir, self.steps_per_rev)

    def freq(self):
        if self.pwm is None:
            return 0
        else:
            try:
                return self.pwm.freq()
            except:
                return 0

    @property
    def rps(self):
        return self.f_to_rps(self.freq())

    @property
    def rpm(self):
        return self.f_to_rpm(self.freq())

    # -----------------------------------------------------------------------
    def dir(self, val):
        """ Set rotate direction """
        if val > 0:
            self.direction = 1
            self.pin_dir.value((1 ^ self.reverse_direction) & 1)
        elif val < 0:
            self.direction = -1
            self.pin_dir.value((0 ^ self.reverse_direction) & 1)
        else:
            self.direction = 0
        #print(""" Set rotate direction """, self.pin_dir, self.reverse_direction, self.direction, val)

    # -----------------------------------------------------------------------
    def single_step(self):
        """ Execute one step """
        if self.direction != 0:
            pin_step = Pin(self.pin_step, Pin.OUT, value=0)
            pin_step.value(0)
            sleep_us(STEP_PULSE_us)
            pin_step.value(1)
            #print(""" Execute one step """, pin_step, self.direction)

    def move_single_step(self):
        """ Check the step period and Execute one step """
        t = ticks_us()
        diff = ticks_diff(t, self.us_prev_step)
        if (diff >= self.us_step_period) or (diff < 0):
            self.single_step()
            self.us_prev_step = t
            return True
        return False

    def go_steps(self, steps):
        "Run steps from current position"
        self.dir(steps)
        steps = abs(steps)
        while (steps > 0):
            if self.move_single_step():
                steps -= 1

    # -----------------------------------------------------------------------
    def on_correct(self, handler):
        """ Set correction handler """
        self._on_correct_handler = handler

    def correct_angles(self, delta_angle):
        if self._on_correct_handler:
            self._on_correct_handler(delta_angle)
