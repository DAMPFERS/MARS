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

import csv

IP_ADDRESS = "192.168.3.6"
PORT = 5005


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


    def send_excel_data(
        self,
        station_id: int,
        index_file: int,
        glav: list,
        svaz: list,
        live: list,
        energ: list,
        state: list
    ) -> bool:
        """
        Отправляет данные из Excel на сервер.
        Args:
            station_id: Номер станции.
            index_file: Индекс файла (1, 2, 3, 4).
            glav, svaz, live, energ, state: Списки данных.
        Returns:
            bool: Успешность отправки.
        """
        if not self._is_connected:
            if not self.connect():
                return False

        try:
            # Определяем срез данных в зависимости от индекса файла
            start_idx = (index_file - 1) * 25
            end_idx = start_idx + 25

            # Формируем JSON с данными
            data = {
                "status": "Кейс по энергетике",
                "station_id": station_id,
                "index_file": index_file,
                "Главный модуль": glav[start_idx:end_idx],
                "Модуль связи": svaz[start_idx:end_idx],
                "Жилой модуль": live[start_idx:end_idx],
                "Модуль энергетики": energ[start_idx:end_idx],
                "Состояние панелей": state[start_idx:end_idx]
            }

            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            self.socket.sendall(json_data.encode("utf-8"))

            # Ожидаем подтверждение от сервера
            response = b""
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response += chunk
                try:
                    response_data = json.loads(response.decode("utf-8"))
                    if response_data.get("status") == "success":
                        print("Сервер подтвердил получение данных.")
                        return True
                    else:
                        print("Сервер вернул ошибку:", response_data.get("error", "Неизвестная ошибка"))
                        return False
                except json.JSONDecodeError:
                    continue

            print("Не удалось получить подтверждение от сервера.")
            return False

        except Exception as e:
            print(f"Ошибка при отправке данных: {e}")
            self._is_connected = False
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            return False

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




def addColumnToCSV(file_path, column_name, data):
    # Чтение существующих данных
    with open(file_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        rows = list(reader)

    # Проверка: длина данных должна совпадать с количеством строк БЕЗ заголовка
    if len(rows) > 0:
        data_rows_count = len(rows) - 1  # исключаем заголовок
        if len(data) != data_rows_count:
            raise ValueError(
                f"Длина списка данных ({len(data)}) должна совпадать "
                f"с количеством строк в файле без заголовка ({data_rows_count})."
            )

    # Добавление нового столбца
    if len(rows) == 0:
        # Если файл пустой, создаем заголовок
        rows.append([column_name])
        for value in data:
            rows.append([value])
    else:
        # Добавляем название столбца в заголовок
        rows[0].append(column_name)
        # Добавляем данные в каждую строку (начиная с первой после заголовка)
        for i, value in enumerate(data):
            rows[i+1].append(value)

    # Запись обновленных данных обратно в файл
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=',')
        writer.writerows(rows)




if __name__ == "__main__":
    
    # sun = readExcelByColumn("Сonsumption plan Data_frame_1.xlsx", "Погода", "Солнце")
    # weat = readExcelByColumn("Сonsumption plan Data_frame_1.xlsx", "Погода", "Ветер")
    
    # glav = readExcelByColumn("Сonsumption plan Data_frame_1.xlsx", "Потребление", "Главный модуль")
    # svaz = readExcelByColumn("Сonsumption plan Data_frame_1.xlsx", "Потребление", "Модуль связи")
    # live = readExcelByColumn("Сonsumption plan Data_frame_1.xlsx", "Потребление", "Жилой модуль")
    # energ = readExcelByColumn("Сonsumption plan Data_frame_1.xlsx", "Потребление", "Модуль энергетики")
    
    # state = readExcelByColumn("Сonsumption plan Data_frame_1.xlsx", "Параметры", "Состояние панелей")
    
    # print(type(sun))
    # print(len(weat))
    
    # print(len(glav))
    # print(len(svaz))
    # print(len(live))
    # print(len(energ))
    
    # print(len(state))
    
    # addColumnToCSV("forecast.csv", "Солнце", sun)
    # addColumnToCSV("forecast.csv", "Ветер", weat) 
    
    # addColumnToCSV("forecast.csv", "Главный модуль", glav) 
    # addColumnToCSV("forecast.csv", "Модуль связи", svaz) 
    # addColumnToCSV("forecast.csv", "Жилой модуль", live) 
    # addColumnToCSV("forecast.csv", "Модуль энергетики", energ) 
    
    # addColumnToCSV("forecast.csv", "Состояние панелей", state)    
    
    # print("Конец")
    # print(len(res))
    # exit()
    
    
    
    print("Вас приветствует центр планирования полетов миссии M.A.Р.C.")
    
    station_name = 4
    # while station_name not in [1, 2, 3, 4]:
    #     station_name = int(input("Введите номер станции: "))
    #     time.sleep(1)
    #     if station_name not in [1, 2, 3, 4]:
    #         print("Неверный номер станции. Пожалуйста, введите число от 1 до 4.")     
        
    print("Получение данных с базы данных управления полетами и формирование файла... (подождите)")
    time.sleep(2)  # Симуляция времени обработки данных
    
    
    directory = ""  # Заменить на нужный путь
    
    index_file = openExcelFile(directory)
    if index_file is None:
        time.sleep(10)
    else:
        print("Вы внесли все необходимые изменения? (не забудьте сохранить изменения в файле)")
        
        while True:
            response = input("Готовы к загрузке плана (да/нет): ")
            if response.lower() == "да":
                print("Проверка корректности данных...")
                flag_err = False
                
                # path_name = directory + "/" + f"Сonsumption plan Data_frame_{index_file}.xlsx"
                path_name = f"Сonsumption plan Data_frame_{index_file}.xlsx"
                sun = readExcelByColumn(path_name, "Погода", "Солнце")
                
                # print(type(sun))
                # print(type(sun[0]))
                l = len(sun)
                # print(l)
                # print(type(l))
                # print(sun)
                
                # sun = list(sun)
                
                
                if l != 100:
                    # print(f"l = {l}, type(l) = {type(l)}, l != 100 = {l != 100}")
                    print("Ошибка в данных: Прогноз солнца, исправьте ошибку")
                    continue
                i = 0
                while (flag_err == False) and (i < 100):
                
                    if (type(sun[i]) is not int) or (sun[i] >= 100):
                        flag_err = True
                        print("Ошибка в данных: Прогноз солнца, исправьте ошибку")
                        break
                    i += 1
                    
                
                
                        
                weat = readExcelByColumn(path_name, "Погода", "Ветер")
                if len(weat) != 100:
                    print("Ошибка в данных: Прогноз ветра, исправьте ошибку")
                    continue
                i = 0
                while (flag_err == False) and (i < 100):
                
                    if (type(weat[i]) is not int) or (weat[i] >= 100):
                        flag_err = True
                        print("Ошибка в данных: Прогноз ветра, исправьте ошибку")
                        break
                    i += 1
                
                
                
                glav = readExcelByColumn(path_name, "Потребление", "Главный модуль")
                if len(glav) != 100:
                    print("Ошибка в данных: Главный модуль, исправьте ошибку")
                    continue
                i = 0
                while (flag_err == False) and (i < 100):
                
                    if (type(glav[i]) is not int) or (glav[i] >= 100):
                        flag_err = True
                        print("Ошибка в данных: Главный модуль, исправьте ошибку")
                        break
                    i += 1
                
                
                svaz = readExcelByColumn(path_name, "Потребление", "Модуль связи")
                if len(svaz) != 100:
                    print("Ошибка в данных: Модуль связи, исправьте ошибку")
                    continue
                i = 0
                while (flag_err == False) and (i < 100):
                
                    if (type(svaz[i]) is not int) or (svaz[i] >= 100):
                        flag_err = True
                        print("Ошибка в данных: Модуль связи, исправьте ошибку")
                        break
                    i += 1
                
                
                live = readExcelByColumn(path_name, "Потребление", "Жилой модуль")
                if len(live) != 100:
                    print("Ошибка в данных: Жилой модуль, исправьте ошибку")
                    continue
                i = 0
                while (flag_err == False) and (i < 100):
                    if (type(live[i]) is not int) or (live[i] >= 100):
                        flag_err = True
                        print("Ошибка в данных: Жилой модуль, исправьте ошибку")
                        break
                    i += 1
                
                
                energ = readExcelByColumn(path_name, "Потребление", "Модуль энергетики")
                if len(energ) != 100:
                    print("Ошибка в данных: Модуль энергетики, исправьте ошибку")
                    continue
                i = 0
                while (flag_err == False) and (i < 100):
                    if (type(energ[i]) is not int) or (energ[i] >= 100):
                        flag_err = True
                        print("Ошибка в данных: Модуль энергетики, исправьте ошибку")
                        break
                    i += 1
                
                
                state = readExcelByColumn(path_name, "Параметры", "Состояние панелей")
                if len(state) != 100:
                    print("Ошибка в данных: Модуль энергетики, исправьте ошибку")
                    continue
                i = 0
                while (flag_err == False) and (i < 100):
                    if (type(state[i]) is not int) or (state[i] > 1) or (state[i] < 0):
                        flag_err = True
                        print("Ошибка в данных: Модуль энергетики, исправьте ошибку")
                        break
                    i += 1
                
                
                if flag_err:    continue
                
                print("Загрузка плана...")
                time.sleep(1)  # Симуляция времени загрузки
                
                client = StationTCPClient(IP_ADDRESS, port=PORT)
                if client.connect():
                    success = client.send_excel_data(
                        station_id=station_name,
                        index_file=index_file,
                        glav=glav,
                        svaz=svaz,
                        live=live,
                        energ=energ,
                        state=state
                    )
                    if success:
                        print("План успешно загружен!")
                        client.stop()
                        # exit()
                    else:
                        print("Ошибка при отправке данных на сервер.")
                        client.stop()
                else:
                    print("Не удалось подключиться к серверу.")

                time.sleep(3)
                exit()
            else:
                print("План не был загружен. Пожалуйста, внесите необходимые изменения и повторите попытку")
                time.sleep(5)
    