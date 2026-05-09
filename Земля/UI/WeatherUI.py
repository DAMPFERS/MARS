"""
Класс MarsForecastApp будет наследует QMainWindow и включать:


Атрибуты:
data: DataFrame с данными из CSV.
csv_path: путь к файлу CSV.
col_x, col_y1, col_y2: номера столбцов для графиков.
text_fields: список из 4 QLabel для отображения текста.
canvas: объект FigureCanvasQTAgg для графиков.
active_point_index: текущий индекс активной точки (по умолчанию None).

Методы:

load_data(csv_path, col_x, col_y1, col_y2): загрузка данных из CSV.
init_ui(): инициализация интерфейса (графики, текстовые поля, таймер).
update_mars_time(): обновление времени на Марсе (местное время).
set_text_field(index, value): установка значения текстового поля.
set_active_point(index): выделение активной точки на графиках.
update_plots(): перерисовка графиков с учётом активной точки.

"""



import sys
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QApplication, QFrame
)
from PyQt5.QtCore import QTimer, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MarsForecastApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = None
        self.csv_path = None
        self.col_x = None
        self.col_y1 = None
        self.col_y2 = None
        self.text_fields = []
        self.active_point_index = None
        self.canvas = None
        self.init_ui()

    def load_data(self, csv_path, col_x, col_y1, col_y2):
        """Загружает данные из CSV и сохраняет номера столбцов."""
        self.csv_path = csv_path
        self.col_x = col_x
        self.col_y1 = col_y1
        self.col_y2 = col_y2
        self.data = pd.read_csv(csv_path, header=None)
        self.update_plots()

    def init_ui(self):
        """Инициализация интерфейса."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # ===== Главный layout =====
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ==========================================================
        # Верхняя часть
        # ==========================================================
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setSpacing(10)

        # ----------------------------------------------------------
        # Левая часть сверху (левое верхнее текстовое поле)
        # ----------------------------------------------------------
        self.text_fields.append(self._create_text_field())
        top_layout.addWidget(self.text_fields[0], stretch=1)

        # ----------------------------------------------------------
        # Правая часть сверху (таймер + графики)
        # ----------------------------------------------------------
        right_top_widget = QWidget()
        right_top_layout = QVBoxLayout(right_top_widget)
        right_top_layout.setSpacing(10)

        # Таймер
        self.time_label = QLabel("Время на Марсе: 00:00:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            border: 1px solid black;
            padding: 5px;
        """)

        right_top_layout.addWidget(self.time_label, stretch=0)

        # Графики
        self.init_plots()
        right_top_layout.addWidget(self.canvas, stretch=1)

        top_layout.addWidget(right_top_widget, stretch=2)

        # Верхняя часть занимает половину окна
        main_layout.addWidget(top_widget, stretch=1)

        # ==========================================================
        # Нижняя часть
        # ==========================================================
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setSpacing(10)

        # Левое нижнее поле
        self.text_fields.append(self._create_text_field())
        bottom_layout.addWidget(self.text_fields[1], stretch=1)

        # Центральное нижнее поле
        self.text_fields.append(self._create_text_field())
        bottom_layout.addWidget(self.text_fields[2], stretch=1)

        # Правое нижнее поле
        self.text_fields.append(self._create_text_field())
        bottom_layout.addWidget(self.text_fields[3], stretch=1)

        # Нижняя часть занимает половину окна
        main_layout.addWidget(bottom_widget, stretch=1)

        # ==========================================================
        # Настройка окна
        # ==========================================================
        self.setWindowTitle("Mars Forecast")
        self.setGeometry(100, 100, 1400, 800)

        # Таймер
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_mars_time)
        self.timer.start(1000)

    def _create_text_field(self):
        """Создаёт текстовое поле."""
        text_field = QLabel("Текст")
        text_field.setWordWrap(True)
        text_field.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        text_field.setStyleSheet("""
            border: 2px solid black;
            border-radius: 5px;
            padding: 10px;
            background-color: white;
            font-size: 14px;
        """)

        text_field.setMinimumSize(250, 180)

        return text_field

    def init_plots(self):
        """Инициализирует графики (matplotlib)."""
        # Размер Figure в дюймах (ширина x высота)
        # При dpi=100: 6x4 дюйма = 600x400 пикселей
        self.figure = Figure(figsize=(6, 4), dpi=100)  # Размеры под 2/3 экрана по ширине и половину по высоте
        self.canvas = FigureCanvas(self.figure)
        self.ax1 = self.figure.add_subplot(211)
        self.ax2 = self.figure.add_subplot(212)

    def update_plots(self):
        """Обновляет графики с учётом активной точки."""
        if self.data is None:
            return

        self.ax1.clear()
        self.ax2.clear()

        x = self.data.iloc[:, self.col_x]
        y1 = self.data.iloc[:, self.col_y1]
        y2 = self.data.iloc[:, self.col_y2]

        self.ax1.plot(x, y1, 'b-', label='Яркость')
        self.ax2.plot(x, y2, 'g-', label='Скорость ветра')

        if self.active_point_index is not None and 0 <= self.active_point_index < len(x):
            self.ax1.plot(
                x.iloc[self.active_point_index],
                y1.iloc[self.active_point_index],
                'ro', markersize=10, label='Активная точка'
            )
            self.ax2.plot(
                x.iloc[self.active_point_index],
                y2.iloc[self.active_point_index],
                'ro', markersize=10, label='Активная точка'
            )

        self.ax1.legend()
        self.ax2.legend()
        self.canvas.draw()

    def update_mars_time(self):
        """Обновляет время на Марсе (местное время)."""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.setText(f"Время на Марсе: {current_time}")

    def set_text_field(self, index, value):
        """Устанавливает значение текстового поля."""
        if 0 <= index < len(self.text_fields):
            self.text_fields[index].setText(str(value))

    def set_active_point(self, index):
        """Выделяет активную точку на графиках."""
        self.active_point_index = index
        self.update_plots()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MarsForecastApp()
    window.load_data("forecast.csv", col_x=0, col_y1=1, col_y2=2)
    window.set_text_field(0, "Левое верхнее поле\nС несколькими строками")
    window.set_text_field(1, "Левое нижнее поле\nС несколькими строками")
    window.set_text_field(2, "Центральное нижнее поле\nС несколькими строками")
    window.set_text_field(3, "Правое нижнее поле\nС несколькими строками")
    window.set_active_point(3)
    window.show()
    sys.exit(app.exec_())