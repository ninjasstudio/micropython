# WiFi.py
'''
Время загрузки:
Mikrotik mAP ~ 35-45c
Mikrotik RB953GS-5HnT(СРШ-5000) ~ 40c (без Mikrotik mAP)
Mikrotik RB953GS-5HnT(СРШ-5000) ~ 60-70c (последовательно через Mikrotik mAP PoE)
Mikrotik RBM33G(СРШ-5000) ~ 45c (без Mikrotik mAP)
Mikrotik RBM33G(СРШ-5000) ~ 55c (последовательно через Mikrotik mAP PoE) 
Mikrotik Drone ~ 45-60c
ESP32 ~ 30-60c
'''
from gc import collect

collect()

from network import WLAN, STA_IF, AP_IF
from utime import ticks_ms, ticks_diff, sleep_ms
from machine import idle
from ubinascii import hexlify
from network_msg import wlan_status, authmode, rssi
from sys import print_exception
collect()

CONNECTING_PAUSE_S = 1  # seconds
ATTEMPTS = 30  # ATTEMPTS * CONNECTING_PAUSE_S = 30 * 1 = 30s

wlan_ap = WLAN(AP_IF)
wlan_st = WLAN(STA_IF)


def WiFi_sta_stop():
    wlan = WLAN(STA_IF)
    try:
        wlan.disconnect()
    except:
        pass
    try:
        wlan.active(False)
    except:
        pass
    print('WiFi station is disconnected and deactivated')
    return wlan


def save_config_WiFi(ssid, password, ifconfig):
    try:
        print("Save './config_WiFi.py'")
        with open("./config_WiFi.py", "w") as f:
            f.write(f"SSID = '{ssid}'\n")
            f.write(f"PASSWORD = '{password}'\n")
            f.write(f"OWL_IP = '{ifconfig[0]}'\n")
            f.write(f"OWL_SUBNET = '{ifconfig[1]}'\n")
            f.write(f"OWL_GATEWAY = '{ifconfig[2]}'\n")
            f.write(f"OWL_DNS = '{ifconfig[3]}'\n")
            f.close()
    except BaseException as e:
        print_exception(e)
        print('Error writing config_WiFi.py')

def WiFi_check_before(ssid, password, ip="192.168.4.1", subnet="255.255.255.0", gateway="192.168.4.1", dns="0.0.0.0"):
    wlan = WLAN(STA_IF)
    wlan.active(True)
    ifconfig = wlan.ifconfig()
    wlan_isconnected = wlan.isconnected()
    if wlan_isconnected:
        if wlan.config('essid') != ssid:
            while wlan.isconnected():
                wlan.disconnect()
                idle()  # save power while waiting
                sleep_ms(200)
            print(f"WiFi disconnected form SSID:{wlan.config('essid')})")
            wlan_isconnected = False
        elif ifconfig != (ip, subnet, gateway, dns):
            while wlan.isconnected():
                wlan.disconnect()
                idle()  # save power while waiting
                sleep_ms(200)
            print(f"WiFi disconnected because:\n{ifconfig} != \n{(ip, subnet, gateway, dns)})")
            wlan_isconnected = False
    return wlan_isconnected

def WiFi_check_after(wlan_isconnected, ssid, password, ip="192.168.4.1", subnet="255.255.255.0", gateway="192.168.4.1", dns="0.0.0.0"):
    wlan = WLAN(STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        wlan_ap.active(False)
        
        ifconfig = wlan.ifconfig()
        if ip != 'dhcp':
            print()
            if ifconfig[0] != ip:
                print('ifconfig[0] != ip', ifconfig[0], '!=', ip)
            if ifconfig[1] != subnet:
                print('ifconfig[1] != subnet', ifconfig[1], '!=', subnet)
            if ifconfig[2] != gateway:
                print('ifconfig[2] != gateway', ifconfig[2], '!=', gateway)
            if ifconfig[3] != dns:
                print('ifconfig[3] != dns', ifconfig[3], '!=', dns)
        
        if not wlan_isconnected:
            print()
            print('ESP mac:', hexlify(wlan.config('mac'), ':').decode("utf-8").upper())
            print(f"Connected to WiFi '{ssid}'")
            print("wlan.ifconfig():", wlan.ifconfig())
            try:
                print("wlan.status('rssi')", rssi(wlan.status('rssi')))
            except:
                pass
            print("wlan.status():", wlan_status(wlan.status()))

            #print('essid:', wlan.config('essid'))
            #print('password:', wlan.config('password'))

            #print('channel:', wlan.config('channel'))
            #print('hidden:', wlan.config('hidden'))
            #print('authmode:', wlan.config('authmode'))
            #print('dhcp_hostname:', wlan.config('dhcp_hostname'))

            print("wlan.isconnected():", wlan.isconnected())

            save_config_WiFi(ssid, password, ifconfig)
    
def WiFi_login(ssid, password, ip="192.168.4.1", subnet="255.255.255.0", gateway="192.168.4.1", dns="0.0.0.0"):
    # Enable station interface and connect to WiFi access point
    wlan = WLAN(STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        # print("Connecting to network '{ssid}'")
        # wlan.config(reconnects=10)
        if ip == 'dhcp':
            wlan.ifconfig(('dhcp'))
        else:
            wlan.ifconfig((ip, subnet, gateway, dns))
        if ssid is None:
            try:
                wlan.connect()
            except:
                pass
        else:
            try:
                wlan.connect(ssid, password)
            except:
                pass
    return wlan

def WiFi_while(ssid, password, ip="192.168.4.1", subnet="255.255.255.0", gateway="192.168.4.1", dns="0.0.0.0"):
    wlan_isconnected = WiFi_check_before(ssid, password, ip, subnet, gateway, dns)
    i = 0
    t = 0
    wlan = WLAN(STA_IF)
    while (wlan.status() != 1010) and (i < ATTEMPTS):
        if ticks_diff(ticks_ms(), t) > CONNECTING_PAUSE_S * 1000:
            i += 1
            print()
            print(f"Connecting to network '{ssid}'")
            #print("ifconfig:", (ip, subnet, gateway, dns))
            print("ifconfig:", wlan.ifconfig())
            print("wlan.status():", wlan_status(wlan.status()), end ='')
            print(f" : WiFi connecting timeout is {CONNECTING_PAUSE_S} seconds, attempt {i} of {ATTEMPTS}.)")
            t = ticks_ms()
            
            WiFi_login(ssid, password, ip, subnet, gateway, dns)
            
        idle()  # save power while waiting
        sleep_ms(250)
        
    WiFi_check_after(wlan_isconnected, ssid, password, ip, subnet, gateway, dns)
        
    if not wlan.isconnected():
        wlan.active(False)  # перестраховка
        print(f"Can not connect to the WiFi '{ssid}'")
        wlan = wlan_ap
        wlan.active(True)
        #wlan_ap.config(essid=ap_ssid, password=ap_password, authmode=ap_authmode)
        ssid = wlan.config('essid')
        print(f"Starting as access point '{ssid}'")
        # wait_connection(ssid)
    
    return wlan

def WiFi_start():
    # Set login parameter here
    try:
        import config_WiFi
        SSID = config_WiFi.SSID
        PASSWORD = config_WiFi.PASSWORD
        IP = config_WiFi.OWL_IP
        SUBNET = config_WiFi.OWL_SUBNET
        GATEWAY = config_WiFi.OWL_GATEWAY
        DNS = config_WiFi.OWL_DNS
        del config_WiFi
        return WiFi_while(SSID, PASSWORD, IP, SUBNET, GATEWAY, DNS)
    except ImportError as e:
        #print(e)
        print_exception(e)

def host(host=""):
    if host in ("", "localhost", "127.0.0.1", "127.0.0.0/8", "0.0.0.0"):
        wlan = WLAN(STA_IF)
        if not wlan.isconnected():
            wlan = WLAN(AP_IF)
        return wlan.ifconfig()[0]
    else:
        return host


# ===============================================================================
if __name__ == "__main__":
    print("WiFi:")
    print(f'AP: active()={wlan_ap.active()}, isconnected()={wlan_ap.isconnected()}, status={wlan_status(wlan_ap.status())}, ifconfig={wlan_ap.ifconfig()}')
    print(f'STA: active()={wlan_st.active()}, isconnected()={wlan_st.isconnected()}, status={wlan_status(wlan_st.status())}, ifconfig={wlan_st.ifconfig()}')
    
    #wlan = WiFi_sta_stop()
    
    wlan = WiFi_start()
    if wlan_st.active():
        print()
        print("WiFi scan()...")
        wireless_networks = wlan.scan()
        if len(wireless_networks):
            print("wlan.scan(): (ssid, bssid, channel, rssi(dBm), authmode, hidden)")
        for e in wireless_networks:
            print(e, end='')
            print(f"| RSSI={e[3]}dBm:{rssi(e[3])} | authmode={authmode(e[4])}")
            print(f"| bssid='{e[1]).decode("utf-8")}' | RSSI={hexlify(e[3]}dBm:{rssi(e[3])} | authmode={authmode(e[4])}")
