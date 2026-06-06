import sys
import csv
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QColor, QPainter, QPen, QFont, QFontDatabase, QGuiApplication
from PyQt5.QtWidgets import QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget, QSizePolicy
import threading
import traceback


# from LED import ledControl
from GUI import GUI_Station_MARS
from SerialControll import serialDom
# from NextionWork import Nextion
from tcp_data import localTCP




# COM_PORT_DOM_ENERGY = "COM11"
# COM_PORT_DOM_CONNECTION = "COM12"
# COM_PORT_DOM_NEXTION = "COM13"

STATION_ADDRESS = "0x15"
STATION_ID = 1

IP_SERVER = "127.0.0.1"
PORT_SERVER = 5005

FONTH_PATH = "GUI/assets/fonts/DPix_8pt.ttf"
WEATHER_CSV = Path("data/weather/forecast.csv")


def main() -> None:
    
    
    
    

    
    forecast_data = {
        "Солнце": (),
        "Ветер": (),
        "Главный модуль": (),
        "Модуль связи": (),
        "Жилой модуль": (),
        "Модуль энергетики": (),
        "Состояние панелей": (),
        "Полное потребление": ()  
    }
    
    rover_data = {
        "charge": 0,
        "status": "Неактивен",
        "distance": 0
    }
    energy_data = {
        "battery1_level": 0,
        "battery2_level": 0,
        "battery3_level": 0,
        "max_battery_level": 1000,
        "full_generation": 0,
        "generation": [0] * 6
    }
    connection_data = {
        "speed": 128,
        "latency": 21,
        "SNR": 22.5
    }
    material_data = {
        "delivery": 981,
        "supply": 12.5,
        "consumption_rate": 13289.6
    }
    
    
    
    # === 0. Настройка обработки исключений ===
    def handle_exception(exc_type, exc_value, exc_traceback):
        print(f"[CRITICAL] Необработанное исключение: {exc_type.__name__}: {exc_value}")
        traceback.print_exception(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception
    
    
    app = QApplication(sys.argv)
    
    # 1. Инициализация GUI
    font_id = QFontDatabase.addApplicationFont(FONTH_PATH)  # Загрузка шрифта
    if font_id != -1:
        family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app.setFont(QFont(family, 10))
    else:
        app.setFont(QFont("Consolas", 10))
    
    window = GUI_Station_MARS.Mars1App()
    # 2. Подготовка/загрузка данных погоды
    
    if not WEATHER_CSV.exists():
        print(f"Ошибка: [Main] forecast.csv не найден {WEATHER_CSV}")
        return
    else:
        df = pd.read_csv(WEATHER_CSV)  # Загрузка данных из CSV в DataFrame
        
        forecast_data["Солнце"] = tuple(df["Солнце"])
        forecast_data["Ветер"] = tuple(df["Ветер"])
        
        forecast_data["Главный модуль"] = df["Главный модуль"]
        forecast_data["Модуль связи"] = df["Модуль связи"]
        forecast_data["Жилой модуль"] = df["Жилой модуль"]
        forecast_data["Модуль энергетики"] = df["Модуль энергетики"]
        forecast_data["Состояние панелей"] = df["Состояние панелей"]
        res = []
        for i in range(len(forecast_data["Главный модуль"])):
            res.append(forecast_data["Главный модуль"][i] + forecast_data["Модуль энергетики"][i] + forecast_data["Жилой модуль"][i] + forecast_data["Модуль связи"][i])
        forecast_data["Полное потребление"] = res

    # 3. Запуск фонового потока чтения порта
    # serial_manager = serialDom.DeviceManager(COM_PORT_DOM_CONNECTION, COM_PORT_DOM_ENERGY)
    # print(f"[Main] Попытка запустить Поток чтения ком портов: {COM_PORT_DOM_CONNECTION}, {COM_PORT_DOM_ENERGY}")
    
    # 4. Запуск фонового потока управления LED
    # led_strip = ledControl.LEDStrip(num_leds=165, pin=18, led_type="RGB")
    # print("[Main] Инициализация LED ленты завершена")
    
    # 5. Запуск TCP соединения
    client = localTCP.StationTCPClient(IP_SERVER, PORT_SERVER)
    print(f"[Main] Попытка запустить поток TCP соединения: {IP_SERVER}:{PORT_SERVER}")
    
    # 6. Таймер обновления GUI 
    update_timer = QTimer()
    update_timer.setInterval(1000)
    
    tick_count = 0
    tact_game = 0
    
    def onTimerTick():
        nonlocal tick_count
        nonlocal tact_game
        
        nonlocal energy_data
        nonlocal connection_data
        nonlocal material_data
        nonlocal rover_data
        
        nonlocal forecast_data

        if tick_count is None:  tick_count = 0
        else:                   tick_count += 1
        
        
        # Получаем текущий такт игры из статуса сервера
        status = client.getStatus()
        tact_game = status['game_tick'] 
        
        
        # ПРОВЕРКА И ПРИМЕНЕНИЕ ОБНОВЛЕНИЙ ОТ АДМИНА (кейс по энергетике)
        admin_updates = client.get_pending_admin_updates()
        if admin_updates is not None:
            print("[Main] ⚠️ Получены обновления данных от администратора!")
        
        for frame in admin_updates.get("frames", []):
            frame_data = frame.get("data", {})
            index_file = frame_data.get("index_file", 1)
            
            # Логика среза совпадает с логикой в скрипте админа
            start_idx = (index_file - 1) * 25
            end_idx = start_idx + 25
            
            columns_to_update = [
                "Главный модуль", "Модуль связи", "Жилой модуль", 
                "Модуль энергетики", "Состояние панелей"
            ]
            
            # 1. Обновляем оперативные данные (forecast_data)
            for col_name in columns_to_update:
                if col_name in frame_data:
                    new_values = frame_data[col_name]
                    current_list = list(forecast_data[col_name]) # Гарантируем тип list
                    
                    if len(new_values) == (end_idx - start_idx) and len(current_list) >= end_idx:
                        # Обновляем конкретный срез (25 значений)
                        current_list[start_idx:end_idx] = new_values
                    else:
                        # Fallback: если пришли все 100 значений, заменяем полностью
                        current_list = list(new_values)
                    
                    forecast_data[col_name] = current_list

            # 2. Пересчитываем "Полное потребление", так как компоненты изменились
            res = []
            length = len(forecast_data["Главный модуль"])
            for i in range(length):
                total = (forecast_data["Главный модуль"][i] + 
                         forecast_data["Модуль связи"][i] + 
                         forecast_data["Жилой модуль"][i] + 
                         forecast_data["Модуль энергетики"][i])
                res.append(total)
            forecast_data["Полное потребление"] = res
            print("[Main] Данные forecast_data и 'Полное потребление' пересчитаны")

            # 3. Сохраняем изменения обратно в CSV файл
            try:
                df = pd.read_csv(WEATHER_CSV)
                for col_name in columns_to_update:
                    if col_name in frame_data:
                        new_vals = frame_data[col_name]
                        if len(new_vals) == (end_idx - start_idx) and len(df) >= end_idx:
                            # Обновляем срез в DataFrame (loc включает правую границу, поэтому end_idx-1)
                            df.loc[start_idx:end_idx-1, col_name] = new_vals
                        else:
                            df[col_name] = list(new_vals)
                
                df.to_csv(WEATHER_CSV, index=False)
                print(f"[Main] ✅ Файл {WEATHER_CSV.name} успешно обновлен на диске.")
            except Exception as e:
                print(f"[Main] ❌ Ошибка при обновлении CSV файла: {e}")
        
        
        # Обновление значений генерации с COM-порта (купол энергетики)
        # energy_data["generation"] = serial_manager.getLastDataSolarPanels() 
        if energy_data["generation"] is None:
            energy_data["generation"] = [0] * 6
        energy_data["full_generation"] = sum(energy_data["generation"])
        
        
        # Баланс энергии: если генерация превышает потребление, заряжаем батареи, иначе разряжаем
        delta = energy_data["full_generation"] - forecast_data["Полное потребление"][tact_game]
        if delta >= 0: # достаточно энергии для покрытия потребления
            for i in range(3):
                if energy_data[f"battery{i+1}_level"] < energy_data["max_battery_level"]:
                    old_level = energy_data[f"battery{i+1}_level"]
                    energy_data[f"battery{i+1}_level"] = min(energy_data[f"battery{i+1}_level"] + delta, energy_data["max_battery_level"])
                    delta -= (energy_data[f"battery{i+1}_level"] - old_level)  # Уменьшаем delta на то, что добавили в батарею
                    if delta <= 0:
                        break
        else: # не хватает энергии, нужно разрядить батареи
            delta = -delta  # Теперь delta - это сколько энергии нам не хватает
            for i in range(3):
                if energy_data[f"battery{i+1}_level"] > 0:
                    old_level = energy_data[f"battery{i+1}_level"]
                    energy_data[f"battery{i+1}_level"] = max(energy_data[f"battery{i+1}_level"] - delta, 0)
                    delta -= (old_level - energy_data[f"battery{i+1}_level"])  # Уменьшаем delta на то, что отняли из батареи
                    if delta <= 0:
                        break
        
            
        # 3. Формирование телеметрии для GUI
        telemetry = {}
        # Энергетика (реальные данные)
        current_consumption = forecast_data["Полное потребление"][tact_game]
        telemetry["total_gen"] = f"{energy_data['full_generation']:.2f} МВт"
        for i, val in enumerate(energy_data["generation"]):
            telemetry[f"Блок А_{i}"] = f"{val:.2f}"
            telemetry[f"Блок Б_{i}"] = f"{val:.2f}"
        telemetry["total_cons"] = f"{current_consumption:.2f} МВт"
        cons_map = ["Главный модуль", "Модуль связи", "Жилой модуль", "Модуль энергетики"]
        for i, mod in enumerate(cons_map):
            val = forecast_data[mod][tact_game]
            telemetry[f"cons_{i}"] = f"{val:.2f}"
            # Пороговая окраска
            col = "#FF4D4D" if val > 5.0 else "#FFB800" if val > 4.2 else "#00FF9D"
            telemetry[f"cons_{i}_style"] = f"color: {col}; font-size: 12px; font-weight: bold;"
        
        # Батареи
        max_lvl = energy_data["max_battery_level"]
        telemetry["battery_levels"] = [energy_data[f"battery{i+1}_level"]/max_lvl for i in range(3)]
        telemetry["total_acc"] = f"{sum(energy_data[f'battery{i+1}_level'] for i in range(3)):.1f} МВт·ч"
        
        # Случайные флуктуации (эмуляция датчиков)
        telemetry["Давление"] = f"{6.2 + np.random.uniform(-0.1, 0.1):.2f}"
        telemetry["Кислород"] = f"{21.0 + np.random.uniform(-0.5, 0.5):.1f}"
        telemetry["Углекислый газ"] = f"{420 + np.random.randint(-15, 15)}"
        telemetry["Герметичность"] = f"{99.8 + np.random.uniform(-0.2, 0.2):.1f}"
        telemetry["Температура"] = f"{22.5 + np.random.uniform(-1, 1):.1f}"
        
        telemetry["Мощность лазера"] = f"{12.4 + np.random.uniform(-0.5, 0.5):.1f}"
        telemetry["Длина волны"] = f"{1550 + np.random.randint(-5, 5)}"
        connection_data['speed'] = connection_data['speed'] + np.random.randint(-20, 20)
        telemetry["Скорость канала"] = f"{connection_data['speed']}"
        telemetry["Буфер передачи"] = f"{68 + np.random.randint(-10, 10)}"
        connection_data['SNR'] = connection_data['SNR'] + np.random.uniform(-1.5, 1.5)
        telemetry["Сигнал/Шум"] = f"{connection_data['SNR']:.1f}"
        telemetry["Ошибки пакетов"] = str(np.random.randint(0, 5))
        h, m, s = tick_count // 3600, (tick_count % 3600) // 60, tick_count % 60
        telemetry["Время сеанса"] = f"{h:02}:{m:02}:{s:02}"
        telemetry["Статус линка"] = "ONLINE"
        telemetry["Статус линка_style"] = f"color: #00FF9D; font-size: 12px; font-weight: bold;"
        
        # h2 = 85.5 + np.random.uniform(-2, 2)
        h2 = rover_data["charge"] + np.random.uniform(-2, 2)
        rover_data["charge"] = h2  # Обновляем заряд в данных ровера
        telemetry["Уровень H₂"] = f"{h2:.1f}"
        telemetry["Уровень H₂_style"] = f"color: {'#FF4D4D' if h2 < 20 else '#00FF9D'}; font-size: 12px; font-weight: bold;"
        telemetry["Давление в системе"] = f"{35.0 + np.random.uniform(-0.5, 0.5):.1f}"
        telemetry["Температура ячейки"] = f"{82 + np.random.uniform(-3, 3):.0f}"
        telemetry["Выходная мощность"] = f"{12.4 + np.random.uniform(-0.8, 0.8):.1f}"
        rover_data["distance"] += np.random.uniform(0.5, 1.5)  # Увеличиваем дистанцию
        telemetry["Запас хода"] = f"{rover_data["distance"]:.1f}"
        telemetry["Статус привода"] = rover_data["status"]
        telemetry["Статус привода_style"] = f"color: #00FF9D; font-size: 12px; font-weight: bold;"

        # 4. Отправка в GUI
        window.update_from_main(telemetry)
        
        
        
        
        if tick_count % 5 == 1:  # отправка данных на сервер каждые 5 секунд      
            client.send_station_data(
                station_id=STATION_ID,
                station_name="Station Alpha",
                consumption=forecast_data["Полное потребление"][tact_game],
                generation=energy_data["full_generation"],
                storage=energy_data["battery1_level"] + energy_data["battery2_level"] + energy_data["battery3_level"],
                speed=connection_data["speed"],
                latency=connection_data["latency"],
                snr=connection_data["SNR"],
                supply=material_data["supply"],
                consumption_rate=material_data["consumption_rate"],
                delivery_time=material_data["delivery"],
                charge=rover_data["charge"],
                distance=rover_data["distance"],
                status=rover_data["status"], 
            )
            pass
        
        if tick_count % 10 == 1: # отправка данных в купол связи каждые 10 секунд
            gen = int(energy_data["full_generation"] * 255 / (1024 * 4))  # Масштабируем генерацию до диапазона 0-255
            gen = gen.to_bytes(1, byteorder='big', signed=False)
            
            consumption = int(forecast_data["Полное потребление"][tact_game] * 255 / max(forecast_data["Полное потребление"]))  # Масштабируем потребление до диапазона 0-255
            consumption = consumption.to_bytes(1, byteorder='big', signed=False)
            # serial_manager.sendToDeviceCommunication(gen + consumption)  # Отправляем данные в купол связи
            
            # serial_manager.sendToDeviceCommunication(b'\x01\x02\x03')  # Пример отправки данных в купол связи
            # serial_manager.sendToDeviceSolarPanels(45, 90)  # Пример отправ
        
        
            
    
    update_timer.timeout.connect(onTimerTick)
    update_timer.start()
    
    # 7. Корректная обработка закрытия окна
    def cleanup():
        print("[Main] Начало очистки ресурсов...")
        try:
            # Останавливаем таймер ПЕРВЫМ
            update_timer.stop()
            print("[Main] Таймер остановлен")

            # Останавливаем сетевые соединения и потоки
            client.stop()
            print("[Main] TCP-клиент остановлен")

            # serial_manager.stop()
            print("[Main] Менеджер COM-портов остановлен")

        except Exception as e:
            print(f"[Main] Ошибка при очистке: {e}")
    
    app.aboutToQuit.connect(cleanup)
    
    window.show()
    sys.exit(app.exec_())    
    
    
    




if __name__ == "__main__":
    
    
    main()