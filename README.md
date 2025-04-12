# esp32-LD2461
A radar IoT device built with a Hi-Link HLK-LD2461 board coupled with a LiteOn LTR329 enviroment sensor docked in an ESP32 S3 board implemented with Micropython.

For the first boot from a device, please set manually the serial speed in config.json. The default speed is 9600 baud, but you can set this directily from the file config.json to any different one.

The following is an example of a complete config.json file:
```Json
{"poll_time": 2000, "serial_speed": 256000, "regions": [{"enabled": 0, "narea": 1, "points": [], "shape": 0, "radarmode": 1, "type": 0}, {"enabled": 0, "narea": 2, "points": [], "shape": 0, "radarmode": 1, "type": 0}, {"enabled": 0, "narea": 3, "points": [], "shape": 0, "radarmode": 1, "type": 0}, {"enabled": 0, "narea": 4, "points": [], "shape": 0, "radarmode": 1, "type": 0}, {"enabled": 0, "narea": 5, "points": [], "shape": 0, "radarmode": 1, "type": 0}, {"enabled": 0, "narea": 6, "points": [], "shape": 0, "radarmode": 1, "type": 0}, {"enabled": 0, "narea": 7, "points": [], "shape": 1, "radarmode": 1, "type": 0}, {"enabled": 0, "narea": 8, "points": [], "shape": 1, "radarmode": 1, "type": 0}, {"enabled": 0, "narea": 9, "points": [], "shape": 1, "radarmode": 1, "type": 0}]}

```

If you are interested in designing the JSON message parser or managing MQTT messages in a similar project see https://github.com/marconicivitavecchia/esp32-radar/tree/main
