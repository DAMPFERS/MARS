#!/bin/bash

# --- Настройки сети ---
INTERFACE="wlan0"  # Интерфейс для статического IP (wlan0 для Wi-Fi, eth0 для Ethernet)
STATIC_IP="192.168.1.100"  # Желаемый статический IP
GATEWAY="192.168.8.1"  # Шлюз (роутер)
NETMASK="255.255.255.0"  # Маска подсети
DNS_SERVERS="8.8.8.8 8.8.4.4"  # DNS Google (можно заменить на свои)

# --- Настройки Wi-Fi ---
SSID="Ваше_имя_сети"  # Имя Wi-Fi сети
PASSWORD="Ваш_пароль"  # Пароль от Wi-Fi

# --- Установка статического IP ---
echo "Настройка статического IP для $INTERFACE..."
cat <<EOF | sudo tee /etc/dhcpcd.conf > /dev/null
interface $INTERFACE
static ip_address=$STATIC_IP/24
static routers=$GATEWAY
static domain_name_servers=$DNS_SERVERS
EOF

# --- Настройка автоподключения к Wi-Fi ---
echo "Настройка автоподключения к Wi-Fi $SSID..."
cat <<EOF | sudo tee /etc/wpa_supplicant/wpa_supplicant.conf > /dev/null
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=FI

network={
    ssid="$SSID"
    psk="$PASSWORD"
    key_mgmt=WPA-PSK
}
EOF

# --- Перезапуск сетевых служб ---
echo "Перезапуск сетевых служб..."
sudo systemctl restart dhcpcd
sudo systemctl restart wpa_supplicant
sudo systemctl restart networking