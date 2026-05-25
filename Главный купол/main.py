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

STATION_ADDRESS = {"0x15": 0}

IP_SSERVER = "127.0.0.1"
PORT_SERVER = 5005

FONTH_PATH = "GUI/assets/fonts/DPix_8pt.ttf"
WEATHER_CSV = Path("data/weather/forecast.csv")


def main() -> None:
    
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
        pd.read_csv(WEATHER_CSV)  # Проверка на валидность CSV
        
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
    
    def onTimerTick():
        nonlocal tick_count
        if tick_count is None:
            tick_count = 0
        else:
            # max_idx = len(window.data) - 1 if window.data is not None else 0
            # tick_count = (tick_count + 1) % (max_idx + 1) if max_idx >= 0 else 0  # Циклический переход
            tick_count += 1
        print(f"[Main] Таймер тик: {tick_count}")
        
        
            
    
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