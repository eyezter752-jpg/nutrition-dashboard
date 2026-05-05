#!/usr/bin/env python3
"""
Сборщик дашборда с AES-256-GCM шифрованием.
Читает daily.json, weight.json, config.json, шифрует и вставляет в HTML.
"""

import json
import base64
import os
import sys
import io
import hashlib
import time
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets

# Фиксим кодировку для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_password():
    """Получить пароль из окружения или файла"""
    # Сначала проверяем переменную окружения
    pwd = os.environ.get('DASHBOARD_PASSWORD')
    if pwd:
        return pwd

    # Затем файл .password
    if Path('.password').exists():
        with open('.password', 'r') as f:
            pwd = f.read().strip()
            if pwd:
                return pwd

    # Если ничего не найдено - ошибка
    print('❌ Не установлен пароль. Установите DASHBOARD_PASSWORD или создайте .password')
    sys.exit(1)

def load_data():
    """Загрузить все данные"""
    with open('data/daily.json', 'r', encoding='utf-8') as f:
        daily = json.load(f)

    with open('data/weight.json', 'r', encoding='utf-8') as f:
        weight = json.load(f) if Path('data/weight.json').exists() else {}

    with open('data/config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    return {'daily': daily, 'weight': weight, 'config': config}

def derive_key(password, salt):
    """Вывести ключ PBKDF2"""
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000, dklen=32)

def encrypt_data(data, password):
    """Зашифровать данные AES-256-GCM"""
    # Генерируем salt и IV
    salt = secrets.token_bytes(16)
    iv = secrets.token_bytes(12)

    # Выводим ключ
    key = derive_key(password, salt)

    # Шифруем
    cipher = AESGCM(key)
    plaintext = json.dumps(data, ensure_ascii=False).encode('utf-8')
    ciphertext = cipher.encrypt(iv, plaintext, None)

    # Кодируем в base64
    salt_b64 = base64.b64encode(salt).decode('ascii')
    iv_b64 = base64.b64encode(iv).decode('ascii')
    ciphertext_b64 = base64.b64encode(ciphertext).decode('ascii')

    return {
        'salt': salt_b64,
        'iv': iv_b64,
        'ciphertext': ciphertext_b64
    }

def build_dashboard():
    """Собрать дашборд: обновить версию в index.html для обхода кэша"""

    print(f'🔄 Обновляю версию index.html для обхода браузерного кэша...')

    # Читаем текущий index.html
    index_path = Path('docs/index.html')
    if not index_path.exists():
        print('⚠️  docs/index.html не найден, пропускаю обновление версии')
        return

    with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Генерируем версию (timestamp)
    version = str(int(time.time()))

    # Обновляем версию в импортах скриптов
    html = __import__('re').sub(
        r'src="(crypto|api|app)\.js(\?v=\d+)?"',
        f'src="\\1.js?v={version}"',
        html
    )

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'✓ Версия обновлена: v={version}')

if __name__ == '__main__':
    build_dashboard()
