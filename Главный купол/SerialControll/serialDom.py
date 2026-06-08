import serial
from serial.tools import list_ports
import time

from enum import Enum
from typing import Optional
from PyQt5.QtCore import QThread, QMutex, QMutexLocker

# from nextionParser import Nextion





class Nextion():
    def __init__(self):
        self.color_set_status = 20460
        self.color_reset_status = 65535
        
        self.active_page = 0
        
        self.page_settings = {
            "Manual mode:" : 0, 
            "Panel 1" : 0,
            "Panel 2" : 0,
            "Main module:" : 0,
            "Conn module:" : 0,
            "Live module:" : 0,
            "Energ module:" : 0,
            "t1": self.color_set_status,
            "t2": self.color_reset_status,
            "t3": self.color_reset_status,
            "t4": self.color_reset_status,
        }
        
        self.page_color = {
            "Power:": 120, 
            "Red:" : 1,
            "Green:" : 1,
            "Blue:" : 1,
            "Main color:" : 0,
            "Conn color:" : 0,
            "Live color:" : 0,
            "Energ color:" : 0,
            "t1": self.color_set_status,
            "t2": self.color_reset_status,
            "t3": self.color_reset_status,
            "t4": self.color_reset_status,
        }



    def _parsingNextionPacket(self, pack: str) -> dict:
        pages = (self.page_settings, self.page_color)
        result = {}
        for page_idx, page in enumerate(pages):
            for key in page.keys():
                if key in pack:
                    try:
                        # Исправлено: корректное извлечение числа после двоеточия
                        parts = pack.split(':')
                        if len(parts) >= 2:
                            val = int(parts[1].strip())
                            result[key] = val
                            self.active_page = 0 if page_idx == 0 else 1
                    except ValueError:
                        pass # Игнорируем, если значение не число
        return result if result else None
    
    def updateStateNextion(self, pack: str) -> bool:
        new_state = self._parsingNextionPacket(pack)
        if new_state:
            for key, val in new_state.items():
                if self.active_page == 0:
                    self.page_settings[key] = val
                elif self.active_page == 1:
                    self.page_color[key] = val
            return True
        return False
    
    
    def setPametersNextion(self, name_vidget:str, param: str, val) -> None:
        pass





class DeviceType(Enum):
    UNKNOWN = 0
    TRANSMITTER = 1
    SOLAR = 2
    NEXTION = 3


class SerialDeviceThread(QThread):

    def __init__(self, port: str, baudrate=9600, timeout=0.1):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.stop_flag = False
        self.device_type = DeviceType.UNKNOWN
        self.last_rx_time = time.time()
        self.last_nextion_heartbeat = 0
        self.nextion_connected = False
        self.mutex = QMutex()
        self.last_solar_data = None
        self.nextion_buffer = bytearray()
        
        # === ДОБАВЛЕНО: Словари для хранения состояния Nextion прямо в потоке ===
        # Они создаются ОДИН раз при инициализации потока и живут, пока работает программа
        self.page_settings = {
             "Manual mode:": 0, 
             "Panel 1": 0,
             "Panel 2": 0,
             "Main module:": 0,
             "Conn module:": 0,
             "Live module:": 0,
             "Energ module:": 0,
        }
        self.page_color = {
             "Power:": 120, 
             "Red:": 1,
             "Green:": 1,
             "Blue:": 1,
             "Main color:": 0,
             "Conn color:": 0,
             "Live color:": 0,
             "Energ color:": 0,
        }
        
        

    def open(self):
        self.ser = serial.Serial(
            self.port,
            self.baudrate,
            timeout=self.timeout
        )
        print(f"[{self.port}] открыт")


    def run(self):

        while not self.stop_flag:
            try:
                if self.ser is None or not self.ser.is_open:
                    self.open()
                buffer = bytearray()
                while not self.stop_flag:
                    data = self.ser.read(1)
                    if not data:
                        self.checkTimeouts()
                        self.msleep(1)
                        continue

                    self.last_rx_time = time.time()
                    buffer.extend(data)
                    # NEXTION
                    if b'\xFF\xFF\xFF' in buffer:
                        packets = buffer.split(b'\xFF\xFF\xFF')
                        for packet in packets[:-1]:
                            self.processNextionPacket(packet)
                        buffer = packets[-1]

                    # TEXT (для Solar)
                    elif b'\n' in buffer:
                        line = buffer.split(b'\n')[0]
                        # line = line[:-1]
                        buffer = buffer[len(line)+1:]
                        self.processLine(
                            line.decode(
                                'utf-8',
                                errors='ignore'
                            ).strip()
                        )

            except serial.SerialException:
                print(f"[{self.port}] устройство отключено")
                self.device_type = DeviceType.UNKNOWN
                self.nextion_connected = False
                try:
                    self.ser.close()
                except:
                    pass

                self.ser = None
                self.sleep(2)

            except Exception as e:
                print(f"[{self.port}] ошибка:", e)
                self.sleep(1)


    def processLine(self, line: str):

        if not line:
            return

        # NEXTION HEARTBEAT
        if line == "Nextion":
            self.device_type = DeviceType.NEXTION
            self.last_nextion_heartbeat = time.time()
            self.nextion_connected = True
            print(f"[{self.port}] обнаружен NEXTION")
            return

        # SOLAR DATA
        try:
            
            # 1. Убираем пробелы по краям и конечную точку с запятой
            clean_line = line.strip().rstrip(';')
            
            numbers = list(map(int, clean_line.split(';')))
            if len(numbers) == 6:
                self.device_type = DeviceType.SOLAR
                with QMutexLocker(self.mutex):
                    self.last_solar_data = tuple(numbers)
                print(f"[{self.port}] Получены данные SOLAR: {self.last_solar_data}") # Для отладки
                return
        except ValueError:
            # Если строка не является набором чисел, просто игнорируем её
            pass
        except Exception as e:
            # На этапе отладки полезно видеть другие неожиданные ошибки
            print(f"[{self.port}] Ошибка парсинга SOLAR: {e} | Строка: '{line}'")

    def processNextionPacket(self, packet: bytes):

        try:
            text = packet.decode(
                'iso-8859-5',
                errors='ignore'
            )

            if text == "Nextion":
                self.device_type = DeviceType.NEXTION
                self.last_nextion_heartbeat = time.time()
                self.nextion_connected = True
                return

            # KEY:VALUE

            if ':' in text:
                # key, value = text.split(':', 1)
                # print(f"NEXTION: {key} = {value}")
                # self.updateStateNextion(text)
                # === ИСПРАВЛЕННЫЙ ПАРСИНГ ===
                # Проверяем оба словаря (настройки и цвета)
                for dict_to_update in (self.page_settings, self.page_color):
                    for key in dict_to_update.keys():
                        # Если полученная строка начинается с известного ключа (например, "Power:120")
                        if text.startswith(key):
                            try:
                                # Извлекаем всё, что идет ПОСЛЕ ключа, и преобразуем в целое число
                                val_str = text[len(key):].strip()
                                dict_to_update[key] = int(val_str)
                                print(f"NEXTION UPDATE: {key} = {dict_to_update[key]}")
                            except ValueError:
                                pass # Если там не число, игнорируем
                            break # Ключ найден и обновлен, переходим к следующей итерации
                print(f"NEXTION UPDATE: {text.strip()}")

        except Exception as e:
            print("Ошибка Nextion:", e)

    def checkTimeouts(self):

        # Проверка потери Nextion
        if self.device_type == DeviceType.NEXTION:
            if time.time() - self.last_nextion_heartbeat > 4:
                self.nextion_connected = False
                print(f"[{self.port}] Nextion отключен")

        # Если устройство молчит долго —
        # считаем что это передатчик
        if self.device_type == DeviceType.UNKNOWN:
            if time.time() - self.last_rx_time > 3:
                self.device_type = DeviceType.TRANSMITTER

    def send(self, data: bytes):
        if not self.ser:
            return False
        try:
            self.ser.write(data)
            return True
        except Exception as e:
            print(e)
            return False

    def stop(self):
        self.stop_flag = True
        self.wait(2000)
        if self.ser and self.ser.is_open:
            self.ser.close()



class DeviceManager:

    def __init__(self):
        self.devices = []
        self.scanPorts()

    def scanPorts(self):
        ports = list_ports.comports()
        for port in ports:
            try:
                thread = SerialDeviceThread(port.device)
                thread.start()
                self.devices.append(thread)
            except Exception as e:
                print(e)
    
    def getSolar(self):
        for dev in self.devices:
            if dev.device_type == DeviceType.SOLAR:
                return dev
        return None


    def getNextion(self):
        for dev in self.devices:
            if dev.device_type == DeviceType.NEXTION:
                return dev
        return None


    def getTransmitter(self):
        for dev in self.devices:
            if dev.device_type == DeviceType.TRANSMITTER:
                return dev
        return None

    
    def sendSolarAngles(self, angle1, angle2):  # Отправка в солнечный генератор
        solar = self.getSolar()
        if not solar:
            return False
        angle1 = max(0, min(250, angle1))
        angle2 = max(0, min(250, angle2))
        byte1 = angle1.to_bytes(1, byteorder='big', signed=False)
        byte2 = angle2.to_bytes(1, byteorder='big', signed=False)
        packet = byte1 + byte2
        
        # packet = bytes([angle1, angle2])
        return solar.send(packet)
    
    def sendToDeviceCommunication(self, data, data_type="BYTE"):  # Отправка в купол связи
        transmitter = self.getTransmitter()
        if not transmitter:
            return False
        if data_type == "BYTE":
            packet = b'\xFE' + data + b'\xFF\xFF\xFF'
        else:
            packet = data.encode('utf-8') + b'\xFF\xFF\xFF'
        return transmitter.send(packet)



    def sendNextionCommand(self, cmd: str):
        nextion = self.getNextion()
        if not nextion:
            return False
        packet = cmd.encode() + b'\xFF\xFF\xFF'
        return nextion.send(packet)





if __name__ == "__main__":

    manager = DeviceManager()

    print("Ожидание определения устройств...")

    # Даем время на автоопределение
    time.sleep(5)

    while True:

        # ========= SOLAR =========
        solar = manager.getSolar()
        if solar:
            solar_data = solar.last_solar_data
            if solar_data:
                print("SOLAR:", solar_data)
            manager.sendSolarAngles(45, 90)
        else:
            print("Solar device not found")
        # ========= NEXTION =========

        nextion = manager.getNextion()
        if nextion:
            print("Nextion connected:",
                  nextion.nextion_connected)
            manager.sendNextionCommand(
                't0.txt="HELLO"'
            )
        else:
            print("Nextion not found")

        # ========= TRANSMITTER =========

        transmitter = manager.getTransmitter()
        if transmitter:
            transmitter.send(
                b'\xFE\x01\x02\x03\xFF\xFF\xFF'
            )
        else:
            print("Transmitter not found")
        time.sleep(1)

