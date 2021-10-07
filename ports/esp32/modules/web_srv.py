USE_ROUTEROS_API = 1

from gc import collect, mem_free

collect()
from sys import exit

collect()
from ujson import dumps, loads

collect()
from network import WLAN, AP_IF, STA_IF

collect()

from WiFi import WiFi_login, save_config_WiFi  #, WiFi_start

collect()
from saves import *

collect()

try:
    import config
    collect()
except ImportError:
    pass

try:
    import config_offset
    collect()
except ImportError:
    pass

try:
    import config_search
    collect()
except ImportError:
    pass

try:
    import config_WiFi
    collect()
except ImportError:
    pass

wlan_ap = WLAN(AP_IF)
wlan_sta = WLAN(STA_IF)

file = open("index.html")
html = file.read()
file.close()
pos1 = html.find("<form action=")
html1 = html[:pos1]
pos2 = html.find("</form>")
html2 = html[pos1:pos2]
html = html[pos2:]

file = open("config.html")
html_config = file.read()
file.close()

file = open("config_WiFi.html")
html_config_WiFi = file.read()
file.close()

file = open("config_PID.html")
html_config_PID = file.read()
file.close()

file = open("debug.html")
html_debug = file.read()
file.close()


def show_index_page(server, arg, owl):
    #if wlan.ifconfig()[0] == '192.168.4.1':
    if wlan_ap.active():
        show_config_WiFi_page(server, arg, owl)
        return

    owl.s1 = "Roll:{:8.1f} Pitch:{:8.1f} Yaw:{:8.1f}".format(owl.roll, owl.pitch, owl.yaw)
    #owl.s1 = "Pitch:{:8.1f} Yaw:{:8.1f}".format(pitch, yaw)
    s2 = dumps(owl.value_now)
    s3 = "Азимут: " + str(round(owl.azim.mover.angle_now(), 1)) + " " + str(round(owl.azim.mover.angle_target(), 1)) + " (" + str(round(owl.azim.min_search)) + ", " + str(round(owl.azim.max_search)) + ")"  # + " | yaw " + str(yaw) + " offset " + str(round(owl.azim.mover.offset, 1))  # + " " + str(owl.azim.mover.is_ready())  # + " " + str(owl.azim.mover.is_pulses) + " " + str(owl.azim.mover.direction)
    s4 = "Кут місця: " + str(round(owl.elev.mover.angle_now(), 1)) + " " + str(round(owl.elev.mover.angle_target(), 1)) + " (" + str(round(owl.elev.min_search)) + ", " + str(round(owl.elev.max_search)) + ")"  # + " | pitch " + str(pitch) + " offset " + str(round(owl.elev.mover.offset, 1)) + " " + str(owl.elev.mover.is_ready())  # + " " + str(owl.elev.mover.is_pulses) + " " + str(owl.elev.mover.direction)

    input_a = str(owl.input_azim)
    input_e = str(owl.input_elev)

    checked0 = ""  # Нерухомо 0
    checked1 = ""  # Ручний 1
    checked2 = ""  # Огляд границь 2 3
    checked4 = ""  # Пошук "Азимут" 4
    checked5 = ""  # Пошук "Кут місця" 5
    checked6 = ""  # Стеження хрестове 6 7
    checked8 = ""  # Стеження кругове 8
    if owl.mode == owl.MD_OFF:
        checked0 = "checked"
    elif owl.mode == owl.MD_MANUAL:
        checked1 = "checked"
    elif owl.mode in (owl.MD_SECTOR_A, owl.MD_SECTOR_E):
        checked2 = "checked"
    elif owl.mode == owl.MD_SEARCH_A:
        checked4 = "checked"
    elif owl.mode == owl.MD_SEARCH_E:
        checked5 = "checked"
    elif owl.mode in (owl.MD_ESCORT_A, owl.MD_ESCORT_E):
        checked6 = "checked"
    elif owl.mode == owl.MD_CIRCLE:
        checked8 = "checked"

    collect()

    server.out("")
    collect()

    s = html1.format(owl.s1, s2, s3, s4)
    collect()
    server.connection_send(s)
    collect()

    s = html2.format(checked0, checked1, checked2, checked4, checked5, checked6, checked8)
    collect()
    server.connection_send(s)
    collect()

    s = html.format(input_a, input_e)
    collect()
    server.connection_send(s)
    server.connection_send("\n")
    collect()
    #print(s)


def show_config_page(server, arg, owl):
    collect()
    s = html_config.format(
        config.ROUTEROS_IP,  #  
        config.ROUTEROS_USER,  #  
        config.ROUTEROS_PASSWORD,  #  
        config.RADIO_NAME
        )
    collect()
    server.out(s)


def show_config_WiFi_page(server, arg, owl):
    collect()
    s = html_config_WiFi.format(
        config_WiFi.SSID,  #
        config_WiFi.PASSWORD,  #
        config_WiFi.OWL_IP,  #
        config_WiFi.OWL_SUBNET,  #
        config_WiFi.OWL_GATEWAY,  #
        config_WiFi.OWL_DNS
        )
    collect()
    server.out(s)


def show_config_PID_page(server, arg, owl):
    collect()
    txt_azim_pid_components = str(list(owl.azim.mover.pid.components)) + ' ' + str(owl.azim.mover.pid._last_output)
    txt_azim_pid_tunings = str(list(owl.azim.mover.pid.tunings))
    txt_azim_pid_output_limits = str(list(owl.azim.mover.pid.output_limits))
    txt_azim_pid_output_pads = str(list(owl.azim.mover.pid.output_pads))

    txt_elev_pid_components = str(list(owl.elev.mover.pid.components)) + ' ' + str(owl.elev.mover.pid._last_output)
    txt_elev_pid_tunings = str(list(owl.elev.mover.pid.tunings))
    txt_elev_pid_output_limits = str(list(owl.elev.mover.pid.output_limits))
    txt_elev_pid_output_pads = str(list(owl.elev.mover.pid.output_pads))
    s = html_config_PID.format(
        txt_azim_pid_components,  #
        txt_azim_pid_tunings,  #
        txt_azim_pid_output_limits,  #
        txt_azim_pid_output_pads,  #
        txt_elev_pid_components,  #
        txt_elev_pid_tunings,  #
        txt_elev_pid_output_limits,  #
        txt_elev_pid_output_pads
        )
    collect()
    server.out(s)


def show_debug_page(server, arg, owl):
    collect()
    try:
        debug_value = dumps(eval(owl.expression))
    except Exception as e:
        debug_value = 'Error:' + dumps(e)
    print('Expression:>', owl.expression, '<\nValue:>', debug_value, '<')
    s = html_debug.format(owl.expression, debug_value)
    collect()
    server.out(s)


#--------------------------------------------------------
def do_save_config(server, arg, owl):
    save_config(owl)
    show_config_page(server, arg, owl)


def do_save_config_PID(server, arg, owl):
    save_config_PID(owl)
    show_config_PID_page(server, arg, owl)


def do_save_config_WiFi(server, arg, owl):
    show_config_WiFi_page(server, arg, owl)
    #sleep_ms(1000)
    ifconfig1 = wlan_sta.ifconfig()
    WiFi_login(config_WiFi.SSID, config_WiFi.PASSWORD, config_WiFi.OWL_IP, config_WiFi.OWL_SUBNET, config_WiFi.OWL_GATEWAY, config_WiFi.OWL_DNS)
    if wlan_sta.isconnected():
        save_config_WiFi(config_WiFi.SSID, config_WiFi.PASSWORD, (config_WiFi.OWL_IP, config_WiFi.OWL_SUBNET, config_WiFi.OWL_GATEWAY, config_WiFi.OWL_DNS))
    else:
        import config_WiFi as restore_WiFi
        collect()
        config_WiFi.SSID = restore_WiFi.SSID
        config_WiFi.PASSWORD = restore_WiFi.PASSWORD
        config_WiFi.OWL_IP = restore_WiFi.OWL_IP
        config_WiFi.OWL_SUBNET = restore_WiFi.OWL_SUBNET
        config_WiFi.OWL_GATEWAY = restore_WiFi.OWL_GATEWAY
        config_WiFi.OWL_DNS = restore_WiFi.OWL_DNS
        WiFi_login(config_WiFi.SSID, config_WiFi.PASSWORD, config_WiFi.OWL_IP, config_WiFi.OWL_SUBNET, config_WiFi.OWL_GATEWAY, config_WiFi.OWL_DNS)
        del restore_WiFi
    if USE_MICROPYSERVER:
        web_server.end()
    if USE_TXTSERVER:
        txt_server.end()
    ifconfig2 = wlan_sta.ifconfig()
    if ifconfig1[0] != ifconfig2[0]:
        print('IP адрес изменен с {} на {}!'.format(ifconfig1[0], ifconfig2[0]))
    show_config_WiFi_page(server, arg, owl)


#--------------------------------------------------------
def do_handler(server, arg, owl):
    owl.mode = int(arg[-1:])
    show_index_page(server, arg, owl)
    owl.auto_start = False


def SET0(owl):
    owl.azim.mover.set0()
    owl.elev.mover.set0()
    save_config_offset(owl)


def do_SET0(server, arg, owl):
    SET0(owl)
    show_index_page(server, arg, owl)


#--------------------------------------------------------
def arg2val(arg):
    #print('arg=', arg)
    val = None
    _from = arg.find("=") + 1
    _to = arg.find("&")
    if _to > 0:
        v = arg[_from:_to]
    else:
        v = arg[_from:]

    if len(v):
        try:
            val = loads(v)
        except ValueError as e:
            print('arg=', arg, 'v=', v, 'Error:', e)
            try:
                val = eval(v)
            except Exception as e:
                print('arg=', arg, 'v=', v, 'Error:', e)
                return v
    #print('arg=', arg, 'v=', v, 'val=', val)
    return val


def do_get(server, arg, owl):
    val = arg2val(arg)
    if val is not None:
        if arg.find("input_a=") > 0:
            owl.input_azim = val
            if arg.find("&max=") > 0:
                owl.azim.max_search = min(val, owl.azim.mover.max_limit)
                save_config_search(owl)
            elif arg.find("&min=") > 0:
                owl.azim.min_search = max(val, owl.azim.mover.min_limit)
                save_config_search(owl)
            else:
                #if owl.mode == owl.MD_MANUAL:
                owl.azim.angle(val)
        elif arg.find("input_e=") > 0:
            owl.input_elev = val
            if arg.find("&max=") > 0:
                owl.elev.max_search = min(val, owl.elev.mover.max_limit)
                save_config_search(owl)
            elif arg.find("&min=") > 0:
                owl.elev.min_search = max(val, owl.elev.mover.min_limit)
                save_config_search(owl)
            else:
                #if owl.mode == owl.MD_MANUAL:
                owl.elev.angle(val)
    show_index_page(server, arg, owl)
    owl.auto_start = False


def do_get_config(server, arg, owl):
    if USE_ROUTEROS_API:
        val = arg2val(arg)
        print('arg, val', arg, val)
        changed = False
        if val is not None:
            if arg.find("ROUTEROS_IP=") >= 0:
                if config.ROUTEROS_IP != val:
                    config.ROUTEROS_IP = val
                    changed = True
            elif arg.find("ROUTEROS_USER=") >= 0:
                if config.ROUTEROS_USER != val:
                    config.ROUTEROS_USER = val
                    changed = True
            elif arg.find("ROUTEROS_PASSWORD=") >= 0:
                if config.ROUTEROS_USER != val:
                    config.ROUTEROS_USER = val
                    changed = True
            elif arg.find("radio_name=") >= 0:
                config.RADIO_NAME = val
                owl.RADIO_NAME = val
                if owl.ros_api:
                    owl.ros_api.radio_name = b"=radio-name=" + config.RADIO_NAME
                    print('do_get_config():ros_api.radio_name', owl.ros_api.radio_name)
        if changed:
            owl.deinit_ros_api()
            owl.init_ros_api(config.ROUTEROS_IP, config.ROUTEROS_USER, config.ROUTEROS_PASSWORD)
            owl.deinit_ros_api2()
            owl.init_ros_api2(config.ROUTEROS_IP, config.ROUTEROS_USER, config.ROUTEROS_PASSWORD)
    show_config_page(server, arg, owl)


def do_get_config_WiFi(server, arg, owl):
    val = arg2val(arg)
    print('arg, val', arg, val)
    if val is not None:
        if arg.find("SSID=") >= 0:
            config_WiFi.SSID = val
        elif arg.find("PASSWORD=") >= 0:
            config_WiFi.PASSWORD = val
        elif arg.find("OWL_IP=") >= 0:
            config_WiFi.OWL_IP = val
        elif arg.find("OWL_SUBNET=") >= 0:
            config_WiFi.OWL_SUBNET = val
        elif arg.find("OWL_GATEWAY=") >= 0:
            config_WiFi.OWL_GATEWAY = val
        elif arg.find("OWL_DNS=") >= 0:
            config_WiFi.OWL_DNS = val
        else:
            raise OwlError
    show_config_WiFi_page(server, arg, owl)


def do_get_config_PID(server, arg, owl):
    val = arg2val(arg)
    print('arg, val', arg, val)
    if val is not None:
        if arg.find("azim_pid_tunings=") > 0:
            owl.azim.mover.pid.tunings = val
        elif arg.find("azim_pid_output_limits=") > 0:
            owl.azim.mover.pid.output_limits = val
        elif arg.find("azim_pid_output_pads=") > 0:
            owl.azim.mover.pid.output_pads = val

        elif arg.find("elev_pid_tunings=") > 0:
            owl.elev.mover.pid.tunings = val
        elif arg.find("elev_pid_output_limits=") > 0:
            owl.elev.mover.pid.output_limits = val
        elif arg.find("elev_pid_output_pads=") > 0:
            owl.elev.mover.pid.output_pads = val
    show_config_PID_page(server, arg, owl)


def do_get_debug(server, arg, owl):
    #     val = arg2val(arg)
    #     #print('arg, val', arg, val)
    #     if val is not None:
    #         if arg.find("expression=") > 0:
    #             owl.expression = val
    show_debug_page(server, arg, owl)


#--------------------------------------------------------
def do_CW(server, arg, owl):
    owl.azim.angle(round(owl.azim.mover.angle_target() + 1, 1))
    show_index_page(server, arg, owl)
    owl.auto_start = False


def do_CCW(server, arg, owl):
    owl.azim.angle(round(owl.azim.mover.angle_target() - 1, 1))
    show_index_page(server, arg, owl)
    owl.auto_start = False


def do_UP(server, arg, owl):
    owl.elev.angle(round(owl.elev.mover.angle_target() + 1, 1))
    show_index_page(server, arg, owl)
    owl.auto_start = False


def do_DOWN(server, arg, owl):
    owl.elev.angle(round(owl.elev.mover.angle_target() - 1, 1))
    show_index_page(server, arg, owl)
    owl.auto_start = False


def park(server, arg, owl):
    print("Park")
    owl.azim.angle(0)
    owl.elev.angle(0)
    owl.mode = owl.MD_MANUAL
    show_index_page(server, arg, owl)
