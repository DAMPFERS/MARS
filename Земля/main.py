# main.py
import sys
import csv
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import threading
import io
from contextlib import redirect_stdout


from GUI import GUI_MCC
from Reciver import serial_logger
from weather import Weather_controller


# ─── Защита от наложения и блокировок stdout ───
_weather_lock = threading.Lock()
_is_weather_busy = False


# ─── КОНФИГУРАЦИЯ ПУТЕЙ ───
LOG_PATH = Path("data/logs/logi.csv")
WEATHER_CSV = Path("data/weather/forecast.csv")
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
    Читает CSV-лог и возвращает dict {station_idx: consumption_value}.
    Если записи для станции нет, значение считается равным 0.

    Args:
        log_path (Path): Путь к файлу с логаими

    Returns:
        dict: _description_
    """
    
    latest = {idx: 0 for idx in STATION_ADDR_MAP.values()}  # Инициализируем нулями
    if not log_path.exists():
        return latest  # Если файл не существует, возвращаем нули
    
    with open(log_path, 'r', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            addr = row.get("Адрес", '').strip()
            if addr in STATION_ADDR_MAP:
                data_hex = row.get("Данные", '').strip()
                # 1-й байт = первые 2 символа hex-строки
                if len(data_hex) >= 2:
                    try:
                        latest[STATION_ADDR_MAP[addr]] = int(data_hex[:2], 16)
                    except ValueError:
                        latest[STATION_ADDR_MAP[addr]] = 0  # Если не удалось распарсить, считаем 0
    return latest
                
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
    app = QApplication(sys.argv)
    
    # 1. Инициализация GUI
    
    window = GUI_MCC.MarsForecastApp()
    
    # 2. Подготовка/загрузка данных погоды для графиков
    if not WEATHER_CSV.exists():
        print(f"Ошибка: [Main] forecast.csv не найден {WEATHER_CSV}")
        return
    window.load_data(str(WEATHER_CSV), col_x=0, col_y1=1, col_y2=2)
    
    # 3. Запуск фонового потока чтения порта
    # logger = serial_logger.SerialLogger(port=COM_PORT, baudrate=9600, log_path=str(LOG_PATH))      
    # logger.start()        
    # print(f"[Main] Поток чтения запущен (порт: {COM_PORT}, лог: {LOG_PATH})")      

    # 4. Таймер обновления GUI (каждые 10 секунд)
    update_timer = QTimer()
    update_timer.setInterval(10000)
    
    def onTimerTick():
        
        global _is_weather_busy
        
        # --- Сдвиг активной точки графика ---
        current_idx = window.active_point_index
        if current_idx is None:
            current_idx = 0
        else:
            max_idx = len(window.data) - 1 if window.data is not None else 0
            current_idx = (current_idx + 1) % (max_idx + 1) if max_idx >= 0 else 0  # Циклический переход
            
        window.set_active_point(current_idx)
        window.update_plots()
        
        # --- Обновление потребления из логов ---
        # consumptions = parseLatestConsumption(LOG_PATH)
        # for idx, val in consumptions.items():
        #     window.set_station_param(idx, param_id=0, value=str(val))  # param_id=0 для потребления
        
        # Безопасная отправка погоды (ТОЛЬКО если предыдущая закончилась)
        
        if (window.data is not None) and (not _is_weather_busy):
            try:
                # .iloc гарантирует скаляр, а не Series
                sun_val = int(window.data.iloc[current_idx][1])
                wind_val = int(window.data.iloc[current_idx][2])
                
                with _weather_lock:
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
        
        
        # if window.data is None:
        #     return  # Защита от отсутствия данных
        # try:
        #     # Надёжный доступ к DataFrame
        #     wind_val = int(window.data.iloc[current_idx][1])
        #     sun_val = int(window.data.iloc[current_idx][2])
            
        #     # Запуск в отдельном потоке. daemon=True гарантирует, что поток не помешает закрытию приложения.
        #     threading.Thread(
        #         target=Weather_controller.set_all_weather, 
        #         args=(sun_val, wind_val), 
        #         daemon=True
        #     ).start()
            
            
        # except ValueError as ve:
        #     print(f"[Timer] Ошибка преобразования данных погоды: {ve}")
        # except Exception as e:
        #     print(f"[Timer] Ошибка отправки погоды: {e}")
            
        # Weather_controller.set_all_weather(int(window.data[current_idx][1]), int(window.data[current_idx][2]))
        
        
    update_timer.timeout.connect(onTimerTick)
    update_timer.start()
    
    # 5. Корректная обработка закрытия окна
    def cleanup():
        print("Завершение приложения...")
        # logger.stop()  # Остановка потока чтения порта
    
    app.aboutToQuit.connect(cleanup)
    
    window.show()
    sys.exit(app.exec_())

                
if __name__ == "__main__":
    print("Запуск приложения...")
    main()