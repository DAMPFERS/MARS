import numpy as np
import matplotlib.pyplot as plt

# Генерация прогноза солнца
def generate_sun_forecast(n=100):
    # Базовые точки: рассвет (20), день (90), вечер (30), ночь (5)
    base_points = [20, 90, 10, 0]
    # Распределение точек по времени (0%, 30%, 60%, 100%)
    base_positions = [0, int(n * 0.3), int(n * 0.6), n - 1]

    # Интерполяция между базовыми точками
    sun = np.interp(np.arange(n), base_positions, base_points)

    # Добавление шума (±10)
    noise = np.random.randint(-5, 6, n)
    sun_forecast = np.clip(sun + noise, 0, 100).astype(int)
    return sun_forecast

# Генерация прогноза ветра
def generate_wind_forecast(n=100):
    wind = np.zeros(n)

    # Экстремумы: 80 на 25% и 60 на 75%
    peak1_pos = int(n * 0.25)
    peak2_pos = int(n * 0.75)
    wind[peak1_pos] = 80
    wind[peak2_pos] = 60

    # Заполнение между экстремумами
    # От начала до первого экстремума
    for i in range(1, peak1_pos):
        wind[i] = wind[i-1] + np.random.randint(-5, 10)
    # От первого экстремума до второго
    for i in range(peak1_pos + 1, peak2_pos):
        wind[i] = wind[i-1] + np.random.randint(-10, 5)
    # От второго экстремума до конца
    for i in range(peak2_pos + 1, n):
        wind[i] = wind[i-1] + np.random.randint(-5, 10)

    # Ограничение диапазона [0, 100]
    wind_forecast = np.clip(wind, 0, 100).astype(int)
    return wind_forecast

# Генерация данных
sun = generate_sun_forecast()
wind = generate_wind_forecast()

# Визуализация
plt.figure(figsize=(12, 6))
plt.plot(sun, label='Солнце', color='orange')
plt.plot(wind, label='Ветер', color='blue')
plt.xlabel('Время (условные единицы)')
plt.ylabel('Значение')
plt.title('Прогноз солнца и ветра')
plt.legend()
plt.grid(True)
plt.show()

# Вывод результатов
print("Прогноз солнца:", sun)
print("Прогноз ветра:", wind)