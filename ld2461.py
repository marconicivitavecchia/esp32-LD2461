from machine import UART, Pin
import time
import struct

# Costanti per il frame e comandi
FRAME_HEADER = b'\xFF\xEE\xDD'  # Valori aggiornati
FRAME_END = b'\xDD\xEE\xFF'  # Valori aggiornati
FH_LAST = 0xDD
FE_LAST = 0xFF

# Comandi specifici per HLK-LD2461
SET_BAUDRATE = 0x01
SET_REPORTING = 0x02
GET_REPORTING = 0x03
SET_REGIONS = 0x04
DISABLE_REGIONS = 0x05
GET_REGIONS = 0x06
GET_COORDINATES = 0x07
GET_NUM_TARGETS = 0x08
READ_FIRMWARE = 0x09
RESTORE_FACTORY = 0x0A

class LD2461:
    def __init__(self, tx_pin, rx_pin, baudrate=115200, callback=None):
        self.uart = UART(1, baudrate=baudrate, tx=Pin(tx_pin), rx=Pin(rx_pin))
        self.serial_data = {'buffer': bytearray(), 'size': 0, 'frame_start': 0}
        self.person = [{'x': 0, 'y': 0} for _ in range(5)]
        self.person_before = [{'x': 0, 'y': 0} for _ in range(5)]
        self.presence_millis = [0 for _ in range(5)]
        self.presence_timeout = 30  # Timeout in secondi, modifica a seconda delle esigenze
        self.callback = callback
        self.state = 0
        self.persons = [
            {"x": 0.0, "y": 0.0},
            {"x": 0.0, "y": 0.0},
            {"x": 0.0, "y": 0.0},
            {"x": 0.0, "y": 0.0},
            {"x": 0.0, "y": 0.0}
        ]
        self.regions = [
            {"enabled": 0, "narea": 1, "type": 0, "x0": 0, "y0": 0, "x1": 0, "y1": 0, "x2": 0, "y2": 0, "x3": 0, "y3": 0},
            {"enabled": 0, "narea": 2, "type": 0, "x0": 0, "y0": 0, "x1": 0, "y1": 0, "x2": 0, "y2": 0, "x3": 0, "y3": 0},
            {"enabled": 0, "narea": 3, "type": 0, "x0": 0, "y0": 0, "x1": 0, "y1": 0, "x2": 0, "y2": 0, "x3": 0, "y3": 0}
        ]
        self.ntargets = [
            {"n": 0.0},
            {"n": 0.0},
            {"n": 0.0}
        ]
        
        self.fw = [
            0,
            0
        ]
        self.baudrate = 9600
        self.candidate_brate = 9600
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin

    def setup(self):
        time.sleep_ms(1000)
        self.read_all_info()

    def update(self):# non necessario!
        self.report_position()
        
    def loop(self):
        if self.uart.any():
            c = self.uart.read(1)[0]
            self.serial_data['buffer'].append(c)
            self.serial_data['size'] += 1

            if c == FH_LAST:
                if self.serial_data['buffer'][-len(FRAME_HEADER):] == FRAME_HEADER:
                    #print(f'Header trovato: {FRAME_HEADER}')  # Stampa di debug per il tail trovato
                    self.serial_data['frame_start'] = self.serial_data['size']

            elif c == FE_LAST:
                if self.serial_data['buffer'][-len(FRAME_END):] == FRAME_END:
                    #print(f'Tail trovato: {FRAME_END}')  # Stampa di debug per il tail trovato
                    self.process_frame()
            #else:
                #print(f'Header NON trovato: {self.serial_data['buffer'][-len(FRAME_HEADER):]}')
                
                

    def process_frame(self):
        frame_size = 2; # dopo inizia il campo command
        frame_data = self.serial_data['buffer'][self.serial_data['frame_start']:]
            
        command = frame_data[frame_size]
        len = self.from_unsigned_bytes_big(frame_data[0:2])
        
        #print(f'cmd0: {command}')
        #print(f'len0: {frame_data[1]}')
        
        if command == GET_REGIONS:
            self.process_regions(frame_data)# from request: get_regions()
        elif command == GET_COORDINATES:
            self.process_coordinates(frame_data)# NO REQUEST, the module takes the initiative to report the data, and the format
        elif command == GET_NUM_TARGETS:
            self.process_occurrences(frame_data)# NO REQUEST, the module takes the initiative to report the data, and the format
        elif command == GET_REPORTING:
            self.process_reporting(frame_data)# from request: get_reporting()
        elif command == READ_FIRMWARE:
            self.process_read_firmware(frame_data)# from request: get_version()
        else:
            if command == RESTORE_FACTORY:
                ok = frame_data[2:3]
                self.callback(command, ok , 1)
            if command == SET_BAUDRATE:
                ok = frame_data[3] # offset = 3 for ack
                if ok:
                    self.baudrate = self.candidate_brate
                    self.uart = UART(1, baudrate=self.baudrate, tx=Pin(self.tx_pin), rx=Pin(self.rx_pin))
                self.callback(command, self.baudrate , 2)
            if command == SET_REPORTING:
                ok = frame_data[2:3]
                self.callback(command, ok , 1)

        # Resetta il buffer
        #self.serial_data['buffer'].clear()
        self.serial_data['buffer'][:] = b''  # Svuota il bytearray mantenendo lo stesso riferimento
        self.serial_data['size'] = 0
        self.serial_data['frame_start'] = 0
        
    def get_baudrate(self, frame_data):
        return self.baudrate

    def process_regions(self, frame_data):# 0x06
        # Logica per processare i dati in risposta delle regioni 
        # Logica per processare i dati in risposta delle coordinate
        result = {
            'narea': [],
            'type': [],
            'enabled': [],
            'x0': [],
            'y0': [],
            'x1': [],
            'y1': [],
        }
        print('frame_data', self.to_hex_string(frame_data), 'len', len(frame_data) if frame_data is not None else 0)
        offset = 3
        for i in range(3):  # Ciclo per 3 regioni
            base_index = i * 10 + offset # Calcola l'indice base per ogni gruppo di 8 byte
            narea = int(frame_data[base_index])
            index = i # Indice array di dizionari
            print("index ", index)
            if 0 <= index <= 2:
                self.regions[index]["narea"] = narea
                self.regions[index]["type"] = frame_data[base_index + 1]
                self.regions[index]["x0"] = self.byte_to_signed_integers(frame_data[base_index + 2])
                self.regions[index]["y0"] = self.byte_to_signed_integers(frame_data[base_index + 3])
                self.regions[index]["x1"] = self.byte_to_signed_integers(frame_data[base_index + 4])
                self.regions[index]["y1"] = self.byte_to_signed_integers(frame_data[base_index + 5])
                self.regions[index]["x2"] = self.byte_to_signed_integers(frame_data[base_index + 6])
                self.regions[index]["y2"] = self.byte_to_signed_integers(frame_data[base_index + 7])
                self.regions[index]["x3"] = self.byte_to_signed_integers(frame_data[base_index + 8])
                self.regions[index]["y3"] = self.byte_to_signed_integers(frame_data[base_index + 9])
                result['narea'].append(self.regions[index]["narea"])
                result['type'].append(self.regions[index]["type"])
                result['x0'].append(self.regions[index]["x0"]/10)
                result['y0'].append(self.regions[index]["y0"]/10)
                result['x1'].append(self.regions[index]["x2"]/10)
                result['y1'].append(self.regions[index]["y3"]/10)
                result['enabled'].append(self.regions[index]["enabled"])
                
        self.callback(GET_REGIONS, result, 3)
        
    def get_regionsFromRAM(self):# 0x06
        # Logica per processare i dati in risposta delle regioni 
        result = {
            'narea': [],
            'type': [],
            'enabled': [],
            'x0': [],
            'y0': [],
            'x1': [],
            'y1': [],
        }
        for i in range(3):  # Ciclo per 3 regioni
            result['narea'].append(self.regions[i]["narea"])
            result['type'].append(self.regions[i]["type"])
            result['enabled'].append(self.regions[i]["enabled"])
            result['x0'].append(self.regions[i]["x0"]/10)
            result['y0'].append(self.regions[i]["y0"]/10)
            result['x1'].append(self.regions[i]["x2"]/10)
            result['y1'].append(self.regions[i]["y3"]/10)
                
        self.callback(GET_REGIONS, result, 3)
        return result
        
    def get_regionFromRAM(self, index):# 0x06
        result = {
            'narea': 0,
            'type': 0,
            'enabled': 0,
            'x0': 0,
            'y0': 0,
            'x1': 0,
            'y1': 0,
        }
        result['narea'] = self.regions[index]["narea"]
        result['type'] = self.regions[index]["type"]
        result['enabled'] = self.regions[index]["enabled"]
        result['x0'] = self.regions[index]["x0"]/10
        result['y0'] = self.regions[index]["y0"]/10
        result['x1'] = self.regions[index]["x2"]/10
        result['y1'] = self.regions[index]["y3"]/10
        return result
        
    def process_coordinates(self, frame_data):
        result = {
            'lista_x': [],
            'lista_y': [],
        }
        
        datalen = self.from_unsigned_bytes_big(frame_data[0:2]) - 1#command word
        
        #print(f'datalen: {datalen}')
        #len = self.serial_data['size'] -1
        datalen = int(datalen / 2)
        if datalen > 5:
            datalen = 5
        offset = 3
        #for i in range(datalen):  
            #base_index = i * 4 + offset # Calcola l'indice base per ogni gruppo di 2 byte
            # Estrai 2 byte per 'x' e 'y' correttamente usando slicing
            #self.persons[i]["x"] = self.from_signed_bytes_big(frame_data[base_index:base_index + 2]) / 10
            #self.persons[i]["y"] = self.from_signed_bytes_big(frame_data[base_index + 2:base_index + 4]) / 10
            #result['lista_x'].append(self.persons[i]["x"])
            #result['lista_y'].append(self.persons[i]["y"])
        
        for i in range(datalen):
            base_index = i * 2 + offset # Calcola l'indice base per ogni byte
            self.persons[i]["x"] = self.byte_to_signed_integers(frame_data[base_index])
            self.persons[i]["y"] = self.byte_to_signed_integers(frame_data[base_index+1])
            result['lista_x'].append(self.persons[i]["x"])
            result['lista_y'].append(self.persons[i]["y"])
            
        #print(f'x: {result['lista_x']}')
        #print(f'y: {result['lista_y']}')   
        self.callback(GET_COORDINATES, result, datalen)
        
    def get_coordinatesFromRAM(self):
        result = {
            'lista_x': [],
            'lista_y': [],
        }
        len = len(self.persons)
        for i in range(len):  
            result['lista_x'].append(self.persons[i]["x"])
            result['lista_y'].append(self.persons[i]["y"])
        return result
    
    def process_occurrences(self, frame_data):
        for i in range(3):  # Ciclo per 2 regioni
            base_index = i + 3 # Calcola l'indice base per ogni gruppo di 1 byte
            self.ntargets[i]["n"] = frame_data[base_index]
        self.callback(GET_NUM_TARGETS, [self.ntargets[0]["n"], self.ntargets[1]["n"], self.ntargets[2]["n"]], 3)
        
    def process_reporting(self, frame_data):
        self.state = frame_data[0]
        #print(f'Reporting stae: {self.state}')
        self.callback(GET_REPORTING, self.state, 1)
        
    def process_read_firmware(self, frame_data):
        vernum = self.from_signed_bytes_big(frame_data[0:4])
        id = self.from_signed_bytes_big(frame_data[4:8])
        self.fw = [vernum, id]
        #print(f'Reporting FW: {self.fw}')
        self.callback(READ_FIRMWARE, self.fw, 2)
        
    """
    def report_position(self): # non necessario!
        # Pubblica la posizione della persona rilevata
        for i in range(5):
            if self.person[i]['x'] != 0 and self.person[i]['y'] != 0:
                self.person_before[i] = self.person[i]
        
        # Logica per pubblicare le coordinate (o stamparle)
        print(f"Person 0: X={self.person[0]['x']}, Y={self.person[0]['y']}")
        # Pubblica altre informazioni su altre persone rilevate
    """  
    def send_command(self, command, command_value=None):
        """
        Invia un comando tramite UART con un checksum e un header finale.
        - command: Il comando principale da inviare (come un byte singolo).
        - command_value: Una sequenza opzionale di byte associata al comando.
        """
        command = bytes([command])
        # Invia l'header
        self.uart.write(FRAME_HEADER)
        
        # Lunghezza del comando (comando + valore opzionale)
        cmd_len = 1  # Partiamo da 1 per NON includere `command` e il checksum finale
        if command_value:  # Se c'è un valore di comando, aggiungi la sua lunghezza
            cmd_len += len(command_value)
        
        cmd_len = cmd_len.to_bytes(2, 'big')
        # Converti `cmd_len` in byte e invia
        self.uart.write(cmd_len)
        
        # Invia il comando principale
        self.uart.write(command)
         
        
        #print('cmd_len', self.to_hex_string(cmd_len), 'len', len(cmd_len) if cmd_len is not None else 0)
        #print('command', self.to_hex_string(command), 'len', len(command) if command is not None else 0)
        #print('command_value', self.to_hex_string(command_value), 'len', len(command_value) if command_value is not None else 0)
        
        
        # Inizializza il checksum con il valore del comando (intero)
        check_sum = command[0]  # Usa il valore intero del primo byte di `command`

        # Se c'è un valore associato, invialo e aggiorna il checksum
        if command_value:
            self.uart.write(command_value)
            check_sum += sum(command_value)  # Somma i byte di `command_value`
        
        # Mantieni solo gli ultimi 8 bit del checksum
        check_sum = check_sum & 0xFF  # Usa 0xFF come intero, non bytes
        
        # Invia il checksum (convertito in byte)
        self.uart.write(bytes([check_sum]))

        # Invia il frame end
        self.uart.write(FRAME_END)
        
        msg = FRAME_HEADER + cmd_len + command + (command_value if command_value else b'') + bytes([check_sum])+FRAME_END
               
        #self.uart.write(msg)
        print('msg', self.to_hex_string(msg), 'len', len(msg) if msg is not None else 0)

    
    def read_all_info(self, regions):
        self.regions = regions
        self.get_version()
        time.sleep(0.05)
        self.get_regions()# sovrascrive tutti i campi di regions tranne enabled!
        time.sleep(0.05)
        self.get_reporting()
        time.sleep(0.05)

    def get_version(self):
        byte_sequence =  b'\x01'
        self.send_command(READ_FIRMWARE, byte_sequence)
        
    def get_versionFromRAM(self):
        return self.fw

    def get_regions(self):
        byte_sequence = b'\x01'
        #self.send_command(GET_REGIONS)
        self.send_command(GET_REGIONS, byte_sequence)

    def set_baud_rate(self, baud_rate=256000):
        print("brate: ", baud_rate)
        possible_baud_rates = [9600, 19200, 38400, 57600, 115200, 256000]
        if baud_rate not in possible_baud_rates:
            raise ValueError('The baud rate must be one of the following: 9600, 19200, 38400, 57600, 115200, 256000')   
        
        #baudrate_index = possible_baud_rates.index(baud_rate)
        byte_sequence = baud_rate.to_bytes(3, 'big')
        self.candidate_brate = baud_rate
        self.send_command(SET_BAUDRATE, byte_sequence)

    def set_region(self, v):# 0x04
        """
        v = {
            'narea': 0,
            'type': 0,
            'x0': 0,
            'y0': 0,
            'x1': 0,
            'y1': 0,
        }
        """
        # modifica la sequenza memorizzata sul microcontrollore
        index = int(v["narea"]) - 1

        if index >= 0 and index < 3:
            #self.regions[index] = v
            self.regions[index]["narea"] = int(v["narea"])
            self.regions[index]["type"] = int(v["type"])
            self.regions[index]["enabled"] = int(v["enabled"])
            self.regions[index]["x0"] = self.limit_value(int(float(v["x0"])*10))
            self.regions[index]["y0"] = self.limit_value(int(float(v["y0"])*10))
            self.regions[index]["x1"] = self.limit_value(int(float(v["x0"])*10))
            self.regions[index]["y1"] = self.limit_value(int(float(v["y1"])*10))
            self.regions[index]["x2"] = self.limit_value(int(float(v["x1"])*10))
            self.regions[index]["y2"] = self.limit_value(int(float(v["y1"])*10))
            self.regions[index]["x3"] = self.limit_value(int(float(v["x0"])*10))
            self.regions[index]["y3"] = self.limit_value(int(float(v["y1"])*10))
                 
        if not int(v["enabled"]):
            self.regions[index]["type"] = 0x00
        
        print('regionnew', self.regions[index])
        # Prepara la sequenza di byte in big endian da inviare sulla seriale
        byte_sequence = self.signed_integers_to_bytearray(bytearray([self.regions[index]["narea"],
                               self.regions[index]["x0"], self.regions[index]["y0"],
                               self.regions[index]["x1"], self.regions[index]["y1"],
                               self.regions[index]["x2"], self.regions[index]["y2"],
                               self.regions[index]["x3"], self.regions[index]["y3"],
                               self.regions[index]["type"]]))
        # modifica la sequenza memorizzata sul sensore
        print('byte_sequence', self.to_hex_string(byte_sequence), 'len', len(byte_sequence) if byte_sequence is not None else 0)
        self.send_command(SET_REGIONS, bytes(byte_sequence))# Trasforma un array di byte in uno stream di byte
        return self.regions
        
    def restore_factory(self):
        byte_sequence = bytes([0x01])
        self.send_command(RESTORE_FACTORY, byte_sequence)

    def set_reporting(self, report_format): #0x02
        report_format = int(report_format)
        possible_report_format = [1, 2, 3]
        if report_format not in possible_report_format:
            raise ValueError('The report value must be one of the following: 1, 2, 3')   
        byte_sequence = report_format.to_bytes(1, 'big')
        self.state = report_format
        self.send_command(SET_REPORTING, byte_sequence)

    def get_reporting(self):
        byte_sequence = b'\x01'
        self.send_command(GET_REPORTING, byte_sequence)

    def disable_region(self, narea): #0x02
        index = int(narea) - 1
        if 0 <= index <= 2:
            index = narea - 1 # Indice array di dizionari
            self.regions[index]["enabled"] = 0
            byte_sequence = (int(narea)).to_bytes(1, 'big') 
            self.send_command(DISABLE_REGIONS, byte_sequence)
        return self.regions
    
    def enable_region(self, narea): #0x02
        index = int(narea) - 1
        if 0 <= index <= 2:
            self.regions[index]["enabled"] = 1
            self.set_region(self.get_regionFromRAM(index))
        return self.regions
        
    def disable_all_regions(self): #0x02
        for i in range(3):  
            area = i + 1
            self.disable_region(area)
        return self.regions

    def delete_all_regions(self): #0x02
        self.regions = [
            {"enabled": 0, "narea": 1, "type": 0, "x0": 0, "y0": 0, "x1": 0, "y1": 0, "x2": 0, "y2": 0, "x3": 0, "y3": 0},
            {"enabled": 0, "narea": 2, "type": 0, "x0": 0, "y0": 0, "x1": 0, "y1": 0, "x2": 0, "y2": 0, "x3": 0, "y3": 0},
            {"enabled": 0, "narea": 3, "type": 0, "x0": 0, "y0": 0, "x1": 0, "y1": 0, "x2": 0, "y2": 0, "x3": 0, "y3": 0}
        ]
        self.disable_all_regions()
        self.set_region(self.get_regionFromRAM(0))
        self.set_region(self.get_regionFromRAM(1))
        self.set_region(self.get_regionFromRAM(2))
        return self.regions
    
    def get_stateFromRAM(self):
        return self.state
    
    def get_ntargetsFromRAM(self):    
        return self.ntargets
    
    def to_hex_string(self, byte_list):
        # Funzione per convertire una lista di byte in una stringa esadecimale per visualizzazione (print)
        if byte_list is None:
            return 'N/A'  # Oppure puoi restituire un messaggio come 'N/A'
        return ' '.join(f'{b:02x}' for b in byte_list)
    
    def from_signed_bytes_big(self, data):
        # Assumiamo che `data` contenga almeno 2 byte

        # Combina i due byte nel formato big-endian
        value = (data[1] | (data[0] << 8))  # Il byte più significativo è in data[0], meno significativo in data[1]

        # Verifica se il numero è negativo (controlla il bit di segno nel byte più significativo)
        if data[0] & 0x80:
            value -= 2**16  # Sottrai 2^16 per la conversione di un numero negativo in complemento a due
        
        return value
    
    def from_signed_bytes_little(self, data):
        #print("data", data)
        #print("data0", data[0])
        value = 2**15
        
        #print("sign_bit", data[0] & sign_bit)
        
        value = (data[0] | (data[1] << 8));
        
        if data[1] & 0x80:
            value -= 2**15
        else:
            value = -value
    
        #print("value", value)
        
        #0E 03 B1 86signed_integers_to_bytearray(
        #Target 1 X coordinate: 0x0E + 0x03 * 256 = 782 0    - 782 = -782 mm
        #Target 1 Y coordinate: 0xB1 + 0x86 * 256 = 34481    34481 - 2^15 = 1713 mm
         
        return value
    
    def from_unsigned_bytes_big(self, data):# prende per ingresso un array di due byte
        # Combina i due byte in formato big-endian
        value = ((data[0] << 8) | data[1])  # Il byte più significativo è in data[0], meno significativo in data[1]
        return value
    
    def limit_value(self, valore):
        return max(-127, min(128, valore))
    
    def signed_to_unsigned_byte(self, n):
        if n < 0:
            n += 256  # Trasforma un numero negativo in non firmato
        return n.to_bytes(1, 'big')
    
    def signed_integers_to_bytearray(self, int_list):
        # Crea un bytearray da una lista di interi con segno
        return bytearray((i & 0xFF for i in int_list))
    """
    def bytearray_to_signed_integers(self, byte_arr):
        # Converti ogni byte nel bytearray in un intero con segno
        return [int.from_bytes(byte_arr[i:i+1], byteorder='big', signed=True) for i in range(len(byte_arr))]
    """
    
    def byte_to_signed_integers(self, byte_value):
        # Controlla se il byte_value ha il bit di segno impostato (MSB = 1)
        if byte_value & 0x80:  # 0x80 è 10000000 in binario, controlla il bit più significativo
            return byte_value - 0x100  # Sottrai 256 (2^8) per ottenere il numero negativo
        else:
            return byte_value  # Restituisce il byte_value se è positivo

