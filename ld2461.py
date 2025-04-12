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
    def __init__(self, tx_pin, rx_pin, baud_rate=115200, callback=None):
        self.uart = UART(1, baudrate=baud_rate, tx=Pin(tx_pin), rx=Pin(rx_pin))
        
        self.serial_data = {'buffer': bytearray(), 'size': 0, 'frame_start': 0}
        self.person = [{'x': 0, 'y': 0} for _ in range(5)]
        self.person_before = [{'x': 0, 'y': 0} for _ in range(5)]
        self.presence_millis = [0 for _ in range(5)]
        self.presence_timeout = 30  # Timeout in secondi, modifica a seconda delle esigenze
        self.callback = callback
        self.state = [1,1,1,1,1,1,1,1,1]
        self.persons = [
            {"x": 0.0, "y": 0.0},
            {"x": 0.0, "y": 0.0},
            {"x": 0.0, "y": 0.0},
            {"x": 0.0, "y": 0.0},
            {"x": 0.0, "y": 0.0}
        ]
        self._regions = [
            {"enabled": 0, "narea": 1, "type": 0, "shape": 0, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 2, "type": 0, "shape": 0, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 3, "type": 0, "shape": 0, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 4, "type": 0, "shape": 0, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 5, "type": 0, "shape": 0, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 6, "type": 0, "shape": 0, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 7, "type": 0, "shape": 1, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 8, "type": 0, "shape": 1, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 9, "type": 0, "shape": 1, 'radarmode': 1, "points":[]}
        ]
        self.ntargets = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        
        self.fw = ""
        # non so se servono
        self.gridWidth = 0
        self.gridHeigth = 0
        self.nw = 0
        self.nh = 0
        self.resx = 0
        self.resy = 0

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
            #print('c: ',c)

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
    
    def get_regionsFromRAM(self):# 0x06
        # Logica per processare i dati in risposta delle regioni 
        result = {
            'narea': [],
            'type': [],
            'enabled': [],
            'shape': [],
            'radarmode': [],
            'polilines': []
        }

        for i in range(9):  # Ciclo per 3 regioni
            result['narea'].append(self._regions[i]["narea"])
            result['type'].append(self._regions[i]["type"])
            result['enabled'].append(self._regions[i]["enabled"])
            result['radarmode'].append(self._regions[i]["radarmode"])
            result['polilines'].append(self._regions[i]["points"])

        #self.callback(GET_REGIONS, result, 3)
        return result
    
    # non usato!
    def get_regionFromRAM(self, index):# 0x06
        result = {
            'narea': 0,
            'type': 0,
            'enabled': 0,
            'shape': 0,
            'radarmode': 0,
            'polilines': []            
        }
        
        result['narea'] = self._regions[index]["narea"]
        result['type'] = self._regions[index]["type"]
        result['enabled'] = self._regions[index]["enabled"]
        result['radarmode'] = self._regions[index]["radarmode"]
        rect = self._regions[index]["points"]
        #result['polilines'] = [[p[0]/10, p[1]/10] for p in rect]
        return result           
            
    def process_frame(self):
        try:
            frame_size = 2; # dopo inizia il campo command
            frame_data = self.serial_data['buffer'][self.serial_data['frame_start']:]
                
            command = frame_data[frame_size]
            length = self.from_unsigned_bytes_big(frame_data[0:2])

            #print(f'cmd0: {command}')
            #print(f'length: {length}')
            
            #print('rcv msg', self.to_hex_string(frame_data), ' - len', len(frame_data) if frame_data is not None else 0)

            if command == GET_REGIONS:
                self.process_regions(frame_data, 3)# from request: get_regions()
            elif command == GET_COORDINATES:
                self.process_coordinates(frame_data, 3)# NO REQUEST, the module takes the initiative to report the data, and the format
            elif command == GET_NUM_TARGETS:
                self.process_occurrences(frame_data, 3)# NO REQUEST, the module takes the initiative to report the data, and the format
            elif command == GET_REPORTING:
                self.process_reporting(frame_data, 3)# from request: get_reporting()
            elif command == READ_FIRMWARE:
                self.process_read_firmware(frame_data, 3)# from request: get_version()
            else:
                if command == RESTORE_FACTORY:
                    ok = int.from_bytes(frame_data[0:1], 'big', signed=True)
                    self.callback(command, ok , 1)

            # Resetta il buffer
            #self.serial_data['buffer'].clear()
            self.serial_data['buffer'][:] = b''  # Svuota il bytearray mantenendo lo stesso riferimento
            self.serial_data['size'] = 0
            self.serial_data['frame_start'] = 0
        except IndexError as e:
            print(f"Error: process_frame: {e}")
            return False 

    def process_regions(self, frame_data, offset):# 0x06 legge le regioni 
        # Logica per processare i dati in risposta delle regioni 
        result = {
            'narea': [],
            'type': [],
            'enabled': [],
            'shape': [],
            'radarmode': [],
            'polilines': []            
        }
        
        # regioni emulate
        for i in range(7):  # Ciclo per 7 regioni
            result['narea'].append(self._regions[i]["narea"])
            result['type'].append(self._regions[i]["type"])
            result['enabled'].append(self._regions[i]["enabled"])
            result['radarmode'].append(self._regions[i]["radarmode"])
            result['polilines'].append(self._regions[i]["points"])
        
        # regioni fisiche   
        for i in range(3):  # Ciclo per 3 regioni
            base_index = i * 8 + offset # Calcola l'indice base per ogni gruppo di 8 byte
            
            narea = self.from_signed_byte(frame_data[base_index])
            if 1 <= narea <= 3:
                index = narea - 1 # Indice array di dizionari
                print("index: ", index)
                index += 6
                self._regions[index]["area"] = narea
                self._regions[index]["type"] = self.from_signed_byte(frame_data[base_index + 1])
                self._regions[index]["points"] = self._regions[index]["points"][:-3]
                self._regions[index]["points"].append([self.from_signed_byte(frame_data[base_index + 2]) / 10, self.from_signed_byte(frame_data[base_index + 3]) / 10])
                self._regions[index]["points"].append([self.from_signed_byte(frame_data[base_index + 4]) / 10, self.from_signed_byte(frame_data[base_index + 5]) / 10])
                self._regions[index]["points"].append([self.from_signed_byte(frame_data[base_index + 6]) / 10, self.from_signed_byte(frame_data[base_index + 7]) / 10])
                self._regions[index]["points"].append([self.from_signed_byte(frame_data[base_index + 8]) / 10, self.from_signed_byte(frame_data[base_index + 9]) / 10])
                result['narea'].append(self._regions[index]["area"])
                result['type'].append(self._regions[index]["type"])
                result['shape'].append(self._regions[index]["shape"])
                result['polilines'].append(self._regions[index]["points"])
                result['enabled'].append(1)
                
        self.callback(GET_REGIONS, result, 3)
    
    def process_coordinates(self, frame_data, offset):
        
        try:
            result = {
                'lista_x': [],
                'lista_y': [],
                'ntarget': [],
            }
             
            datalen = self.from_unsigned_bytes_big(frame_data[0:2]) - 1# toglie il command
            
            #print(f'datalen: {datalen}')
            #len = self.serial_data['size'] -1
            datalen = datalen / 2
            if datalen > 5:
                datalen = 5
            datalen = int(datalen)
            
            for i in range(datalen):  
                base_index = i * 2 + offset # Calcola l'indice base per ogni gruppo di 2 byte
                result['lista_x'].append(self.from_signed_byte(frame_data[base_index]) / 10)
                result['lista_y'].append(self.from_signed_byte(frame_data[base_index + 1]) / 10)
        except IndexError as e:
            print(f"Process_coordinates 1: {e}")
            return False
        
            print(f'x: {xx}')
            print(f'y: {yy}')        
        try:
            suppressed = [0, 0, 0, 0, 0]
            
            self.ntargets[0:6] = [0] * 6
            for i in range(6):
                punti = self._regions[i]['points']
                # nt.append(0)
                #print(f"0-datalen: {datalen}")
                for j in range(datalen):
                    px = result['lista_x'][j]
                    py = result['lista_y'][j]
                    
                    if self._regions[i]['shape'] == 0 and (px!=0 or py!=0):# se le regioni non sono rettangolari e se j non è sullo zero
                        #print(f"0.1-test:")
                        inside = self.punto_dentro_poligono(px, py, punti)
                        #print(f"0.2-test:")
                        if (inside and self.state[j] != 1):# j se sta dentro una regione di monitor o di crop (no track)
                            self.ntargets[i] = 1                   # accendi la regione
                            #print(f'1-accendi: {i} - { nt[i]}')  
                        if (inside and self._regions[i]['type']==1 or self._regions[i]['type']==2 and (not inside)) and self._regions[i]['enabled']==1:
                            # se j sta dentro una regione di filtro abile o sta fuori di una regione croppata abile, allora 
                            result['lista_x'][j] = 0 # cancella j, 
                            result['lista_y'][j] = 0
                            self.ntargets[i] = 0                # spegni la regione,
                            #print(f'2-spegni: {i} - { nt[i]}')
                            suppressed[j] = 1        # sopprimi j
                        for k in range (0, i):# per tutte le regioni già elaborate
                            punti = self._regions[k]['points']# recupera i loro vertici
                            inside = self.punto_dentro_poligono(px, py, punti)# vedi se contiene j
                            if inside  and suppressed[j]:# se contiene il soppresso j, allora spegni la regione di qualunque tipo essa sia
                                self.ntargets[k] = 0
                                #print(f'3-contiene soppressi: {i} - { nt[i]}')
                        if self.state[i] == 2:
                            result['lista_x'][j] = 0
                            result['lista_y'][j] = 0
                            #print(f"0.5-test:")     
            
            #self.ntargets = nt
            #print("ntargets coord: ", self.ntargets)
            result['ntarget'] = self.ntargets;
                
            #print("state: ", self.state)
            result['lista_x'] = xx
            result['lista_y'] = yy
            
            self.callback(GET_COORDINATES, result, datalen)
            return result
        except IndexError as e:
            print(f"Process_coordinates 2: {e}")
            return False
    
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
    
    def process_occurrences(self, frame_data, offset):
        for i in range(3):  # Ciclo per 3 regioni
            #base_index = i +1 # Calcola l'indice base per ogni gruppo di 1 byte
            #print("ntargets: ", self.ntargets)
            self.ntargets[i+6] = self.from_signed_byte(frame_data[i + offset])
            
        self.callback(GET_NUM_TARGETS, self.ntargets, 3)        
    
    def process_reporting(self, frame_data, offset):
        app = self.from_signed_byte(frame_data[0])
        self.state[6] = app
        self._regions[6]["radarmode"] = app
        self._regions[7]["radarmode"] = app
        self._regions[8]["radarmode"] = app
        print(f'Reporting inner state: {self.state}')
        self.callback(GET_REPORTING, self.state, 1)
        
    def process_read_firmware(self, frame_data, offset):
        try:
            # Estrazione versione (primi 4 byte)
            month = frame_data[0]
            day = frame_data[1]
            major_version = frame_data[2]
            minor_version = frame_data[3]

            # Estrazione ID (successivi 4 byte)
            id_number = (frame_data[4] << 24) | (frame_data[5] << 16) | (frame_data[6] << 8) | frame_data[7]

            # Creazione di un'unica stringa con entrambe le informazioni
            self.fw = f"Version {major_version}.{minor_version} from {month}/{day}/2021, ID: {id_number}"
            print(f'Firmware: {self.fw}')
            self.callback(READ_FIRMWARE, self.fw, 1)
        except IndexError as e:
            print(f"Gestito errore durante process_read_firmware: {e}")
            return False
        
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
        self.uart.write(bytes([command]))
        
        
        #print('cmd_len', self.to_hex_string(cmd_len), 'len', len(cmd_len) if cmd_len is not None else 0)
        #print('command', self.to_hex_string(bytes([command])), 'len', len(bytes([command])) if command is not None else 0)
        #print('send command_value', self.to_hex_string(command_value), 'len', len(command_value) if command_value is not None else 0)
        
        
        # Inizializza il checksum con il comando
        check_sum = command
        
        # Se c'è un valore associato, invialo e aggiornane il checksum
        if command_value:
            self.uart.write(command_value)
            check_sum += sum(command_value)
            
        # Mantieni solo gli ultimi 8 bit del checksum
        check_sum = check_sum & 0xFF
        
        # Invia il checksum
        self.uart.write(bytes([check_sum]))
        
        # Invia il frame end
        self.uart.write(FRAME_END)
        
        msg = FRAME_HEADER+cmd_len+bytes([command])+command_value+bytes([check_sum])+FRAME_END
        
        print('send msg', self.to_hex_string(msg), ' - len', len(msg) if msg is not None else 0)

    def load_regions(self, reg):
        self._regions = reg
        for i in range(6, 9):
            if self._regions[i]["enabled"]:
                self.enable_region(i + 1)# copia i valori in self._regions sul radar creandola sul radar
            else:
                self.disable_region(i + 1)# manda un comando di cancellazione della regione al radar
            
    def read_all_info(self):
        self.get_version()
        #time.sleep_ms(1000)
        #self.get_regions()
        #time.sleep_ms(1000)
        #self.get_reporting()
        #time.sleep_ms(1000)
        

    def get_version(self):
        cmd = 0x01
        byte_sequence = cmd.to_bytes(1, 'big')
        self.send_command(READ_FIRMWARE, byte_sequence)
        
    def get_versionFromRAM(self):
        return self.fw

    def get_regions(self):
        cmd = 0x01
        byte_sequence = cmd.to_bytes(1, 'big')
        self.send_command(GET_REGIONS, byte_sequence)
        
    def init_serial(self,baud_rate):
        self.uart.init(baudrate=baud_rate)

    def set_baud_rate(self, baud_rate=256000):
        possible_baud_rates = [9600, 19200, 38400, 57600, 115200, 256000]
        if baud_rate not in possible_baud_rates:
            raise ValueError('The baud rate must be one of the following: 19200, 38400, 57600, 115200, 256000')   
        
        byte_sequence = baud_rate.to_bytes(3, 'big')
        self.send_command(SET_BAUDRATE, byte_sequence)
        self.uart.init(baudrate=baud_rate)

    def set_region(self, v):# 0x04 scrive una regione
        """
        v = {
            'narea': 0,
            'type': 0,
            'shape': 0,
            'radarmode': 0,
            'polilines': []  sono float in metri
        }
        """
        # modifica la sequenza memorizzata sul microcontrollore
        narea = v["narea"]
        index = narea - 1 # Indice array di dizionari
        
        #self._regions[index] = v
        self._regions[index]["narea"] = int(v["narea"])
        self._regions[index]["type"] = int(v["type"])
        self._regions[index]["enabled"] = int(v["enabled"])
        self._regions[index]["shape"] = int(v["shape"])
        self._regions[index]["points"] = v["polilines"]
        self._regions[index]["radarmode"] = v["radarmode"]
        self.state[index] = v["radarmode"]
        print('Write region: ', index, ' points', self._regions[index]["points"])
            
        if 6 <= index < 9 and len(v["polilines"]) == 4:
            if self.state[6] != self._regions[index]["radarmode"]:
                set_reporting(self, report_format)
                
            # Prepara la sequenza di byte in big endian ('>': big-endian, 'h': signed short) da inviare sulla seriale
            byte_sequence = struct.pack(
                ">hhhhhhhhhh",  # Formato per 10 valori (signed short)
                self._regions[index]["narea"] - 6,          
                int(self._regions[index]['points'][0][0]*10), int(self._regions[index]['points'][0][1]*10), # X0, Y0
                int(self._regions[index]['points'][1][0]*10), int(self._regions[index]['points'][1][1]*10), # X1, Y1
                int(self._regions[index]['points'][2][0]*10), int(self._regions[index]['points'][2][1]*10), # X2, Y2
                int(self._regions[index]['points'][3][0]*10), int(self._regions[index]['points'][3][1]*10), # X3, Y3
                self._regions[index]["type"]
            )
            
            # modifica la sequenza memorizzata sul sensore        
            self.send_command(SET_REGIONS, byte_sequence)
            
        return self._regions
        
    def restore_factory(self):
        cmd = 0x01
        byte_sequence = cmd.to_bytes(1, 'big')
        self.send_command(RESTORE_FACTORY, byte_sequence)

    def set_reporting(self, v): #0x02
        """
        v = {
            'narea': 0,
            'type': 0,
            'shape': 0,
            'radarmode': 0,
            'polilines': []  sono float in metri
        }
        """
        narea = v["narea"]
        index = narea - 1 # Indice array di dizionari
        
        report_format = int(v["radarmode"])
        possible_report_format = [0x01, 0x02, 0x03]
        if report_format not in possible_report_format:
            raise ValueError('The report value must be one of the following: 1, 2, 3')
        
        self._regions[index]["radarmode"] = report_format
        self.state[index] = report_format
        
        if 6 <= index < 9:
            self.state[6] = report_format
            byte_sequence = report_format.to_bytes(1, 'big')
            self.send_command(SET_REPORTING, byte_sequence)
        
        return self._regions
    
    def get_reporting(self):
        cmd = 0x01
        byte_sequence = bytes.fromhex('01')
        self.send_command(GET_REPORTING, byte_sequence)

    def disable_region(self, area): #0x05
        index = area - 1 # Indice array di dizionari
        
        self._regions[index]["enabled"] = 0 # per tutte le aree
        if 6 <= index < 9:# per le aree fisiche
            byte_sequence = area.to_bytes(1, 'big')
            self.send_command(DISABLE_REGIONS, byte_sequence)# cancella una certa area fisica
        return self._regions
    
    def enable_region(self, area): #0x02
        index = area - 1 # Indice array di dizionari

        self._regions[index]["enabled"] = 1 # per tutte le aree
        
        if 6 <= index < 9 and len(self._regions[index]) == 4:# per le aree fisiche
            #self.set_region(v)
            print('s1')
            #self._regions[index]["points"] = [int(x) for x in self._regions[index]["points"]]
            # Prepara la sequenza di byte in big endian ('>': big-endian, 'h': signed short) da inviare sulla seriale
            byte_sequence = struct.pack(
                ">hhhhhhhhhh",  # Formato per 10 valori (signed short)
                self._regions[index]["narea"] - 6,          
                int(self._regions[index]['points'][0][0]*10), int(self._regions[index]['points'][0][1]*10), # X0, Y0
                int(self._regions[index]['points'][1][0]*10), int(self._regions[index]['points'][1][1]*10), # X1, Y1
                int(self._regions[index]['points'][2][0]*10), int(self._regions[index]['points'][2][1]*10), # X2, Y2
                int(self._regions[index]['points'][3][0]*10), int(self._regions[index]['points'][3][1]*10), # X3, Y3
                self._regions[index]["type"]
            )
            print('s2')
            # modifica la sequenza memorizzata sul sensore        
            #self.send_command(SET_REGIONS, byte_sequence)
        return self._regions
        
    def disable_all_regions(self): #0x02
        for i in range(3):  
            area = i + 1
            self.disable_region(area)
        return self._regions

    def delete_all_regions(self): #0x02
        self._regions = [
            {"enabled": 0, "narea": 1, "type": 0, "shape": 0, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 2, "type": 0, "shape": 0, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 3, "type": 0, "shape": 0, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 4, "type": 0, "shape": 0, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 5, "type": 0, "shape": 0, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 6, "type": 0, "shape": 0, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 7, "type": 0, "shape": 1, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 8, "type": 0, "shape": 1, 'radarmode': 1, "points":[]},
            {"enabled": 0, "narea": 9, "type": 0, "shape": 1, 'radarmode': 1, "points":[]}
        ]
        
        #self.disable_all_regions()
        self.restore_factory
        #for i in len(self._regions):
        #    self.set_region(self.get_regionFromRAM(i))
        return self._regions
    
    def set_filtermode_region(self, v): #0x02
        """
        v = {
            'narea': 0,
            'type': 0,
            'shape': 0,
            'radarmode': 0,
            'polilines': []    
        }
        """
        #print('vvvv',v)
        # modifica la sequenza memorizzata sul microcontrollore
        index = int(v["narea"]) - 1
        mode = int(v["type"])
        
        if 0 <= mode <= 2:
            self._regions[index]["type"] = mode
        return self._regions
    
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
        
        # Restituisce il valore convertito in big-endian
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
        
        #0E 03 B1 86
        #Target 1 X coordinate: 0x0E + 0x03 * 256 = 782 0    - 782 = -782 mm
        #Target 1 Y coordinate: 0xB1 + 0x86 * 256 = 34481    34481 - 2^15 = 1713 mm
         
        return value
    
    def from_unsigned_bytes_big(self, data):
        # Combina i due byte in formato big-endian
        value = (data[0] << 8) | data[1]  # Il byte più significativo è in data[0], meno significativo in data[1]
        return value
    
    def from_signed_byte(self, value):               
        # Verifica se il numero è negativo (controlla il bit di segno)
        if value & 0x80:
            value -= 2**8  # Sottrai 2^8 per la conversione di un numero negativo in complemento a due
        
        # Restituisce il valore convertito
        return value
    
    def punto_dentro_poligono(self, px, py, vertices):
        dentro = False
        n = len(vertices)

        for i in range(n):
            j = (i - 1) % n
            xi, yi = vertices[i]
            xj, yj = vertices[j]

            # Verifica se il punto è all'interno del segmento con l'algoritmo Ray-Casting
            intersect = ((yi > py) != (yj > py)) and \
                        (px < (xj - xi) * (py - yi) / (yj - yi) + xi)
            if intersect:
                dentro = not dentro

        return dentro
    
    def punto_dentro_cerchio(self, x, y, cx, cy, r):
        # Calcola il quadrato della distanza dal centro
        distanza_quad = (x - cx) ** 2 + (y - cy) ** 2
        # Confronta con il quadrato del raggio
        return distanza_quad <= r ** 2