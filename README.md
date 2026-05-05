# 🍽️ Дашборд питания и веса

Приватный дашборд для трекинга питания, веса и жидкостей. Все данные зашифрованы AES-256-GCM.

## Инструкция

### Первый раз

1. **Создайте GitHub репо** (приватное или публичное)
2. **Установите пароль**:
   ```bash
   echo "ваш_пароль" > .password
   ```
   Или через переменную окружения:
   ```bash
   export DASHBOARD_PASSWORD="ваш_пароль"
   ```

3. **Инициализируйте Git** и сделайте первый commit:
   ```bash
   git init
   git add .
   git commit -m "init: nutrition dashboard"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/nutrition-dashboard.git
   git push -u origin main
   ```

4. **Включите GitHub Pages**:
   - Перейдите в Settings → Pages
   - Выберите Source: `main branch` → `/docs` folder
   - Сохраните

5. **Откройте дашборд**: `https://YOUR_USERNAME.github.io/nutrition-dashboard/` (или просто откройте `docs/index.html` локально)

### Каждый день

1. **Создайте или отредактируйте файл** `meals/YYYY-MM-DD.md` (по шаблону из `templates/day-template.md`)

2. **Заполните приём пищи**:
   ```markdown
   ### Завтрак (07:30)
   - Овсянка 200 г
   - Яйцо 1 шт
   - Банан 1 шт
   - Кофе с молоком 200 мл
   ```

3. **Заполните жидкости** в таблице (галочки ✓ или цифры):
   ```markdown
   | Напиток | Объём | Сегодня |
   |---|---|---|
   | Кофе молотый с молоком | 200 мл | ✓ |
   | Вода (стакан) | 200 мл | 5 |
   ```

4. **Запустите парсер**:
   ```bash
   python scripts/parse_day.py YYYY-MM-DD
   # или для сегодня:
   python scripts/parse_day.py
   ```

5. **Пересоберите дашборд**:
   ```bash
   python scripts/build_dashboard.py
   ```

6. **Запушьте на GitHub**:
   ```bash
   bash scripts/deploy.sh "update 2026-05-05"
   ```

### Добавление нового продукта

Если парсер не узнал продукт, он попросит добавить его. Добавляйте в `data/products.json`:

```json
{
  "id": "product_id",
  "name": "Название продукта",
  "aliases": ["alias1", "alias2"],
  "kcal_per_100g": 165,
  "protein": 31.0,
  "fat": 3.6,
  "carbs": 0,
  "default_unit": "g"
}
```

Для штучных продуктов:
```json
{
  "id": "banana",
  "name": "Банан",
  "aliases": ["банан"],
  "kcal_per_100g": 89,
  "protein": 1.1,
  "fat": 0.3,
  "carbs": 22.0,
  "piece_weight_g": 120,
  "default_unit": "шт"
}
```

## Структура

```
nutrition-dashboard/
├── meals/                 # Markdown-файлы по дням (НЕ коммитятся)
├── templates/            # Шаблоны
├── data/
│   ├── products.json    # База продуктов
│   ├── config.json      # Конфиг (цели, стоп-лист)
│   ├── daily.json       # Итоги по дням
│   └── weight.json      # История веса
├── scripts/
│   ├── parse_day.py     # Парсер MD → daily.json
│   ├── build_dashboard.py # Сборка HTML с шифрованием
│   └── deploy.sh        # Push на GitHub
└── dashboard/           # Собранный сайт (хостится)
    └── index.html
```

## Безопасность

- ✅ Все данные шифруются **AES-256-GCM** перед загрузкой на GitHub
- ✅ Markdown-файлы `meals/` не коммитятся (в `.gitignore`)
- ✅ Пароль не хранится в коде (в `.password`, который также в `.gitignore`)
- ✅ Расшифровка происходит **в браузере** (WebCrypto API), не на сервере

## Команды

```bash
# Парсить день и обновить дашборд
python scripts/parse_day.py 2026-05-05

# Собрать дашборд с шифрованием
python scripts/build_dashboard.py

# Запушить всё на GitHub
bash scripts/deploy.sh "update nutrition"

# Все вместе (быстро)
python scripts/parse_day.py && python scripts/build_dashboard.py && bash scripts/deploy.sh
```

## Требования

- Python 3.8+
- `pip install cryptography`

## Примечания

- Единицы: `г`, `мл`, `шт`, `ст` (стакан 200 мл), `л` (литр)
- Если продукт не найден — попадёт в `data/unknown_products.txt`
- Стоп-лист срабатывает при совпадении названия продукта со списком в `config.json`
