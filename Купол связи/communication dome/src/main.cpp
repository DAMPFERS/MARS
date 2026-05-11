#include <Arduino.h>

// КУПОЛ СВЯЗИ


#include "NecEncoder.h"
#include "GyverOLED.h"    // Для работы с дисплеем
// #include "NecDecoder.h" 


#define IR_PIN 3  // Пин для подключения ИК-приемника

#define DOM_ADDRESS   0x15
#define SERIAL_SPEED  9600

#define SIZE_BUFFER 128


NecEncoder ir(IR_PIN);                                // Создаем объект для кодирования ИК-сигналов
// NecDecoder ir;                                // Создаем объект для декодирования ИК-сигналов

GyverOLED<SSD1306_128x64, OLED_NO_BUFFER> oled;  // Инициализация OLED-дисплея
#define SCALE 1


// void irIsr();                         // Функция для чтения ИК сигнала приемником



void setup() {
  pinMode(IR_PIN, OUTPUT);  // Настраиваем пин для ИК-приемника как вход
  Serial.begin(SERIAL_SPEED); // Инициализация последовательного порта для отладки
  oled.init();        // Инициализация экрана
  oled.clear();       // Очистка экрана
  oled.setScale(SCALE);   // Масштаб текста (1..4)
  oled.home();        // Курсор в (0,0)
  oled.println("Ready 0_o");  // Сообщение о готовности
  delay(1000);
  // attachInterrupt(0, irIsr, FALLING); // Привязываем прерывание к функции irIsr на спад сигнала
}

void loop() {
  static char input_buffer[SIZE_BUFFER];  // Статический буфер
  static int buffer_index = 0;             // Текущая позиция в буфере

  if (Serial.available() > 0) {
    char incoming_char = Serial.read(); // Читаем входящий символ

    // Проверяем, есть ли место в буфере
    if (buffer_index < SIZE_BUFFER - 1)
      input_buffer[buffer_index++] = incoming_char;  // Добавляем символ
     else {
      // Буфер переполнен, очищаем его
      buffer_index = 0;
      oled.clear();
      oled.home();
      oled.println("Buffer overflow!");
      delay(1000);
      oled.clear();
      oled.home();
    }

    // Если получен символ конца строки
    if (incoming_char == '\n') {
      input_buffer[buffer_index] = '\0';  // Завершаем строку

      // Отправляем данные по ИК
      for (int i = 0; i < buffer_index; i++) {
        ir.send(DOM_ADDRESS, input_buffer[i]);
        delay(50);
      }

      // Добавляем три байта 0xFF в конец пакета
      for (int i = 0; i < 3; i++) {
        ir.send(DOM_ADDRESS, 0xFF);
        delay(50);
      }

      // Отображаем на дисплее
      oled.clear();
      oled.home();
      oled.println("Sent: ");
      oled.println(input_buffer);

      // Очищаем буфер
      buffer_index = 0;
    }
  }
  
  // Проверяем, доступен ли ИК-сигнал
    // if (ir.available()) {}
      
  
}


// Функция для чтения ИК сигнала приемником
// void irIsr() {
//   ir.tick();  // Обрабатываем ИК-сигнал
//   return;
// }


