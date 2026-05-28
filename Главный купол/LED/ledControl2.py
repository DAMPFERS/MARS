
"""
Класс LEDStrip:

Атрибуты:

num_leds: общее количество светодиодов (165).
pin: пин GPIO (по умолчанию 18).
brightness: глобальная яркость (0-255).
sections: список секций, где каждая секция — это словарь с полями:

start: начальный индекс светодиода (включительно).
end: конечный индекс светодиода (включительно).
color: текущий цвет секции (кортеж RGB, например (255, 0, 0)).
brightness: яркость секции (0-255, может переопределять глобальную).


Методы:

__init__(self, num_leds, pin=18, sections=None): инициализация ленты и секций.
set_section_color(self, section_index, color): установка цвета для секции.
set_section_brightness(self, section_index, brightness): установка яркости для секции.
set_global_brightness(self, brightness): установка глобальной яркости.
show(self): применение изменений к ленте.
clear(self): отключение всех светодиодов.



Логическое разбиение на секции:

По умолчанию разобьём 165 светодиодов на 4 секции:

Секция 0: 0-40 (41 светодиод)
Секция 1: 41-81 (41 светодиод)
Секция 2: 82-122 (41 светодиод)
Секция 3: 123-164 (42 светодиода)

Если нужно другое разбиение, его можно будет передать при инициализации.


"""

import numpy as np
from rpi_ws281x import PixelStrip, Color
import time
import threading

class LEDStrip:
    
    def __init__(self, num_leds, pin=18, led_type="RGB", sections=None, global_brightness=255):
        """
        Инициализация ленты.

        Args:
            num_leds (int): Общее количество светодиодов.
            pin (int): Номер пина GPIO (по умолчанию 18).
            led_type (str): Тип ленты ("RGB" или "RGBW").
            sections (list): Список секций. Если None, создаётся стандартное разбиение на 4 секции.
            global_brightness (int): Глобальная яркость (0-255).
        """
        self.num_leds = num_leds
        self.pin = pin
        self.led_type  = led_type.upper()
        self.global_brightness = global_brightness
        
        # Инициализация ленты
        self.strip = PixelStrip(num_leds, pin)
        
        # Настройка типа ленты (RGB или RGBW)
        if self.led_type == "RGBW":
            self.strip.set_pixel_color = self._set_pixel_color_rgbw
        else:
            self.strip.set_pixel_color = self._set_pixel_color_rgb
            
        # Инициализация секций
        if  sections is None:
            # Стандартное разбиение на 4 секции
            section_size = num_leds // 4
            self.sections = [{"start": 0, "end": section_size - 1, "color": (0,0,0), "brightness":255},
                             {"start": section_size, "end": 2 * section_size - 1, "color": (0,0,0), "brightness":255},
                             {"start": 2 * section_size, "end": 3 * section_size - 1, "color": (0,0,0), "brightness":255},
                             {"start": 3 * section_size, "end": num_leds - 1, "color": (0,0,0), "brightness":255}
                             ]
        else:
            self.sections = sections
        
        self._stop_event = threading.Event()
        self._thread = None
        
        # Начальная установка  
        self.strip.begin()
        self.clear()
        self.show()
        
        
        
        
        
    def _set_pixel_color_rgb(self, pixel_index, color):
        """Установка цвета для RGB-ленты."""
        r, g, b = color[:3]
        self.strip.setPixelColor(pixel_index, Color(r, g, b))
    
    
    def _set_pixel_color_rgbw(self, pixel_index, color):
        """Установка цвета для RGBW-ленты."""
        r, g, b, w = color[:4]
        self.strip.setPixelColor(pixel_index, Color(r, g, b, w))
        
        
    def set_section_color(self, section_index, color):
        """
        Установка цвета для секции.

        Args:
            section_index (int): Индекс секции.
            color (tuple): Цвет в формате RGB или RGBW (в зависимости от типа ленты).
        """
        if (section_index < 0) or (section_index >= len(self.sections)):
            raise ValueError(f"Некорректный индекс секции: {section_index}")
        section = self.sections[section_index]
        section["color"] = color
        
        
    def set_section_brightness(self, section_index, brightness):
        """
        Установка яркости для секции.

        Args:
            section_index (int): Индекс секции.
            brightness (int): Яркость (0-255).
        """
        if (section_index < 0) or (section_index >= len(self.sections)):
            raise ValueError(f"Некорректный индекс секции: {section_index}")
        
        self.sections[section_index]["brightness"] = brightness
        
        
    def set_global_brightness(self, brightness):
        """Установка глобальной яркости."""
        self.global_brightness = brightness
  
        
    def show(self):
        """Применение изменений к ленте"""
        for section in self.sections:
            start = section["start"]
            end = section["end"]
            color = section["color"]
            section_brightness = section["brightness"]
            
            # Применяем глобальную яркость, если она ниже яркости секции
            brightness = min(self.global_brightness, section_brightness)
            
            for i in range(start, end + 1):
                if self.led_type == "RGBW":
                    r, g, b, w = color
                    r = int(r * brightness / 255)
                    g = int(g * brightness / 255)
                    b = int(b * brightness / 255)
                    w = int(w * brightness / 255)
                    self.strip.setPixelColor(i, Color(r, g, b, w))
                else:
                    r, g, b = color
                    r = int(r * brightness / 255)
                    g = int(g * brightness / 255)
                    b = int(b * brightness / 255)
                    self.strip.setPixelColor(i, Color(r, g, b))
        
        self.strip.show()
        
    def clear(self):
        """Отключение всех светодиодов."""
        for i in range(self.num_leds):
            if self.led_type == "RGBW":  self.strip.setPixelColor(i, Color(0, 0, 0, 0))
            else:                       self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()


    def startAnimationThread(self, animation_func, *args, **kwargs):
        """Запускает анимацию в отдельном потоке"""
        if self._thread and self._thread.is_alive():
            self.stopAnimationThread()  # Останавливаем предыдущую анимацию

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=animation_func,
            args=(self,) + args,
            kwargs=kwargs,
            daemon=True  # Поток завершится при завершении основной программы
        )
        self._thread.start()


    def stopAnimationThread(self):
        """Останавливает текущую анимацию"""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=1.0)  # Ждём завершения потока (максимум 1 секунда)
            self.clear()
            self.show()
    
    def isAnimationRunning(self):
        """Проверяет, запущена ли анимация"""
        return self._thread and self._thread.is_alive() and not self._stop_event.is_set()
    
    
def running_light_animation(strip, color=(255, 0, 0), speed=0.1):
    """Анимация бегущего огонька по всей ленте."""
    num_leds = strip.num_leds
    while not strip._stop_event.is_set():  # Проверяем флаг остановки
        for i in range(num_leds):
            if strip._stop_event.is_set():
                break
            strip.clear()
            strip.strip.setPixelColor(i, Color(*color))
            strip.strip.show()
            time.sleep(speed)

    


if __name__ == "__main__":
    # Создание ленты (RGB, 165 светодиодов, пин 18)
    strip = LEDStrip(num_leds=165, pin=18, led_type="RGB")
    
    # Запускаем анимацию в потоке
    strip.startAnimationThread(running_light_animation, color=(255, 0, 0), speed=0.05)
    
    
    time.sleep(10)
    
    strip.stopAnimationThread()
    
    
    
