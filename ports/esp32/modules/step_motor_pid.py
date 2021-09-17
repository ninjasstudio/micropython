#from micropython import const
from gc import collect
collect()
from machine import Pin, PWM  # Timer
collect()
from utime import sleep_us, ticks_us, ticks_diff
collect()

from esp32_ import *
collect()

ANGLE_PRECISION = 0.05
STEP_PULSE_us = 5  # 10  # длительность импульса в мкс


class StepMotorPid():
    def __init__(self, name, _pin_step, _pin_dir, in_angle, pid, max_limit=180, min_limit=-180):  # steps_per_angle, step_frequency,
        """ Constructor """
        self.name = name

        #self.set_frequency(step_frequency)

        self.inverse_dir = False
        self.pin_dir = Pin(_pin_dir, Pin.OUT, value=0)
        self.pin_step = Pin(_pin_step, Pin.OUT, value=0)

        self.in_angle = in_angle  # function
        self.pid = pid

        self.offset = 0  # смещение(неточность установки) датчика в градусах

        self.is_pulses = 0
        # 0 - выключены импульсы, координаты актуальны, возможно перемещение одиночными шагами в главном цикле
        # 1 - включены импульсы, перемещаемся в фоновом режиме, координаты рассчитываются на лету
        # -1 - выключены импульсы, координаты еще не пересчитаны в актуальные

        self.is_position = 0
        # 0 - координаты актуальны после включения или после пересчета
        # 1 - координаты не актуальны после наезда на "плюсовый" конечный выключатель
        # -1 - координаты не актуальны после наезда на "минусовый" конечный выключатель

        self.pwm = None
        self._angle_target = 0

        self.direction = 0

        self.us_prev_step = ticks_us()
        self._last_time = ticks_us()

        self.max_limit = max_limit  # физические механические ограничения конструкции
        self.min_limit = min_limit

        self._on_correct_handler = None  # call back function for correct external angles
        self.angle_precision = ANGLE_PRECISION

    # -----------------------------------------------------------------------
    def __del__(self):
        """ Destructor """  # Special method __del__ not implemented for user-defined classes in MicroPython !!!
        #print("Destructor", self)
        self.deinit()

    #@micropython.native
    def deinit(self):
        try:
            self.stop_pulses(1)
        except:
            pass

    @micropython.native
    def start_pulses(self):
        self.pid.setpoint = self._angle_target
        now = ticks_us()
        dt = ticks_diff(now, self._last_time) / 1000000
        if dt <= 0.0:
            dt = 1e-16
        self._last_time = now                
        self.step_frequency = self.pid(self.angle_now(), dt)
        self.dir(self.step_frequency)
        self.step_frequency = abs(self.step_frequency)
        #         if self.name[0] == 'A':
        #             print(self.name + ".start_pulses()", self.is_pulses, self.step_frequency, 'Hz')

        if self.is_pulses == 0:
            self.is_pulses = 1
            self.pwm = PWM(self.pin_step, freq=self.step_frequency, duty=512)  # 2 # 1024 == 100% # 512 == 50%
        else:
            self.pwm.freq(self.step_frequency)

    @micropython.native
    def stop_pulses(self, n=-1):
        if self.pwm is not None:
            #if n:
            #    print('self.pwm.deinit() from stop_pulses(', n, ')')  #print() запрещено в прерываниии
            #    pass
            try:
                self.pwm.deinit()  # 1
            except:
                pass
            self.pwm = None  # 2
            self.is_pulses = 0  # 3

    @micropython.native
    def set_angle_now(self, to_angle):
        #self.angle(to_angle)
        pass

    @micropython.native
    def is_ready(self) -> bool:
        #delta = self._angle_target - self.angle_now()
        #print('is_ready(): delta', delta)
        if self.direction > 0:
            #if delta >= self.angle_precision:
            if self.angle_now() >= self.max_limit:
                self.stop_pulses(2)
                return True
            if self.angle_now() >= (self._angle_target - self.angle_precision):
                self.stop_pulses(3)
                return True
        elif self.direction < 0:
            #if delta <= self.angle_precision:
            if self.angle_now() <= self.min_limit:
                self.stop_pulses(4)
                return True
            if self.angle_now() <= (self._angle_target + self.angle_precision):
                self.stop_pulses(5)
                return True
        else:
            return abs(self._angle_target - self.angle_now()) <= (self.angle_precision * 2)
        return False

    # -----------------------------------------------------------------------
    @micropython.native
    def dir(self, val=0):
        """ Set rotate direction """
        _d = self.direction
        if val > 0:
            self.direction = 1
            self.pin_dir.value((1 ^ self.inverse_dir) & 1)
        elif val < 0:
            self.direction = -1
            self.pin_dir.value((0 ^ self.inverse_dir) & 1)
        else:
            self.direction = 0
        if _d != self.direction:
            self.pid._integral = 0  # сброс интегральной составляющей при смене направления

    @micropython.native
    def set0(self):
        self.offset = self.in_angle()
        self.angle(0)
        #print('set0():self.offset, self._angle_target, self.angle_now()', self.offset, self._angle_target, self.angle_now())

    @micropython.native
    def angle_now(self):
        #print('self.in_angle(), self.offset', self.in_angle(), self.offset)
        #return to180(self.in_angle() - self.offset)
        return self.in_angle() - self.offset

    @micropython.native
    def angle_target(self):
        return self._angle_target

    @micropython.native
    def angle(self, to_angle):
        """ Set the target position that will be executed in the main loop """
        if to_angle > self.max_limit:
            to_angle = self.max_limit
        elif to_angle < self.min_limit:
            to_angle = self.min_limit
        self._angle_target = to_angle

    # -----------------------------------------------------------------------
    @micropython.native
    def on_correct(self, handler):
        """ Set correction handler """
        self._on_correct_handler = handler

    @micropython.native
    def correct_angles(self, delta_angle):
        if self._on_correct_handler:
            self._on_correct_handler(delta_angle)

    # -----------------------------------------------------------------------
    @micropython.native
    def single_step(self):
        """ Execute one step """
        if self.direction != 0:
            self.pin_step.on()
            sleep_us(STEP_PULSE_us)
            self.pin_step.off()

    @micropython.native
    def move_single_step(self):
        """ Check the step period and Execute one step """
        t = ticks_us()
        diff = ticks_diff(t, self.us_prev_step)
        if (diff >= self.us_step_period) or (diff < 0):
            self.single_step()
            self.us_prev_step = t
        #elif diff < 0:
        #    #self.us_prev_step = ticks_us()
        #    raise

    @micropython.native
    def go_steps(self, steps):
        "Run steps from current position"
        #steps = int(steps)
        while (steps > 0):
            self.move_single_step()
            steps -= 1

    # -----------------------------------------------------------------------
    @micropython.native
    def go(self):
        """ Perform one step each time in the main loop to achieve the target position """
        delta = self._angle_target - self.angle_now()
        #print('delta', delta, 'target', self._angle_target, 'angle_now', self.angle_now())
        if delta > (self.angle_precision * 2):
            self.dir(1)
            if delta > self.angle_precision:
                self.start_pulses()
            else:
                self.stop_pulses(6)
                self.single_step()
        elif delta < (-self.angle_precision * 2):
            self.dir(-1)
            if delta < -self.angle_precision:
                self.start_pulses()
            else:
                self.stop_pulses(7)
                self.single_step()
        else:
            self.stop_pulses(8)

    @micropython.native
    def stop_move(self):
        self.stop_pulses(9)
        self._angle_target = self.angle_now()
