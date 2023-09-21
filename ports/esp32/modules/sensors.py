# sensors.py

from utime import ticks_us, ticks_diff

from avg_filter import *
import mahony


class Sensors():
    def __init__(self, mrps, imu):
        self.imu = imu

        self.offset_roll = 0
        self.offset_pitch = 0
        self.offset_yaw = 0

        self.roll = 0  # None  # discrete
        self.pitch = 0  # None  # discrete
        self.temperature = 0  # None

        self.mrps = mrps
        self.yaw = mrps.readAngleCom()  # required before mrps.angle
        self.yaw = self.read_yaw()

        self._t_us_IMU = ticks_us()  # us !!!

    def __repr__(self):
        return "Sensors(mrps={}, imu={})".format(self.mrps, self.imu)

    def info(self):
        return f"Sensors: roll={self.roll}, pitch={self.pitch}, yaw={self.yaw}, temperature={self.temperature}"

    #@micropython.native
    def handle(self):
        #print('Sensors().handle()')
        try:
            _t = ticks_us()  # us !!!
            a = self.imu.acceleration
            g = self.imu.gyro
            mahony.MahonyAHRSupdateIMU(
                g[1],
                -g[0],
                g[2],  # датчик горизонтально # сова3 провода идут влево внутрь
                a[1],
                -a[0],
                a[2],
                ticks_diff(_t, self._t_us_IMU)
                )
            self._t_us_IMU = _t

            self.pitch = round(-mahony.Mahony_pitch() - self.offset_pitch, 2)  # discrete
            self.roll = round(mahony.Mahony_roll() + self.offset_roll, 2)  # discrete
            self.temperature = round(self.imu.temperature,1)
        except SyntaxError:
            self.pitch = None
            self.temperature = None
#             self.pitch = 0
#             self.temperature = 0

        try:
            self.yaw = self.read_yaw()  # discrete
        except SyntaxError:
            self.yaw = None
#             self.yaw = 0

    #@micropython.native
    def read_yaw(self):  # instant
        return round(self.mrps.readAngleComInfinity() - self.offset_yaw, 2)

    #@micropython.native
    def get_pitch(self):  # discrete
        return self.pitch

    #@micropython.native
    def get_roll(self):  # discrete
        return self.roll

    #@micropython.native
    def get_yaw(self):  # discrete
        return self.yaw
