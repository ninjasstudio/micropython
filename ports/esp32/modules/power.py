MULTIPLIER_V_PoE = 0.7
MULTIPLIER_V_BAT = 0.8

SECONDS = 30  # 30s

try:
    import config_power
    MULTIPLIER_V_PoE = config_power.MULTIPLIER_V_PoE
    MULTIPLIER_V_BAT = config_power.MULTIPLIER_V_BAT
    SECONDS = config_power.SECONDS
    del (config_power)
except ImportError as e:
    print("ImportError: import config_power: ", e)

from micropython import kbd_intr
from _thread import start_new_thread
from utime import sleep_ms
from machine import Pin, ADC, idle
from esp32 import raw_temperature

from esp32_ import LED, PWR_CTRL, ADC_PoE, ADC_BAT, STEP_1, STEP_2, DIR_1, DIR_2
from temperature_conversion import Celsius_from_Fahrenheit

power_off_s = 0  # секунд после отключения питания
power_off_ready = False

step1 = Pin(STEP_1, Pin.OUT, value=1)  # Pin.IN может создавать дребезг на входах драйверов ШД
step2 = Pin(STEP_2, Pin.OUT, value=1)

dir1 = Pin(DIR_1, Pin.OUT, value=1)
dir2 = Pin(DIR_2, Pin.OUT, value=1)

led = Pin(LED, Pin.OUT, value=1)

pwr = Pin(PWR_CTRL, Pin.OUT, value=0)  # battery off
sleep_ms(1000)  # Is PoE on?
pwr.value(1)  # battery on

adc_PoE = ADC(Pin(ADC_PoE))  # create ADC object on ADC pin
adc_PoE.atten(ADC.ATTN_6DB)  # 6dB attenuation, gives a maximum input voltage of approximately 2.00v

adc_BAT = ADC(Pin(ADC_BAT))
adc_BAT.atten(ADC.ATTN_6DB)

# напряжение на клеммах
def V_PoE():
    return round(2 * adc_PoE.read() * 30 / 4095 * MULTIPLIER_V_PoE, 1) # 30В т.к. бортовая сеть 24-28В

def V_BAT():
    return round(2 * adc_BAT.read() * 12 / 4095 * MULTIPLIER_V_BAT, 1) # 12В т.к. 11.2В максимум для батареи

def esp32_Celsius():
    return round(Celsius_from_Fahrenheit(raw_temperature()), 1)

def check_PoE_thread():
    global power_off_s
    
    kbd_intr(-1)
    while True:
        try:
            if adc_PoE.read() < 500:
                print(f'\nPoE IN lost {power_off_s}s.')
                if power_off_s >= SECONDS:
                    if power_off_ready or power_off_s >= SECONDS:
                        print('\nSelf battery off.')
                        sleep_ms(1000)  # 1s
                        pwr.value(0)  # self power off
                        break
                power_off_s += 1
            else:
                if power_off_s != 0:
                    power_off_s = 0
                    print('\nPoE IN is on again.')
                idle()
                sleep_ms(1000)

            led.value(not led.value())
            
#            1/0

            idle()
            sleep_ms(1000)
        except KeyboardInterrupt:
            print('check_PoE(): KeyboardInterrupt:')
            sleep_ms(1000)
            raise KeyboardInterrupt

def start_check_PoE_thread():
    try:
        start_new_thread(check_PoE_thread, ())
    except Exception as e:
        print("Exception: start_new_thread(check_PoE, ()):", e)
        pass

def power_print():
    print('V_PoE():', V_PoE(), '\tV_BAT():', V_BAT(), '\tesp32_Celsius():', esp32_Celsius())

def power_test():
    while True:
        power_print()
        sleep_ms(500)
