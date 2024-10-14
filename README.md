# esp32-LD2461
A radar IoT device built with a Hi-Link HLK-LD2461 board coupled with a LiteOn LTR329 enviroment sensor docked in an ESP32 S3 board implemented with Micropython.

For the first boot from a device, please set manually the serial speed in config.json. The default speed is 9600 baud, but you can set this directily from the file config.json to any different one.

The following is an example of a complete config.json file:
```Json
{"poll_time": 2000, "serial_speed": 9600, "regions": [{"x1": 10, "x0": 10, "x3": 10, "x2": 30, "enabled": 1, "narea": 1, "type": 0, "y0": 40, "y1": 20, "y2": 20, "y3": 20}, {"x1": 49, "x0": 49, "x3": 49, "x2": 78, "enabled": 1, "narea": 2, "type": 0, "y0": 39, "y1": 21, "y2": 21, "y3": 21}, {"x1": -47, "x0": -47, "x3": -47, "x2": -8, "enabled": 0, "narea": 3, "type": 1, "y0": 40, "y1": 25, "y2": 25, "y3": 25}]}
```

If you are interested in designing the JSON message parser or managing MQTT messages in a similar project see https://github.com/marconicivitavecchia/esp32-radar/tree/main
