power_exit = False
try:
    from gc import collect
    collect()
    from esp32_ import LED, PWR_CTRL, ADC_PoE, STEP_1, STEP_2, DIR_1, DIR_2
    collect()
    from micropython import kbd_intr
    collect()
    from _thread import start_new_thread, exit
    collect()
    from utime import sleep_ms
    collect()
    from machine import Pin, ADC, idle

    step1 = Pin(STEP_1, Pin.OUT, value=1)  # Pin.IN может создавать дребезг на входах драйверов ШД
    step2 = Pin(STEP_2, Pin.OUT, value=1)

    dir1 = Pin(DIR_1, Pin.OUT, value=1)
    dir2 = Pin(DIR_2, Pin.OUT, value=1)

    led = Pin(LED, Pin.OUT, value=1)

    pwr = Pin(PWR_CTRL, Pin.OUT, value=0)  # battery off
    sleep_ms(1000)  # Is PoE on?
    pwr.value(1)  # battery on

    def check_PoE():
        #kbd_intr(-1)
        adc_PoE = ADC(Pin(ADC_PoE))  # create ADC object on ADC pin
        adc_PoE.atten(ADC.ATTN_6DB)  # 6dB attenuation, gives a maximum input voltage of approximately 2.00v
        a_PoE = adc_PoE.read()
        n = 0
        while True:
            try:
                a_PoE = adc_PoE.read()
                if a_PoE < 500:
                    print('\nPoE IN lost {}s of 30s.'.format(n))
                    if n >= 30:  # 30s
                        print('\nSelf battery off.')
                        sleep_ms(1000)  # 1s
                        pwr.value(0)  # self power off
                    n += 1
                else:
                    if n != 0:
                        n = 0
                        print('\nPoE IN is on again.')
                    idle()
                    sleep_ms(1000)

                led.value(not led.value())
                #print('check_PoE()')
                if power_exit:
                    exit()
                idle()
                sleep_ms(1000)
            except KeyboardInterrupt:
                print('check_PoE(): KeyboardInterrupt:')
                sleep_ms(1000)
                raise KeyboardInterrupt
                pass

    try:
        from config_version import HARDWARE
        collect()
    except Exception as e:
        print("import config_version:", e)
        HARDWARE = -1

    if HARDWARE >= 0:
        start_new_thread(check_PoE, ())
except Exception as e:
    print("Exception: start_new_thread:", e)
    pass
