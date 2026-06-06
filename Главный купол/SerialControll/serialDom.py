import serial
from serial.tools import list_ports
import time

from enum import Enum
from typing import Optional
from PyQt5.QtCore import QThread, QMutex, QMutexLocker

# from nextionParser import Nextion


COLOR_SET_STATUS = 20460
COLOR_RESET_STATUS = 65535



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
            "Power:": 0, 
            "Red:" : 0,
            "Green:" : 0,
            "Blue:" : 0,
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
        for page in range(len(pages)):
            for key in pages[page].keys():
                if key in pack:
                    self.active_page = 0 if page == 0 else 1
                    return {key: int(pack[-1])}

        return None
    
    def updateStateNextion(self, pack: str) -> bool:
        new_state = self._parsingNextionPacket(pack)
        if self.active_page == 0:
            pass
        elif self.active_page == 1:
            pass
        else:
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

                    # TEXT
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
            numbers = list(map(int, line.split(';')))
            if len(numbers) == 6:
                self.device_type = DeviceType.SOLAR
                with QMutexLocker(self.mutex):
                    self.last_solar_data = tuple(numbers)
                return
        except:
            pass

    def processNextionPacket(self, packet: bytes):

        try:
            text = packet.decode(
                'iso-8859-5s',
                errors='ignore'
            )

            if text == "Nextion":
                self.device_type = DeviceType.NEXTION
                self.last_nextion_heartbeat = time.time()
                self.nextion_connected = True
                return

            # KEY:VALUE

            if ':' in text:
                key, value = text.split(':', 1)
                print(f"NEXTION: {key} = {value}")

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


# class ListenerThread(QThread):
#     """Фоновый поток для чтения данных из COM-порта второго устройства."""
    
#     def __init__(self, ser: serial.Serial, timeout: float = 1.0):
#         super().__init__()
#         self._ser = ser  # Используем уже открытый порт
#         self.timeout = timeout
#         self.stop_flag = False
#         self.last_data: Optional[Tuple[int, ...]] = None  # Хранит последние распарсенные данные
#         self.mutex = QMutex()  # Мьютекс для защиты доступа к last_data
        
        
#     def run(self) -> None:
#         try:
            
#             buffer = bytearray()
#             while not self.stop_flag:
#                 byte = self._ser.read(1)
#                 if not byte:
#                     self.msleep(1)
#                     continue
                    
#                 buffer.extend(byte)
                
#                 if b'\n' in buffer:
#                     line = buffer.split(b'\n')[0].decode('utf-8', errors='replace').strip()
#                     buffer = buffer[len(line.encode('utf-8')) + 1:]  # Удаляем обработанную строку из буфера
                    
#                     line = line[:-1]
                    
#                     # Парсим строку с 6 числами
                    
#                     try:
#                         numbers = list(map(int, line.split(';')))

#                         if len(numbers) == 6:
#                             with QMutexLocker(self.mutex):
#                                 self.last_data = tuple(numbers)  # Сохраняем последние данные
#                     except (ValueError, IndexError):
#                         continue # Игнорируем некорректные данные
#         except serial.SerialException as e:
#             print(f"[ListenerThread] Ошибка при открытии COM-порта: {e}")
#         except Exception as e:
#             print(f"[ListenerThread] Критическая ошибка: {e}")
#         finally:
#             print("[ListenerThread] Поток чтения завершён.")
    
#     def stop(self) -> None:
#         """Останавливает поток чтения."""
#         self.stop_flag = True
#         self.wait(2000)  # Ждём завершения потока
        
        
        
# class DeviceManager:
#     """Класс для управления двумя устройствами по COM-портам."""
#     def __init__(self, port1: str, port2: str, baudrate: int = 9600, timeout: float = 1.0):
#         self.port1 = port1
#         self.port2 = port2
#         self.baudrate = baudrate
#         self.timeout = timeout
#         self._ser1 = None
#         self._ser2 = None
#         self.mutex1 = QMutex()  # Мьютекс для первого порта
#         self.mutex2 = QMutex()  # Мьютекс для второго порта
        
#         #  Открываем порты при инициализации
#         self._openPorts()
        
        
#         self.listener_thread = ListenerThread(self._ser2, timeout)
        
        
        
#         # Запускаем поток чтения
#         self.listener_thread.start()
    
#     def _openPorts(self) -> None:
#         """Открывает COM-порты с проверкой ошибок."""
#         try:
#             self._ser1 = serial.Serial(self.port1, self.baudrate, timeout=self.timeout)
#             print(f"[DeviceManager] Порт {self.port1} открыт.")
#         except serial.SerialException as e:
#             print(f"[DeviceManager] Не удалось открыть порт {self.port1}: {e}")
#             self._ser1 = None

#         try:
#             self._ser2 = serial.Serial(self.port2, self.baudrate, timeout=self.timeout)
#             print(f"[DeviceManager] Порт {self.port2} открыт.")
#         except serial.SerialException as e:
#             print(f"[DeviceManager] Не удалось открыть порт {self.port2}: {e}")
#             self._ser2 = None
    
    
#     def _ensurePortOpen(self, ser: serial.Serial, port_name: str) -> bool:
#         """Проверяет, открыт ли порт, и пытается открыть его, если закрыт."""
#         if ser is None:
#             print(f"[DeviceManager] Порт {port_name} не инициализирован.")
#             return False
#         if not ser.is_open:
#             try:
#                 ser.open()
#                 print(f"[DeviceManager] Порт {port_name} открыт повторно.")
#             except serial.SerialException as e:
#                 print(f"[DeviceManager] Не удалось открыть порт {port_name}: {e}")
#                 return False
#         return True

   
#     def sendToDeviceCommunication(self, data: bytes) -> bool:
#         """Отправляет данные на первое устройство (купол связи), добавляя в конец 3 байта 0xFF
#         Возвращает True, если отправка успешна, иначе False"""
#         with QMutexLocker(self.mutex1):
#             if not self._ensurePortOpen(self._ser1, self.port1):
#                 return False
#             try:
#                 packet = b'\xFE' + data + b'\xFF\xFF\xFF'
#                 self._ser1.write(packet)
#                 return True
#             except serial.SerialException as e:
#                 print(f"[DeviceManager] Ошибка отправки в купол связи: {e}")
#                 return False


#     def sendToDeviceSolarPanels(self, angle1: int, angle2: int) -> bool:
#         """Отправляет два угла на второе устройство (купол энергетики), преобразуя их в байты
#         Возвращает True, если отправка успешна, иначе False"""
        
#         with QMutexLocker(self.mutex2):
#             if not self._ensurePortOpen(self._ser2, self.port2):
#                 return False
#             try:
#                 byte1 = angle1.to_bytes(1, byteorder='big', signed=False)
#                 byte2 = angle2.to_bytes(1, byteorder='big', signed=False)
#                 packet = byte1 + byte2
#                 self._ser2.write(packet)
#                 return True
#             except serial.SerialException as e:
#                 print(f"[DeviceManager] Ошибка отправки в купол энергетики: {e}")
#                 return False


#     def getLastDataSolarPanels(self) -> Optional[Tuple[int, ...]]:
#         """Возвращает последние распарсенные данные от второго устройства."""
#         with QMutexLocker(self.listener_thread.mutex):
#             return self.listener_thread.last_data
    
#     def stop(self) -> None:
#         """Закрывает все порты и останавливает поток чтения"""
#         self.listener_thread.stop()
#         with QMutexLocker(self.mutex1):
#             if self._ser1 and self._ser1.is_open:
#                 self._ser1.close()
#                 print(f"[DeviceManager] Порт {self.port1} закрыт")
#         with QMutexLocker(self.mutex2):
#             if self._ser2 and self._ser2.is_open:
#                 self._ser2.close()
#                 print(f"[DeviceManager] Порт {self.port2} закрыт")



# if __name__ == "__main__":
#     # Инициализация
#     manager = DeviceManager(port1='/dev/ttyACM0', port2='/dev/ttyACM1', baudrate=9600, timeout=1.0)
#     manager.sendToDeviceCommunication(b'\x01\x02\x03')  # Пример отправки данных в купол связи
#     manager.sendToDeviceSolarPanels(45, 90)  # Пример отправки углов в купол энергетики
    
#     import time
#     i = 0
#     while i < 10:
#         time.sleep(1) 
#         manager.sendToDeviceCommunication(b'\x01\x02\x03')  # Пример отправки данных в купол связи
#         manager.sendToDeviceSolarPanels(45, 90)  # Пример отправки углов в купол энергетики   
#         last_data = manager.getLastDataSolarPanels()
#         if last_data:
#             print(f"Последние данные от купола энергетики: {last_data}")
#         else:
#             print("Нет данных от купола энергетики.")
#         i += 1
        
#     manager.stop()
