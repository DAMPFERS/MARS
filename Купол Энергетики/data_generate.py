import numpy as np
import matplotlib.pyplot as plt
import csv


# Генерация прогноза солнца
def generate_sun_forecast(n=100):
    base_points = [20, 90, 10, 0]
    base_positions = [0, int(n * 0.3), int(n * 0.6), n - 1]
    sun = np.interp(np.arange(n), base_positions, base_points)
    noise = np.random.randint(-5, 6, n)
    sun_forecast = np.clip(sun + noise, 0, 100).astype(int)
    return sun_forecast

# Генерация прогноза ветра
def generate_wind_forecast(n=100):
    wind = np.zeros(n)
    peak1_pos = int(n * 0.25)
    peak2_pos = int(n * 0.75)
    wind[peak1_pos] = 80
    wind[peak2_pos] = 60
    
    for i in range(1, peak1_pos):
        wind[i] = wind[i-1] + np.random.randint(-5, 10)
    for i in range(peak1_pos + 1, peak2_pos):
        wind[i] = wind[i-1] + np.random.randint(-10, 5)
    for i in range(peak2_pos + 1, n):
        wind[i] = wind[i-1] + np.random.randint(-5, 10)
    
    wind_forecast = np.clip(wind, 0, 100).astype(int)
    return wind_forecast

# Генерация данных потребителей
def generate_consumers_forecast(n=100, num_consumers=4):
    consumers = np.zeros((num_consumers, n))
    
    for i in range(num_consumers):
        # Базовый паттерн для каждого потребителя
        if i == 0:  # Потребитель 1: пиковое потребление днём
            base_points = [30, 90, 50, 20]
            base_positions = [0, int(n * 0.3), int(n * 0.6), n - 1]
        elif i == 1:  # Потребитель 2: равномерное потребление
            base_points = [50, 50, 50, 50]
            base_positions = [0, int(n * 0.3), int(n * 0.6), n - 1]
        elif i == 2:  # Потребитель 3: пиковое потребление утром и вечером
            base_points = [70, 30, 80, 40]
            base_positions = [0, int(n * 0.3), int(n * 0.6), n - 1]
        else:  # Потребитель 4: случайное потребление
            base_points = [40, 60, 30, 70]
            base_positions = [0, int(n * 0.3), int(n * 0.6), n - 1]
        
        # Интерполяция
        consumer = np.interp(np.arange(n), base_positions, base_points)
        # Добавление шума
        noise = np.random.randint(-10, 11, n)
        consumer = np.clip(consumer + noise, 0, 100).astype(int)
        consumers[i] = consumer
    
    return consumers






if __name__ == "__main__":
        
    # exit()

    # Генерация данных
    n = 100
    sun = generate_sun_forecast(n)
    wind = generate_wind_forecast(n)
    consumers = generate_consumers_forecast(n)

    # Визуализация
    plt.figure(figsize=(14, 8))
    plt.plot(sun, label='Солнце', color='orange', linewidth=2)
    plt.plot(wind, label='Ветер', color='blue', linewidth=2)

    # Добавляем графики потребителей
    colors = ['red', 'green', 'purple', 'brown']
    for i in range(consumers.shape[0]):
        plt.plot(consumers[i], label=f'Потребитель {i+1}', color=colors[i], linestyle='--', linewidth=1.5)

    plt.xlabel('Время (условные единицы)')
    plt.ylabel('Значение')
    plt.title('Прогноз солнца, ветра и потребителей')
    plt.legend()
    plt.grid(True)
    plt.show()

    # Вывод результатов
    print("Прогноз солнца:", sun)
    print("Прогноз ветра:", wind)
    for i in range(consumers.shape[0]):
        # print(f"Потребитель {i+1}:", consumers[i])
        print(f"Потребитель {i+1}:")
        for j in consumers[i]:
            print(int(j))
        print("----")