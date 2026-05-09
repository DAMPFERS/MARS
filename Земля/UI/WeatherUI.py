import sys
import pandas as pd
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import (
    QColor,
    QPainter,
    QPen,
    QFont,
    QFontDatabase
)

from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QVBoxLayout,
    QWidget
)

import pyqtgraph as pg


# ============================================================
# ГЛОБАЛЬНЫЕ ЦВЕТА
# ============================================================

BG_DARK = "#FF0400FF"
PANEL_BG = "rgba(10, 25, 50, 180)"
# PANEL_BG = "rgba(255, 255, 250, 180)"


CYAN = "#8FFFFF"
CYAN_SOFT = "#6BE7E7"

GREEN = "#00FF9D"
YELLOW = "#FFB800"
RED = "#FF3355"

GRID = (143, 255, 255, 40)


# ============================================================
# HUD PANEL
# ============================================================

class HUDPanel(QFrame):
    """
    Sci-Fi панель как в HTML интерфейсе.
    """

    def __init__(self, title="", parent=None):
        super().__init__(parent)

        self.setObjectName("hudPanel")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(10)

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        self.header_layout = QHBoxLayout()

        self.title_label = QLabel(title)
        self.title_label.setObjectName("panelTitle")

        self.status_label = QLabel("ONLINE")
        self.status_label.setObjectName("panelStatus")

        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.status_label)

        self.layout.addLayout(self.header_layout)

        # glow effect
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(20)
        glow.setColor(QColor(143, 255, 255, 80))
        glow.setOffset(0)

        self.setGraphicsEffect(glow)

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        # ----------------------------------------------------
        # HUD CORNERS
        # ----------------------------------------------------

        pen = QPen(QColor(CYAN))
        pen.setWidth(2)

        painter.setPen(pen)

        size = 14

        # top left
        painter.drawLine(0, size, 0, 0)
        painter.drawLine(0, 0, size, 0)

        # top right
        painter.drawLine(rect.width() - size, 0, rect.width(), 0)
        painter.drawLine(rect.width(), 0, rect.width(), size)

        # bottom left
        painter.drawLine(0, rect.height() - size, 0, rect.height())
        painter.drawLine(0, rect.height(), size, rect.height())

        # bottom right
        painter.drawLine(
            rect.width() - size,
            rect.height(),
            rect.width(),
            rect.height()
        )

        painter.drawLine(
            rect.width(),
            rect.height() - size,
            rect.width(),
            rect.height()
        )


# ============================================================
# TELEMETRY PLOT
# ============================================================

class TelemetryPlotWidget(pg.PlotWidget):

    def __init__(self, title="", color=CYAN):
        super().__init__()

        self.line_color = color

        self.setBackground((0, 0, 0, 0))

        self.plotItem.showGrid(x=True, y=True, alpha=0.2)

        self.plotItem.getAxis("left").setPen(pg.mkPen(CYAN))
        self.plotItem.getAxis("bottom").setPen(pg.mkPen(CYAN))

        self.plotItem.getAxis("left").setTextPen(pg.mkPen(CYAN))
        self.plotItem.getAxis("bottom").setTextPen(pg.mkPen(CYAN))

        self.plotItem.setMenuEnabled(False)

        self.plotItem.hideButtons()

        self.plotItem.setContentsMargins(10, 10, 10, 10)

        # Disable mouse
        self.setMouseEnabled(x=False, y=False)

        # curves
        self.glow_curve = self.plot(
            pen=pg.mkPen(color=(143, 255, 255, 60), width=8)
        )

        self.main_curve = self.plot(
            pen=pg.mkPen(color=color, width=2)
        )

        self.scatter = pg.ScatterPlotItem(
            size=14,
            brush=pg.mkBrush(255, 80, 80),
            pen=pg.mkPen("white", width=2)
        )

        self.addItem(self.scatter)

        # title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"""
            color: {CYAN};
            font-size: 10px;
            padding-bottom: 4px;
        """)

    def update_data(self, x, y, active_index=None):

        self.main_curve.setData(x, y)
        self.glow_curve.setData(x, y)

        if active_index is not None:
            if 0 <= active_index < len(x):

                self.scatter.setData(
                    [x[active_index]],
                    [y[active_index]]
                )


# ============================================================
# MAIN WINDOW
# ============================================================

class MarsForecastApp(QMainWindow):

    def __init__(self):
        super().__init__()

        self.data = None

        self.col_x = None
        self.col_y1 = None
        self.col_y2 = None

        self.active_point_index = None

        self.text_fields = []

        self.init_ui()

    # ========================================================
    # UI
    # ========================================================

    def init_ui(self):

        self.setWindowTitle("MARS CONTROL CENTER")

        self.setGeometry(100, 100, 1600, 900)

        # ----------------------------------------------------
        # CENTRAL WIDGET
        # ----------------------------------------------------

        central = QWidget()

        self.setCentralWidget(central)

        self.main_layout = QVBoxLayout(central)

        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(16)

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        self.create_header()

        # ----------------------------------------------------
        # MAIN GRID
        # ----------------------------------------------------

        self.grid = QGridLayout()

        self.grid.setSpacing(16)

        self.main_layout.addLayout(self.grid)

        # ----------------------------------------------------
        # LEFT PANEL
        # ----------------------------------------------------

        self.left_panel = HUDPanel("СТАНЦИЯ МАРС-1")

        self.left_text = self.create_text_block()

        self.left_panel.layout.addWidget(self.left_text)

        self.grid.addWidget(self.left_panel, 0, 0)

        # ----------------------------------------------------
        # RIGHT PANEL (CHARTS)
        # ----------------------------------------------------

        self.charts_panel = HUDPanel("МЕТЕОДАТЧИКИ")

        self.wind_plot = TelemetryPlotWidget(
            "СКОРОСТЬ ВЕТРА",
            CYAN
        )

        self.sun_plot = TelemetryPlotWidget(
            "СОЛНЕЧНАЯ АКТИВНОСТЬ",
            YELLOW
        )

        self.charts_panel.layout.addWidget(
            self.wind_plot.title_label
        )

        self.charts_panel.layout.addWidget(
            self.wind_plot,
            stretch=1
        )

        self.charts_panel.layout.addWidget(
            self.sun_plot.title_label
        )

        self.charts_panel.layout.addWidget(
            self.sun_plot,
            stretch=1
        )

        self.grid.addWidget(self.charts_panel, 0, 1)

        # ----------------------------------------------------
        # BOTTOM PANELS
        # ----------------------------------------------------

        self.bottom1 = HUDPanel("СТАНЦИЯ МАРС-2")
        self.bottom2 = HUDPanel("СТАНЦИЯ МАРС-3")
        self.bottom3 = HUDPanel("СТАНЦИЯ МАРС-4")

        self.bottom1.layout.addWidget(
            self.create_text_block()
        )

        self.bottom2.layout.addWidget(
            self.create_text_block()
        )

        self.bottom3.layout.addWidget(
            self.create_text_block()
        )

        self.grid.addWidget(self.bottom1, 1, 0)
        self.grid.addWidget(self.bottom2, 1, 1)
        self.grid.addWidget(self.bottom3, 1, 2)

        # ----------------------------------------------------
        # GRID STRETCH
        # ----------------------------------------------------

        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 2)
        self.grid.setColumnStretch(2, 1)

        self.grid.setRowStretch(0, 2)
        self.grid.setRowStretch(1, 1)

        # ----------------------------------------------------
        # TIMER
        # ----------------------------------------------------

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.update_mars_time
        )

        self.timer.start(1000)

        # ----------------------------------------------------
        # STYLE
        # ----------------------------------------------------

        self.apply_styles()

    # ========================================================
    # HEADER
    # ========================================================

    def create_header(self):

        self.header = HUDPanel()

        self.header.setFixedHeight(110)

        self.header.status_label.hide()

        title = QLabel("ЦЕНТР УПРАВЛЕНИЯ ПОЛЕТАМИ")
        title.setObjectName("mainTitle")

        subtitle = QLabel(
            "СМЕНА М.А.Р.С. | МИССИЯ АВАРИЙНОГО РЕМОНТА"
        )

        subtitle.setObjectName("subTitle")

        self.time_label = QLabel("00:00:00")
        self.time_label.setObjectName("timeLabel")

        title.setAlignment(Qt.AlignCenter)
        subtitle.setAlignment(Qt.AlignCenter)
        self.time_label.setAlignment(Qt.AlignCenter)

        self.header.layout.addWidget(title)
        self.header.layout.addWidget(subtitle)
        self.header.layout.addWidget(self.time_label)

        self.main_layout.addWidget(self.header)

    # ========================================================
    # TEXT BLOCK
    # ========================================================

    def create_text_block(self):

        label = QLabel()

        label.setWordWrap(True)

        label.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        label.setObjectName("textBlock")

        label.setText(
            "СИСТЕМА ГОТОВА\n"
            "ТЕЛЕМЕТРИЯ АКТИВНА\n"
            "КАНАЛ ЗЕМЛЯ-МАРС СТАБИЛЕН"
        )

        self.text_fields.append(label)

        return label

    # ========================================================
    # LOAD DATA
    # ========================================================

    def load_data(
            self,
            csv_path,
            col_x,
            col_y1,
            col_y2
    ):

        self.data = pd.read_csv(
            csv_path,
            header=None
        )

        self.col_x = col_x
        self.col_y1 = col_y1
        self.col_y2 = col_y2

        self.update_plots()

    # ========================================================
    # UPDATE PLOTS
    # ========================================================

    def update_plots(self):

        if self.data is None:
            return

        x = self.data.iloc[:, self.col_x].values

        y1 = self.data.iloc[:, self.col_y1].values

        y2 = self.data.iloc[:, self.col_y2].values

        self.wind_plot.update_data(
            x,
            y1,
            self.active_point_index
        )

        self.sun_plot.update_data(
            x,
            y2,
            self.active_point_index
        )

    # ========================================================
    # ACTIVE POINT
    # ========================================================

    def set_active_point(self, index):

        self.active_point_index = index

        self.update_plots()

    # ========================================================
    # TIME
    # ========================================================

    def update_mars_time(self):

        current = datetime.now().strftime("%H:%M:%S")

        self.time_label.setText(current)

    # ========================================================
    # SET TEXT
    # ========================================================

    def set_text_field(self, index, value):

        if 0 <= index < len(self.text_fields):

            self.text_fields[index].setText(str(value))

    # ========================================================
    # STYLES
    # ========================================================

    def apply_styles(self):

        self.setStyleSheet(f"""

            QMainWindow {{
                background-color: {BG_DARK};
            }}

            QWidget {{
                background-color: transparent;
                color: {CYAN};
                font-family: "DPix_8pt";
            }}

            #hudPanel {{

                background-color: rgba(10,25,50,180);

                border: 1px solid rgba(143,255,255,70);

                border-radius: 8px;
            }}

            #panelTitle {{

                color: {CYAN};

                font-size: 11px;

                font-weight: bold;
            }}

            #panelStatus {{

                color: {GREEN};

                font-size: 10px;
            }}

            #mainTitle {{

                color: {CYAN};

                font-size: 22px;

                font-weight: bold;
            }}

            #subTitle {{

                color: rgba(143,255,255,180);

                font-size: 11px;
            }}

            #timeLabel {{

                color: {GREEN};

                font-size: 18px;

                padding-top: 8px;
            }}

            #textBlock {{

                border: none;

                background-color: rgba(143,255,255,15);

                padding: 10px;

                color: {CYAN};

                font-size: 11px;

                line-height: 18px;
            }}
        """)

    # ========================================================
    # BACKGROUND GRID
    # ========================================================

    def paintEvent(self, event):

        super().paintEvent(event)

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing)
        # Заполняем фон цветом BG_DARK
        painter.fillRect(self.rect(), QColor(BG_DARK))
        # ----------------------------------------------------
        # GRID
        # ----------------------------------------------------

        # pen = QPen(QColor(143, 255, 255, 20))
        pen = QPen(QColor(255, 255, 255, 200))
        pen.setWidth(1)

        painter.setPen(pen)

        spacing = 30

        width = self.width()
        height = self.height()

        for x in range(0, width, spacing):
            painter.drawLine(x, 0, x, height)

        for y in range(0, height, spacing):
            painter.drawLine(0, y, width, y)

        # ----------------------------------------------------
        # SCANLINES
        # ----------------------------------------------------

        scan_pen = QPen(QColor(0, 0, 0, 25))

        painter.setPen(scan_pen)

        for y in range(0, height, 4):
            painter.drawLine(0, y, width, y)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    # ========================================================
    # LOAD FONT
    # ========================================================

    font_id = QFontDatabase.addApplicationFont(
        "assets/fonts/DPix_8pt.ttf"
    )

    if font_id != -1:

        family = QFontDatabase.applicationFontFamilies(
            font_id
        )[0]

        app.setFont(QFont(family))

    # ========================================================
    # CREATE WINDOW
    # ========================================================

    window = MarsForecastApp()

    # ========================================================
    # LOAD CSV
    # ========================================================

    window.load_data(
        "forecast.csv",
        col_x=0,
        col_y1=1,
        col_y2=2
    )

    # ========================================================
    # TEST DATA
    # ========================================================

    window.set_text_field(
        0,
        "СТАТУС СТАНЦИИ:\n"
        "ЭНЕРГЕТИКА: ONLINE\n"
        "СВЯЗЬ: STABLE\n"
        "РОВЕР: ACTIVE"
    )

    window.set_text_field(
        1,
        "ПРОВОДИТСЯ\n"
        "КАЛИБРОВКА\n"
        "ЛАЗЕРНОГО МОДУЛЯ"
    )

    window.set_text_field(
        2,
        "СОЛНЕЧНАЯ АКТИВНОСТЬ:\n"
        "УМЕРЕННАЯ"
    )

    window.set_text_field(
        3,
        "МЕТЕОУСЛОВИЯ:\n"
        "ВЕТЕР 12.4 м/с"
    )

    window.set_active_point(3)

    window.show()

    sys.exit(app.exec_())