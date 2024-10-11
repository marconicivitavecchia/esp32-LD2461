#WIFI_SSID = "sensori"
#WIFI_PASSWORD = "sensori2019"
#WIFI_SSID = "Galaxy A54 5G 1BFE"
#WIFI_PASSWORD = "7y3fbbivw6db26y"
#WIFI_SSID = "RedmiSeb"
#WIFI_PASSWORD = "pippo2503"
#WIFI_SSID = "WebPocket-E280"
#WIFI_PASSWORD = "dorabino.7468!"
#WIFI_SSID = "casafleri"
#WIFI_PASSWORD = "fabseb050770250368120110$"
WIFI_SSID = "D-Link-6A30CC"
WIFI_PASSWORD = "FabSeb050770250368120110"
MQTT_CLIENT_ID = "radar-01"
# The main broker is the preferred broker
# The backup broker is choosen only when the main broker is unavailable
# If the backup broker is active, the main broker is periodically tested and
# selected if again avalilable
# The same behaviour is applied by the IoT device
MQTT_BROKER1 = "proxy.marconicloud.it"
MQTT_BROKER2 = "broker.emqx.io"
NTP_SERVER = '3.pool.ntp.org'
MQTT_USER = ""
MQTT_PASSWORD = ""
MQTT_PUSHTOPIC = "radar/misure"
MQTT_CMDTOPIC = "radar/comandi"
MQTT_STATETOPIC = "radar/stato"