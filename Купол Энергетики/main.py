import time
import os
import subprocess
import pandas as pd

import json
import socket
import threading
import queue
from datetime import datetime
from typing import Optional, Dict, Any





class StationTCPClient:
    """
    TCP-клиент для обмена данными станции с сервером в фоновом режиме.
    Работает в отдельном потоке, чтобы не блокировать GUI.
    """

    def __init__(self, host: str, port: int):
        """
        Инициализация клиента.

        Args:
            host: IP-адрес или имя хоста сервера.
            port: Порт сервера.
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self._is_connected = False


        # Управление потоком
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._task_queue = queue.Queue()

    def connect(self) -> bool:
        """Устанавливает соединение с сервером."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)  # Таймаут для операций с сокетом
            self.socket.connect((self.host, self.port))
            self._is_connected = True
            return True
        except Exception as e:
            print(f"Ошибка подключения к станции: {e}")
            self._is_connected = False
            self.socket = None
            return False

    def createStationJSON(
        self,
        station_id: int,
        station_name: str,
        consumption: float,
        generation: float,
        storage: float,
        speed: int,
        latency: int,
        snr: float,
        supply: int,
        consumption_rate: float,
        delivery_time: int,
        charge: int,
        distance: float,
        status: str
    ) -> str:
        """Формирует JSON-строку с данными станции."""
        data = {
            "station_id": station_id,
            "station_name": station_name,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "params": {
                "energy": {
                    "consumption": consumption,
                    "generation": generation,
                    "storage": storage
                },
                "communication": {
                    "speed": speed,
                    "latency": latency,
                    "snr": snr
                },
                "materials": {
                    "supply": supply,
                    "consumption_rate": consumption_rate,
                    "delivery_time": delivery_time
                },
                "rover": {
                    "charge": charge,
                    "distance": distance,
                    "status": status
                }
            }
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def send_station_data(
        self,
        station_id: int,
        station_name: str,
        consumption: float,
        generation: float,
        storage: float,
        speed: int,
        latency: int,
        snr: float,
        supply: int,
        consumption_rate: float,
        delivery_time: int,
        charge: int,
        distance: float,
        status: str
    ) -> None:
        """
        Ставит задачу на отправку данных станции в очередь.
        Не блокирует вызывающий поток (например, GUI).
        """
        task = {
            "station_id": station_id,
            "station_name": station_name,
            "consumption": consumption,
            "generation": generation,
            "storage": storage,
            "speed": speed,
            "latency": latency,
            "snr": snr,
            "supply": supply,
            "consumption_rate": consumption_rate,
            "delivery_time": delivery_time,
            "charge": charge,
            "distance": distance,
            "status": status
        }
        self._task_queue.put(task)

    def _process_task(self, task: Dict[str, Any]) -> bool:
        """Обрабатывает одну задачу: отправляет данные и принимает ответ"""
        if not self._is_connected:
            if not self.connect():
                return False

        try:
            # Генерируем и отправляем JSON
            json_data = self.createStationJSON(**task)
            self.socket.sendall(json_data.encode("utf-8"))

            # Чтение ответа
            response = b""
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response += chunk
                try:
                    json.loads(response.decode("utf-8"))
                    break  # Полный JSON получен
                except json.JSONDecodeError:
                    continue

            # Парсим ответ и обновляем атрибуты
            response_data = json.loads(response.decode("utf-8"))
            with self._lock:
                self.last_timestamp = response_data.get("timestamp")
                self.game_tick = response_data.get("game_tick")
                self.operation_mode = response_data.get("operation_mode")

            return True

        except Exception as e:
            print(f"Ошибка при обработке задачи: {e}")
            self._is_connected = False
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            return False

    def _worker(self) -> None:
        """Фоновый поток для обработки задач из очереди."""
        while not self._stop_event.is_set():
            try:
                task = self._task_queue.get(timeout=0.1)
                self._process_task(task)
                self._task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Критическая ошибка в рабочем потоке: {e}")
                self._is_connected = False
                if self.socket:
                    try:
                        self.socket.close()
                    except:
                        pass
                    self.socket = None

    def start(self) -> None:
        """Запускает фоновый поток обработки задач."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Останавливает фоновый поток и закрывает соединение."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self._is_connected = False

    def getStatus(self) -> Dict[str, Any]:
        """
        Возвращает текущие атрибуты состояния.

        Returns:
            Словарь с атрибутами:
            - last_timestamp: Метка времени из последнего ответа
            - game_tick: Текущий такт игры
            - operation_mode: Текущий режим работы
        """
        with self._lock:
            return {
                "last_timestamp": self.last_timestamp,
                "game_tick": self.game_tick,
                "operation_mode": self.operation_mode
            }





def openExcelFile(directory: str)-> int:
    for i in range(1, 5):
        filename = f"Сonsumption plan Data_frame_{i}.xlsx"
        filepath = os.path.join(directory, filename)
        if os.path.exists(filepath):
            print(f"Сформирован файл: {filename}")
            # Открываем файл с помощью стандартного приложения
            if os.name == 'nt':  # Windows
                os.startfile(filepath)
            elif os.name == 'posix':  # Linux/Mac
                subprocess.run(['xdg-open', filepath])
            return i
    print("Не удалось сформировать Файл Сonsumption plan")
    return None



def readExcelByColumn(file_path, column_group, subcolumn_name):
    """
    Считывает данные из файла Excel по имени подстолбца в группе столбцов.

    Args:
        file_path (str): Путь к файлу Excel
        column_group (str): Имя группы столбцов (верхний уровень заголовка)
        subcolumn_name (str): Имя подстолбца (нижний уровень заголовка)

    Returns:
        list: Список значений из указанного подстолбца
        None: Если подстолбец не найден или файл не существует
    """
    try:
        # Чтение файла Excel с многоуровневыми заголовками
        df = pd.read_excel(file_path, header=[0, 1])

        # Проверка наличия группы и подстолбца
        if (column_group, subcolumn_name) in df.columns:
            return df[(column_group, subcolumn_name)].tolist()
        else:
            print(f"Подстолбец '{subcolumn_name}' в группе '{column_group}' не найден в файле.")
            return None
    except FileNotFoundError:
        print(f"Файл '{file_path}' не найден.")
        return None
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return None





if __name__ == "__main__":
    
    res = readExcelByColumn("Сonsumption plan Data_frame_1.xlsx", "Погода", "Ветер")
    print(res)
    print(len(res))
    exit()
    
    
    
    print("Вас приветствует центр планирования полетов миссии M.A.Р.C.")
    
    station_name = None
    while station_name not in [1, 2, 3, 4]:
        station_name = int(input("Введите номер станции: "))
        time.sleep(1)
        if station_name not in [1, 2, 3, 4]:
            print("Неверный номер станции. Пожалуйста, введите число от 1 до 4.")     
        
    print("Получение данных с базы данных управления полетами и формирование файла... (подождите)")
    time.sleep(3)  # Симуляция времени обработки данных
    
    
    directory = "D:/PROGRAMS/MARS/Купол Энергетики"  # Заменить на нужный путь
    
    index_file = openExcelFile(directory)
    if index_file is None:
        time.sleep(10)
    else:
        print("Вы внесли все необходимые изменения? (не забудьте сохранить изменения в файле)")
        
        response = input("Готовы к загрузке плана (да/нет): ")
        if response.lower() == "да":
            print("Загрузка плана...")
            time.sleep(2)  # Симуляция времени загрузки
            print("План успешно загружен!")
        else:
            print("План не был загружен. Пожалуйста, внесите необходимые изменения и повторите попытку")
    