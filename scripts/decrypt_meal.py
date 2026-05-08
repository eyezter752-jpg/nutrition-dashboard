#!/usr/bin/env python3
"""
Standalone utility для расшифровки .json.enc meal files.
Использует: python scripts/decrypt_meal.py meals/2026-05-06.json.enc
"""

import json
import sys
import os
import base64
import hashlib
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def get_password():
    """Получить пароль из окружения или файла"""
    pwd = os.environ.get('DASHBOARD_PASSWORD')
    if pwd:
        return pwd
    if Path('.password').exists():
        with open('.password', 'r') as f:
            pwd = f.read().strip()
            if pwd:
                return pwd
    raise RuntimeError('Пароль не найден. Установите DASHBOARD_PASSWORD или создайте .password')

def decrypt_meal(file_path: str, password: str) -> dict:
    """Расшифровать .json.enc файл и вернуть JSON"""
    with open(file_path, 'rb') as f:
        content = f.read()

    data = json.loads(content.decode('utf-8'))
    salt = base64.b64decode(data['salt'])
    iv = base64.b64decode(data['iv'])
    ciphertext = base64.b64decode(data['ciphertext'])

    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000, dklen=32)
    cipher = AESGCM(key)
    plaintext = cipher.decrypt(iv, ciphertext, None)

    return json.loads(plaintext.decode('utf-8'))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python scripts/decrypt_meal.py <путь к файлу>")
        print("Пример: python scripts/decrypt_meal.py meals/2026-05-06.json.enc")
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        password = get_password()
        data = decrypt_meal(file_path, password)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"❌ Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
