# Главный купол

Проверка подключенных ком-порт устройств:  ls /dev/tty*
Искать: /dev/ttyACM0
pip3 install PyQt5 --break-system-packages


# --- Установка библиотек Python ---
echo "Установка библиотек Python (PyQt5, pyqtgraph, pyserial)..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-pyqt5 python3-pyqt5.qtchart python3-serial
pip3 install pyqtgraph pyserial
sudo pip3 install rpi_ws281x

echo "Готово! Перезагрузите Raspberry Pi для применения изменений."



chmod +x setup_raspberry.sh
sudo ./setup_raspberry.sh
sudo reboot

После перезагрузки проверьте IP-адрес:
ip a
