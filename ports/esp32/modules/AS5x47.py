from uctypes import BF_POS, BF_LEN, BFUINT16, BIG_ENDIAN, struct, bytes_at, addressof, sizeof
from utime import sleep_us

from angles import to180

# ----------------------------------------------------------------------
__MSB_mask = 0x4000  # for lower 15 bits
__to_angle = 360 / 0x4000

@micropython.native
def is_even(data, msb_mask):
    # Calc parity bit
    count = 0
    while msb_mask:
        if data & msb_mask:
            count += 1
        msb_mask >>= 1
    return count & 1


# ----------------------------------------------------------------------
# SPI Command Frame
# Name | Bit Position & Bit Length | Description
Command_Frame_struct = {
    "PARC": 15 << BF_POS | 1 << BF_LEN | BFUINT16,  #      Parity bit (even) calculated on the lower 15 bits of command frame
    "R_W": 14 << BF_POS | 1 << BF_LEN | BFUINT16,  #       0: Write, 1: Read
    "ADDR": 0 << BF_POS | 14 << BF_LEN | BFUINT16,  # 13:0 Address to read or write
    }

WRITE = 0  # constants for "Command_Frame_struct.R_W" field
READ = 1

# SPI Read Data Frame
# Name | Bit Position & Bit Length | Description
Read_Data_Frame_struct = {
    "PARD": 15 << BF_POS | 1 << BF_LEN | BFUINT16,  #      Parity bit (even) for the data frame
    "EF": 14 << BF_POS | 1 << BF_LEN | BFUINT16,  #        0: No command frame error occurred, 1: Error occurred
    "DATA": 0 << BF_POS | 14 << BF_LEN | BFUINT16,  # 13:0 Data
    }

# SPI Write Data Frame
# Name | Bit Position & Bit Length | Description
Write_Data_Frame_struct = {
    "PARD": 15 << BF_POS | 1 << BF_LEN | BFUINT16,  #      Parity bit (even)
    "LOW": 14 << BF_POS | 1 << BF_LEN | BFUINT16,  #       Always low
    "DATA": 0 << BF_POS | 14 << BF_LEN | BFUINT16,  # 13:0 Data
    }

# ----------------------------------------------------------------------
# Volatile Register Table
# Name | Address    | Default | Description
NOP = 0x0000  #       0x0000    No operation
ERRFL = 0x0001  #     0x0000    Error register
PROG = 0x0003  #      0x0000    Programming register
DIAAGC = 0x3FFC  #    0x0180    Diagnostic and AGC
MAG = 0x3FFD  #       0x0000    CORDIC magnitude
ANGLEUNC = 0x3FFE  #  0x0000    Measured angle without dynamic angle error compensation
ANGLECOM = 0x3FFF  #  0x0000    Measured angle with dynamic angle error compensation

# Defining structure layouts for registers:

# ERRFL (0x0001)
# Name | Bit Position & Bit Length | Read/Write | Description
ERRFL_struct = {
    "PARERR": 2 << BF_POS | 1 << BF_LEN | BFUINT16,  #  R Parity error
    "INVCOMM": 1 << BF_POS | 1 << BF_LEN | BFUINT16,  # R Invalid command error: set to 1 by reading or writing an invalid register address
    "FRERR": 0 << BF_POS | 1 << BF_LEN | BFUINT16,  #   R Framing error: is set to 1 when a non-compliant SPI frame is detected
    }

# PROG (0x0003)
# Name | Bit Position & Bit Length | Read/Write | Description
PROG_struct = {
    "PROGVER": 6 << BF_POS | 1 << BF_LEN | BFUINT16,  # R/W Program verify: must be set to 1 for verifying the correctness of the OTP programming
    "PROGOTP": 3 << BF_POS | 1 << BF_LEN | BFUINT16,  # R/W Start OTP programming cycle
    "OTPREF": 2 << BF_POS | 1 << BF_LEN | BFUINT16,  #  R/W Refreshes the non-volatile memory content with the OTP programmed content
    "PROGEN": 0 << BF_POS | 1 << BF_LEN | BFUINT16,  #  R/W Program OTP enable: enables programming the entire OTP memory
    }

# DIAAGC (0x3FFC)
# Name | Bit Position & Bit Length | Read/Write | Description
DIAAGC_struct = {
    "MAGL": 11 << BF_POS | 1 << BF_LEN | BFUINT16,  #   R Diagnostics: Magnetic field strength too low; AGC=0xFF
    "MAGH": 10 << BF_POS | 1 << BF_LEN | BFUINT16,  #   R Diagnostics: Magnetic field strength too high; AGC=0x00
    "COF": 9 << BF_POS | 1 << BF_LEN | BFUINT16,  #     R Diagnostics: CORDIC overflow
    "LF": 8 << BF_POS | 1 << BF_LEN | BFUINT16,  #      R Diagnostics: Offset compensation
    #                                                                  LF=0:internal offset loops not ready regulated
    #                                                                  LF=1:internal offset loop finished
    "AGC": 0 << BF_POS | 8 << BF_LEN | BFUINT16,  # 7:0 R Automatic gain control value
    }

# MAG (0x3FFD)
# Name | Bit Position & Bit Length | Read/Write | Description
MAG_struct = {
    "CMAG": 0 << BF_POS | 14 << BF_LEN | BFUINT16,  # 13:0 R CORDIC magnitude information
    }

# ANGLE (0x3FFE)
# Name | Bit Position & Bit Length | Read/Write | Description
ANGLEUNC_struct = {
    "CORDICANG": 0 << BF_POS | 14 << BF_LEN | BFUINT16,  # 13:0 R Angle information without dynamic angle error compensation
    }

# ANGLECOM (0x3FFF)
# Name | Bit Position & Bit Length | Read/Write | Description
ANGLECOM_struct = {
    "DAECANG": 0 << BF_POS | 14 << BF_LEN | BFUINT16,  # 13:0 R Angle information with dynamic angle error compensation
    }

# ----------------------------------------------------------------------
# Non-Volatile Register Table
# Name | Address       | Default | Description
ZPOSM = 0x0016  #        0x0000    Zero position MSB
ZPOSL = 0x0017  #        0x0000    Zero position LSB /MAG diagnostic
SETTINGS1 = 0x0018  #    0x0001    Custom setting register 1
SETTINGS2 = 0x0019  #    0x0000    Custom setting register 2

# Defining structure layouts for registers:

# ZPOSM (0x0016)
# Name | Bit Position & Bit Length | Read/Write/Program | Description
ZPOSM_struct = {
    "ZPOSM": 0 << BF_POS | 8 << BF_LEN | BFUINT16,  #       7:0 R/W/P 8 most significant bits of the zero position
    }

# ZPOSL (0x0017)
# Name | Bit Position & Bit Length | Read/Write/Program | Description
ZPOSL_struct = {
    "ZPOSL": 5 << BF_POS | 6 << BF_LEN | BFUINT16,  #       5:0 R/W/P 6 least significant bits of the zero position
    "COMP_L_ERROR_EN": 6 << BF_POS | 1 << BF_LEN | BFUINT16,  # R/W/P This bit enables the contribution of MAGH (magnetic field strength too high) to the error flag
    "COMP_H_ERROR_EN": 7 << BF_POS | 1 << BF_LEN | BFUINT16,  # R/W/P This bit enables the contribution of MAGL (magnetic field strength too low) to the error flag
    }

# SETTINGS1 (0x0018)
# Name | Bit Position & Bit Length | Read/Write/Program | Description
SETTINGS1_struct = {
    "FACTORY_SETTING": 0 << BF_POS | 1 << BF_LEN | BFUINT16,  # R     Pre-Programmed to 1
    "NOT_USED": 1 << BF_POS | 1 << BF_LEN | BFUINT16,  #        R/W/P Pre-Programmed to 0, must not be overwritten.
    "DIR": 2 << BF_POS | 1 << BF_LEN | BFUINT16,  #             R/W/P Rotation direction
    "UVW_ABI": 3 << BF_POS | 1 << BF_LEN | BFUINT16,  #         R/W/P Defines the PWM Output
    #                                                                                         (0 = ABI is operating, W is used as PWM, 1 = UVW is operating, I is used as PWM)
    "DAECDIS": 4 << BF_POS | 1 << BF_LEN | BFUINT16,  #         R/W/P Disable Dynamic Angle Error Compensation
    #                                                                                         (0 = DAE compensation ON, 1 = DAE compensation OFF)
    "ABIBIN": 5 << BF_POS | 1 << BF_LEN | BFUINT16,  #          R/W/P ABI decimal or binary selection of the ABI pulses per revolution
    "DATASELECT": 6 << BF_POS | 1 << BF_LEN | BFUINT16,  #      R/W/P This bit defines which data can be read form address 16383dec (3FFFhex).
    #                                                                                         (0->DAECANG, 1->CORDICANG)
    "PWMON": 7 << BF_POS | 1 << BF_LEN | BFUINT16,  #           R/W/P Enables PWM (setting of UVW_ABI Bit necessary)
    }

# SETTINGS2 (0x0019)
# Name | Bit Position & Bit Length | Read/Write/Program | Description
SETTINGS2_struct = {
    "UVWPP": 0 << BF_POS | 3 << BF_LEN | BFUINT16,  #       2:0 R/W/P UVW number of pole pairs
    #                                                       (000 = 1, 001 = 2, 010 = 3, 011 = 4, 100 = 5, 101 = 6, 110 = 7, 111 = 7)
    "HYS": 3 << BF_POS | 2 << BF_LEN | BFUINT16,  #         4:3 R/W/P Hysteresis setting
    "ABIRES": 5 << BF_POS | 3 << BF_LEN | BFUINT16,  #      7:5 R/W/P Resolution of ABI
    }
# ----------------------------------------------------------------------


class AS5x47():
    # SPI Interface(slave) communicates at clock rates up to 10 MHz.
    # The AS5047D SPI uses mode=1 (CPOL=0, CPHA=1) to exchange data.
    #
    # The ESP32 polarity can be 0 or 1, and is the level the idle clock line sits at.
    # The ESP32 phase can be 0 or 1 to sample data on the first or second clock edge respectively.
    #
    # The ESP32 polarity is the idle state of SCK.
    # The ESP32 phase=0 means sample on the first edge of SCK, phase=1 means the second.
    #
    # spi = SPI(HSPI_ID, sck=Pin(HSPI_sck), mosi=Pin(HSPI_mosi), miso=Pin(HSPI_miso), baudrate=10000000, polarity=0, phase=1, bits=16, firstbit=SPI.MSB)
    # cs = Pin(esp32_.HSPI_cs1, Pin.OUT, value=1)
    def __init__(self, spi, spi_baudrate, cs, direction=1):
        self.spi = spi
        self.tclk_2_us = 1000000 // (spi_baudrate * 2) + 1  # tH = tclk / 2 us # Time between last falling edge of CLK and rising edge of cs
        self.cs = cs  # active is low
        self.direction = direction  # set -1 to reverse angles

        self._write_command = bytearray(b'\xc0\x00')
        self._received_data = bytearray(2)
        self._command_buff = bytearray(2)
        self._data_buff = bytearray(2)

        self._angle_major = 0
        self._angle14 = 0
        self._angle14_prev = 0
        
        for _ in range(10):
            self.readAngleCom()
            sleep_us(10_000)
        i = 0
        n = 0
        while True:
            i += 1
            n += 1
            x1 = self.readAngleCom()  # before self.readAngleComInfinity()
            if self._angle14 >= 0:  # 8192:
                if self._angle14_prev < 0:
                     n = 0
            else:
                if self._angle14_prev >= 0:
                     n = 0
            self._angle14_prev = self._angle14
            x2 = self.readAngleComInfinity()  # after self.readAngleCom()
            # print('AS5x47 _angle14:{:10}, angle_major:{:10}, res:{:10}:{:10}'.format(self._angle14, self._angle_major, x1, x2))
            if (n > 5) or (i > 50):
                break
            sleep_us(10_000)

    # ------------------
    @micropython.native
    def _readAngleInfinity(self, readAngleFunc):
        angle_new = readAngleFunc()  # 8192 == 2 ** 14 / 2
        #print(' _angle14_prev:{}, _angle14:{}'.format(self._angle14_prev, self._angle14))
        if self._angle14_prev - self._angle14 >= 8192:
            self._angle_major += 360
            #print('+360 _angle14_prev:{}, _angle14:{}, angle_major:{}, angle_new:{}, res:{}'.format(self._angle14_prev, self._angle14, self._angle_major, angle_new, self._angle_major + angle_new))
        elif self._angle14 - self._angle14_prev >= 8192:
            self._angle_major -= 360
            #print('-360 _angle14_prev:{}, _angle14:{}, angle_major:{}, angle_new:{}, res:{}'.format(self._angle14_prev, self._angle14, self._angle_major, angle_new, self._angle_major + angle_new))
        self._angle14_prev = self._angle14
        return self._angle_major + angle_new

    def __repr__(self):
        return 'AS5x47(spi={}, cs={})'.format(self.spi, self.cs)

    @micropython.native
    def writeData(self, command, value):
        # Send command
        self.cs.off()
        self.spi.write(command)
        sleep_us(self.tclk_2_us)
        self.cs.on()

        # Send data
        self.cs.off()
        self.spi.write(value)
        sleep_us(self.tclk_2_us)
        self.cs.on()

    @micropython.native
    def readData(self, command):
        # Send Read Command
        self._write_command = bytes_at(addressof(command), sizeof(command))
        self.cs.off()
        self.spi.write(self._write_command)
        sleep_us(self.tclk_2_us)
        self.cs.on()

        # Send Nop Command while receiving data
        self.cs.off()
        self.spi.write_readinto(self._write_command, self._received_data)
        sleep_us(self.tclk_2_us)
        self.cs.on()

    @micropython.native
    def readDataAgain(self):
        self.cs.off()
        self.spi.write_readinto(self._write_command, self._received_data)
        sleep_us(self.tclk_2_us)
        self.cs.on()

    @micropython.native
    def receivedFrameStruct(self, receivedFrame):
        return struct(addressof(receivedFrame), Read_Data_Frame_struct, BIG_ENDIAN)

    @micropython.native
    def readRegister(self, registerAddress):
        command = struct(addressof(self._command_buff), Command_Frame_struct, BIG_ENDIAN)
        command.ADDR = registerAddress
        command.R_W = READ
        command.PARC = is_even(int.from_bytes(self._command_buff, 'big'), __MSB_mask)

        self.readData(command)
        receivedFrame = self.receivedFrameStruct(self._received_data)
        if receivedFrame.EF:
            self.readData(command)
            receivedFrame = self.receivedFrameStruct(self._received_data)
            if receivedFrame.EF:
                #raise ValueError
                print('receivedFrame.EF')
        if receivedFrame.PARD != is_even(receivedFrame.DATA, __MSB_mask):
            #raise ValueError
            print('receivedFrame.PARD != is_even')

    @micropython.native
    def readRegisterAgain(self):
        self.readDataAgain()

    @micropython.native
    def writeRegister(self, registerAddress, registerValue):
        command = struct(addressof(self._command_buff), Command_Frame_struct, BIG_ENDIAN)
        command.ADDR = registerAddress
        command.R_W = WRITE
        command.PARC = is_even(int.from_bytes(self._command_buff, 'big'), __MSB_mask)

        data = struct(addressof(self._data_buff), Write_Data_Frame_struct, BIG_ENDIAN)
        data.DATA = registerValue
        data.LOW = 0
        data.PARD = is_even(int.from_bytes(self._data_buff, 'big'), __MSB_mask)

        self.writeData(command, data)

    # ------------------
    def readAngle(self):
        self.readRegister(ANGLEUNC)
        self._angle14 = struct(addressof(self._received_data), ANGLEUNC_struct, BIG_ENDIAN).CORDICANG - 0x2000
        return self.direction * self._angle14 * __to_angle

    def readAngleAgain(self):
        self.readRegisterAgain()
        self._angle14 = struct(addressof(self._received_data), ANGLEUNC_struct, BIG_ENDIAN).CORDICANG - 0x2000
        return self.direction * self._angle14 * __to_angle

    def readAngleInfinity(self):
        return self._readAngleInfinity(self.readAngleAgain)

    # ------------------
    @micropython.native
    def readAngleCom(self):
        self.readRegister(ANGLECOM)
        self._angle14 = struct(addressof(self._received_data), ANGLECOM_struct, BIG_ENDIAN).DAECANG - 0x2000
        return self.direction * self._angle14 * __to_angle

    @micropython.native
    def readAngleComAgain(self):
        self.readRegisterAgain()
        self._angle14 = struct(addressof(self._received_data), ANGLECOM_struct, BIG_ENDIAN).DAECANG - 0x2000
        return self.direction * self._angle14 * __to_angle

    @micropython.native
    def readAngleComInfinity(self):
        return self._readAngleInfinity(self.readAngleComAgain)

    # ------------------
    def writeSettings1(self, value):
        self.writeRegister(SETTINGS1, value)

    def writeSettings2(self, value):
        self.writeRegister(SETTINGS2, value)

    def writeZeroPosition(self, zposm, zposl):
        self.writeRegister(ZPOSM, zposm)
        self.writeRegister(ZPOSL, zposl)
