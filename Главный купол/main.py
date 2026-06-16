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
import random

from LED import ledControl
from GUI import GUI_Station_MARS
from GUI.ui_scale import sp, sx
from SerialControll import serialDom


# from NextionWork import Nextion
from tcp_data import localTCP



STATION_ADDRESS = "0x15"
STATION_ID = 1

IP_SERVER = "192.168.3.10"
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
    
    # Включаем поддержку High DPI
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    
    # Получаем текущий DPI экрана
    # screen = QApplication.primaryScreen()
    # dpi = screen.physicalDotsPerInch()
    # scale_factor = dpi / 96.0  # 96 DPI — стандартное значение
    
    # 1. Инициализация GUI
    font_id = QFontDatabase.addApplicationFont(FONTH_PATH)  # Загрузка шрифта
    if font_id != -1:
        family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app.setFont(QFont(family, int(10)))  # Масштабируем размер шрифта в зависимости от DPI
    else:
        app.setFont(QFont("Consolas", int(10)))
    
    window = GUI_Station_MARS.Mars1App()
    # 2. Подготовка/загрузка данных погоды
    
    if not WEATHER_CSV.exists():
        print(f"Ошибка: [Main] forecast.csv не найден {WEATHER_CSV}")
        sys.exit(1)
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

    # 3. Запуск менеджера COM-портов (Автоматический поиск всех устройств)
    print("[Main] Инициализация менеджера COM-портов...")
    serial_manager = serialDom.DeviceManager()
    # Даем пару секунд на автоопределение устройств в фоновых потоках
    # (Это не блокирует GUI, так как внутри DeviceManager используются QThread)
    import time
    time.sleep(2) 
    print("[Main] Менеджер COM-портов запущен. Поиск устройств завершен")
    
    
    # 4. Запуск фонового потока управления LED
    led_strip = ledControl.LEDStrip(num_leds=165, pin=18, led_type="RGB")
    print("[Main] Инициализация LED ленты завершена")
    
    # 5. Запуск TCP соединения
    client = localTCP.StationTCPClient(IP_SERVER, PORT_SERVER)
    client.start()  # Запуск в отдельном потоке
    print(f"[Main] Попытка запустить поток TCP соединения: {IP_SERVER}:{PORT_SERVER}")
    
    # 6. Таймер обновления GUI 
    update_timer = QTimer()
    update_timer.setInterval(1000)
    
    tick_count = 0
    tact_game = 0
    old_state_panels = 0
    
    # Новая переменная для отслеживания ручного режима
    is_manual_mode_active = False
    
    
    def onTimerTick():
        nonlocal tick_count
        nonlocal tact_game
        nonlocal old_state_panels
        nonlocal is_manual_mode_active
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
        
        
        # Проверка статуса Nextion
        nextion_device = serial_manager.getNextion()
        manual_mode_requested = False
        
        if nextion_device and nextion_device.nextion_connected:
            settings = nextion_device.page_settings
            colors = nextion_device.page_color
            
            # Проверяем, включен ли ручной режим на экране
            manual_mode_requested = (settings.get("Manual mode:", 0) == 1)
       
        # =========================================================================
        # === ЛОГИКА РУЧНОГО РЕЖИМА ===
        # =========================================================================
        if manual_mode_requested:
            is_manual_mode_active = True
            
            # 1. Управление панелями
            panel1_state = settings.get("Panel 1", 0)
            panel2_state = settings.get("Panel 2", 0)
            
            angle1 = 250 if panel1_state == 1 else 10
            angle2 = 250 if panel2_state == 1 else 10
            serial_manager.sendSolarAngles(angle1, angle2)
            
            # 2. Управление подсветкой модулей
            # Считываем глобальные настройки цвета и яркости с экрана
            r = 255 if colors.get("Red:", 0) == 1 else 0
            g = 255 if colors.get("Green:", 0) == 1 else 0
            b = 255 if colors.get("Blue:", 0) == 1 else 0
            power = colors.get("Power:", 120) # 0-255
            
            target_color = (r, g, b)
            
            # Словарь связывает: имя модуля -> (имя флага цвета, индекс секции ленты)
            modules_map = {
                "Main module:": ("Main color:", 0),
                "Conn module:": ("Conn color:", 1),
                "Live module:": ("Live color:", 2),
                "Energ module:": ("Energ color:", 3)
            }
            
            for mod_name, (color_flag_name, section_idx) in modules_map.items():
                # Проверяем ОБА условия: модуль включен И его цветовой флаг включен
                mod_is_on = (settings.get(mod_name, 0) == 1)
                color_is_on = (colors.get(color_flag_name, 0) == 1)
                
                if mod_is_on and color_is_on:
                    led_strip.set_section_color(section_idx, target_color)
                    led_strip.set_section_brightness(section_idx, power)
                else:
                    # Если хотя бы одно условие не выполнено, гасим этот модуль
                    led_strip.set_section_color(section_idx, (0, 0, 0))
                    led_strip.set_section_brightness(section_idx, 0)
                    
            led_strip.show()
            
            # Обновляем GUI статусом, чтобы было видно в интерфейсе
            telemetry_manual = {
                "Статус линка": "РУЧНОЙ РЕЖИМ",
                "Статус линка_style": "color: #FFB800; font-size: 14pt; font-weight: bold; "
            }
            window.update_from_main(telemetry_manual)
            
            # ВАЖНО: Прерываем выполнение функции, чтобы автоматическая логика не сработала
            return 



        # =========================================================================
        # === ЛОГИКА АВТОМАТИЧЕСКОГО РЕЖИМА ===
        # =========================================================================
        if is_manual_mode_active:
            # Если мы только что вышли из ручного режима, сбрасываем флаг
            is_manual_mode_active = False
            print("[Main] Возврат к автоматическому режиму")   
        
        
        # 0. ПРОВЕРКА И ПРИМЕНЕНИЕ ОБНОВЛЕНИЙ ОТ АДМИНА (кейс по энергетике)
        admin_updates = client.getPendingAdminUpdates()
        if admin_updates is not None:
            print("[Main] Получены обновления данных от администратора!")
        
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
        solar_device = serial_manager.getSolar()
        if solar_device and solar_device.last_solar_data:
            energy_data["generation"] = list(solar_device.last_solar_data)
        else:
            energy_data["generation"] = [0] * 6
        
        energy_data["full_generation"] = sum(energy_data["generation"])
        
        
        # Баланс энергии: если генерация превышает потребление, заряжаем батареи, иначе разряжаем
        delta = energy_data["full_generation"] - forecast_data["Полное потребление"][tact_game]
        # === УПРАВЛЕНИЕ ПОДСВЕТКОЙ МОДУЛЕЙ ===
        # 1. Определяем текущий такт с защитой от выхода за границы списка
        safe_tact = tact_game % len(forecast_data["Главный модуль"])
        
        # 2. Определяем цвет на основе энергобаланса (delta уже рассчитан выше)
        if delta >= 0:
            # Энергии достаточно: Зелено-голубой спектр с небольшим шумом
            # R: почти 0, G: высокий (180-255), B: высокий (150-255)
            r = 0
            g = 255
            b = 0
            target_color = (r, g, b)
        else:
            # Энергии не хватает: Красный спектр (можно добавить легкое мерцание через шум в G)
            r = 255
            g = 0
            b = 0
            target_color = (r, g, b)

        # 3. Сопоставляем модули с секциями ленты и обновляем их
        modules_mapping = [
            "Главный модуль",       # Секция 0
            "Модуль связи",         # Секция 1
            "Жилой модуль",         # Секция 2
            "Модуль энергетики"     # Секция 3
        ]
        
        for section_idx, module_name in enumerate(modules_mapping):
            # Получаем прогноз потребления (гарантируем, что число в диапазоне 0-100)
            forecast_val = forecast_data[module_name][safe_tact]
            forecast_val = max(0.0, min(100.0, float(forecast_val)))
            
            # Конвертируем 0-100 в яркость 0-255
            brightness = int(forecast_val * 2.55)
            
            # Применяем к ленте
            led_strip.set_section_color(section_idx, target_color)
            led_strip.set_section_brightness(section_idx, brightness)

        # 4. Отправляем обновленные данные на физическую ленту
        led_strip.show()
            
        
        
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
        if forecast_data["Состояние панелей"][tact_game] != old_state_panels:
            serial_manager.sendSolarAngles(250, 250) if forecast_data["Состояние панелей"][tact_game] == 1 else serial_manager.sendSolarAngles(10, 10) # Угол 250 - панели раскрыты, угол 10 - панели сложены
            old_state_panels = forecast_data["Состояние панелей"][tact_game]
        
        
            
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
            telemetry[f"cons_{i}_style"] = f"color: {col}; font-size: {sx(12)}pt; font-weight: bold;"
        
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
        telemetry["Статус линка_style"] = f"color: #00FF9D; font-size: {sx(12)}pt; font-weight: bold;"
        
        # h2 = 85.5 + np.random.uniform(-2, 2)
        h2 = rover_data["charge"] + np.random.uniform(-2, 2)
        rover_data["charge"] = h2  # Обновляем заряд в данных ровера
        telemetry["Уровень H₂"] = f"{h2:.1f}"
        telemetry["Уровень H₂_style"] = f"color: {'#FF4D4D' if h2 < 20 else '#00FF9D'}; font-size: {sx(12)}pt; font-weight: bold;"
        telemetry["Давление в системе"] = f"{35.0 + np.random.uniform(-0.5, 0.5):.1f}"
        telemetry["Температура ячейки"] = f"{82 + np.random.uniform(-3, 3):.0f}"
        telemetry["Выходная мощность"] = f"{12.4 + np.random.uniform(-0.8, 0.8):.1f}"
        rover_data["distance"] += np.random.uniform(0.5, 1.5)  # Увеличиваем дистанцию
        telemetry["Запас хода"] = f"{rover_data["distance"]:.1f}"
        telemetry["Статус привода"] = rover_data["status"]
        telemetry["Статус привода_style"] = f"color: #00FF9D; font-size: {sx(12)}pt; font-weight: bold;"

        # 4. Отправка в GUI
        window.update_from_main(telemetry)
        
        
        
        
        if tick_count % 5 == 1:  # отправка данных на сервер каждые 5 секунд 
            
            client.send_station_data(
                station_id=STATION_ID,
                station_name="Station Alpha",
                consumption=round(float(forecast_data["Полное потребление"][tact_game]), 1),
                generation=round(float(energy_data["full_generation"]), 1),
                storage=round(float(energy_data["battery1_level"] + energy_data["battery2_level"] + energy_data["battery3_level"]), 1),
                speed=round(float(connection_data["speed"]), 1),
                latency=round(float(connection_data["latency"]), 1),
                snr=round(float(connection_data["SNR"]), 1),
                supply=round(float(material_data["supply"]), 1),
                consumption_rate=round(float(material_data["consumption_rate"]), 1),
                delivery_time=round(float(material_data["delivery"]), 1),
                charge=round(float(rover_data["charge"]), 1),
                distance=round(float(rover_data["distance"]), 1),
                status=rover_data["status"]
            )
            # time.sleep(5)
            status = client.getStatus()
            print(f"Текущий такт: {status['game_tick']}, Режим: {status['operation_mode']}")
            
        
        if tick_count % 10 == 1: # отправка данных в купол связи каждые 10 секунд
            # 1. Отправка в купол связи (Transmitter)
            gen_byte = int(energy_data["full_generation"] * 255 / (1024 * 4)).to_bytes(1, byteorder='big', signed=False)
            
            # Защита от деления на ноль, если потребление пока нулевое
            max_cons = max(forecast_data["Полное потребление"]) if max(forecast_data["Полное потребление"]) > 0 else 1
            cons_byte = int(forecast_data["Полное потребление"][tact_game] * 255 / max_cons).to_bytes(1, byteorder='big', signed=False)
            
            # Отправляем (DeviceManager сам добавит \xFE в начало и \xFF\xFF\xFF в конец)
            serial_manager.sendToDeviceCommunication(gen_byte + cons_byte)

            # 2. Отправка углов в Solar (если нужно управлять панелями)
            # serial_manager.sendSolarAngles(45, 90)
            
            # 3. Отправка команды на экран Nextion
            # serial_manager.sendNextionCommand('t0.txt="HELLO"')
        
        
            
    
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

            serial_manager.stop()
            print("[Main] Менеджер COM-портов остановлен")

        except Exception as e:
            print(f"[Main] Ошибка при очистке: {e}")
    
    app.aboutToQuit.connect(cleanup)
    
    window.show()
    window.showFullScreen() 
    sys.exit(app.exec_())    
    

if __name__ == "__main__":  
    main()