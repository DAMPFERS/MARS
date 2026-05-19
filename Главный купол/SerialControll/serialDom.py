import serial
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
from typing import Optional,Tuple


class ListenerThread(QThread):
    """Фоновый поток для чтения данных из COM-порта второго устройства."""
    
    def __init__(self, ser: serial.Serial, timeout: float = 1.0):
        super().__init__()
        self._ser = ser  # Используем уже открытый порт
        self.timeout = timeout
        self.stop_flag = False
        self.last_data: Optional[Tuple[int, ...]] = None  # Хранит последние распарсенные данные
        self.mutex = QMutex()  # Мьютекс для защиты доступа к last_data
        
        
    def run(self) -> None:
        try:
            
            buffer = bytearray()
            while not self.stop_flag:
                byte = self._ser.read(1)
                if not byte:
                    self.msleep(1)
                    continue
                    
                buffer.extend(byte)
                
                if b'\n' in buffer:
                    line = buffer.split(b'\n')[0].decode('utf-8', errors='replace').strip()
                    buffer = buffer[len(line.encode('utf-8')) + 1:]  # Удаляем обработанную строку из буфера
                    
                    line = line[:-1]
                    
                    # Парсим строку с 6 числами
                    
                    try:
                        numbers = list(map(int, line.split(';')))

                        if len(numbers) == 6:
                            with QMutexLocker(self.mutex):
                                self.last_data = tuple(numbers)  # Сохраняем последние данные
                    except (ValueError, IndexError):
                        continue # Игнорируем некорректные данные
        except serial.SerialException as e:
            print(f"[ListenerThread] Ошибка при открытии COM-порта: {e}")
        except Exception as e:
            print(f"[ListenerThread] Критическая ошибка: {e}")
        finally:
            print("[ListenerThread] Поток чтения завершён.")
    
    def stop(self) -> None:
        """Останавливает поток чтения."""
        self.stop_flag = True
        self.wait(2000)  # Ждём завершения потока
        
        
        
class DeviceManager:
    """Класс для управления двумя устройствами по COM-портам."""
    def __init__(self, port1: str, port2: str, baudrate: int = 9600, timeout: float = 1.0):
        self.port1 = port1
        self.port2 = port2
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser1 = None
        self._ser2 = None
        self.mutex1 = QMutex()  # Мьютекс для первого порта
        self.mutex2 = QMutex()  # Мьютекс для второго порта
        
        #  Открываем порты при инициализации
        self._openPorts()
        
        
        self.listener_thread = ListenerThread(self._ser2, timeout)
        
        
        
        # Запускаем поток чтения
        self.listener_thread.start()
    
    def _openPorts(self) -> None:
        """Открывает COM-порты с проверкой ошибок."""
        try:
            self._ser1 = serial.Serial(self.port1, self.baudrate, timeout=self.timeout)
            print(f"[DeviceManager] Порт {self.port1} открыт.")
        except serial.SerialException as e:
            print(f"[DeviceManager] Не удалось открыть порт {self.port1}: {e}")
            self._ser1 = None

        try:
            self._ser2 = serial.Serial(self.port2, self.baudrate, timeout=self.timeout)
            print(f"[DeviceManager] Порт {self.port2} открыт.")
        except serial.SerialException as e:
            print(f"[DeviceManager] Не удалось открыть порт {self.port2}: {e}")
            self._ser2 = None
    
    
    def _ensurePortOpen(self, ser: serial.Serial, port_name: str) -> bool:
        """Проверяет, открыт ли порт, и пытается открыть его, если закрыт."""
        if ser is None:
            print(f"[DeviceManager] Порт {port_name} не инициализирован.")
            return False
        if not ser.is_open:
            try:
                ser.open()
                print(f"[DeviceManager] Порт {port_name} открыт повторно.")
            except serial.SerialException as e:
                print(f"[DeviceManager] Не удалось открыть порт {port_name}: {e}")
                return False
        return True

   
    def sendToDeviceCommunication(self, data: bytes) -> bool:
        """Отправляет данные на первое устройство (купол связи), добавляя в конец 3 байта 0xFF
        Возвращает True, если отправка успешна, иначе False"""
        with QMutexLocker(self.mutex1):
            if not self._ensurePortOpen(self._ser1, self.port1):
                return False
            try:
                packet = b'\xFE' + data + b'\xFF\xFF\xFF'
                self._ser1.write(packet)
                return True
            except serial.SerialException as e:
                print(f"[DeviceManager] Ошибка отправки в купол связи: {e}")
                return False


    def sendToDeviceSolarPanels(self, angle1: int, angle2: int) -> bool:
        """Отправляет два угла на второе устройство (купол энергетики), преобразуя их в байты
        Возвращает True, если отправка успешна, иначе False"""
        
        with QMutexLocker(self.mutex2):
            if not self._ensurePortOpen(self._ser2, self.port2):
                return False
            try:
                byte1 = angle1.to_bytes(1, byteorder='big', signed=False)
                byte2 = angle2.to_bytes(1, byteorder='big', signed=False)
                packet = byte1 + byte2
                self._ser2.write(packet)
                return True
            except serial.SerialException as e:
                print(f"[DeviceManager] Ошибка отправки в купол энергетики: {e}")
                return False


    def getLastDataSolarPanels(self) -> Optional[Tuple[int, ...]]:
        """Возвращает последние распарсенные данные от второго устройства."""
        with QMutexLocker(self.listener_thread.mutex):
            return self.listener_thread.last_data
    
    def stop(self) -> None:
        """Закрывает все порты и останавливает поток чтения"""
        self.listener_thread.stop()
        with QMutexLocker(self.mutex1):
            if self._ser1 and self._ser1.is_open:
                self._ser1.close()
                print(f"[DeviceManager] Порт {self.port1} закрыт")
        with QMutexLocker(self.mutex2):
            if self._ser2 and self._ser2.is_open:
                self._ser2.close()
                print(f"[DeviceManager] Порт {self.port2} закрыт")



if __name__ == "__main__":
    # Инициализация
    manager = DeviceManager(port1='/dev/ttyACM0', port2='/dev/ttyACM1', baudrate=9600, timeout=1.0)
    manager.sendToDeviceCommunication(b'\x01\x02\x03')  # Пример отправки данных в купол связи
    manager.sendToDeviceSolarPanels(45, 90)  # Пример отправки углов в купол энергетики
    
    import time
    i = 0
    while i < 10:
        time.sleep(1) 
        manager.sendToDeviceCommunication(b'\x01\x02\x03')  # Пример отправки данных в купол связи
        manager.sendToDeviceSolarPanels(45, 90)  # Пример отправки углов в купол энергетики   
        last_data = manager.getLastDataSolarPanels()
        if last_data:
            print(f"Последние данные от купола энергетики: {last_data}")
        else:
            print("Нет данных от купола энергетики.")
        i += 1
        
    manager.stop()
