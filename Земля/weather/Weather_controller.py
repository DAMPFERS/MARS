#!/usr/bin/env python3
"""
weather_cli.py - Интерактивное управление погодой лабораторных стендов.
Может работать как самостоятельное CLI-приложение или импортироваться как модуль.
🔌 Как импортировать в другие скрипты
from weather_cli import apply_weather, set_all_wind, set_all_sun, set_all_weather
"""

import socket
import sys
import json
import threading
from typing import Dict, Optional, List, Tuple
from datetime import datetime

class StationData:
    """Класс для хранения последних данных станции"""
    def __init__(self, station_id: int, station_name: str):
        self.station_id = station_id
        self.station_name = station_name
        self.timestamp: str = "None"
        self.params: Dict = {"energy": {"consumption": 0.0, "generation": 0.0, "storage": 0.0},
            "communication": {"speed": 0, "latency": 0, "snr": 0.0},
            "materials": {"supply": 0, "consumption_rate": 0.0, "delivery_time": 0},
            "rover": {"charge": 0, "distance": 0.0, "status": "None"}
        }
        self.lock = threading.Lock()  # Для потокобезопасного доступа
        
    
    def update (self, data: Dict) -> None:
        """Обновляет данные станции."""
        with self.lock:
            self.timestamp = data.get("timestamp", "None")
            self.params = data.get("params", self.params)
            
    def getData(self) -> Dict:
        """Возвращает текущие данные станции"""
        with self.lock:
            return {
                "station_id": self.station_id,
                "station_name": self.station_name,
                "timestamp": self.timestamp,
                "params": self.params
            }
    
    
    
class TCPReceiver:
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5005, allowed_ips: Optional[List[str]] = None):
        """
        Инициализация сервера.
        :param host: IP-адрес для прослушивания (по умолчанию все интерфейсы)
        :param port: Порт для прослушивания
        :param allowed_ips: Список разрешенных IP-адресов. Если None, разрешены все
        """
        self.host = host
        self.port = port
        self.allowed_ips = allowed_ips
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False
        # self.stations: Dict[int, StationData] = {}  # Хранилище данных станций
        # Инициализируем данные для 4 станций
        self.stations: Tuple[StationData, ...] = (
            StationData(1, "Station 1"),
            StationData(2, "Station 2"),
            StationData(3, "Station 3"),
            StationData(4, "Station 4")
        )
        self.stations_lock = threading.Lock()  # Для потокобезопасного доступа к словарю станций
        self.pending_admin_commands: Dict[int, List[Dict]] = {1: [], 2: [], 3: [], 4: []}
        self.admin_lock = threading.Lock()  # Для потокобезопасного доступа к командам админа
        
        
        self.game_tick = 0  # Текущий такт игры
        self.operation_mode = "unknown"  # Текущий режим работы 
        
        
    def setGameTick(self, tick: int) -> None:
        """Устанавливает текущий такт игры"""
        self.game_tick = tick
        
    def setOperationMode(self, mode: str) -> None:
        """Устанавливает текущий режим работы (например, 'normal', 'emergency', 'maintenance')"""
        self.operation_mode = mode
        
    def start(self) -> None:
        """Запускает сервер в отдельном потоке."""
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)    # Очередь из 5 соединени
        self.running = True
        print(f" TCP-сервер запущен на {self.host}:{self.port} (ожидание JSON-пакетов)...")
        
        server_thread = threading.Thread(target=self._acceptConnection, daemon=True)
        server_thread.start()
        
    def stop(self) -> None:
        """Останавливает сервер."""
        self.running = False
        self.server_socket.close()
        print("🛑 TCP-сервер остановлен.")
        
    def _acceptConnection(self) -> None:
        """Принимает входящие соединения и обрабатывает их."""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                client_ip = addr[0]
                if self.allowed_ips and client_ip not in self.allowed_ips:
                    print(f"Подключение от {addr} отклонено (IP не в списке разрешенных).")
                    client_socket.close()
                    continue
                print(f"Новое соединение от {addr}")
                
                # Обрабатываем клиента в отдельном потоке
                client_threar = threading.Thread(
                    target=self._handleClient,
                    args=(client_socket, addr),
                    daemon=True
                )
                client_threar.start()
            except OSError:
                # Сервер закрыт
                break
            
    def _handleClient(self, client_socket: socket.socket, addr: tuple) -> None:
        
        """Обрабатывает клиентское соединение"""
        try:
            
            data = client_socket.recv(4096).decode("utf-8").strip()
            if not data:
                return
            # --- Фиксируем время получения пакета ---
            packet_timestamp = datetime.now().isoformat()  # Формат: "YYYY-MM-DDTHH:MM:SS.mmmmmm"
            try:
                # json_data = json.load(data)
                json_data = json.loads(data)
                # Обновляем данные станции
                station_id = json_data.get("station_id")
                # station_name = json_data.get("station_name")
                if not(1 <= station_id <= 4):
                    print(f"Некорректный station_id: {station_id}")
                    return
                    # with self.stations_lock:
                        # self.stations[station_id - 1].update(json_data)    
                # Разделяем типы сообщений по полю "status"
                is_admin_msg = json_data.get("status") == "Кейс по энергетике"
                if is_admin_msg:
                    # ─────────────────────────────────────────────────────
                    # ЛОГИКА АДМИНА: кладем команду в очередь станции
                    # ─────────────────────────────────────────────────────
                    with self.admin_lock:
                        self.pending_admin_commands[station_id].append(json_data)

                    # Отправляем админу немедленное подтверждение
                    response = {
                        "status": "success",
                        "message": "Команда администратора принята в очередь"
                    }   
                else:
                    # ─────────────────────────────────────────────────────
                    # ЛОГИКА СТАНЦИИ: обновляем данные станции (+ проверяем очередь админа)
                    # ─────────────────────────────────────────────────────
                    with self.stations_lock:
                        self.stations[station_id - 1].update(json_data)
                    
                    # Отправляем ответ
                
                
                    response = {"status": "success", 
                                "message": "Пакет получен", 
                                "from": addr,
                                "last_timestamp": packet_timestamp,
                                "game_tick": self.game_tick,  
                                "operation_mode": self.operation_mode
                    }
                    
                    # Вкладываем накопленные команды админа в ответ станции
                    with self.admin_lock:
                        pending = self.pending_admin_commands[station_id]
                        if pending:
                            response["admin_updates"] = {
                                "count": len(pending),  # кол-во фреймов по ТЗ
                                "frames": [
                                    {"id": cmd.get("index_file"), "data": cmd} 
                                    for cmd in pending
                                ]
                            }
                            # Очищаем очередь после отправки
                            self.pending_admin_commands[station_id] = []
                
                
                
                
                client_socket.sendall(json.dumps(response, ensure_ascii=False).encode("utf-8"))
            
            except json.JSONDecodeError:
                print(f"⚠️ Получены некорректные данные от {addr}: {data}")
            
        except Exception as e:
            print(f"⚠️ Ошибка при обработке клиента {addr}: {e}")
        finally:
            client_socket.close()
     
            
    def getStationData(self, station_id: int) -> Optional[Dict]:
        """Возвращает последние данные станции по её ID"""
        if 1 <= station_id <= 4:
            with self.stations_lock:
                station = self.stations[station_id - 1]
                return station.getData()
        return None
        
        
        
        
        
        

# ───────────────────────────────────────────────────────────────
# КОНФИГУРАЦИЯ (соответствует индексам 8-11 массива GATES)
# ───────────────────────────────────────────────────────────────
STANDS = {
    1: ("192.168.88.88", 5000, "S1d1"),
    2: ("192.168.88.89", 5000, "S1d4"),
    3: ("192.168.88.87", 5000, "S1d3"),
    4: ("192.168.88.87", 5001, "S1d5"),
}

OBJ_IDS = {"wind": "A0", "sun_east": "A1", "sun_west": "A2"}

def _send_command(ip: str, port: int, obj_id: str, value: int) -> bool:
    """Отправляет TCP-команду стенду. Диапазон автоматически ограничивается [0, 100]."""
    value = max(0, min(100, int(value)))
    hex_val = hex(value)[2:].zfill(3)
    payload = f"#{obj_id}S{hex_val}&".encode("utf-8")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((ip, port))
            s.sendall(payload)
            s.recv(1024)  # читаем подтверждение стенда
        return True
    except Exception as e:
        print(f"  ⚠️ Ошибка связи ({ip}:{port}): {e}")
        return False

def apply_weather(stand: int, wind: int, sun_e: int, sun_w: int) -> bool:
    """Устанавливает погоду на ОДНОМ стенде."""
    ip, port, name = STANDS[stand]
    print(f"\n🔹 Стенд {stand} ({name})...")
    r1 = _send_command(ip, port, OBJ_IDS["wind"], wind)
    r2 = _send_command(ip, port, OBJ_IDS["sun_east"], sun_e)
    r3 = _send_command(ip, port, OBJ_IDS["sun_west"], sun_w)
    if r1 and r2 and r3:
        print(f"✅ Успешно: Ветер={wind}, СолнцеВ={sun_e}, СолнцеЗ={sun_w}")
        return True
    print("❌ Ошибка при установке.")
    return False

# ───────────────────────────────────────────────────────────────
# ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ ВСЕМИ СТЕНДАМИ
# ───────────────────────────────────────────────────────────────
def set_all_wind(wind: int) -> bool:
    """Устанавливает ветер на всех 4 стендах."""
    print("\n🌬️ Устанавливаю ветер на всех стендах...")
    ok = True
    for sid in STANDS:
        ip, port, _ = STANDS[sid]
        if not _send_command(ip, port, OBJ_IDS["wind"], wind):
            ok = False
    print(f"✅ Ветер={wind} применен ко всем стендам." if ok else "❌ Были ошибки связи.")
    return ok

def set_all_sun(sun_val: int) -> bool:
    """Устанавливает одинаковое значение Солнца (Восток+Запад) на всех 4 стендах (8 светильников)."""
    print("\n☀️ Устанавливаю солнце на всех стендах...")
    ok = True
    for sid in STANDS:
        ip, port, _ = STANDS[sid]
        if not _send_command(ip, port, OBJ_IDS["sun_east"], sun_val): ok = False
        if not _send_command(ip, port, OBJ_IDS["sun_west"], sun_val): ok = False
    print(f"✅ Солнце={sun_val} применено ко всем 8 светильникам." if ok else "❌ Были ошибки связи.")
    return ok

def set_all_weather(sun_val: int, wind_val: int) -> bool:
    """Устанавливает полную погоду на всех 4 стендах двумя параметрами."""
    print(f"\n🌦️ Устанавливаю погоду на всех стендах: Солнце={sun_val}, Ветер={wind_val}...")
    sun_val = max(0, min(100, int(sun_val)))
    wind_val = max(0, min(100, int(wind_val)))
    
    set_all_sun(sun_val)
    
    return set_all_wind(wind_val)


# ───────────────────────────────────────────────────────────────
# ИНТЕРАКТИВНЫЙ CLI
# ───────────────────────────────────────────────────────────────
def main() -> None:
    
    import time 
    i = 0
    server = TCPReceiver()
    server.start()
    while i < 30:
        station_1_data = server.getStationData(1)
        print(f"Данные станции 1: {station_1_data}")
        time.sleep(5)
        i += 1
    
    
    exit(0)
    
    print("=" * 52)
    print("🌦️  УПРАВЛЕНИЕ ПОГОДОЙ  СТЕНДОВ")
    print("=" * 52)
    print("📝 Доступные команды:")
    print("  <стенд> <ветер> <солнце_восток> <солнце_запад>")
    print("  all_wind <0-100>")
    print("  all_sun <0-100>")
    print("  all_weather <солнце> <ветер>")
    print("💡 Примеры: 1 45 70 20 | all_sun 80 | all_weather 60 40")
    print("🚪 Для выхода: exit, q или Ctrl+C")
    print("=" * 52)

    while True:
        try:
            raw = input("\n> ").strip().lower()
            if raw in ("exit", "q", "quit"):
                print("👋 Выход из программы.")
                break
            if not raw: continue

            parts = raw.split()
            cmd = parts[0]

            # Массовые команды
            if cmd == "all_wind":
                if len(parts) == 2: set_all_wind(int(parts[1]))
                else: print("⚠️ Формат: all_wind <0-100>")
                continue

            if cmd == "all_sun":
                if len(parts) == 2: set_all_sun(int(parts[1]))
                else: print("⚠️ Формат: all_sun <0-100>")
                continue

            if cmd == "all_weather":
                if len(parts) == 3: set_all_weather(int(parts[1]), int(parts[2]))
                else: print("⚠️ Формат: all_weather <солнце> <ветер>")
                continue

            # Команда для одного стенда
            if len(parts) == 4:
                stand = int(parts[0])
                wind = int(parts[1])
                sun_e = int(parts[2])
                sun_w = int(parts[3])
                if stand not in STANDS:
                    print(f"⚠️ Стенд {stand} не найден. Доступны: {list(STANDS.keys())}")
                    continue
                if not all(0 <= x <= 100 for x in [wind, sun_e, sun_w]):
                    print("⚠️ Значения должны быть в диапазоне 0-100.")
                    continue
                apply_weather(stand, wind, sun_e, sun_w)
            else:
                print("⚠️ Неверный формат. См. подсказку выше.")

        except ValueError:
            print("⚠️ Ошибка: вводите только целые числа.")
        except KeyboardInterrupt:
            print("\n👋 Прервано пользователем. Выход.")
            break
        except EOFError:
            break

if __name__ == "__main__":
    main()