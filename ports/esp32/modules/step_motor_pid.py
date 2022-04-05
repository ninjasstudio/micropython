from gc import collect
from machine import Pin, PWM
from utime import sleep_us, ticks_us, ticks_diff

from esp32_ import *
from step_motor_base import StepMotorBase

collect()

ANGLE_PRECISION = 0.1


class StepMotorPid(StepMotorBase):
    def __init__(self, name, pin_step, pin_dir, steps_per_rev, angle_now, pid, max_limit=180, min_limit=-180):
        """ Constructor """
        super().__init__(name, pin_step, pin_dir, steps_per_rev, max_limit=max_limit, min_limit=min_limit)

        self.angle_now = angle_now  # function
        self.pid = pid

        self.is_pulses = 0
        # 0 - выключены импульсы, координаты актуальны, возможно перемещение одиночными шагами в главном цикле
        # 1 - включены импульсы, перемещаемся в фоновом режиме, координаты рассчитываются на лету

        self.pwm = None
        self.step_frequency = 0
        self.us_step_period = 0  # round(1_000_000 / step_frequency)

        self.angle_target = 0

        self._last_time = ticks_us()

        self.angle_precision = ANGLE_PRECISION

    def __repr__(self):
        return 'StepMotorPid({}, angle_now={}, pid={}, max_limit={}, min_limit={})'.format(super().__repr__(), self.angle_now(), self.pid, self.max_limit, self.min_limit)

    # -----------------------------------------------------------------------
    def deinit(self):
        try:
            self.pwm.deinit()
        except:
            pass

    @property
    def rps(self):
        if 0 and self.is_pulses:
            return self.f_to_rps(self.freq())
        else:
            return self.f_to_rps(self.pid.output_limits[1])

    @rps.setter
    def rps(self, rps):
        max_step_frequency = round(self.rps_to_f(rps))
        self.pid.output_limits = -max_step_frequency, max_step_frequency

    @property
    def rpm(self):
        if 0 and self.is_pulses:
            return self.f_to_rpm(self.freq())
        else:
            return self.f_to_rpm(self.pid.output_limits[1])

    @rpm.setter
    def rpm(self, rpm):
        max_step_frequency = round(self.rpm_to_f(rpm))
        self.pid.output_limits = -max_step_frequency, max_step_frequency

    def start_pulses(self):
        self.pid.setpoint = self.angle_target
        now = ticks_us()
        dt = ticks_diff(now, self._last_time)
        self._last_time = now
        if dt <= 0:
            dt = 1e-16
        else:
            dt /= 1_000_000
        step_frequency = int(round(self.pid(self.angle_now(), dt)))
        self.dir(step_frequency)
        self.step_frequency = abs(step_frequency)

        if self.is_pulses == 0:
            self.pwm = PWM(Pin(self.pin_step), freq=self.step_frequency) # , duty_u16=32768)  # 50%
            self.is_pulses = 1
        else:
            self.pwm.freq(self.step_frequency)
            # self.pwm.duty_u16(32768)
            self.pwm.duty(512)

    def stop_pulses(self):
        if self.pwm is not None:
            try:
                self.pwm.deinit()  # 1
            except:
                pass
            self.pwm = None  # 2
        self.is_pulses = 0  # 3

    def is_ready(self) -> bool:
        if self.direction > 0:
            if self.angle_now() >= self.max_limit - self.angle_precision:
                self.stop_pulses()
        elif self.direction < 0:
            if self.angle_now() <= self.min_limit + self.angle_precision:
                self.stop_pulses()

        if abs(self.angle_target - self.angle_now()) <= self.angle_precision:
            self.stop_pulses()
            return True
        return False

    # -----------------------------------------------------------------------
    def dir(self, val):
        """ Set rotate direction """
        _d = self.direction
        super().dir(val)
        if _d != self.direction:
            self.pid._integral = 0  # сброс интегральной составляющей при смене направления

    def set0(self):
        self.offset = self.angle_now()
        self.target = 0

    @property
    def angle(self):
        return self.angle_now()

    @property
    def target(self):
        return self.angle_target

    @target.setter
    def target(self, angle_target):
        if angle_target > self.max_limit:
            self.angle_target = self.max_limit
        elif angle_target < self.min_limit:
            self.angle_target = self.min_limit
        else:    
            self.angle_target = angle_target

    # -----------------------------------------------------------------------
    def go(self):
        """ Perform one step each time in the main loop to achieve the target position """
        delta = self.angle_target - self.angle_now()
        if delta > self.angle_precision:
            self.start_pulses()
        elif delta < -self.angle_precision:
            self.start_pulses()
        else:
            self.stop_pulses()

    def stop(self):
        self.stop_pulses()
        self.angle_target = self.angle_now()
