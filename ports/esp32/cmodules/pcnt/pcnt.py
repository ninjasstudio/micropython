'''
ESP32 Pulse Counter
https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/pcnt.html
Wrapped around
https://github.com/espressif/esp-idf/blob/master/components/driver/include/driver/pcnt.h
https://github.com/espressif/esp-idf/blob/master/components/hal/include/hal/pcnt_types.h
https://github.com/espressif/esp-idf/blob/master/components/driver/pcnt.c
See also
https://github.com/espressif/esp-idf/tree/master/examples/peripherals/pcnt/pulse_count_event
'''

__author__ = 'Ihor Nehrutsa'

PCNT_PIN_NOT_USED =    -1  # When selected for a pin, this pin will not be used

'''
PCNT port number, the max port number is (PCNT_PORT_MAX - 1).
'''
PCNT_PORT_0 = 0                 # PCNT port 0
PCNT_PORT_MAX = 1               # PCNT port max

'''
Selection of all available PCNT units
'''
UNIT_0 = 0                 # PCNT unit 0
UNIT_1 = 1                 # PCNT unit 1
UNIT_2 = 2                 # PCNT unit 2
UNIT_3 = 3                 # PCNT unit 3
UNIT_4 = 4                 # PCNT unit 4
UNIT_5 = 5                 # PCNT unit 5
UNIT_6 = 6                 # PCNT unit 6
UNIT_7 = 7                 # PCNT unit 7
UNIT_MAX = 8

'''
Selection of available modes that determine the counter's action depending on the state of the control signal's input GPIO
Configuration covers two actions, one for high, and one for low level on the control input
'''
MODE_KEEP = 0             # Control mode: won't change counter mode'''
MODE_REVERSE = 1          # Control mode: invert counter mode(increase -> decrease, decrease -> increase)
MODE_DISABLE = 2          # Control mode: Inhibit counter(counter value will not change in this condition)
MODE_MAX = 3

'''
Selection of available modes that determine the counter's action on the edge of the pulse signal's input GPIO
Configuration covers two actions, one for positive, and one for negative edge on the pulse input
'''
COUNT_DIS = 0            # Counter mode: Inhibit counter(counter value will not change in this condition)
COUNT_INC = 1            # Counter mode: Increase counter value
COUNT_DEC = 2            # Counter mode: Decrease counter value
COUNT_MAX = 3

'''
Selection of channels available for a single PCNT unit
'''
CHANNEL_0 = 0x00           # PCNT channel 0
CHANNEL_1 = 0x01           # PCNT channel 1
CHANNEL_MAX = 1

'''
Selection of counter's events the may trigger an interrupt
'''
EVT_THRES_1 = 1<<2           # PCNT watch point event: threshold1 value event
EVT_THRES_0 = 1<<3           # PCNT watch point event: threshold0 value event
EVT_L_LIM = 1<<4             # PCNT watch point event: Minimum counter value
EVT_H_LIM = 1<<5             # PCNT watch point event: Maximum counter value
EVT_ZERO = 1<<6              # PCNT watch point event: counter value zero event

'''
Pulse Counter configuration for a single channel

typedef struct {
    int pulse_gpio_num;             # Pulse input GPIO number, if you want to use GPIO16, enter pulse_gpio_num = 16, a negative value will be ignored
    int ctrl_gpio_num;              # Control signal input GPIO number, a negative value will be ignored
    pcnt_ctrl_mode_t lctrl_mode;    # PCNT low control mode
    pcnt_ctrl_mode_t hctrl_mode;    # PCNT high control mode
    pcnt_count_mode_t pos_mode;     # PCNT positive edge count mode
    pcnt_count_mode_t neg_mode;     # PCNT negative edge count mode
    int16_t counter_h_lim;          # Maximum counter value
    int16_t counter_l_lim;          # Minimum counter value
    pcnt_unit_t unit;               # PCNT unit number
    pcnt_channel_t channel;         # the PCNT channel
} pcnt_config_t;
'''

#typedef intr_handle_t pcnt_isr_handle_t;

class PCNT():
    def unit_config(self, pcnt_config:int) -> int:
        '''
        Configure Pulse Counter unit
                @note
                This function will disable three events: PCNT_EVT_L_LIM, PCNT_EVT_H_LIM, PCNT_EVT_ZERO.

         @param pcnt_config Pointer of Pulse Counter unit configure parameter

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver already initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def get_counter_value(self, pcnt_unit:int, count:int) -> int:
        '''
        Get pulse counter value

         @param pcnt_unit  Pulse Counter unit number
         @param count Pointer to accept counter value

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def counter_pause(self, pcnt_unit:int) -> int:
        '''
        Pause PCNT counter of PCNT unit

         @param pcnt_unit PCNT unit number

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def counter_resume(self, pcnt_unit:int) -> int:
        '''
        Resume counting for PCNT counter

         @param pcnt_unit: 0 -> int PCNT unit number, select from pcnt_unit: 0 -> int_t

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    #def counter_clear(self:object, pcnt_unit=0) -> int:
    def counter_clear(self, pcnt_unit:int) -> int:
        '''
        Clear and reset PCNT counter value to zero

         @param  pcnt_unit PCNT unit number, select from pcnt_unit_t

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def intr_enable(self, pcnt_unit:int) -> int:
        '''
        Enable PCNT interrupt for PCNT unit
                @note
                Each Pulse counter unit has five watch point events that share the same interrupt.
                Configure events with pcnt_event_enable() and pcnt_event_disable()

         @param pcnt_unit PCNT unit number

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def intr_disable(self, pcnt_unit:int=0) -> int:
        '''
        Disable PCNT interrupt for PCNT unit

         @param pcnt_unit PCNT unit number

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def event_enable(self, unit:int, evt_type:int) -> int:
        '''
        Enable PCNT event of PCNT unit

         @param unit PCNT unit number
         @param evt_type Watch point event type.
                         All enabled events share the same interrupt (one interrupt per pulse counter unit).
         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def event_disable(self, unit:int, evt_type:int) -> int:
        '''
        Disable PCNT event of PCNT unit

         @param unit PCNT unit number
         @param evt_type Watch point event type.
                         All enabled events share the same interrupt (one interrupt per pulse counter unit).
         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def set_event_value(self, unit:int, evt_type:int, value:int) -> int:
        '''
        Set PCNT event value of PCNT unit

         @param unit PCNT unit number
         @param evt_type Watch point event type.
                         All enabled events share the same interrupt (one interrupt per pulse counter unit).

         @param value Counter value for PCNT event

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def get_event_value(self, unit:int, evt_type:int, value:int) -> int:
        '''
        Get PCNT event value of PCNT unit

         @param unit PCNT unit number
         @param evt_type Watch point event type.
                         All enabled events share the same interrupt (one interrupt per pulse counter unit).
         @param value Pointer to accept counter value for PCNT event

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def isr_unregister(self, handle:int) -> int:
        '''
        Unregister PCNT interrupt handler (registered by pcnt_isr_register), the handler is an ISR.
                The handler will be attached to the same CPU core that this function is running on.
                If the interrupt service is registered by pcnt_isr_service_install, please call pcnt_isr_service_uninstall instead

         @param handle handle to unregister the ISR service.

         @return
             - ESP_OK Success
             - ESP_ERR_NOT_FOUND Can not find the interrupt that matches the flags.
             - ESP_ERR_INVALID_ARG Function pointer error.
        '''
        pass

    def isr_register(self, fn:int, arg:int, intr_alloc_flags:int, handle:int) -> int:
        '''
        Register PCNT interrupt handler, the handler is an ISR.
                The handler will be attached to the same CPU core that this function is running on.
                Please do not use pcnt_isr_service_install if this function was called.

         @param fn Interrupt handler function.
         @param arg Parameter for handler function
         @param intr_alloc_flags Flags used to allocate the interrupt. One or multiple (ORred)
                ESP_INTR_FLAG_* values. See esp_intr_alloc.h for more info.
         @param handle Pointer to return handle. If non-NULL, a handle for the interrupt will
                be returned here. Calling pcnt_isr_unregister to unregister this ISR service if needed,
                but only if the handle is not NULL.

         @return
             - ESP_OK Success
             - ESP_ERR_NOT_FOUND Can not find the interrupt that matches the flags.
             - ESP_ERR_INVALID_ARG Function pointer error.
        '''
        pass

    def set_pin(self, unit:int, channel:int, pulse_io:int, ctrl_io:int) -> int:
        '''
        Configure PCNT pulse signal input pin and control input pin

         @param unit PCNT unit number
         @param channel PCNT channel number
         @param pulse_io Pulse signal input GPIO
         @param ctrl_io Control signal input GPIO

        Set the signal input to PCNT_PIN_NOT_USED if unused.

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def filter_enable(self, unit:int) -> int:
        '''
        Enable PCNT input filter

         @param unit PCNT unit number

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def filter_disable(self, unit:int) -> int:
        '''
        Disable PCNT input filter

         @param unit PCNT unit number

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def set_filter_value(self, unit:int, filter_val:int) -> int:
        '''
        Set PCNT filter value

         @param unit PCNT unit number
         @param filter_val PCNT signal filter value, counter in APB_CLK cycles.
                Any pulses lasting shorter than this will be ignored when the filter is enabled.
                @note
                filter_val is a 10-bit value, so the maximum filter_val should be limited to 1023.

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def get_filter_value(self, unit:int, filter_val:int) -> int:
        '''
        Get PCNT filter value

         @param unit PCNT unit number
         @param filter_val Pointer to accept PCNT filter value.

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def set_mode(self, unit:int, channel:int,
                            pos_mode:int, neg_mode:int,
                            hctrl_mode:int, lctrl_mode:int) -> int:
        '''
        Set PCNT counter mode

         @param unit PCNT unit number
         @param channel PCNT channel number
         @param pos_mode Counter mode when detecting positive edge
         @param neg_mode Counter mode when detecting negative edge
         @param hctrl_mode Counter mode when control signal is high level
         @param lctrl_mode Counter mode when control signal is low level

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def isr_handler_add(self, unit:int, isr_handler:int, args:int) -> int:
        '''
        Add ISR handler for specified unit.

         Call this function after using pcnt_isr_service_install() to
         install the PCNT driver's ISR handler service.

         The ISR handlers do not need to be declared with IRAM_ATTR,
         unless you pass the ESP_INTR_FLAG_IRAM flag when allocating the
         ISR in pcnt_isr_service_install().

         This ISR handler will be called from an ISR. So there is a stack
         size limit (configurable as "ISR stack size" in menuconfig). This
         limit is smaller compared to a global PCNT interrupt handler due
         to the additional level of indirection.

         @param unit PCNT unit number
         @param isr_handler Interrupt handler function.
         @param args Parameter for handler function

         @return 
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass

    def isr_service_install(self, intr_alloc_flags:int) -> int:
        '''
        Install PCNT ISR service.
         @note We can manage different interrupt service for each unit.
               This function will use the default ISR handle service, Calling pcnt_isr_service_uninstall to
               uninstall the default service if needed. Please do not use pcnt_isr_register if this function was called.

         @param intr_alloc_flags Flags used to allocate the interrupt. One or multiple (ORred)
                ESP_INTR_FLAG_* values. See esp_intr_alloc.h for more info.

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_NO_MEM No memory to install this service
             - ESP_ERR_INVALID_STATE ISR service already installed
        '''
        pass

    def pcnt_isr_service_uninstall(self):
        '''
        Uninstall PCNT ISR service, freeing related resources.
        '''
        pass

    def isr_handler_remove(self, unit:int) -> int:
        '''
        Delete ISR handler for specified unit.

         @param unit PCNT unit number

         @return
             - ESP_OK Success
             - ESP_ERR_INVALID_STATE pcnt driver has not been initialized
             - ESP_ERR_INVALID_ARG Parameter error
        '''
        pass
    
if __name__ == "__main__":
#     print(dir(isr_unregister))
#     for e in dir(isr_unregister):
#         print(e)
#         
#     print(dir(isr_unregister.__code__))
#     
#     import dis
#     dis.dis(isr_unregister)
    
    pass

'''
 EXAMPLE OF PCNT CONFIGURATION
 ==============================
 //1. Config PCNT unit
 pcnt_config_t pcnt_config = {
     .pulse_gpio_num = 4,         //set gpio4 as pulse input gpio
     .ctrl_gpio_num = 5,          //set gpio5 as control gpio
     .channel = PCNT_CHANNEL_0,         //use unit 0 channel 0
     .lctrl_mode = PCNT_MODE_REVERSE,   //when control signal is low, reverse the primary counter mode(inc->dec/dec->inc)
     .hctrl_mode = PCNT_MODE_KEEP,      //when control signal is high, keep the primary counter mode
     .pos_mode = PCNT_COUNT_INC,        //increment the counter
     .neg_mode = PCNT_COUNT_DIS,        //keep the counter value
     .counter_h_lim = 10,
     .counter_l_lim = -10,
 };
 pcnt_unit_config(&pcnt_config):        //init unit

 EXAMPLE OF PCNT EVENT SETTING
 ==============================
 //2. Configure PCNT watchpoint event.
 pcnt_set_event_value(PCNT_UNIT_0, PCNT_EVT_THRES_1, 5):   //set thres1 value
 pcnt_event_enable(PCNT_UNIT_0, PCNT_EVT_THRES_1):         //enable thres1 event

 For more examples please refer to PCNT example code in IDF_PATH/examples
'''
