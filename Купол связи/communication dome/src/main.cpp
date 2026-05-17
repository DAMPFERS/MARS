#include <Arduino.h>

// КУПОЛ СВЯЗИ


#include "NecEncoder.h"
#include "GyverOLED.h"    // Для работы с дисплеем
// #include "NecDecoder.h" 

#define PAUSE 50
#define IR_PIN 3  // Пин для подключения ИК-приемника

#define DOM_ADDRESS   0x15
#define SERIAL_SPEED  9600

#define SIZE_BUFFER 128


NecEncoder ir(IR_PIN);                                // Создаем объект для кодирования ИК-сигналов
// NecDecoder ir;                                // Создаем объект для декодирования ИК-сигналов

GyverOLED<SSD1306_128x64, OLED_NO_BUFFER> oled;  // Инициализация OLED-дисплея
#define SCALE 2


// void irIsr();                         // Функция для чтения ИК сигнала приемником



void setup() {
  pinMode(IR_PIN, OUTPUT);  // Настраиваем пин для ИК-приемника как вход
  Serial.begin(SERIAL_SPEED); // Инициализация последовательного порта для отладки
  oled.init();        // Инициализация экрана
  oled.clear();       // Очистка экрана
  oled.setScale(SCALE);   // Масштаб текста (1..4)
  oled.home();        // Курсор в (0,0)
  // oled.println("Купол готов к отправке");  // Сообщение о готовности
  oled.println("   MARS");
  oled.println("Купол готов");
  oled.println("к отправке");
  oled.println("  Данных");
  delay(1000);
  // attachInterrupt(0, irIsr, FALLING); // Привязываем прерывание к функции irIsr на спад сигнала
}

void loop() {
  static char input_buffer[SIZE_BUFFER];  // Статический буфер
  static uint8_t buffer_index = 0;             // Текущая позиция в буфере

  static uint32_t last_send_time = 0; // Время последней отправки данных
  static uint8_t counter_0xff = 0; // Счетчик для отправки 0xFF после каждого сообщения


  if (millis() - last_send_time > 1000) { // Проверяем, прошло ли 1 секунда с последней отправки
    
    // Очищаем буфер
    buffer_index = 0;
    counter_0xff = 0; // Сброс счетчика 0xFF
    last_send_time = millis(); // Обновляем время последней отправки
    
  }

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
      oled.println("Buffer \noverflow!");
      delay(1000);
      oled.clear();
      oled.home();
    }
    last_send_time = millis(); // Обновляем время последней активности
    
    // Если получен символ 0xFF, увеличиваем счетчик и проверяем, нужно ли отправлять данные
    if (incoming_char == 0xff) {
      counter_0xff++;
      if(counter_0xff >= 3) {
        counter_0xff = 0; // Сброс счетчика

        // Отправляем данные по ИК
        for (int i = 0; i < buffer_index; i++) {
          ir.send(DOM_ADDRESS, input_buffer[i]);
          Serial.print(input_buffer[i]);
          delay(PAUSE);
        }

        // Отображаем на дисплее
        oled.clear();
        oled.home();
        oled.println("Сообщение:");
        for (int i = 0; i < buffer_index; i++) {
          oled.print(input_buffer[i]);
          if ((i + 1) % 11 == 0) { // Переход на новую строку после определенного количества символов
            oled.println();
          }
        }
  
  
        last_send_time = millis(); // Обновляем время последней активности
        // Очищаем буфер
        buffer_index = 0;
      }
      
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


