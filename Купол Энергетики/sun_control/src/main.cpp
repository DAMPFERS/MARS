#include <Arduino.h>

// КУПОЛ ЭНЕРГЕТИКИ
#include <Servo.h>  // Подключаем библиотеку Servo


#define SERVO_MIN_ANGLE 0
#define SERVO_MAX_ANGLE 360
#define SERVO_PIN_1 9
#define SERVO_PIN_2 10

#define ADC_PAUSE 1000 // Пауза между отправкой данных с аналоговых входов (в миллисекундах)

// Создаём объекты для сервомоторов
Servo servo1;
Servo servo2;

void setup() {
  // Подключаем сервомоторы к пинам
  servo1.attach(SERVO_PIN_1);  // Серво 1 на пине 9
  servo2.attach(SERVO_PIN_2); // Серво 2 на пине 10

  // Открываем Serial Port
  Serial.begin(9600);

  pinMode(SERVO_PIN_1, OUTPUT);
  pinMode(SERVO_PIN_2, OUTPUT);
  pinMode(A0, INPUT);
  pinMode(A1, INPUT);
  pinMode(A2, INPUT);
  pinMode(A3, INPUT);
  pinMode(A4, INPUT);
  pinMode(A5, INPUT); 

}

void loop() {

  static uint32_t timer = 0;
  if (millis() - timer > ADC_PAUSE) { // Проверяем, прошло ли ADC_PAUSE мс
    uint8_t adc_name[6] = {A0, A1, A2, A3, A4, A5};
    uint16_t adc_value[6];
    for (int i = 0; i < 6; i++) {
      adc_value[i] = analogRead(adc_name[i]); // Читаем значение с аналогового входа
      // Serial.write((adc_value[i] >> 8) & 0xFF); // Отправляем старший байт
      // Serial.write(adc_value[i] & 0xFF);        // Отправляем младший байт
      // Serial.print((float)adc_value[i] / 1023.0 * 5.0); // Отправляем значение входа
      Serial.print(adc_value[i]);
      Serial.print(';'); // Разделитель между значениями
    }
    Serial.print('\n'); // Новая строка после всех значений
    timer = millis(); // Сбрасываем таймер
  }



  if (Serial.available() >= 2) {
    // Читаем 2 байта
    byte byte1 = Serial.read();
    byte byte2 = Serial.read();

    // Преобразуем байты в углы (0-255 → 0-360)
    int angle1 = map(byte1, 0, 255, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);
    int angle2 = map(byte2, 0, 255, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);

    // Ограничиваем углы диапазоном 0-360 (на случай ошибок)
    angle1 = constrain(angle1, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);
    angle2 = constrain(angle2, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);


    // Устанавливаем углы для сервомоторов
    servo1.write(angle1);
    servo2.write(angle2);

    // Ждём, пока сервомоторы выполнят команду (опционально)
    delay(15);  // Минимальная задержка для стабильности
  }
}