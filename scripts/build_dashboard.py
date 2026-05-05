#!/usr/bin/env python3
"""Собирает дашборд: шифрует data/*.json, вставляет в docs/index.html на место __ENCRYPTED_PAYLOAD__."""
import json, os, base64, sys, io
from pathlib import Path
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets

ROOT = Path(__file__).resolve().parent.parent

def get_password():
    pw_file = ROOT / '.password'
    if pw_file.exists():
        return pw_file.read_text(encoding='utf-8').strip()
    pw = os.environ.get('DASHBOARD_PASSWORD')
    if not pw:
        raise RuntimeError("Нет .password или DASHBOARD_PASSWORD")
    return pw

def load_json(path, default):
    p = ROOT / path
    if p.exists():
        return json.loads(p.read_text(encoding='utf-8'))
    return default

def encrypt(plaintext_bytes, password):
    salt = secrets.token_bytes(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
    key = kdf.derive(password.encode('utf-8'))
    iv = secrets.token_bytes(12)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(iv, plaintext_bytes, None)
    return {
        'salt': base64.b64encode(salt).decode('ascii'),
        'iv': base64.b64encode(iv).decode('ascii'),
        'ciphertext': base64.b64encode(ct).decode('ascii'),
    }

def main():
    pw = get_password()
    payload = {
        'daily': load_json('data/daily.json', {}),
        'weight': load_json('data/weight.json', {}),
        'config': load_json('data/config.json', {}),
    }
    print(f"📊 Собираю дашборд:")
    print(f"   daily: {len(payload['daily'])} дней")
    print(f"   weight: {len(payload['weight'])} замеров")
    print(f"   config: {len(payload['config'])} настроек")

    plaintext = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    encrypted = encrypt(plaintext, pw)
    encrypted_json = json.dumps(encrypted)
    print(f"   шифртекст: {len(encrypted['ciphertext'])} базовых64 символов")

    template_path = ROOT / 'docs' / 'index.template.html'
    if not template_path.exists():
        raise RuntimeError(f"Шаблон {template_path} не найден")

    template = template_path.read_text(encoding='utf-8')
    marker = '__ENCRYPTED_PAYLOAD__'
    if marker not in template:
        raise RuntimeError(f"Маркер {marker} не найден в шаблоне")

    new_html = template.replace(marker, encrypted_json, 1)

    output_path = ROOT / 'docs' / 'index.html'
    output_path.write_text(new_html, encoding='utf-8')
    print(f"✅ docs/index.html: {len(new_html)} bytes")

if __name__ == '__main__':
    main()
