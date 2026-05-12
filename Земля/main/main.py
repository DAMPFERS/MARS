import serial
import csv
import time
from datetime import datetime



# Настройки COM-порта
PORT = 'COM11'  # Уточните, если нужно изменить
BAUDRATE = 9600
PARITY = serial.PARITY_NONE
STOPBITS = serial.STOPBITS_ONE
TIMEOUT = 1  # Таймаут чтения (секунды)

# Имя файла для лога
CSV_FILE = 'logi.csv'

# Константы для парсинга
START_PACKET = b'Start packet: '
END_PACKET = b'\xFF\xFF\xFF'

def main():
    # Инициализация порта
    with serial.Serial(PORT, BAUDRATE, parity=PARITY, stopbits=STOPBITS, timeout=TIMEOUT) as ser:
        # Открываем CSV-файл для записи
        with open(CSV_FILE, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Записываем заголовки, если файл пустой
            if csvfile.tell() == 0:
                writer.writerow(['Адрес', 'Время принятия', 'Данные'])

            buffer = bytearray()
            last_byte_time = time.time()

            while True:
                try:
                    # Читаем 1 байт
                    byte = ser.read(1)
                    if not byte:
                        # Если данных нет, проверяем таймаут
                        if time.time() - last_byte_time > 5:
                            buffer = bytearray()  # Сбрасываем буфер
                        continue

                    last_byte_time = time.time()
                    buffer.extend(byte)

                    # Проверяем начало пакета
                    if START_PACKET in buffer:
                        # Находим начало пакета и обрезаем буфер
                        start_index = buffer.find(START_PACKET)
                        buffer = buffer[start_index + len(START_PACKET):]

                    # Проверяем конец пакета
                    if len(buffer) >= 3 and buffer[-3:] == END_PACKET:
                        # Удаляем завершающие байты
                        packet = buffer[:-3]
                        if len(packet) >= 1:  # Должен быть хотя бы адрес
                            address = packet[0]
                            data = packet[1:]
                            # Записываем в CSV
                            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            writer.writerow([f"0x{address:02X}", current_time, data.hex()])
                        buffer = bytearray()  # Сбрасываем буфер

                except KeyboardInterrupt:
                    print("\nЗавершение работы...")
                    break
                except Exception as e:
                    print(f"Ошибка: {e}")
                    buffer = bytearray()



if __name__ == '__main__':
    main()