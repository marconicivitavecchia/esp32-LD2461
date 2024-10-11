# esp32-LD2461
A radar IoT device built with a Hi-Link HLK-LD2461 board coupled with a LiteOn LTR329 enviroment sensor docked in an ESP32 S3 board implemented with Micropython.

For the first boot from a device set manually the serial speed in config.json. The default speed is 9600 baud, but you can set this directily from the file config.json to any different one.

The following is an example of a complete config.json file:
```Json
{"regions": [{"x1": 10, "x0": 10, "x3": 10, "x2": 30, "enabled": 1, "narea": 1, "type": 0, "y0": 40, "y1": 20, "y2": 20, "y3": 20}, {"x1": 49, "x0": 49, "x3": 49, "x2": 78, "enabled": 1, "narea": 2, "type": 0, "y0": 39, "y1": 21, "y2": 21, "y3": 21}, {"x1": 0, "x0": 0, "x3": 0, "x2": 0, "enabled": 0, "narea": 3, "type": 0, "y0": 0, "y1": 0, "y2": 0, "y3": 0}], "serial_speed": 9600}
```
