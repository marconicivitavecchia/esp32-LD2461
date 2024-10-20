from machine import UART
from machine import reset as machine_reset
from bme680 import *
from utils import *


# Manage debug
import esp

esp.osdebug(None)  # turn off vendor O/S debugging messages
# esp.osdebug(0)          # redirect vendor O/S debugging messages to UART(0)

# Run Garbage Collector
import gc
import machine
gc.collect()
from config import *
import ujson
import time
import ntptime
from machine import deepsleep
from umqtt.simple import MQTTClient
from machine import Pin, SoftI2C
import utime
from collections import OrderedDict
import json
from ld2461 import *
from adafruit_ltr329_ltr303 import LTR329
from movingStatistics2 import *

S_ON = Pin(42, Pin.OUT) # PIN RADAR POWER MENAGEMENT
S_ON.value(1)
Pin(18, Pin.IN, Pin.PULL_UP)
#Pin(17, Pin.IN, Pin.PULL_UP)
# Serial configuration
print("Configuring serial...")
# Carica la configurazione all'avvio
default_config = {
    'poll_time': 2000,
    'serial_speed': 9600,
    'regions': [
        {"enabled": 0, "narea": 0, "type": 0, "x0": 0, "y0": 0, "x1": 0, "y1": 0, "x2": 0, "y2": 0, "x3": 0, "y3": 0},
        {"enabled": 0, "narea": 1, "type": 0, "x0": 0, "y0": 0, "x1": 0, "y1": 0, "x2": 0, "y2": 0, "x3": 0, "y3": 0},
        {"enabled": 0, "narea": 2, "type": 0, "x0": 0, "y0": 0, "x1": 0, "y1": 0, "x2": 0, "y2": 0, "x3": 0, "y3": 0}
    ]
}

config = load_config('config.json')# in utils
if config:
    pollTime = config.get('poll_time')
    if not pollTime:
        config.update({"poll_time": 2000})
        pollTime = config.get('poll_time')
        save_config('config.json',config)
    pollTime = int(pollTime)
       
    radarvel = config.get('serial_speed')
    if not radarvel:
        config.update({"serial_speed": 9600})
        radarvel = config.get('serial_speed')
        save_config('config.json',config)
    radarvel = int(radarvel) 
        
    print("radarvel ", radarvel)
    print("pollTime ", pollTime)
else:
    # Configurazione di default
    save_config('config.json', default_config)
    config = default_config
    print("DEFAULT radar_config: ", default_config)
    
radaregions = config.get('regions', default_config)
#test_speeds = [9600, 19200, 38400, 57600, 115200, 230400, 256000, 460800]
#for speed in test_speeds:
#radarvel = 115200 # CAMBIA QUESTA VELOCITA'. Quando hai trovato la imposti nella pagina e poi commenti la riga
S_ON.value(1)
time.sleep(0.5)
lista_x = []
lista_y = []
lista_n = []

print('Baud rate', radarvel)
def my_callback(code, val, len):
    global lista_x
    global lista_y
    global filter_x
    global filter_y
    global lista_n
    
    newlen = 0
    #print('Len: ', len)
    if code == 0x06:
        print('Callback get_regions!')
        pubStateAtt("regions", val)
    elif code == 0x07:
        #print('Callback get_coordinates!')
        mode = radar.get_stateFromRAM()
        if mode != 2:
            if filter_x.getNumSensors() != len:                
                filter_x = MovingStatistics(window_size=10, num_sensors=len, alpha=0.125, quantile=0.5, quantile_low=0.25, quantile_high=0.75)
                filter_y = MovingStatistics(window_size=10, num_sensors=len, alpha=0.125, quantile=0.5, quantile_low=0.25, quantile_high=0.75)
            lista_x = filter_x.update(val.get('lista_x', []), ['emafilter']).get('emafilter')
            lista_y = filter_y.update(val.get('lista_y', []), ['emafilter']).get('emafilter')
    elif code == 0x08:
        #print('Callback get_num_targets! ', val )
        mode = radar.get_stateFromRAM()
        if mode != 1:
            lista_n = val             
    elif code == 0x03:
        print('Callback get_reporting type!')
        pubStateAtt("radarmode", val)
    elif code == 0x02:
        mode = radar.get_stateFromRAM()
        print(f'Radar set mode feedback: {mode}')
        if mode == 1:
            lista_n = []
        elif mode == 2:
            lista_x = []
            lista_y = []
            filter_x = MovingStatistics(window_size=10, num_sensors=len, alpha=0.125, quantile=0.5, quantile_low=0.25, quantile_high=0.75)
            filter_y = MovingStatistics(window_size=10, num_sensors=len, alpha=0.125, quantile=0.5, quantile_low=0.25, quantile_high=0.75)        
        pubStateAtt("radarmode", mode)
    elif code == 0x09:
        print('Callback get_FW!')
        pubStateAtt("fw", val)
    elif code == 0x0A:
        print('Callback set radar_factory!')
        if val:
            pubStateAtt("radarfactory", val)
    elif code == 0x01:
        print('Callback set baudrate!')
        scrivi_servel(val)
        pubStateAtt("servel", val)
        
radar = LD2461(17, 18, radarvel, my_callback)    
# Sensor configuration
print("Configuring sensor...")
time.sleep(0.1)
i2c = SoftI2C(scl=Pin(14),sda=Pin(13))
#i2c = I2C(-1, sda=Pin(13), scl=Pin(14))
print('Scan i2c bus...')
devices = i2c.scan()
bme = BME680_I2C(i2c=i2c, address=0x76)
time.sleep(1)
radar.read_all_info(radaregions)# sovra
time.sleep(0.1)

# Partial JSON of the single states that are retrieved in PULL mode from the web interface
# upon receipt of a status request command
def pubStateAtt(att, val):
     timestamp = getTimestamp()
     message = ujson.dumps(
        {
            "state": {
                att: val,
            },
            "boardID": esp32_unique_id,
            "timestamp": timestamp,
        }
     )
     print(f"Reporting to MQTT topic {MQTT_STATETOPIC}: {message}")
     client.publish(MQTT_STATETOPIC, message)
    
def getAllState():
     radar.get_reporting()
     time.sleep(0.05)
     radar.get_version()
     time.sleep(0.05)
     radar.get_regions()
     time.sleep(0.05)
     
     timestamp = getTimestamp()
     polltimeval = pollTime
     rstate = "on" if S_ON.value() else "off"
     message = ujson.dumps(
        {
            "state": {
                #"fw": fwval,
                "servel": radarvel,
                "polltime": polltimeval,
                "radarstate": rstate,
                #"radarmode": reportype,
                "radarfactory": 1,
                #"regions": regions,
            },
            "boardID": esp32_unique_id,
            "timestamp": timestamp,
        }
     )
     print(f"Reporting AllState to MQTT topic {MQTT_STATETOPIC}: {message}")
     client.publish(MQTT_STATETOPIC, message)

# Callback function to manage incoming messages
def sub_cb(topic, msg):
    print("Message received on topic %s: %s" % (topic, msg))
    try:
        # Decodifica il messaggio JSON
        data = ujson.loads(msg)
        print(data) 
        if data['boardID'] == MY_MQTT_CLIENT_ID:
            # Processa il JSON per eseguire i comand
            ms = ["write"]
            process_json(command_map, data, [], ms)
            #process_json(command_map, data)
    except ValueError as e:
        print("Errore di decodifica JSON:", e)

def readFW():
    global radar
    data = None
    data = radar.get_versionFromRAM()
    return data    
        
def setBaudRate(rate):
   radar.set_baud_rate(int(rate))
       
def scrivi_radarToggle(val):
    if S_ON.value():
        S_ON.value(0)
    else:
        S_ON.value(1)
    leggi_radarState()
    lista_x = []
    lista_y = []
    lista_n = []
    filter_x = MovingStatistics(window_size=10, num_sensors=len, alpha=0.125, quantile=0.5, quantile_low=0.25, quantile_high=0.75)
    filter_y = MovingStatistics(window_size=10, num_sensors=len, alpha=0.125, quantile=0.5, quantile_low=0.25, quantile_high=0.75)        
# Funzioni di comando

def scrivi_pollTime(valore):
    global pollTime
    print(f"Scrivi pollTime a {valore}")
    pollTime = valore
    leggi_pollTime()

def scrivi_servel(valore):
    global radarvel
    radarvel = int(valore)
    print(f"Scrivi servel a {valore}")
    config['serial_speed'] = radarvel
    save_config('config.json', config)  
    #setBaudRate(radarvel)

def scrivi_radarMode(valore):
    print(f"Scrivi radarMode a {valore}")
    radar.set_reporting(int(valore))

def scrivi_radarFactory(valore):
    print(f"Scrivi radarFactory a {valore}")
    radar.restore_factory()
    radarvel = 9600
    config = default_config
    save_config('config.json', config)

def disable_region(area): #0x02
    r = radar.disable_region(area)
    config['regions'] = r
    save_config('config.json', config)
    leggi_regioni()
    
def disable_all_region(): #0x02
    r = radar.disable_all_regions()
    config['regions'] = r
    save_config('config.json', config)
    leggi_regioni()

def delete_all_regions(val):    
     r = radar.delete_all_regions()# imposta le regioni di default nel dispositivo
     save_config('config.json', config)# imposta le regioni di default nella MCU 
     leggi_regioni()
     
def enable_region(area): #0x02
    r = radar.enable_region(area)# restituisce TUTTE le regioni sul dispositivo
    config['regions'] = r
    save_config('config.json', config)# sincronizza le regioni sulla MCU con quelle MODIFICATE sul dispositivo
    leggi_regioni()

def scrivi_regioni(val):
    print("Scrivi regioni")
    val2 = radar.set_region(val)# restituisce TUTTE le regioni sul dispositivo
    config['regions'] = val2
    save_config('config.json', config)# sincronizza le regioni sulla MCU con quelle MODIFICATE sul dispositivo
    leggi_regioni()
# FEEDBACKS ---------------------------------------------------------------------------------------------------
def leggi_radarState():
    print("Leggi radarstate")
    pubStateAtt("radarstate", "on" if S_ON.value() else "off")
    
def leggi_regioni():
    print("Leggi regioni")
    val = radar.get_regionsFromRAM()
    pubStateAtt("regions", val)
    
def leggi_radarfw():
    global radarFW
    print("Leggi radarfw")
    val = readFW()
    pubStateAtt("fw", val)

def leggi_servel():
    global radarvel
    print("Leggi servel")
    pubStateAtt("servel", radarvel)

def leggi_pollTime():
    global pollTime
    print("Leggi pollTime")
    pubStateAtt("polltime", pollTime)

def leggi_radarMode():
    print("Leggi radarMode")
    val = radar.get_stateFromRAM()
    pubStateAtt("radarmode", val)
    
   
# Map of the functions to be executed on a certain path of the received commands (statuses).
# They must coincide with the corresponding paths of the JSON object being transmitted.
# Read-only commands are parameterless and can be invoked in JSON as cells in a command list. For example, with JSON
# "configs": {
#   "read": ["polltime", "servel"]
# }
# but they must be stored as field-value pairs of an object because in Python dictionary arrays are encoded as objects.
# Write-only commands are parameterized and must be invoked in JSON as field, value pairs. For example, with JSON
# "configs": {
# 	"write":{
# 		"polltime": 1
# 		"servel": defaultrate
# 	},
# }
command_map = {
    #"boardID": check_id,
    "config": {
        "write": {# commands whose reception causes a configuration action on the system
            "polltime": scrivi_pollTime,
            "servel": setBaudRate,
            "radarmode": scrivi_radarMode,
            "radarfactory": scrivi_radarFactory,
            "radartoggle": scrivi_radarToggle,
            "areaenable": enable_region,
            "areadisable": disable_region,
            "areareset": delete_all_regions,
            "region": scrivi_regioni,
        },
        "read": {# commands whose reception causes the sending of a system status
            "radarfw": leggi_radarfw,
            "servel": leggi_servel,
            "polltime": leggi_pollTime,
            "radarmode": leggi_radarMode,
            "allstate": getAllState,
            "radarstate": leggi_radarState,
            "regions": leggi_regioni,
        }
    }
}

if len(devices) == 0:
  print("No i2c device !")
else:
  print('i2c devices found:',len(devices))

  for device in devices:  
    print("Decimal address: ",device)

  for _ in range(3):
    print(bme.temperature, bme.humidity, bme.pressure, bme.gas)
    time.sleep(1)
    

i = 0
ok = False
temp = bme.temperature
press = bme.pressure
hum =  bme.humidity
gas = bme.gas

t1 =DiffTimer()
t2 =DiffTimer2()
t3 =DiffTimer2()
t4 =DiffTimer2()
t1.start()
t2.setBase(500)
t2.start()
t3.setBase(500)
t3.start()
#t4.setBase(500)
#t4.stop()

sensor = LTR329(i2c)
ch0, ch1, lux_ch0, lux_ch1, total_lux = sensor.get_lux()
print("Canale 0 (luce visibile):", ch0, "lux")
print("Canale 1 (luce infrarossa):", ch1, "lux")
print("Lux luce visibile:", lux_ch0, "lux")
print("Lux luce infrarossa:", lux_ch1, "lux")
print("Lux totale:", total_lux, "lux")

# Costante di smoothing per la media esponenziale pesata (0 < alpha <= 1)
alpha = 0.125
beta = 0.25
#pollTime = 2000

while not ok:
    try:
        # WiFi configuration
        print(f"Connecting to WiFi {WIFI_SSID}...", end="")
        (ip, wlan_mac, sta_if) = wifi_connect(WIFI_SSID, WIFI_PASSWORD)
        print(" Connected!")
        print(f"ip: {ip}, mac: {bin2hex(wlan_mac)}")
        esp32_unique_id = MQTT_CLIENT_ID + bin2hex(wlan_mac)
        # MQTT init
        #MQTT_CLIENT_ID_RND = MQTT_CLIENT_ID + random_string()
        MY_MQTT_CLIENT_ID = MQTT_CLIENT_ID + str(bin2hex(wlan_mac))#+":"+ random_string()
        client1 = MQTTClient(MY_MQTT_CLIENT_ID, MQTT_BROKER1, user=MQTT_USER, password=MQTT_PASSWORD)
        client2 = MQTTClient(MY_MQTT_CLIENT_ID, MQTT_BROKER2, user=MQTT_USER, password=MQTT_PASSWORD)
        # Imposta la funzione di callback per la sottoscrizione
        client1.set_callback(sub_cb)
        client2.set_callback(sub_cb)        
        time.sleep(0.5)
        ntptime.host = NTP_SERVER
        ntptime.timeout = 5
        ntptime.settime()
        lastTimeUpdate = time.time()
        interval = 60*60*5
        print("NTP connected.")
        ok = True
    except OSError as e:
        print(e)
        i += 1
        time.sleep(i)

# Prova a connettersi al primo broker
print("Connecting to primary broker...")
client = client1
if not connect_and_subscribe(client1, MQTT_CMDTOPIC):
    print("Switching to backup broker...")
    connect_and_subscribe(client2, MQTT_CMDTOPIC)
    client = client2

time.sleep(0.5)
#ema = MovingStatistics(window_size=10, num_sensors=3, alpha=0.125)
filter_x = MovingStatistics(window_size=10, num_sensors=5, alpha=0.125, quantile=0.5, quantile_low=0.25, quantile_high=0.75)
filter_y = MovingStatistics(window_size=10, num_sensors=5, alpha=0.125, quantile=0.5, quantile_low=0.25, quantile_high=0.75)
#radar.read_all_info(config)

while True:
    radar.loop()
    try:            
        client = check_and_process_messages(client, client1, client2, MQTT_CMDTOPIC)
        if t1.get() > 500:
            #print('t2',t2.peek())
            t1.reset()
            
            # The main broker is the preferred broker
            # The backup broker is choosen only when the main broker is unavailable
            # If the backup broker is active, the main broker is periodically tested and
            # selected if again avalilable
            # The same behaviour is applied by the IoT device
            if t3.update() > 60000:
                t3.reset()
                if  client == client2:
                    print("Tentativo di riconnessione su broker 1")
                    if connect_and_subscribe(client1, MQTT_CMDTOPIC):
                        client = client1
                        print("Riconnessione su broker 1 avvenuta con successo")
                            
            if t2.update() >= pollTime:
                #print('Time: ',t2.peek())
                t2.reset()
                print('Acceso',S_ON.value())
                
                if not sta_if.isconnected():
                    (ip, wlan_mac, sta_if) = wifi_connect(WIFI_SSID, WIFI_PASSWORD)
                    time.sleep(1)
                    client.connect()
                if time.time() - lastTimeUpdate > interval:
                    lastTimeUpdate = time.time()
                    ntptime.settime()
                    print('NTP time updated.')
                                
                if False:
                    temp = 1
                    press = 1
                    hum =  1
                    gas = 1
                else:
                    temp = bme.temperature
                    press = bme.pressure
                    hum =  bme.humidity
                    gas = bme.gas
                    
                ch0, ch1, lux_ch0, lux_ch1, total_lux = sensor.get_lux()               
                visible = lux_ch0
                infrared = lux_ch1
                total = total_lux
                
                #if S_ON.value():
                #    radar.flushUart()
                #    data = radar.printTargets()
                                    
                timestamp = getTimestamp()
                
                # Json of the measurements sent in push mode to the MQTT broker
                message = ujson.dumps(
                    {
                        "measures":{
                            "tempSensor": {
                                "temp": temp,
                                "press": press,
                                "hum": hum,
                                "gas": gas,
                            },
                            "luxSensor": {
                                "visible": visible,
                                "infrared": infrared,
                                "total": total,
                            },
                            "radar": {
                                "x": round_2(lista_x),
                                "y": round_2(lista_y),
                                "n": lista_n,
                            },
                        },
                        "boardID": esp32_unique_id,
                        "timestamp": timestamp,
                    }   
                )
               
                print(f"Reporting to MQTT topic {MQTT_PUSHTOPIC}: {message}")
                # mqtt message publishing
                client.publish(MQTT_PUSHTOPIC, message)                             
                #S_ON.value(0)
        """
        if t4.update() > 1000:
            print("Riacceso radar")
            t2.stop()
            S_ON.value(1)
        """
    except ValueError as ve:
        print(ve)
    except OSError as e:
                print(e)    
            #time.sleep(5)
