# import json
# from datetime import datetime

# def createStationJson(
#     station_id: int,
#     station_name: str,
#     # Энергетика
#     consumption: float,
#     generation: float,
#     storage: float,
#     # Связь
#     speed: int,
#     latency: int,
#     snr: float,
#     # Материалы
#     supply: int,
#     consumption_rate: float,
#     delivery_time: int,
#     # Ровер
#     charge: int,
#     distance: float,
#     status: str
# ) -> str:
#     """
#     Формирует JSON-строку с данными станции для отправки на сервер.

#     Args:
#         station_id: Идентификатор станции (0-3).
#         station_name: Название станции.
#         consumption: Потребление энергии (МВт).
#         generation: Генерация энергии (МВт).
#         storage: Уровень накопителя (МВт).
#         speed: Скорость связи (Мбит/с).
#         latency: Задержка связи (мс).
#         snr: Отношение сигнал/шум (dB).
#         supply: Запас материалов (кг).
#         consumption_rate: Расход материалов (кг/ч).
#         delivery_time: Время доставки (дней).
#         charge: Заряд ровера (%).
#         distance: Дистанция ровера (км).
#         status: Статус ровера (строка).

#     Returns:
#         JSON-строка.
#     """
#     data = {
#         "station_id": station_id,
#         "station_name": station_name,
#         "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
#         "params": {
#             "energy": {
#                 "consumption": consumption,
#                 "generation": generation,
#                 "storage": storage
#             },
#             "communication": {
#                 "speed": speed,
#                 "latency": latency,
#                 "snr": snr
#             },
#             "materials": {
#                 "supply": supply,
#                 "consumption_rate": consumption_rate,
#                 "delivery_time": delivery_time
#             },
#             "rover": {
#                 "charge": charge,
#                 "distance": distance,
#                 "status": status
#             }
#         }
#     }
#     return json.dumps(data, ensure_ascii=False, indent=2)


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

        # Атрибуты, обновляемые при получении ответа
        self.last_timestamp: Optional[str] = None
        self.game_tick: Optional[int] = 0
        self.operation_mode: Optional[str] = None
        self._lock = threading.Lock()

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
            print(f"Ошибка подключения: {e}")
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
        """Обрабатывает одну задачу: отправляет данные и принимает ответ."""
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


if __name__ == "__main__":
    import time
    # Создание клиента
    client = StationTCPClient("127.0.0.1", 5005)

    # Запуск фонового потока
    client.start()

    # Отправка данных (не блокирует GUI)
    client.send_station_data(
        station_id=1,
        station_name="Station Alpha",
        consumption=10.5,
        generation=15.0,
        storage=50.0,
        speed=100,
        latency=50,
        snr=25.5,
        supply=1000,
        consumption_rate=10.0,
        delivery_time=2,
        charge=80,
        distance=150.5,
        status="active"
    )
    time.sleep(5)  # Ждем немного, чтобы данные были отправлены и ответ получен
    # Получение текущего состояния
    status = client.getStatus()
    print(f"Текущий такт: {status['game_tick']}, Режим: {status['operation_mode']}")

    # Остановка клиента
    client.stop()