# serial_logger.py
import serial
import csv
import time
from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import QThread

class SerialLoggerThread(QThread):
    """Фоновый поток для чтения данных из COM-порта и записи в CSV-лог."""

    
    # Маппинг адресов → индексы станций в GUI
    STATION_ADDR_MAP = {
        "0x15": 0,  # Станция МАРС-1
        "0x16": 1,  # Станция МАРС-2
        "0x17": 2,  # Станция МАРС-3
        "0x18": 3   # Станция МАРС-4
    }
    
    
    def __init__(self, port: str, baudrate: int = 9600, log_path: str = "logi.csv", timeout: float = 1.0):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.log_path = Path(log_path)
        self.timeout = timeout
        self.stop_flag = False
        self._ser = None

    def start(self) -> None:
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            
            with serial.Serial(self.port, self.baudrate, 
                               parity=serial.PARITY_NONE, 
                               stopbits=serial.STOPBITS_ONE, 
                               timeout=self.timeout) as self._ser:
                
                is_new_file = not self.log_path.exists() or self.log_path.stat().st_size == 0
                with open(self.log_path, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    if is_new_file:
                        writer.writerow(['Адрес', 'Время принятия', 'Сообщение', 'Потребление', 'Генерация'])

                    buffer = bytearray()
                    last_byte_time = time.time()
                    START_PACKET = b'Start packet:'
                    END_PACKET = b'\xFF\xFF\xFF'

                    while not self.stop_flag:
                        byte = self._ser.read(1)
                        if not byte:
                            # Если данных нет >5 сек, сбрасываем буфер
                            if time.time() - last_byte_time > 5.0:
                                buffer.clear()
                            self.msleep(1)  # Yield в цикл событий Qt
                            continue

                        last_byte_time = time.time()
                        buffer.extend(byte)

                        # Поиск начала пакета
                        if START_PACKET in buffer:
                            idx = buffer.find(START_PACKET)
                            buffer = buffer[idx + len(START_PACKET):]

                        # Поиск конца пакета
                        if len(buffer) >= 3 and buffer[-3:] == END_PACKET:
                            packet = buffer[:-3]    # Убираем END_PACKET
                            if packet:
                                address = packet[0]
                                address_hex = f"0x{address:02X}"
                                data = packet[1:]
                                
                                # Проверка адреса
                                if address_hex not in self.STATION_ADDR_MAP:
                                    buffer.clear()  # Очищаем буфер для следующего пакета
                                    continue  # Игнорируем пакеты с данными, если адрес не в маппинге
                                
                                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                
                                # Обработка пакета
                                if len(data) >= 1:
                                    if data[0] == 0xFE and len(data) >= 3:
                                        # Пакет с потреблением и генерацией
                                        consumption_byte = data[1]
                                        generation_byte = data[2]
                                        consumption = int((consumption_byte / 255) * 1000)
                                        generation = int((generation_byte / 255) * 1000)
                                        writer.writerow([address_hex, timestamp, "", consumption, generation])
                                    else:
                                        # Текстовое сообщение: удаляем Start packet: и декодируем
                                        message = data.decode("utf-8", errors='replace')
                                        writer.writerow([address_hex, timestamp, message, "", ""])
                                
                                csvfile.flush()  # Гарантируем запись на диск для чтения из main
                            buffer.clear()

        except serial.SerialException as e:
            print(f"[SerialLogger] Ошибка порта: {e}")
        except Exception as e:
            print(f"[SerialLogger] Критическая ошибка: {e}")
        finally:
            print("[SerialLogger] Поток чтения завершён.")

    def stop(self) -> None:
        """Безопасная остановка потока."""
        self.stop_flag = True
        # timeout=1 гарантирует, что read(1) вернёт b'' максимум через 1 сек,
        # после чего цикл проверит stop_flag и корректно выйдет.
        self.wait(2000)
        
if __name__ == "__main__":
    import time
    # Создаем логгер
    logger = SerialLoggerThread(
        port="COM13",
        baudrate=9600,
        log_path="logi.csv",
        timeout=1.0
    )
    
    # Запускаем
    print("Запуск логгера...")
    logger.start()
    
    # Ждем 30 секунд или пока пользователь не нажмет Enter
    print("Логгер будет работать 30 секунд...")
    time.sleep(30)
    
    # Останавливаем
    print("Остановка логгера...")
    logger.stop()
    
    pass