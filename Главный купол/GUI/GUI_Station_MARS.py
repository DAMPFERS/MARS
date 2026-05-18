# 1-7: Импорт стандартных библиотек
import sys
import pandas as pd
import numpy as np
from datetime import datetime

# 9-14: Импорт модулей PyQt5
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QColor, QPainter, QPen, QFont, QFontDatabase, QGuiApplication
from PyQt5.QtWidgets import QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget, QSizePolicy

# 23-29: ГЛОБАЛЬНЫЕ ЦВЕТА И ШРИФТЫ
APP_BG = "#111B2E"
PANEL_BG = "rgba(5, 10, 20, 200)"
CYAN = "#8FFFFF"
GREEN = "#00FF9D"
YELLOW = "#FFB800"
RED = "#FF4D4D"
DARK_CYAN = "rgba(143, 255, 255, 30)"
ROW_BG = "rgba(5, 10, 20, 100)"

# Унифицированные стили шрифтов (УВЕЛИЧЕНЫ НА 1 ШАГ, ЦВЕТ ПОДПИСЕЙ = CYAN)
FONT_LABEL = f"color: {CYAN}; font-size: 11px;"
FONT_VALUE = f"color: {GREEN}; font-size: 12px; font-weight: bold;"
FONT_UNIT  = f"color: {CYAN}; font-size: 10px;"
FONT_TITLE = f"color: {CYAN}; font-size: 12px; font-weight: bold;"

# 35-75: КЛАСС HUD PANEL
class HUDPanel(QFrame):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("hudPanel")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(8)

        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("panelTitle")
        h_layout.addWidget(self.title_label)
        h_layout.addStretch()
        self.layout.addLayout(h_layout)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addLayout(self.content_layout, stretch=1)

        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(18)
        glow.setColor(QColor(143, 255, 255, 60))
        glow.setOffset(0)
        self.setGraphicsEffect(glow)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        pen = QPen(QColor(CYAN))
        pen.setWidth(2)
        painter.setPen(pen)

        size = 14
        painter.drawLine(0, size, 0, 0)
        painter.drawLine(0, 0, size, 0)
        painter.drawLine(rect.width() - size, 0, rect.width(), 0)
        painter.drawLine(rect.width(), 0, rect.width(), size)
        painter.drawLine(0, rect.height() - size, 0, rect.height())
        painter.drawLine(0, rect.height(), size, rect.height())
        painter.drawLine(rect.width() - size, rect.height(), rect.width(), rect.height())
        painter.drawLine(rect.width(), rect.height() - size, rect.width(), rect.height())

# === ВИЗУАЛЬНЫЙ HUD-ИНДИКАТОР ЗАРЯДА ===
class ChargeBarWidget(QWidget):
    def __init__(self, label="Нак. #1"):
        super().__init__()
        self.level = 0.0
        self.label = label
        self.setMinimumHeight(28)

    def set_level(self, value):
        self.level = max(0.0, min(1.0, value))
        self.update()

    def _get_color(self):
        if self.level > 0.6: return GREEN
        if self.level > 0.25: return YELLOW
        return RED

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        painter.setPen(QPen(QColor(CYAN), 1))
        painter.setBrush(QColor(DARK_CYAN))
        painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 3, 3)

        fill_w = (w - 6) * self.level
        color = QColor(self._get_color())
        color.setAlpha(180)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        if fill_w > 4:
            painter.drawRoundedRect(QRectF(3, 3, fill_w, h - 6), 2, 2)

        painter.setPen(QPen(QColor(0, 0, 0, 80), 1))
        for i in range(1, 10):
            x = 3 + (w - 6) * (i / 10)
            painter.drawLine(int(x), 3, int(x), int(h - 3))

        # УВЕЛИЧЕННЫЕ ШРИФТЫ
        painter.setPen(QColor(255, 255, 255, 220))
        font = painter.font()
        font.setPixelSize(11); font.setBold(False)
        painter.setFont(font)
        painter.drawText(QRectF(6, 0, w * 0.4, h), Qt.AlignVCenter | Qt.AlignLeft, self.label)

        painter.setPen(QColor(255, 255, 255, 250))
        font.setBold(True); font.setPixelSize(12)
        painter.setFont(font)
        painter.drawText(QRectF(w * 0.4, 0, w * 0.6 - 6, h), Qt.AlignVCenter | Qt.AlignRight, f"{self.level * 100:.0f}%")

# === СОСТОЯНИЕ СТАНЦИИ (TITLE CASE, CYAN ЦВЕТ) ===
class StationStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.labels = {}
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)

        frame = QFrame()
        frame.setStyleSheet("background: rgba(0,0,0,60); border: 1px solid rgba(143,255,255,25); border-radius: 3px;")
        f_layout = QVBoxLayout(frame)
        f_layout.setContentsMargins(8, 6, 8, 6)
        f_layout.setSpacing(4)

        # Заголовки с заглавной буквы
        metrics = [("Давление", "кПа"), ("Кислород", "%"), ("Углекислый газ", "ppm"), ("Герметичность", "%"), ("Температура", "°C")]
        for name, unit in metrics:
            r = QHBoxLayout()
            r.setContentsMargins(4, 2, 4, 2)
            r.addWidget(QLabel(f"{name}:", styleSheet=FONT_LABEL))
            r.addStretch()
            lbl_v = QLabel("0")
            lbl_v.setStyleSheet(FONT_VALUE)
            lbl_v.setAlignment(Qt.AlignRight)
            r.addWidget(lbl_v)
            r.addWidget(QLabel(unit, styleSheet=FONT_UNIT))
            f_layout.addLayout(r)
            self.labels[name] = lbl_v

        main_layout.addWidget(frame)
        main_layout.addStretch()

# === МОДУЛЬ СВЯЗИ ===
class CommsDetailWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.labels = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setStyleSheet("background: rgba(0,0,0,60); border: 1px solid rgba(143,255,255,25); border-radius: 3px;")
        f_layout = QVBoxLayout(frame)
        f_layout.setContentsMargins(6, 5, 6, 5)
        f_layout.setSpacing(2)

        params = [
            ("Мощность лазера", "0", "Вт"),
            ("Длина волны", "1550", "нм"),
            ("Скорость канала", "0", "Мбит/с"),
            ("Буфер передачи", "0", "%"),
            ("Сигнал/Шум", "0", "dB"),
            ("Ошибки пакетов", "0", "/ч"),
            ("Время сеанса", "00:00:00", ""),
            ("Статус линка", "ONLINE", "")
        ]
        for name, def_val, unit in params:
            r = QHBoxLayout()
            r.setContentsMargins(4, 2, 4, 2)
            r.addWidget(QLabel(f"{name}:", styleSheet=FONT_LABEL))
            r.addStretch()
            val = QLabel(def_val)
            val.setStyleSheet(FONT_VALUE)
            val.setAlignment(Qt.AlignRight)
            r.addWidget(val)
            if unit:
                r.addWidget(QLabel(unit, styleSheet=FONT_UNIT))
            f_layout.addLayout(r)
            self.labels[name] = val

        layout.addWidget(frame)
        layout.addStretch()

# === МАРСОХОД (ВОДОРОДНАЯ СИСТЕМА) ===
class RoverDetailWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.labels = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setStyleSheet("background: rgba(0,0,0,60); border: 1px solid rgba(143,255,255,25); border-radius: 3px;")
        f_layout = QVBoxLayout(frame)
        f_layout.setContentsMargins(6, 5, 6, 5)
        f_layout.setSpacing(2)

        params = [
            ("Уровень H₂", "0", "%"),
            ("Давление в системе", "0", "МПа"),
            ("Температура ячейки", "0", "°C"),
            ("Выходная мощность", "0", "кВт"),
            ("Запас хода", "0", "км"),
            ("Статус привода", "Активен", "")
        ]
        for name, def_val, unit in params:
            r = QHBoxLayout()
            r.setContentsMargins(4, 2, 4, 2)
            r.addWidget(QLabel(f"{name}:", styleSheet=FONT_LABEL))
            r.addStretch()
            val = QLabel(def_val)
            val.setStyleSheet(FONT_VALUE)
            val.setAlignment(Qt.AlignRight)
            r.addWidget(val)
            if unit:
                r.addWidget(QLabel(unit, styleSheet=FONT_UNIT))
            f_layout.addLayout(r)
            self.labels[name] = val

        layout.addWidget(frame)
        layout.addStretch()

# === ЭНЕРГОСИСТЕМА ===
class EnergyDetailWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.labels = {}
        self.charge_bars = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)

        # 1. ГЕНЕРАЦИЯ
        gen_frame = QFrame()
        gen_frame.setStyleSheet(f"background: {ROW_BG}; border: 1px solid rgba(143,255,255,40); border-radius: 4px;")
        gen_main = QVBoxLayout(gen_frame)
        gen_main.setContentsMargins(8, 6, 8, 6)
        gen_main.setSpacing(5)

        gen_title = QLabel("Генерация (Солнечные панели)")
        gen_title.setStyleSheet(FONT_TITLE)
        gen_title.setAlignment(Qt.AlignCenter)
        gen_main.addWidget(gen_title)

        gen_h = QHBoxLayout()
        gen_h.setSpacing(8)
        for block in ["Блок А", "Блок Б"]:
            b_frame = QFrame()
            b_frame.setStyleSheet("background: rgba(0,0,0,80); border: 1px solid rgba(143,255,255,25); border-radius: 3px;")
            b_layout = QVBoxLayout(b_frame)
            b_layout.setContentsMargins(6, 5, 6, 5)
            b_layout.setSpacing(2)

            b_lbl = QLabel(block)
            b_lbl.setStyleSheet(f"color: {YELLOW}; font-size: 11px; font-weight: bold; border-bottom: 1px solid rgba(143,255,255,40); padding-bottom: 3px;")
            b_lbl.setAlignment(Qt.AlignCenter)
            b_layout.addWidget(b_lbl)

            for i in range(6):
                r = QHBoxLayout(); r.setContentsMargins(2, 1, 2, 1)
                r.addWidget(QLabel(f"Панель {i+1}:", styleSheet=FONT_LABEL))
                v = QLabel("0.00"); v.setAlignment(Qt.AlignRight); v.setStyleSheet(FONT_VALUE)
                r.addWidget(v); r.addWidget(QLabel("МВт", styleSheet=FONT_UNIT))
                b_layout.addLayout(r)
                self.labels[f"{block}_{i}"] = v
            b_layout.addStretch()
            gen_h.addWidget(b_frame, stretch=1)
        gen_main.addLayout(gen_h)

        total_gen_layout = QHBoxLayout()
        total_gen_layout.setContentsMargins(4, 2, 4, 2)
        total_gen_layout.addWidget(QLabel("Общая генерация:", styleSheet=FONT_LABEL))
        total_gen_layout.addStretch()
        self.labels["total_gen"] = QLabel("0.00 МВт")
        self.labels["total_gen"].setStyleSheet(FONT_VALUE)
        total_gen_layout.addWidget(self.labels["total_gen"])
        gen_main.addLayout(total_gen_layout)

        main_layout.addWidget(gen_frame, stretch=2)

        # 2. НАКОПИТЕЛИ
        acc_frame = QFrame()
        acc_frame.setStyleSheet(f"background: {ROW_BG}; border: 1px solid rgba(143,255,255,40); border-radius: 4px;")
        acc_layout = QVBoxLayout(acc_frame)
        acc_layout.setContentsMargins(8, 6, 8, 6)
        acc_layout.setSpacing(5)

        acc_title = QLabel("Накопители энергии")
        acc_title.setStyleSheet(FONT_TITLE)
        acc_title.setAlignment(Qt.AlignCenter)
        acc_layout.addWidget(acc_title)

        self.charge_bars = []
        for i in range(3):
            bar = ChargeBarWidget(f"Нак. #{i+1}")
            bar.set_level(0.85 - i * 0.15)
            self.charge_bars.append(bar)
            acc_layout.addWidget(bar)

        total_acc_layout = QHBoxLayout()
        total_acc_layout.setContentsMargins(4, 2, 4, 2)
        total_acc_layout.addWidget(QLabel("Общий заряд:", styleSheet=FONT_LABEL))
        total_acc_layout.addStretch()
        self.labels["total_acc"] = QLabel("0 МВт·ч")
        self.labels["total_acc"].setStyleSheet(FONT_VALUE)
        total_acc_layout.addWidget(self.labels["total_acc"])
        acc_layout.addLayout(total_acc_layout)
        main_layout.addWidget(acc_frame, stretch=1)

        # 3. ПОТРЕБЛЕНИЕ
        con_frame = QFrame()
        con_frame.setStyleSheet(f"background: {ROW_BG}; border: 1px solid rgba(143,255,255,40); border-radius: 4px;")
        con_main_layout = QVBoxLayout(con_frame)
        con_main_layout.setContentsMargins(8, 6, 8, 6)
        con_main_layout.setSpacing(4)

        con_title = QLabel("Потребление по модулям")
        con_title.setStyleSheet(FONT_TITLE)
        con_title.setAlignment(Qt.AlignCenter)
        con_main_layout.addWidget(con_title)

        inner_frame = QFrame()
        inner_frame.setStyleSheet("background: rgba(0,0,0,60); border: 1px solid rgba(143,255,255,25); border-radius: 3px;")
        inner_layout = QVBoxLayout(inner_frame)
        inner_layout.setContentsMargins(6, 5, 6, 5)
        inner_layout.setSpacing(2)

        consumers = ["Жилой", "Связи", "Энергетический", "Центральный"]
        for i, name in enumerate(consumers):
            r = QHBoxLayout()
            r.setContentsMargins(4, 2, 4, 2)
            r.addWidget(QLabel(f"{name}:", styleSheet=FONT_LABEL))
            v_lbl = QLabel("0.00")
            v_lbl.setStyleSheet(FONT_VALUE)
            v_lbl.setAlignment(Qt.AlignRight)
            r.addWidget(v_lbl)
            r.addWidget(QLabel("МВт", styleSheet=FONT_UNIT))
            inner_layout.addLayout(r)
            self.labels[f"cons_{i}"] = v_lbl

        con_main_layout.addWidget(inner_frame, stretch=1)
        con_main_layout.addStretch()
        
        total_con_layout = QHBoxLayout()
        total_con_layout.setContentsMargins(4, 2, 4, 2)
        total_con_layout.addWidget(QLabel("Общее потребление:", styleSheet=FONT_LABEL))
        total_con_layout.addStretch()
        self.labels["total_cons"] = QLabel("0.00 МВт")
        self.labels["total_cons"].setStyleSheet(FONT_VALUE)
        total_con_layout.addWidget(self.labels["total_cons"])
        con_main_layout.addLayout(total_con_layout)
        
        main_layout.addWidget(con_frame, stretch=1)

# === ГЛАВНОЕ ОКНО ===
class Mars1App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.drag_pos = None
        self.is_fullscreen = False
        self.timer_1s = QTimer()
        self.timer_2s = QTimer()
        self.uptime = 0
        self.init_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.is_fullscreen:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos and not self.is_fullscreen:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def init_ui(self):
        self.setWindowTitle("MARS CONTROL STATION")
        
        screen = QGuiApplication.primaryScreen().availableGeometry()
        w = int(min(1500, screen.width() * 0.95))
        h = int(min(850, screen.height() * 0.95))
        self.setGeometry((screen.width() - w) // 2, (screen.height() - h) // 2, w, h)

        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(5)

        self.create_header()

        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(5)

        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)

        # Заголовки панелей остаются КАПСОМ
        self.status_panel = HUDPanel("СОСТОЯНИЕ СТАНЦИИ")
        self.comm_panel = HUDPanel("СВЯЗЬ")
        self.rover_panel = HUDPanel("МАРСОХОД")
        self.energy_panel = HUDPanel("ЭНЕРГОСИСТЕМА")

        self.status_widget = StationStatusWidget()
        self.comm_widget = CommsDetailWidget()
        self.rover_widget = RoverDetailWidget()
        self.energy_widget = EnergyDetailWidget()

        self.status_panel.content_layout.addWidget(self.status_widget)
        self.comm_panel.content_layout.addWidget(self.comm_widget)
        self.rover_panel.content_layout.addWidget(self.rover_widget)
        self.energy_panel.content_layout.addWidget(self.energy_widget, stretch=1)

        left_layout.addWidget(self.status_panel, stretch=0)
        left_layout.addWidget(self.comm_panel, stretch=0)
        left_layout.addWidget(self.rover_panel, stretch=0)
        left_layout.addStretch()

        content_layout.addWidget(left_col, 1)
        content_layout.addWidget(self.energy_panel, 1)

        self.main_layout.addWidget(content_widget, stretch=1)

        self.timer_1s.timeout.connect(self.update_mars_time)
        self.timer_1s.start(1000)
        self.timer_2s.timeout.connect(self.simulate_telemetry)
        self.timer_2s.start(2000)
        self.apply_styles()

    def create_header(self):
        self.header = HUDPanel()
        self.header.setFixedHeight(46)
        self.header.title_label.hide()
        self.header.layout.setContentsMargins(0, 0, 0, 0)
        self.header.layout.setSpacing(0)
        while self.header.layout.count():
            item = self.header.layout.takeAt(0)
            if item.widget(): item.widget().setParent(None)
            
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(12, 4, 12, 4)
        h_layout.setSpacing(14)

        title = QLabel("СТАНЦИЯ МАРС-1 | СЕКТОР ОЛИМП")
        title.setObjectName("mainTitle")
        title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self.time_label = QLabel("00:00:00")
        self.time_label.setObjectName("timeLabel")
        self.time_label.setAlignment(Qt.AlignVCenter)

        fullscreen_btn = QLabel("⛶")
        fullscreen_btn.setObjectName("fullscreenBtn")
        fullscreen_btn.setAlignment(Qt.AlignCenter)
        fullscreen_btn.setCursor(Qt.PointingHandCursor)
        fullscreen_btn.mouseReleaseEvent = self.create_fullscreen_handler()

        close_btn = QLabel("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setAlignment(Qt.AlignCenter)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.mouseReleaseEvent = lambda e: self.close()

        h_layout.addWidget(title)
        h_layout.addStretch()
        h_layout.addWidget(self.time_label)
        h_layout.addWidget(fullscreen_btn)
        h_layout.addWidget(close_btn)
        self.header.layout.addLayout(h_layout)
        self.main_layout.addWidget(self.header)

    def create_fullscreen_handler(self):
        def handler(event):
            if self.is_fullscreen: self.showNormal(); self.is_fullscreen = False
            else: self.showFullScreen(); self.is_fullscreen = True
        return handler

    def update_mars_time(self):
        self.time_label.setText(datetime.now().strftime("%H:%M:%S"))

    def simulate_telemetry(self):
        # НАКОПИТЕЛИ
        total_acc = 0
        for i in range(3):
            level = 0.88 - i * 0.12 + np.random.uniform(-0.02, 0.02)
            self.energy_widget.charge_bars[i].set_level(level)
            total_acc += level * 250
        self.energy_widget.labels["total_acc"].setText(f"{total_acc:.1f} МВт·ч")

        # ГЕНЕРАЦИЯ
        total_gen = 0
        for block in ["Блок А", "Блок Б"]:
            block_total = 0
            for i in range(6):
                val = 1.4 + np.random.uniform(0.3, 1.1)
                self.energy_widget.labels[f"{block}_{i}"].setText(f"{val:.2f}")
                block_total += val
            total_gen += block_total
        self.energy_widget.labels["total_gen"].setText(f"{total_gen:.2f} МВт")

        # ПОТРЕБЛЕНИЕ (УВЕЛИЧЕННЫЙ ШРИФТ В УСЛОВИИ)
        total_cons = 0
        for i in range(4):
            val = 3.2 + i * 0.8 + np.random.uniform(-0.15, 0.15)
            self.energy_widget.labels[f"cons_{i}"].setText(f"{val:.2f}")
            col = "#FF4D4D" if val > 5.0 else "#FFB800" if val > 4.2 else "#00FF9D"
            self.energy_widget.labels[f"cons_{i}"].setStyleSheet(f"color: {col}; font-size: 12px; font-weight: bold;")
            total_cons += val
        self.energy_widget.labels["total_cons"].setText(f"{total_cons:.2f} МВт")

        # СВЯЗЬ
        self.comm_widget.labels["Мощность лазера"].setText(f"{12.4 + np.random.uniform(-0.5, 0.5):.1f}")
        self.comm_widget.labels["Длина волны"].setText(f"{1550 + np.random.randint(-5, 5)}")
        self.comm_widget.labels["Скорость канала"].setText(f"{450 + np.random.randint(-20, 20)}")
        self.comm_widget.labels["Буфер передачи"].setText(f"{68 + np.random.randint(-10, 10)}")
        self.comm_widget.labels["Сигнал/Шум"].setText(f"{24.1 + np.random.uniform(-1.5, 1.5):.1f}")
        self.comm_widget.labels["Ошибки пакетов"].setText(str(np.random.randint(0, 5)))
        self.uptime += 2
        h, m, s = self.uptime//3600, (self.uptime%3600)//60, self.uptime%60
        self.comm_widget.labels["Время сеанса"].setText(f"{h:02}:{m:02}:{s:02}")
        st = self.comm_widget.labels["Статус линка"]
        st.setText("ONLINE")
        st.setStyleSheet(f"color: {GREEN}; font-size: 12px; font-weight: bold;")

        # МАРСОХОД (УВЕЛИЧЕННЫЙ ШРИФТ В УСЛОВИИ)
        h2_level = 85.5 + np.random.uniform(-2, 2)
        self.rover_widget.labels["Уровень H₂"].setText(f"{h2_level:.1f}")
        h2_lbl = self.rover_widget.labels["Уровень H₂"]
        h2_lbl.setStyleSheet(f"color: {'#FF4D4D' if h2_level < 20 else '#00FF9D'}; font-size: 12px; font-weight: bold;")
        
        self.rover_widget.labels["Давление в системе"].setText(f"{35.0 + np.random.uniform(-0.5, 0.5):.1f}")
        self.rover_widget.labels["Температура ячейки"].setText(f"{82 + np.random.uniform(-3, 3):.0f}")
        self.rover_widget.labels["Выходная мощность"].setText(f"{12.4 + np.random.uniform(-0.8, 0.8):.1f}")
        self.rover_widget.labels["Запас хода"].setText(f"{240 + np.random.randint(-5, 5)}")
        r_st = self.rover_widget.labels["Статус привода"]
        r_st.setText("Активен")
        r_st.setStyleSheet(f"color: {GREEN}; font-size: 12px; font-weight: bold;")

        # СОСТОЯНИЕ СТАНЦИИ
        self.status_widget.labels["Давление"].setText(f"{6.2 + np.random.uniform(-0.1, 0.1):.2f}")
        self.status_widget.labels["Кислород"].setText(f"{21.0 + np.random.uniform(-0.5, 0.5):.1f}")
        self.status_widget.labels["Углекислый газ"].setText(f"{420 + np.random.randint(-15, 15)}")
        self.status_widget.labels["Герметичность"].setText(f"{99.8 + np.random.uniform(-0.2, 0.2):.1f}")
        self.status_widget.labels["Температура"].setText(f"{22.5 + np.random.uniform(-1, 1):.1f}")

    def apply_styles(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {APP_BG}; }}
            QWidget {{ background-color: transparent; color: {CYAN}; font-family: "DPix_8pt", monospace; }}
            #hudPanel {{ background-color: {PANEL_BG}; border: 1px solid rgba(143,255,255,70); border-radius: 8px; }}
            #panelTitle {{ color: {CYAN}; font-size: 13px; font-weight: bold; letter-spacing: 0.5px; }}
            #mainTitle {{ color: {CYAN}; font-size: 16px; font-weight: bold; letter-spacing: 1px; }}
            #timeLabel {{ color: {GREEN}; font-size: 15px; font-weight: bold; padding: 0 4px; }}
            #fullscreenBtn {{ color: {CYAN}; font-size: 18px; background: transparent; border: none; padding: 0; margin: 0; line-height: 1; }}
            #fullscreenBtn:hover {{ color: {GREEN}; }}
            #closeBtn {{ color: {CYAN}; font-size: 16px; background: transparent; border: none; padding: 0; margin: 0; line-height: 1; }}
            #closeBtn:hover {{ color: #FF3355; }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(APP_BG))
        pen_border = QPen(QColor(CYAN), 2)
        painter.setPen(pen_border)
        painter.drawRect(QRectF(1, 1, self.width() - 2, self.height() - 2))
        pen_grid = QPen(QColor(0x8F, 0xFF, 0xFF, 50))
        pen_grid.setWidth(1)
        painter.setPen(pen_grid)
        spacing = 20
        for x in range(0, self.width(), spacing): painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), spacing): painter.drawLine(0, y, self.width(), y)
        scan_pen = QPen(QColor(0, 0, 0, 25))
        painter.setPen(scan_pen)
        for y in range(0, self.height(), 4): painter.drawLine(0, y, self.width(), y)

# === MAIN ===
if __name__ == "__main__":
    app = QApplication(sys.argv)
    font_path = "assets/fonts/DPix_8pt.ttf"
    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id != -1:
        family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app.setFont(QFont(family, 10))
    else:
        app.setFont(QFont("Consolas", 10))

    try: pd.read_csv("forecast.csv")
    except FileNotFoundError:
        np.savetxt("forecast.csv", np.column_stack((
            np.arange(100), np.sin(np.arange(100)/10)*50+50, np.cos(np.arange(100)/10)*30+70
        )), delimiter=",")

    window = Mars1App()
    window.show()
    sys.exit(app.exec_())