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
from NextionWork import Nextion
from tcp_data import localTCP




COM_PORT_DOM_ENERGY = "COM11"
COM_PORT_DOM_CONNECTION = "COM12"
COM_PORT_DOM_NEXTION = "COM13"

STATION_ADDRESS = "0x15"
STATION_ID = 1

IP_SSERVER = "127.0.0.1"
PORT_SERVER = 5005

FONTH_PATH = "GUI/assets/fonts/DPix_8pt.ttf"
WEATHER_CSV = Path("data/weather/forecast.csv")


def main() -> None:
    
    
    
    

    
    forecast_data = {
        "sun": (),
        "wind": (),
        "central_module_consumption": (),
        "energy_module_consumption": (),
        "residential_module_consumption": (),
        "communication_module_consumption": (),
        "full_consumption": ()  
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
        
        forecast_data["sun"] = tuple(df["sun"])
        forecast_data["wind"] = tuple(df["wind"])
        
        forecast_data["central_module_consumption"] = tuple(df["p_central"])
        forecast_data["energy_module_consumption"] = tuple(df["p_energy"])
        forecast_data["residential_module_consumption"] = tuple(df["p_live"])
        forecast_data["communication_module_consumption"] = tuple(df["p_conn"])
        res = []
        for i in range(len(forecast_data["central_module_consumption"])):
            res.append(forecast_data["central_module_consumption"][i] + forecast_data["energy_module_consumption"][i] + forecast_data["residential_module_consumption"][i] + forecast_data["communication_module_consumption"][i])
        forecast_data["full_consumption"] = tuple(res)

    # 3. Запуск фонового потока чтения порта
    serial_manager = serialDom.DeviceManager(COM_PORT_DOM_CONNECTION, COM_PORT_DOM_ENERGY)
    print(f"[Main] Попытка запустить Поток чтения ком портов: {COM_PORT_DOM_CONNECTION}, {COM_PORT_DOM_ENERGY}")
    
    # 4. Запуск фонового потока управления LED
    # led_strip = ledControl.LEDStrip(num_leds=165, pin=18, led_type="RGB")
    # print("[Main] Инициализация LED ленты завершена")
    
    # 5. Запуск TCP соединения
    client = localTCP.StationTCPClient(IP_SSERVER, PORT_SERVER)
    print(f"[Main] Попытка запустить поток TCP соединения: {IP_SSERVER}:{PORT_SERVER}")
    
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

        if tick_count is None:  tick_count = 0
        else:                   tick_count += 1
        
        # Получаем текущий такт игры из статуса сервера
        status = client.getStatus()
        tact_game = status['game_tick'] 
        
        # Обновление значений генерации с COM-порта (купол энергетики)
        energy_data["generation"] = serial_manager.getLastDataSolarPanels() 
        if energy_data["generation"] is None:
            energy_data["generation"] = [0] * 6
        energy_data["full_generation"] = sum(energy_data["generation"])
        
        
        # Баланс энергии: если генерация превышает потребление, заряжаем батареи, иначе разряжаем
        delta = energy_data["full_generation"] - forecast_data["full_consumption"][tact_game]
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
            

        
        
        if tick_count % 5 == 1:  # отправка данных на сервер каждые 5 секунд      
            client.send_station_data(
                station_id=STATION_ID,
                station_name="Station Alpha",
                consumption=forecast_data["full_consumption"][tact_game],
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
            
            gen = energy_data["full_generation"] * 255 / (1024 * 4)  # Масштабируем генерацию до диапазона 0-255
            gen = gen.to_bytes(1, byteorder='big', signed=False)
            
            consumption = forecast_data["full_consumption"][tact_game] * 255 / max(forecast_data["full_consumption"])  # Масштабируем потребление до диапазона 0-255
            consumption = consumption.to_bytes(1, byteorder='big', signed=False)
            serial_manager.sendToDeviceCommunication(gen + consumption)  # Отправляем данные в купол связи
            
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

            serial_manager.stop()
            print("[Main] Менеджер COM-портов остановлен")

        except Exception as e:
            print(f"[Main] Ошибка при очистке: {e}")
    
    app.aboutToQuit.connect(cleanup)
    
    window.show()
    sys.exit(app.exec_())    
    
    
    




if __name__ == "__main__":
    
    
    main()