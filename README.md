# patriot-m-bot

## Подсчёт трафика на перекрёстке (6 направлений)

Добавлен отдельный скрипт `traffic_counter.py`, который считает транспорт в реальном времени
по 6 настраиваемым направлениям (виртуальные линии), показывает счётчики на видео и сохраняет итоги в CSV.

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Настройка направлений

1. Скопируйте шаблон:
   ```bash
   cp traffic_directions.example.json traffic_directions.json
   ```
2. Отредактируйте координаты линий под ваш ракурс камеры (ровно 6 направлений).

Формат:

```json
{
  "directions": [
    {"name": "Направление 1", "line": [[x1, y1], [x2, y2]]}
  ]
}
```

### Запуск

С камерой:

```bash
python traffic_counter.py --source 0 --config traffic_directions.json
```

С видеофайлом:

```bash
python traffic_counter.py --source ./sample_intersection.mp4 --config traffic_directions.json
```

Сохранение CSV:

```bash
python traffic_counter.py --source ./sample_intersection.mp4 --config traffic_directions.json --output-csv counts.csv
```

### Управление

- `ESC` — завершить обработку.
- `P` — пауза/продолжение.

Если хотите, можете прислать фрагмент видео — я помогу подобрать координаты линий под ваш перекрёсток.
