#include <Arduino.h>

// ПРИЕМНИК NEC


// #include "NecEncoder.h"
#include "NecDecoder.h" 


#define IR_PIN 2  // Пин для подключения ИК-приемника

#define DOM_1_ADDRESS   0x15
#define DOM_2_ADDRESS   0x16
#define DOM_3_ADDRESS   0x17
#define DOM_4_ADDRESS   0x18

#define SERIAL_SPEED  9600

#define SIZE_BUFFER 256


// NecEncoder ir(IR_PIN);                                // Создаем объект для кодирования ИК-сигналов
NecDecoder ir;                                // Создаем объект для декодирования ИК-сигналов




void irIsr();                         // Функция для чтения ИК сигнала приемником



void setup() {
  pinMode(IR_PIN, INPUT);  // Настраиваем пин для ИК-приемника как вход
  Serial.begin(SERIAL_SPEED); // Инициализация последовательного порта для отладки
  attachInterrupt(0, irIsr, FALLING); // Привязываем прерывание к функции irIsr на спад сигнала
}

void loop() {
  static uint8_t start_packet_flags = false; // Флаг для отслеживания начала пакета
  static uint8_t ff_counter = 0; // Счетчик для отслеживания количества подряд идущих 0xFF
  // Проверяем, доступен ли ИК-сигнал
    if (ir.available()) {
      uint8_t ik_address = ir.readAddress();  // Читаем адрес и выводим его в шестнадцатеричном формате
      uint8_t ik_command = ir.readCommand();  // Читаем команду и выводим её в шестнадцатеричном формате
      
      if (!start_packet_flags) {
        Serial.print("Start packet: ");
        Serial.print(ik_address, HEX);
        start_packet_flags = true; // Устанавливаем флаг начала пакета
        ff_counter = 0; // Сбрасываем счетчик при начале нового пакета
      }
      else{
        Serial.print(ik_command);
        if (ik_command == 0xFF) {
          ff_counter++; // Увеличиваем счетчик при получении 0xFF
          
          if(ff_counter >= 3) { // Если получили 3 подряд 0xFF, считаем пакет завершенным
            start_packet_flags = false; // Сбрасываем флаг после окончания пакета
            ff_counter = 0; // Сбрасываем счетчик для следующего пакета
          }
        } 
        else {
          ff_counter = 0; // Сбрасываем счетчик при получении команды, отличной от 0xFF
        }
      }
    }
  
}


// Функция для чтения ИК сигнала приемником
void irIsr() {
  ir.tick();  // Обрабатываем ИК-сигнал
  return;
}


