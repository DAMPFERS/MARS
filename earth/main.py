# main.py
import sys
import csv
import numpy as np
from pathlib import Path
from PyQt5.QtCore import Qt, QTimer, QRectF, QSize  # Qt - константы выравнивания, QTimer - таймер для часов, QRectF - прямоугольник для рисования
from PyQt5.QtGui import QColor, QPainter, QPen, QFont, QFontDatabase  # QColor - цвета, QPainter - рисование, QPen - перо/линии, QFont - шрифты
from PyQt5.QtWidgets import QApplication, QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget, QSizePolicy  # Все виджеты
import threading
import io
from contextlib import redirect_stdout
from typing import List, Dict

from GUI import GUI_MCC
from Reciver import serial_logger
from weather import Weather_controller


# ─── Защита от наложения и блокировок stdout ───
_weather_lock = threading.Lock()
_is_weather_busy = False


# ─── КОНФИГУРАЦИЯ ПУТЕЙ ───
LOG_PATH = Path("data/logs/logi.csv")
WEATHER_CSV = Path("data/weather/forecast.csv")
# FONT_PATH = Path("GUI/assets/fonts/DPix_8pt.ttf")

FONT_PATH = "GUI/assets/fonts/DPix_8pt.ttf"
COM_PORT = "COM11"


# Маппинг адресов → индексы станций в GUI
STATION_ADDR_MAP = {
    "0x15": 0,  # Станция МАРС-1
    "0x16": 1,  # Станция МАРС-2
    "0x17": 2,  # Станция МАРС-3
    "0x18": 3   # Станция МАРС-4
}


def parseLatestConsumption(log_path: Path) -> dict:
    """
    Читает CSV-лог и возвращает список словарей для каждой станции.
    Индекс списка соответствует индексу станции в STATION_ADDR_MAP.
    Каждый словарь содержит ключи: "потребление", "генерация", "сообщение".

    Args:
        log_path (Path): Путь к файлу с логами.

    Returns:
        List[Dict[str, str | float]]: Список словарей с данными для каждой станции.
    """
    
    # Инициализируем результат: для каждой станции словарь с нулевыми значениями
    result = [ {
        {"потребление": 0, "генерация": 0, "сообщение": ""}
        for _ in STATION_ADDR_MAP
    }]
    
    if not log_path.exists():
        return result  # Если файл не существует, возвращаем нули
    
    
    
    # latest = {idx: 0 for idx in STATION_ADDR_MAP.values()}  # Инициализируем нулями
    
    with open(log_path, 'r', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)  # Чтение всех строк для поиска последних записей (обычно не очень большой файл)
        
        # Проходим по всем строкам и обновляем последние значения для каждой станции
        for row in rows:
            addr = row.get("Адрес", '').strip()
            
            if addr not in STATION_ADDR_MAP:
                continue  # Если адрес не распознан, пропускаем
            
            station_idx = STATION_ADDR_MAP[addr]
            
            # Обновляем сообщение, если оно есть
            message = row.get("Сообщение", '').strip()
            if message:
                result[station_idx]["сообщение"] = message
                
            # Обновляем потребление и генерацию, если они есть
            consumption = row.get("Потребление", '').strip()
            generation = row.get("Генерация", '').strip()
            
            if consumption:
                try:
                    result[station_idx]["потребление"] = int(consumption)
                except ValueError:
                    result[station_idx]["потребление"] = 0  # Если не число, оставляем 0
            if generation:
                try:
                    result[station_idx]["генерация"] = int(generation)
                except ValueError:
                    result[station_idx]["генерация"] = 0  # Если не число, оставляем 0
            
        return result    
            
            
                
def _sendWeatherTask(sun_val: int, wind_val: int) -> None:
    """Изолированная задача отправки погоды. Не трогает Qt, не блокирует stdout."""
    global _is_weather_busy
    try:
        # Подавляем print() из weather_cli, чтобы не блокировать Qt-stdout
        # with redirect_stdout(io.StringIO()):
        Weather_controller.set_all_weather(sun_val, wind_val)
        print(f"[Weather] Погода отправлена: Солнце={sun_val}, Ветер={wind_val}")
    except Exception as e:
        print(f"[Weather] Ошибка сети: {e}", file=sys.stderr)
    finally:
        with _weather_lock:
            _is_weather_busy = False



def main() -> None:
    
    global _is_weather_busy
    
    app = QApplication(sys.argv)
    
    # 1. Инициализация GUI
    # Получаем текущий DPI экрана
    # screen = QApplication.primaryScreen()
    # dpi = screen.physicalDotsPerInch()
    # scale_factor = dpi / 96.0  # 96 DPI — стандартное значение
    scale_factor = 1.0  # Отключаем масштабирование для тестов
    
    font_id = QFontDatabase.addApplicationFont(FONT_PATH)
    if font_id != -1:  # Если шрифт загрузился успешно
        family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app.setFont(QFont(family, int(6 * scale_factor)))  # Применяем шрифт
    else:
        app.setFont(QFont("Consolas", int(6 * scale_factor)))  # Шрифт по умолчанию
    
    
    window = GUI_MCC.MarsForecastApp()
    
    # 2. Подготовка/загрузка данных погоды для графиков
    if not WEATHER_CSV.exists():
        print(f"Ошибка: [Main] forecast.csv не найден {WEATHER_CSV}")
        return
    window.load_data(str(WEATHER_CSV), col_y1_name="Ветер", col_y2_name="Солнце")
    
    # 3. Запуск фонового потока чтения порта
    logger = serial_logger.SerialLoggerThread(port=COM_PORT, baudrate=9600, log_path=str(LOG_PATH))
          
    logger.start()        
    print(f"[Main] Попытка запустить Поток чтения (порт: {COM_PORT}, лог: {LOG_PATH})")      


    #TCP соединение
    server = Weather_controller.TCPReceiver()
    server.start()
    server.setOperationMode("Start")

    # 4. Таймер обновления GUI (каждые 10 секунд)
    update_timer = QTimer()
    update_timer.setInterval(10000)
    
    current_idx = 0  # Глобальный индекс для активной точки графика
    # Инициализация активной точки и отправка начальной погоды
    window.set_active_point(current_idx)
    window.update_plots()
    server.setGameTick(current_idx)
    
    
    # Установка начальной погоды
    if (window.data is not None) and (not _is_weather_busy):       
            try:
                sun_val = int(window.data["Солнце"][current_idx])
                wind_val = int(window.data["Ветер"][current_idx])
                # .iloc гарантирует скаляр, а не Series
                
                
                
                with _weather_lock:
                    print("0_o")
                    if not _is_weather_busy:     # Двойная проверка (race-condition защита)
                        _is_weather_busy = True  # Блокируем отправку, пока не завершится текущая
                    threading.Thread(
                        target=_sendWeatherTask, 
                        args=(sun_val, wind_val), 
                        daemon=True
                    ).start()
                
            except ValueError as ve:
                print(f"[Timer] Ошибка преобразования данных погоды: {ve}")
            except Exception as e:
                print(f"[Timer] Ошибка при запуске задачи погоды: {e}")
    
    
    
    #----------------------------------------------------------------------------###################################
    #Установка статических значений для всех станций
    ERROR_COLOR = "#D71212"  # Красный цвет для ошибок
    
    #1я станция
    window.set_station_block_glow(0, "ЭНЕРГЕТИКА", color="#E8EC19", intensity=120)
    window.set_station_block_glow(0, "СВЯЗЬ", color="#8FFFFF", intensity=50)
    window.set_station_block_glow(0, "МАТЕРИАЛЫ", color="#8FFFFF", intensity=50)
    window.set_station_block_glow(0, "РОВЕР", color="#D92424", intensity=120)
    # Ровер
    station_idx = 0
    window.set_station_param(station_idx, 9, "0", ERROR_COLOR)     # Заряд (%)
    window.set_station_param(station_idx, 10, "0", ERROR_COLOR)  # Дистанция (км)
    window.set_station_param(station_idx, 11, "0", ERROR_COLOR)    # Ресурсы (шт.)
    # Материалы
    window.set_station_param(station_idx, 6, "5/5")           # Семена
    window.set_station_param(station_idx, 7, "Готов") # Активатор
    window.set_station_param(station_idx, 8, "Готов")    # Биоматериал
    
    #2я станция
    window.set_station_block_glow(1, "ЭНЕРГЕТИКА", color="#D92424", intensity=120)
    window.set_station_block_glow(1, "СВЯЗЬ", color="#E8EC19", intensity=120)
    window.set_station_block_glow(1, "МАТЕРИАЛЫ", color="#8FFFFF", intensity=50)
    window.set_station_block_glow(1, "РОВЕР", color="#8FFFFF", intensity=50)
    # Ровер
    station_idx = 1
    window.set_station_param(station_idx, 9, "91")     # Заряд (%)
    window.set_station_param(station_idx, 10, "81")  # Дистанция (км)
    window.set_station_param(station_idx, 11, "27")    # Ресурсы (шт.)
    # Материалы
    window.set_station_param(station_idx, 6, "5/5")           # Семена
    window.set_station_param(station_idx, 7, "Готов") # Активатор
    window.set_station_param(station_idx, 8, "Готов")    # Биоматериал
    
    #3я станция
    window.set_station_block_glow(2, "ЭНЕРГЕТИКА", color="#8FFFFF", intensity=50)
    window.set_station_block_glow(2, "СВЯЗЬ", color="#D92424", intensity=120)
    window.set_station_block_glow(2, "МАТЕРИАЛЫ", color="#E8EC19", intensity=120)
    window.set_station_block_glow(2, "РОВЕР", color="#8FFFFF", intensity=50)
    # Ровер
    station_idx = 2
    window.set_station_param(station_idx, 9, "95")     # Заряд (%)
    window.set_station_param(station_idx, 10, "30")  # Дистанция (км)
    window.set_station_param(station_idx, 11, "10")    # Ресурсы (шт.)
    # Материалы
    window.set_station_param(station_idx, 6, "0/5", ERROR_COLOR)           # Семена
    window.set_station_param(station_idx, 7, "Не готов", ERROR_COLOR) # Активатор
    window.set_station_param(station_idx, 8, "Не готов", ERROR_COLOR)    # Биоматериал
    
    #4я станция
    window.set_station_block_glow(3, "ЭНЕРГЕТИКА", color="#8FFFFF", intensity=50)
    window.set_station_block_glow(3, "СВЯЗЬ", color="#8FFFFF", intensity=50)
    window.set_station_block_glow(3, "МАТЕРИАЛЫ", color="#D92424", intensity=120)
    window.set_station_block_glow(3, "РОВЕР", color="#E8EC19", intensity=120)
    # Ровер
    station_idx = 3
    window.set_station_param(station_idx, 9, "0", ERROR_COLOR)     # Заряд (%)
    window.set_station_param(station_idx, 10, "0", ERROR_COLOR)  # Дистанция (км)
    window.set_station_param(station_idx, 11, "0", ERROR_COLOR)    # Ресурсы (шт.)
    # Материалы
    window.set_station_param(station_idx, 6, "0/5", ERROR_COLOR)           # Семена
    window.set_station_param(station_idx, 7, "Не готов", ERROR_COLOR) # Активатор
    window.set_station_param(station_idx, 8, "Не готов", ERROR_COLOR)    # Биоматериал
    
    ################################################################################
    
    
    def onTimerTick():
        
        global _is_weather_busy
        nonlocal current_idx
        
        # --- Сдвиг активной точки графика ---
        current_idx = window.active_point_index
        if current_idx is None:
            current_idx = 0
        else:
            current_idx = (current_idx + 1) % 100  # Циклический переход (предполагая, что данных не менее 100 точек)
            # max_idx = len(window.data) - 1 if window.data is not None else 0
            # current_idx = (current_idx + 1) % (max_idx + 1) if max_idx >= 0 else 0  # Циклический переход   
        window.set_active_point(current_idx)
        window.update_plots()
        server.setGameTick(current_idx)
        
        
        # --- Обновление UI из Буффера для TCP ---
        # Получаем данные для каждой станции из TCPReceiver
        for station_idx in range(4):    # 4 станции (МАРС-1, МАРС-2, МАРС-3, МАРС-4)
            # station_id в TCPReceiver: 1, 2, 3, 4 (соответствуют индексам 0-3)
            station_data = server.getStationData(station_id=station_idx + 1)
            if station_data:
                params = station_data.get("params", {})
                
                # ЭНЕРГЕТИКА
                energy = params.get("energy", {})
                consumption = energy.get("consumption", 0)
                generation = energy.get("generation", 0)
                storage = energy.get("storage", 0)
                
                window.set_station_param(station_idx, 0, str(consumption))  # Потребление (МВт)
                window.set_station_param(station_idx, 1, str(generation))   # Генерация (МВт)
                window.set_station_param(station_idx, 2, str(storage))      # Накопитель (МВт)
                
                # СВЯЗЬ
                communication = params.get("communication", {})
                speed = communication.get("speed", 0)
                latency = communication.get("latency", 0)
                snr = communication.get("snr", 0)
                
                window.set_station_param(station_idx, 3, str(speed))    # Скорость (Мбит/с)
                window.set_station_param(station_idx, 4, str(latency))  # Задержка (мс)
                window.set_station_param(station_idx, 5, str(snr))      # SNR (dB)
                
                
                # МАТЕРИАЛЫ
                materials = params.get("materials", {})
                supply = materials.get("supply", 0)
                consumption_rate = materials.get("consumption_rate", 0)
                delivery_time = materials.get("delivery_time", 0)
                
                # window.set_station_param(station_idx, 6, str(supply))           # Запас (кг)
                # window.set_station_param(station_idx, 7, str(consumption_rate)) # Расход (кг/ч)
                # window.set_station_param(station_idx, 8, str(delivery_time))    # Доставка (дней)
                
                # РОВЕР
                rover = params.get("rover", {})
                charge = rover.get("charge", 0)
                distance = rover.get("distance", 0)
                status = rover.get("status", "Неизвестно")
                
                # window.set_station_param(station_idx, 9, str(charge))     # Заряд (%)
                # window.set_station_param(station_idx, 10, str(distance))  # Дистанция (км)
                # window.set_station_param(station_idx, 11, str(status))    # Статус
                
                
                
        # --- Обновление UI из логов ---
        # log_data = parseLatestConsumption(LOG_PATH)
        # print(log_data)
        # for idx in range(len(log_data)):
        #     station_data = log_data[idx]
        #     consumption = station_data.get("потребление", 0)
        #     generation = station_data.get("генерация", 0)
        #     message = station_data.get("сообщение", "")
            
        #     window.set_station_param(idx, param_id=0, value=str(consumption))  # param_id=0 для потребления
        #     window.set_station_param(idx, param_id=1, value=str(generation))   # param_id=1 для генерации
            # window.set_station_param(idx, param_id=2, value=message)          # param_id=2 для сообщения
             
          
                
        # Безопасная отправка погоды (ТОЛЬКО если предыдущая закончилась)
        if (window.data is not None) and (not _is_weather_busy):
            # print(window.data)
            # print(f"sun: {sun_val}")
            # print(f"wind: {wind_val}")
            
            try:
                sun_val = int(window.data["Солнце"][current_idx])
                wind_val = int(window.data["Ветер"][current_idx])
                # .iloc гарантирует скаляр, а не Series
                
                
                
                with _weather_lock:
                    print("0_o")
                    if not _is_weather_busy:     # Двойная проверка (race-condition защита)
                        _is_weather_busy = True  # Блокируем отправку, пока не завершится текущая
                    threading.Thread(
                        target=_sendWeatherTask, 
                        args=(sun_val, wind_val), 
                        daemon=True
                    ).start()
                
            except ValueError as ve:
                print(f"[Timer] Ошибка преобразования данных погоды: {ve}")
            except Exception as e:
                print(f"[Timer] Ошибка при запуске задачи погоды: {e}")
        
        
        
    update_timer.timeout.connect(onTimerTick)
    update_timer.start()
    
    # 5. Корректная обработка закрытия окна
    def cleanup():
        print("Завершение приложения...")
        server.stop()
        logger.stop()  # Остановка потока чтения порта
    
    app.aboutToQuit.connect(cleanup)
    
    window.show()
    sys.exit(app.exec_())

                
if __name__ == "__main__":
    print("Запуск приложения...")
    main()