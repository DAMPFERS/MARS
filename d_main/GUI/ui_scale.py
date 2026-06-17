# from PyQt5.QtWidgets import QApplication

BASE_DPI = 96

# screen = QApplication.primaryScreen()

UI_SCALE = 1.0

# if screen:
#     SCALE = screen.logicalDotsPerInch() / BASE_DPI
#     SCALE = UI_SCALE
# else:
#     SCALE = 1.0


def sx(v):
    return int(v * UI_SCALE)


def sp(v):
    return round(v * UI_SCALE, 1)