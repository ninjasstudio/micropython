# rotator.py

from time import ticks_ms, ticks_diff, sleep_ms
from machine import Timer
from _thread import start_new_thread


class Rotator():
    def __init__(self, azim, elev, sensors, rotator_period=100):  # rotator_period in ms
        self.azim = azim
        self.elev = elev
        self.sensors = sensors

        self.manual = False
        self.dt_handle_sensors = 0
        self.dt_handle_motors = 0

        self.rotator_period = rotator_period

        self.is_handle_motors = False

        self.timer = None

        self.is_thread = 0
        self.thread_ms = ticks_ms()

    def __repr__(self):
        return "Rotator(azim={}, elev={}, sensors={}, rotator_period={})".format(self.azim, self.elev, self.sensors, self.rotator_period)

    def prn(self):
        #print('yaw:{:5.1f} pitch:{:5.1f} slef.azim.angle:{:5.1f} elev.angle:{:5.1f}'.format(self.sensors.yaw, self.sensors.pitch, self.azim.angle, self.elev.angle), self.azim.freq(), self.elev.freq() )#, end=' \r')
        print('yaw', self.sensors.yaw, 'pitch', self.sensors.pitch, 'targets', self.azim.angle_target, self.elev.angle_target, 'freqs', self.azim.freq(), self.elev.freq(), 'dt', self.dt_handle_sensors, self.dt_handle_motors)  #, end=' \r')
        #print(elev_pid.components, elev_pid._last_input, elev_pid._last_output, elev_pid._last_error)

    def deinit(self):
        self.stop_thread()
        self.stop_timer()

    def work_on_timer(self):
        if self.is_thread <= 0:
            if self.timer is None:
                self.timer = Timer(-1)
                self.timer.init(period=self.rotator_period, mode=Timer.PERIODIC, callback=self.__handle_motors)
                # self.timer.init(period=self.rotator_period, mode=Timer.ONE_SHOT, callback=self.__timer_motors)

    def stop_timer(self):
        if self.timer is not None:
            try:
                self.timer.deinit()
            except:
                pass
            self.timer = None

    @micropython.native
    def handle_sensors(self):
        t = ticks_ms()

        self.sensors.handle()

        tmp = ticks_diff(ticks_ms(), t)
        if tmp > 0:
            self.dt_handle_sensors = tmp

    @micropython.native
    def handle_motors(self):
        if self.is_handle_motors:
            return
        while not self.is_handle_motors:
            self.is_handle_motors = True

        t = ticks_ms()

        self.handle_sensors()

        if not self.manual:
            if not self.azim.is_ready():
                self.azim.go()
            if not self.elev.is_ready():
                self.elev.go()

        tmp = ticks_diff(ticks_ms(), t)
        if tmp > 0:
            self.dt_handle_motors = tmp

        while self.is_handle_motors:
            self.is_handle_motors = False

    @micropython.native
    def __handle_motors(self, timer):
        self.handle_motors()

    @micropython.native
    def __timer_motors(self, timer):
        self.handle_motors()
        if self.rotator_period > self.dt_handle_motors:
            t = self.rotator_period - self.dt_handle_motors
        else:
            t = self.rotator_period
        self.timer.init(period=t, mode=Timer.ONE_SHOT, callback=self.__timer_motors)

    @micropython.native
    def __thread_motors(self):
        while self.is_thread > 0:
            if ticks_diff(t := ticks_ms(), self.thread_ms) >= self.rotator_period:
                self.thread_ms = t
                self.handle_motors()
            sleep_ms(10)
        self.is_thread = -1
        #print('self.is_thread', self.is_thread)

    def work_on_thread(self):
        if self.timer is None:
            if self.is_thread <= 0:
                self.is_thread = 1
                #print('self.is_thread', self.is_thread)
                start_new_thread(self.__thread_motors, ())

    def stop_thread(self):
        if self.is_thread > 0:
            self.is_thread = 0
            #print('self.is_thread', self.is_thread)
            while self.is_thread == 0:
                sleep_ms(20)
            #print('stop_thread(), self.is_thread', self.is_thread)

    @property
    def ready(self):
        return self.azim.is_ready(), self.elev.is_ready()

    @micropython.native
    def is_ready(self):
        return self.azim.is_ready() and self.elev.is_ready()

    def wait(self):
        while not self.is_ready():
            sleep_ms(10)

    @property
    @micropython.native
    def angles(self):
        return self.azim.angle, self.elev.angle

    @property
    @micropython.native
    def targets(self):
        return self.azim.angle_target, self.elev.angle_target

    @targets.setter
    @micropython.native
    def targets(self, angles):
        self.azim.target, self.elev.target = angles

    @property
    def rpm(self):
        return self.azim.rpm, self.elev.rpm

    @rpm.setter
    def rpm(self, rpm):
        self.azim.rpm, self.elev.rpm = rpm

    @property
    def rps(self):
        return self.azim.rps, self.elev.rps

    @rps.setter
    def rps(self, rps):
        self.azim.rps, self.elev.rps = rps
