#!/usr/bin/env python3
"""
Парсер дневного файла питания (Markdown или зашифрованный JSON).
Читает meals/{date}.md или meals/{date}.json.enc, считает КБЖУ, обновляет data/daily.json
"""

import json
import sys
import re
import io
import os
import base64
import hashlib
from datetime import datetime
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Фиксим кодировку для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def load_products():
    """Загрузить базу продуктов"""
    with open('data/products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)
    # Создаём индекс для быстрого поиска
    product_index = {}
    for p in products:
        product_index[p['name'].lower()] = p
        for alias in p.get('aliases', []):
            product_index[alias.lower()] = p
    return products, product_index

def load_config():
    """Загрузить конфигурацию"""
    with open('data/config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def load_daily_data():
    """Загрузить существующие данные дня"""
    if Path('data/daily.json').exists():
        with open('data/daily.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def load_weight_data():
    """Загрузить историю веса"""
    if Path('data/weight.json').exists():
        with open('data/weight.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

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

def decrypt_json_meal(file_path: str, password: str) -> dict:
    """Расшифровать .json.enc файл"""
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

def convert_json_meal_to_md_format(meal_data: dict) -> tuple[dict, dict]:
    """Конвертировать JSON формат питания в структуру приёмов пищи и жидкостей"""
    meals = {
        'завтрак': [],
        '2-й завтрак': [],
        'обед': [],
        'полдник': [],
        'ужин': [],
        'поздний перекус': []
    }

    # Преобразуем meals
    for meal_name, items in meal_data.get('meals', {}).items():
        if meal_name in meals:
            for item in items:
                product = item.get('product', '')
                amount = item.get('grams') or item.get('pieces')
                unit = 'г' if 'grams' in item else ('шт' if 'pieces' in item else 'г')
                if amount:
                    meals[meal_name].append(f"{product} {amount} {unit}")
                else:
                    meals[meal_name].append(product)

    # Преобразуем drinks
    drinks = meal_data.get('drinks', {})

    return meals, drinks

def parse_frontmatter(content):
    """Извлечь фронтмэттер из markdown"""
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if value.isdigit():
                fm[key] = int(value)
            elif value.replace('.', '', 1).isdigit():
                fm[key] = float(value)
            elif value.lower() in ('true', 'false'):
                fm[key] = value.lower() == 'true'
            else:
                fm[key] = value if value else None
    return fm

def parse_meals(content):
    """Извлечь продукты из секций приёмов пищи"""
    meals_data = {}
    meal_names = ['завтрак', '2-й завтрак', 'обед', 'полдник', 'ужин', 'поздний перекус']

    for meal in meal_names:
        pattern = rf'### {meal}.*?\n(.*?)(?=###|## |$)'
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            meal_text = match.group(1)
            items = []
            for line in meal_text.split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    items.append(line[2:])
            meals_data[meal] = items
        else:
            meals_data[meal] = []

    return meals_data

def parse_meal_item(item_str):
    """Распарсить строку вроде 'куриная грудка 150 г'"""
    # Паттерны единиц измерения
    units_map = {
        'г': 1,
        'грамм': 1,
        'мл': 1,
        'шт': 'piece',
        'ст': 200,  # стакан
        'л': 1000   # литр
    }

    # Ищем число + единицу в конце
    match = re.search(r'(\d+(?:\.\d+)?)\s*(г|грамм|мл|шт|ст|л)?$', item_str)

    if match:
        amount = float(match.group(1))
        unit = match.group(2) or 'г'
        product_name = item_str[:match.start()].strip()
    else:
        product_name = item_str.strip()
        amount = None
        unit = None

    return product_name, amount, unit

def find_product(product_name, product_index):
    """Найти продукт в индексе (кейс-инсенситивный)"""
    normalized = product_name.lower().strip()
    if normalized in product_index:
        return product_index[normalized]

    # Попробовать частичное совпадение
    for key, product in product_index.items():
        if normalized in key or key in normalized:
            return product

    return None

def calculate_nutrition(product, amount, unit):
    """Расчитать КБЖУ для порции"""
    if amount is None:
        return None, None, None, None

    if unit == 'piece' or unit == 'шт':
        # Для штучных продуктов - используем piece_weight_g
        if 'piece_weight_g' in product:
            amount_g = amount * product['piece_weight_g']
        else:
            return None, None, None, None
    elif unit == 'ст':
        amount_g = amount * 200
    elif unit == 'л':
        amount_g = amount * 1000
    else:
        amount_g = amount

    kcal_per_g = product['kcal_per_100g'] / 100
    protein_per_g = product['protein'] / 100
    fat_per_g = product['fat'] / 100
    carbs_per_g = product['carbs'] / 100

    return (
        int(kcal_per_g * amount_g),
        round(protein_per_g * amount_g, 1),
        round(fat_per_g * amount_g, 1),
        round(carbs_per_g * amount_g, 1)
    )

def parse_liquids_table(content):
    """Парсить таблицу жидкостей"""
    # Найти таблицу после '## ЖИДКОСТИ'
    match = re.search(r'## ЖИДКОСТИ.*?\n\|.*?\|(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if not match:
        return {}

    table_text = match.group(1)

    liquids = {
        'coffee_count': 0,
        'tea_count': 0,
        'water_ml': 0,
        'items': []
    }

    for line in table_text.split('\n'):
        if '|' not in line:
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 4:
            continue

        drink_name = parts[1].lower()
        volume = parts[2]
        marked = parts[3]

        if not marked or marked == '-':
            continue

        # Считаем символы ✓, +, цифры
        count = 0
        if '✓' in marked:
            count = marked.count('✓')
        elif '+' in marked:
            count = marked.count('+')
        else:
            # Пробуем прочитать цифру
            digit_match = re.search(r'\d+', marked)
            if digit_match:
                count = int(digit_match.group())

        if 'кофе' in drink_name:
            liquids['coffee_count'] += count
        elif 'чай' in drink_name:
            liquids['tea_count'] += count
        elif 'вода' in drink_name:
            # Парсим объём
            if 'л' in volume.lower():
                ml = count * 1000
            elif 'мл' in volume.lower():
                vol_match = re.search(r'\d+', volume)
                if vol_match:
                    ml = count * int(vol_match.group())
                else:
                    ml = count * 200
            else:
                ml = count * 200
            liquids['water_ml'] += int(ml)

        liquids['items'].append({
            'drink': drink_name,
            'volume': volume,
            'count': count
        })

    return liquids

def get_day_of_week(date_str):
    """Получить день недели на русском"""
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        days_ru = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        return days_ru[dt.weekday()]
    except:
        return 'Пн'

def process_day(date_str, source_file: str = None):
    """Обработать день (из MD или .json.enc файла)"""
    if source_file is None:
        md_path = Path(f'meals/{date_str}.md')
        json_path = Path(f'meals/{date_str}.json.enc')
        if md_path.exists():
            source_file = str(md_path)
        elif json_path.exists():
            source_file = str(json_path)
        else:
            print(f'Файл meals/{date_str}.md или meals/{date_str}.json.enc не найден')
            return

    file_path = Path(source_file)
    if not file_path.exists():
        print(f'Файл {file_path} не найден')
        return

    config = load_config()
    products, product_index = load_products()
    daily_data = load_daily_data()
    weight_data = load_weight_data()

    # Определяем формат и парсим
    if str(file_path).endswith('.json.enc'):
        password = get_password()
        meal_data = decrypt_json_meal(str(file_path), password)
        fm = {
            'weight_morning': meal_data.get('weight_morning'),
            'sleep_hours': meal_data.get('sleep_hours'),
            'training': meal_data.get('training'),
            'binge': meal_data.get('binge', False),
            'mood': meal_data.get('mood'),
        }
        meals, drinks_data = convert_json_meal_to_md_format(meal_data)
        # Преобразуем drinks в формат liquids
        liquids = {
            'coffee_count': drinks_data.get('Кофе молотый с молоком 200мл', 0),
            'tea_count': sum(drinks_data.get(k, 0) for k in drinks_data if 'Чай' in k),
            'water_ml': int((drinks_data.get('Вода стакан 200мл', 0) or 0) * 200 + (drinks_data.get('Вода с газом литры', 0) or 0) * 1000),
            'items': []
        }
    else:
        # MD формат
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        fm = parse_frontmatter(content)
        meals = parse_meals(content)
        liquids = parse_liquids_table(content)

    # Извлечение training_done и training_text
    training_text = fm.get('training')
    if training_text is None or (isinstance(training_text, str) and training_text.lower() in ('null', '', '—', 'нет', 'ничего', 'нету', '-', 'none')):
        training_done = False
        training_text = None
    else:
        training_done = True
        training_text = str(training_text).strip()

    # Инициализируем запись дня
    day_record = {
        'date': date_str,
        'day_of_week': get_day_of_week(date_str),
        'weight_morning': fm.get('weight_morning'),
        'sleep_hours': fm.get('sleep_hours'),
        'training_done': training_done,
        'training_text': training_text,
        'binge': fm.get('binge', False),
        'mood': fm.get('mood'),
        'totals': {'kcal': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
        'evening_kcal': 0,
        'by_meal': {},
        'drinks': liquids,
        'stoplist_hits': [],
        'zone': 'green',
        'unknown_products': []
    }

    # Обработаем каждый приём пищи
    evening_meals = {'ужин', 'поздний перекус'}

    for meal_name, items in meals.items():
        meal_kcal = 0
        meal_items = []

        for item in items:
            product_name, amount, unit = parse_meal_item(item)
            product = find_product(product_name, product_index)

            if product:
                kcal, protein, fat, carbs = calculate_nutrition(product, amount, unit)
                if kcal is not None:
                    meal_kcal += kcal
                    day_record['totals']['kcal'] += kcal
                    day_record['totals']['protein'] += protein
                    day_record['totals']['fat'] += fat
                    day_record['totals']['carbs'] += carbs

                    # Проверяем стоп-лист
                    for stop_word in config['stoplist']:
                        if stop_word.lower() in product_name.lower():
                            if product_name not in day_record['stoplist_hits']:
                                day_record['stoplist_hits'].append(product_name)

                    meal_items.append({
                        'product': product_name,
                        'amount': amount,
                        'unit': unit,
                        'kcal': kcal,
                        'protein': protein,
                        'fat': fat,
                        'carbs': carbs
                    })
            else:
                # Неизвестный продукт
                day_record['unknown_products'].append(product_name)
                # Добавляем в файл неизвестных продуктов
                with open('data/unknown_products.txt', 'a', encoding='utf-8') as f:
                    f.write(f'{product_name}\n')

        day_record['by_meal'][meal_name] = meal_kcal

        # Считаем вечерние калории
        if meal_name in evening_meals:
            day_record['evening_kcal'] += meal_kcal

    # Определяем зону
    if day_record['totals']['kcal'] <= config['calorie_zones']['green_max']:
        day_record['zone'] = 'green'
    elif day_record['totals']['kcal'] <= config['calorie_zones']['yellow_max']:
        day_record['zone'] = 'yellow'
    else:
        day_record['zone'] = 'red'

    # Обновляем daily.json
    daily_data[date_str] = day_record
    with open('data/daily.json', 'w', encoding='utf-8') as f:
        json.dump(daily_data, f, ensure_ascii=False, indent=2)

    # Обновляем weight.json если есть вес
    if day_record['weight_morning']:
        weight_data[date_str] = day_record['weight_morning']
        with open('data/weight.json', 'w', encoding='utf-8') as f:
            json.dump(weight_data, f, ensure_ascii=False, indent=2)

    # Выводим результат
    print(f"✓ {date_str} обработан")
    print(f"  Калорий: {day_record['totals']['kcal']}/{config['calorie_target']} ({day_record['zone']})")
    print(f"  Белок: {day_record['totals']['protein']:.0f}г / Жиры: {day_record['totals']['fat']:.0f}г / Углеводы: {day_record['totals']['carbs']:.0f}г")
    print(f"  Вечер: {day_record['evening_kcal']} ккал")
    print(f"  Тренировка: {'да' if day_record['training_done'] else 'нет'}")
    print(f"  Кофе: {day_record['drinks'].get('coffee_count', 0)}/2")
    print(f"  Вода: {day_record['drinks'].get('water_ml', 0)}/2000 мл")

    if day_record['unknown_products']:
        print(f"  ⚠ Неизвестные продукты: {', '.join(day_record['unknown_products'])}")
    if day_record['stoplist_hits']:
        print(f"  ⛔ Стоп-лист: {', '.join(day_record['stoplist_hits'])}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # Если передан путь к файлу (содержит /)
        if '/' in arg or '\\' in arg or arg.endswith('.json.enc') or arg.endswith('.md'):
            source_file = arg
            # Пытаемся извлечь дату из имени файла
            file_stem = Path(arg).stem
            process_day(file_stem, source_file=source_file)
        else:
            # Иначе это дата
            process_day(arg)
    else:
        date = datetime.now().strftime('%Y-%m-%d')
        process_day(date)
