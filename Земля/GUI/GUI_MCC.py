# 1-7: Импорт стандартных библиотек
import sys  # Системные функции (аргументы командной строки, выход из приложения)
import pandas as pd  # Работа с CSV файлами (чтение данных)
import numpy as np  # Математические операции (генерация тестовых данных)
from datetime import datetime  # Получение текущего времени для часов в шапке

# 9-18: Импорт модулей PyQt5
from PyQt5.QtCore import Qt, QTimer, QRectF  # Qt - константы выравнивания, QTimer - таймер для часов, QRectF - прямоугольник для рисования
from PyQt5.QtGui import QColor, QPainter, QPen, QFont, QFontDatabase  # QColor - цвета, QPainter - рисование, QPen - перо/линии, QFont - шрифты
from PyQt5.QtWidgets import QApplication, QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget, QSizePolicy  # Все виджеты

import pyqtgraph as pg  # Библиотека для графиков

# 23-27: ГЛОБАЛЬНЫЕ ЦВЕТА
APP_BG = "#111B2E"  # Тёмно-синий фон всего приложения
PANEL_BG = "rgba(5, 10, 20, 200)"  # Полупрозрачный фон панелей (чёрный с прозрачностью 200/255)
CYAN = "#8FFFFF"  # Бирюзовый цвет для рамок и текста (как у графиков)
GREEN = "#00FF9D"  # Зелёный для статусов ONLINE и нормальных значений
YELLOW = "#FFB800"  # Жёлтый для предупреждений

# 33-71: КЛАСС HUD PANEL - панель с угловыми скобками
class HUDPanel(QFrame):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("hudPanel")  # Устанавливаем имя для CSS стилей
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Панель растягивается во все стороны

        self.layout = QVBoxLayout(self)  # Вертикальное расположение внутри панели
        self.layout.setContentsMargins(14, 14, 14, 14)  # Отступы от краёв панели до содержимого (14px со всех сторон)
        self.layout.setSpacing(10)  # Расстояние между заголовком и контентом (10px)

        h_layout = QHBoxLayout()  # Горизонтальный блок для заголовка
        h_layout.setContentsMargins(0, 0, 0, 0)  # Отступы внутри блока заголовка (0px - прижато к краям)
        self.title_label = QLabel(title)  # Метка с названием панели
        self.title_label.setObjectName("panelTitle")  # Имя для CSS
        h_layout.addWidget(self.title_label)  # Добавляем название
        h_layout.addStretch()  # Растяжка, чтобы прижать название к левому краю
        self.layout.addLayout(h_layout)  # Добавляем блок заголовка в основную верт. компоновку

        self.content_layout = QVBoxLayout()  # Контейнер для основного содержимого панели
        self.content_layout.setContentsMargins(0, 0, 0, 0)  # Отступы внутри контейнера (0px)
        self.layout.addLayout(self.content_layout, stretch=1)  # Добавляем контент, stretch=1 - растягивается

        glow = QGraphicsDropShadowEffect()  # Эффект свечения
        glow.setBlurRadius(20)  # Радиус размытия свечения (20px)
        glow.setColor(QColor(143, 255, 255, 80))  # Цвет свечения - CYAN с прозрачностью 80
        glow.setOffset(0)  # Смещение свечения (0 - свечение равномерно во все стороны)
        self.setGraphicsEffect(glow)  # Применяем эффект свечения

    def paintEvent(self, event):  # Отрисовка угловых скобок по углам панели
        super().paintEvent(event)
        painter = QPainter(self)  # Создаём объект для рисования
        painter.setRenderHint(QPainter.Antialiasing)  # Включаем сглаживание
        rect = self.rect()  # Получаем прямоугольник панели

        pen = QPen(QColor(CYAN))  # Создаём перо цвета CYAN
        pen.setWidth(2)  # Толщина линии 2px
        painter.setPen(pen)

        size = 14  # Длина углового отрезка (14px)
        # Рисуем 8 отрезков - угловые скобки в каждом углу
        painter.drawLine(0, size, 0, 0)  # Левый верхний угол - вертикальная линия
        painter.drawLine(0, 0, size, 0)  # Левый верхний угол - горизонтальная линия
        painter.drawLine(rect.width() - size, 0, rect.width(), 0)  # Правый верхний угол
        painter.drawLine(rect.width(), 0, rect.width(), size)  # Правый верхний угол
        painter.drawLine(0, rect.height() - size, 0, rect.height())  # Левый нижний угол
        painter.drawLine(0, rect.height(), size, rect.height())  # Левый нижний угол
        painter.drawLine(rect.width() - size, rect.height(), rect.width(), rect.height())  # Правый нижний угол
        painter.drawLine(rect.width(), rect.height() - size, rect.width(), rect.height())  # Правый нижний угол

# 77-120: КЛАСС TELEMETRY PLOT - виджет для отображения графиков
class TelemetryPlotWidget(pg.PlotWidget):
    def __init__(self, title="", color=CYAN):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # График растягивается
        self.line_color = color
        self.setBackground((0, 0, 0, 0))  # Прозрачный фон графика
        
        self.plotItem.showGrid(x=False, y=False)  # Отключаем сетку на графике

        for axis in ("left", "bottom"):  # Для левой и нижней оси
            self.plotItem.getAxis(axis).setPen(pg.mkPen(CYAN, width=1))  # Цвет оси CYAN, толщина 1px
            self.plotItem.getAxis(axis).setTextPen(pg.mkPen(CYAN))  # Цвет текста на осях CYAN

        self.plotItem.setMenuEnabled(False)  # Отключаем контекстное меню графика
        self.plotItem.hideButtons()  # Прячем кнопки управления графиком
        self.plotItem.setContentsMargins(10, 10, 10, 10)  # Отступы внутри графика (10px)
        self.setMouseEnabled(x=False, y=False)  # Отключаем взаимодействие мышью

        self.glow_curve = self.plot(pen=pg.mkPen(color=(143, 255, 255, 60), width=8))  # Свечение под графиком (толщина 8px, прозрачность 60)
        self.main_curve = self.plot(pen=pg.mkPen(color=color, width=1))  # Основная линия графика (толщина 1px)

        self.scatter = pg.ScatterPlotItem(  # Красная точка на графике (активная точка)
            size=14, brush=pg.mkBrush(255, 80, 80), pen=pg.mkPen("white", width=2)  # Размер 14px, красная заливка, белая обводка толщиной 2px
        )
        self.addItem(self.scatter)

        self.title_label = QLabel(title)  # Название графика
        self.title_label.setStyleSheet(f"color: {CYAN}; font-size: 10px; padding-bottom: 4px;")

    def update_data(self, x, y, active_index=None):
        self.main_curve.setData(x, y)  # Обновляем основную линию
        self.glow_curve.setData(x, y)  # Обновляем свечение
        if active_index is not None and 0 <= active_index < len(x):
            self.scatter.setData([x[active_index]], [y[active_index]])  # Обновляем позицию красной точки

# 126-256: КЛАСС СТАНЦИЯ - блок с 4 квадратами (Энергетика, Связь, Материалы, Ровер)
class StationWidget(QWidget):
    def __init__(self, title, station_idx):
        super().__init__()
        self.station_idx = station_idx
        self.value_labels = {}  # Словарь для хранения ссылок на лейблы значений (ключ: (станция, id_параметра))
        
        # Основной layout - сетка 2x2 (два столбца, две строки)
        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Отступы от краёв виджета до сетки (0px)
        main_layout.setSpacing(5)  # Расстояние между 4 квадратами (5px)
        
        # 1. ЭНЕРГЕТИКА (верхний левый) - строка 0, столбец 0
        energy_widget = self._create_param_widget("ЭНЕРГЕТИКА", [
            ("Потребление", "0", "МВт", 0),  # (название, значение_по_умолчанию, единица_измерения, id_параметра)
            ("Генерация", "0", "МВт", 1),
            ("Накопитель", "0", "МВт", 2)
        ])
        main_layout.addWidget(energy_widget, 0, 0)
        
        # 2. СВЯЗЬ (верхний правый) - строка 0, столбец 1
        comm_widget = self._create_param_widget("СВЯЗЬ", [
            ("Скорость", "0", "Мбит/с", 3),
            ("Задержка", "0", "мс", 4),
            ("SNR", "0", "dB", 5)
        ])
        main_layout.addWidget(comm_widget, 0, 1)
        
        # 3. МАТЕРИАЛЫ (нижний левый) - строка 1, столбец 0
        materials_widget = self._create_param_widget("МАТЕРИАЛЫ", [
            ("Запас", "0", "кг", 6),
            ("Расход", "0", "кг/ч", 7),
            ("Доставка", "0", "дней", 8)
        ])
        main_layout.addWidget(materials_widget, 1, 0)
        
        # 4. РОВЕР (нижний правый) - строка 1, столбец 1
        rover_widget = self._create_param_widget("РОВЕР", [
            ("Заряд", "0", "%", 9),
            ("Дистанция", "0", "км", 10),
            ("Статус", "Активен", "", 11)
        ])
        main_layout.addWidget(rover_widget, 1, 1)
        
        # Растягиваем ячейки сетки 2x2 (чтобы квадраты занимали всё доступное место)
        main_layout.setColumnStretch(0, 1)  # 1-й столбец растягивается
        main_layout.setColumnStretch(1, 1)  # 2-й столбец растягивается
        main_layout.setRowStretch(0, 1)  # 1-я строка растягивается
        main_layout.setRowStretch(1, 1)  # 2-я строка растягивается
    
    def _create_param_widget(self, title, params):
        """Создаёт виджет для группы параметров (один квадрат: Энергетика, Связь и т.д.)"""
        widget = QFrame()
        # Стилизация квадрата: полупрозрачный фон, тонкая рамка, скругление углов
        widget.setStyleSheet("""
            QFrame {
                background-color: rgba(5, 10, 20, 100);
                border: 1px solid rgba(143, 255, 255, 40);
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(widget)  # Вертикальное расположение внутри квадрата
        layout.setContentsMargins(8, 8, 8, 8)  # Отступы от краёв квадрата до содержимого (8px со всех сторон)
        layout.setSpacing(20)  # Расстояние между элементами внутри квадрата (20px)
        
        # Заголовок квадрата (например "ЭНЕРГЕТИКА")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {CYAN}; font-size: 11px; font-weight: bold; border-bottom: 1px solid rgba(143,255,255,50); padding-bottom: 4px;")
        title_lbl.setAlignment(Qt.AlignCenter)  # Выравнивание заголовка по центру
        layout.addWidget(title_lbl)
        
        # Параметры (3 штуки: Потребление, Генерация, Накопитель и т.д.)
        for param_name, default_value, unit, param_id in params:
            param_layout = QHBoxLayout()  # Горизонтальное расположение для одного параметра
            param_layout.setContentsMargins(4, 2, 4, 2)  # Отступы вокруг строки параметра (лево=4, верх=2, право=4, низ=2)
            param_layout.setSpacing(8)  # Расстояние между элементами внутри строки (8px)
            
            # Название параметра (например "Потребление:")
            name_lbl = QLabel(f"{param_name}:")
            name_lbl.setStyleSheet("color: rgba(143, 255, 255, 160); font-size: 10px;")
            name_lbl.setMinimumWidth(70)  # Минимальная ширина для выравнивания всех названий
            
            # Значение параметра (число)
            value_lbl = QLabel(default_value)
            value_lbl.setStyleSheet(f"color: {GREEN}; font-size: 10px; font-weight: bold;")
            value_lbl.setAlignment(Qt.AlignRight)  # Выравнивание числа по правому краю
            value_lbl.setMinimumWidth(45)  # Минимальная ширина для выравнивания чисел
            
            # Единица измерения (МВт, Мбит/с, кг и т.д.)
            unit_lbl = QLabel(unit)
            unit_lbl.setStyleSheet("color: rgba(143, 255, 255, 120); font-size: 9px;")
            unit_lbl.setMinimumWidth(30)  # Минимальная ширина для выравнивания единиц
            
            param_layout.addWidget(name_lbl)  # Добавляем название
            param_layout.addStretch()  # Растяжка - прижимает число и единицу к правому краю
            param_layout.addWidget(value_lbl)  # Добавляем значение
            param_layout.addWidget(unit_lbl)  # Добавляем единицу измерения
            
            layout.addLayout(param_layout)  # Добавляем строку в вертикальный блок
            
            # Сохраняем ссылку на лейбл значения для последующего обновления
            self.value_labels[(self.station_idx, param_id)] = value_lbl
        
        layout.addStretch()  # Растяжка внизу - прижимает все параметры к верху, чтобы не было пустоты снизу
        return widget
    
    def set_param_value(self, param_id, value):
        """Устанавливает значение параметра по его ID"""
        key = (self.station_idx, param_id)
        if key in self.value_labels:
            self.value_labels[key].setText(str(value))

# 262-600: КЛАСС MAIN WINDOW - главное окно приложения
class MarsForecastApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)  # Убираем системную рамку окна
        self.drag_pos = None  # Для перетаскивания окна

        self.data = None  # Данные из CSV
        self.col_x = self.col_y1 = self.col_y2 = None  # Номера колонок для X, Y1, Y2
        self.active_point_index = None  # Индекс активной точки на графиках
        self.stations = []  # Список станций
        self.init_ui()

    def mousePressEvent(self, event):  # Для перетаскивания окна без рамки
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # Для перетаскивания окна без рамки
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def init_ui(self):
        self.setWindowTitle("MARS CONTROL CENTER")
        self.setGeometry(100, 100, 1600, 900)  # Размер окна: ширина 1600, высота 900

        central = QWidget()  # Центральный виджет
        self.setCentralWidget(central)

        self.main_layout = QVBoxLayout(central)  # Вертикальная компоновка для всего окна
        self.main_layout.setContentsMargins(10, 10, 10, 10)  # Отступы от края приложения (10px со всех сторон)
        self.main_layout.setSpacing(5)  # Расстояние между шапкой и сеткой со станциями (5px)

        self.create_header()  # Создаём шапку

        self.grid = QGridLayout()  # Сетка 2x3 (станции + графики)
        self.grid.setSpacing(5)  # Расстояние между станциями и графиками (5px)
        self.grid.setContentsMargins(0, 0, 0, 0)  # Отступы внутри сетки (0px)
        self.main_layout.addLayout(self.grid)

        # Создаём 4 станции
        self.stations.append(self._create_station("СТАНЦИЯ МАРС-1", 0))
        self.stations.append(self._create_station("СТАНЦИЯ МАРС-2", 1))
        self.stations.append(self._create_station("СТАНЦИЯ МАРС-3", 2))
        self.stations.append(self._create_station("СТАНЦИЯ МАРС-4", 3))

        # Располагаем в сетке:
        self.grid.addWidget(self.stations[0], 0, 0)  # Станция 1 в строке 0, столбце 0
        self.grid.addWidget(self._create_graphs(), 0, 1, 1, 2)  # Графики в строке 0, столбцах 1-2 (занимает 1 строку, 2 столбца)
        self.grid.addWidget(self.stations[1], 1, 0)  # Станция 2 в строке 1, столбце 0
        self.grid.addWidget(self.stations[2], 1, 1)  # Станция 3 в строке 1, столбце 1
        self.grid.addWidget(self.stations[3], 1, 2)  # Станция 4 в строке 1, столбце 2

        # Растягиваем столбцы и строки сетки, чтобы все элементы равномерно заполняли пространство
        self.grid.setColumnStretch(0, 1)  # 1-й столбец растягивается
        self.grid.setColumnStretch(1, 1)  # 2-й столбец растягивается
        self.grid.setColumnStretch(2, 1)  # 3-й столбец растягивается
        self.grid.setRowStretch(0, 1)  # 1-я строка растягивается
        self.grid.setRowStretch(1, 1)  # 2-я строка растягивается

        self.timer = QTimer()  # Таймер для обновления времени
        self.timer.timeout.connect(self.update_mars_time)  # Каждую секунду обновляем время
        self.timer.start(1000)  # Интервал 1000 мс (1 секунда)

        self.apply_styles()  # Применяем CSS стили

    def create_header(self):
        self.header = HUDPanel()  # Создаём панель для шапки
        self.header.setFixedHeight(48)  # Фиксированная высота шапки 48px
        
        self.header.title_label.hide()  # Прячем стандартный заголовок

        # Очищаем стандартный layout шапки
        self.header.layout.setContentsMargins(0, 0, 0, 0)
        self.header.layout.setSpacing(0)

        while self.header.layout.count():
            item = self.header.layout.takeAt(0)
            if item.widget(): item.widget().setParent(None)

        h_layout = QHBoxLayout()  # Создаём горизонтальный блок
        h_layout.setContentsMargins(12, 6, 12, 6)  # Отступы внутри шапки: лево=12, верх=6, право=12, низ=6
        h_layout.setSpacing(16)  # Расстояние между элементами в шапке (16px)

        title = QLabel("ЦЕНТР УПРАВЛЕНИЯ ПОЛЕТАМИ | ЗЕМЛЯ")  # Заголовок шапки
        title.setObjectName("mainTitle")
        title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self.time_label = QLabel("00:00:00")  # Время
        self.time_label.setObjectName("timeLabel")
        self.time_label.setAlignment(Qt.AlignVCenter)

        close_btn = QLabel("✕")  # Кнопка закрытия
        close_btn.setObjectName("closeBtn")
        close_btn.setAlignment(Qt.AlignCenter)
        close_btn.setCursor(Qt.PointingHandCursor)  # Курсор-рука при наведении
        close_btn.mousePressEvent = lambda e: self.close()  # Закрываем приложение при клике

        h_layout.addWidget(title)
        h_layout.addStretch()  # Растяжка между заголовком и временем
        h_layout.addWidget(self.time_label)
        h_layout.addWidget(close_btn)

        self.header.layout.addLayout(h_layout)
        self.main_layout.addWidget(self.header)

    def _create_station(self, title, panel_idx):
        """Создаёт панель станции с виджетом StationWidget"""
        panel = HUDPanel(title)
        station_widget = StationWidget(title, panel_idx)
        panel.content_layout.addWidget(station_widget)
        return panel

    def _create_graphs(self):
        """Создаёт панель с двумя графиками"""
        panel = HUDPanel("МЕТЕОДАТЧИКИ")
        self.wind_plot = TelemetryPlotWidget("СКОРОСТЬ ВЕТРА", CYAN)
        self.sun_plot = TelemetryPlotWidget("СОЛНЕЧНАЯ АКТИВНОСТЬ", YELLOW)

        panel.content_layout.addWidget(self.wind_plot.title_label)
        panel.content_layout.addWidget(self.wind_plot, stretch=1)  # stretch=1 - график растягивается
        panel.content_layout.addWidget(self.sun_plot.title_label)
        panel.content_layout.addWidget(self.sun_plot, stretch=1)
        return panel

    def set_station_param(self, station_idx, param_id, value):
        """Устанавливает значение параметра для станции"""
        if 0 <= station_idx < len(self.stations):
            station_widget = self.stations[station_idx].content_layout.itemAt(0).widget()
            if station_widget and isinstance(station_widget, StationWidget):
                station_widget.set_param_value(param_id, value)

    def load_data(self, csv_path, col_x, col_y1, col_y2):
        self.data = pd.read_csv(csv_path, header=None)  # Читаем CSV без заголовков
        self.col_x, self.col_y1, self.col_y2 = col_x, col_y1, col_y2
        self.update_plots()

    def update_plots(self):
        if self.data is None: return
        x = self.data.iloc[:, self.col_x].values  # X-данные (время, отсчёты)
        y1 = self.data.iloc[:, self.col_y1].values  # Y-данные для первого графика (скорость ветра)
        y2 = self.data.iloc[:, self.col_y2].values  # Y-данные для второго графика (солнечная активность)
        self.wind_plot.update_data(x, y1, self.active_point_index)
        self.sun_plot.update_data(x, y2, self.active_point_index)

    def set_active_point(self, index):
        self.active_point_index = index
        self.update_plots()

    def update_mars_time(self):
        self.time_label.setText(datetime.now().strftime("%H:%M:%S"))  # Обновляем время в шапке

    def apply_styles(self):
        # CSS стили для всего приложения
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {APP_BG}; }}
            QWidget {{ background-color: transparent; color: {CYAN}; font-family: "DPix_8pt", monospace; }}
            
            #hudPanel {{ background-color: {PANEL_BG}; border: 1px solid rgba(143,255,255,70); border-radius: 8px; }}
            #panelTitle {{ color: {CYAN}; font-size: 12px; font-weight: bold; letter-spacing: 0.5px; }}
            
            #mainTitle {{ 
                color: {CYAN}; font-size: 16px; font-weight: bold; letter-spacing: 1px; 
            }}
            #timeLabel {{ 
                color: {GREEN}; font-size: 15px; font-weight: bold; padding: 0 4px;
            }}
            
            #closeBtn {{ 
                color: {CYAN}; 
                font-size: 16px; 
                background: transparent; 
                border: none; 
                padding: 0; margin: 0; line-height: 1;
            }}
            #closeBtn:hover {{ color: #FF3355; }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(APP_BG))  # Заливаем фон

        # Рисуем внешний контур приложения
        pen_border = QPen(QColor(CYAN), 2)  # Цвет CYAN, толщина 2px
        painter.setPen(pen_border)
        painter.drawRect(QRectF(1, 1, self.width() - 2, self.height() - 2))  # Прямоугольник с отступом 1px

        # Рисуем фоновую сетку (дисплейный эффект)
        pen_grid = QPen(QColor(0x8F,0xFF,0xFF,50))  # CYAN с прозрачностью 50
        pen_grid.setWidth(1)  # Толщина 1px
        painter.setPen(pen_grid)
        spacing = 20  # Шаг сетки 20px
        for x in range(0, self.width(), spacing):  # Вертикальные линии
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), spacing):  # Горизонтальные линии
            painter.drawLine(0, y, self.width(), y)

        # Рисуем скан-линии (эффект старого монитора)
        scan_pen = QPen(QColor(0, 0, 0, 25))  # Чёрные с прозрачностью 25
        painter.setPen(scan_pen)
        for y in range(0, self.height(), 4):  # Каждые 4px
            painter.drawLine(0, y, self.width(), y)

# 606-649: MAIN - точка входа в программу
if __name__ == "__main__":
    app = QApplication(sys.argv)  # Создаём QApplication

    # Загружаем шрифт DPix_8pt.ttf из папки assets/fonts/
    font_path = "assets/fonts/DPix_8pt.ttf"
    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id != -1:  # Если шрифт загрузился успешно
        family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app.setFont(QFont(family, 10))  # Применяем шрифт размером 10
    else:
        app.setFont(QFont("Consolas", 10))  # Шрифт по умолчанию

    # Пытаемся прочитать forecast.csv, если нет - создаём тестовые данные
    try:
        pd.read_csv("forecast.csv")
    except FileNotFoundError:
        # Генерируем 100 точек: X = 0..99, Y1 = синус, Y2 = косинус
        np.savetxt("forecast.csv", np.column_stack((
            np.arange(100), np.sin(np.arange(100)/10), np.cos(np.arange(100)/10)
        )), delimiter=",")

    window = MarsForecastApp()  # Создаём главное окно
    window.load_data("forecast.csv", col_x=0, col_y1=1, col_y2=2)  # Загружаем данные (X-0, Y1-1, Y2-2)

    # Заполняем станции тестовыми данными
    for i in range(4):
        window.set_station_param(i, 0, f"{125 + i * 5:.1f}")   # Потребление (МВт)
        window.set_station_param(i, 1, f"{145 + i * 3:.1f}")   # Генерация (МВт)
        window.set_station_param(i, 2, f"{78 - i * 5:.1f}")    # Накопитель (МВт)
        window.set_station_param(i, 3, f"{128 + i * 20}")      # Скорость связи (Мбит/с)
        window.set_station_param(i, 4, f"{45 + i * 5}")        # Задержка (мс)
        window.set_station_param(i, 5, f"{22.5 - i * 2:.1f}")  # SNR (dB)
        window.set_station_param(i, 6, f"{1250 - i * 100}")    # Запас материалов (кг)
        window.set_station_param(i, 7, f"{12.5 + i * 2:.1f}")  # Расход (кг/ч)
        window.set_station_param(i, 8, f"{14 - i}")            # Доставка (дней)
        window.set_station_param(i, 9, f"{87 - i * 5}")        # Заряд ровера (%)
        window.set_station_param(i, 10, f"{34.2 + i * 8:.1f}") # Дистанция ровера (км)
        window.set_station_param(i, 11, "Активен")             # Статус ровера
    
    # Устанавливаем аварийные значения для станции 1 (МАРС-2)
    window.set_station_param(1, 1, "82.1")    # Генерация (дефицит)
    window.set_station_param(1, 2, "12.8")    # Накопитель (критически мало)
    window.set_station_param(1, 5, "8.2")     # SNR (низкий)
    window.set_station_param(1, 9, "34")      # Заряд ровера (низкий)
    
    # Статус "Ремонт" для станции 3 (МАРС-4)
    window.set_station_param(3, 11, "Ремонт")

    window.set_active_point(3)  # Активная точка на графиках (индекс 3)
    window.show()  # Показываем окно
    sys.exit(app.exec_())  # Запускаем цикл обработки событий