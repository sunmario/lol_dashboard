# Дашборд по Ranked-матчам League of Legends
Аналитический дашборд по Ranked-матчам League of Legends для анализа эффективности игроков и популярности чемпионов.


**Структура дашборда**
- Вкладка 1 - Общая статистика
- Вкладка 2 - Чемпионы

Дашборд доступен по ссылке https://datalens.yandex/sfgd73akzid6b



#####

# League of Legends ETL Pipeline

ETL-пайплайн для получения, обработки и сохранения данных матчей League of Legends через Riot API.

Проект разработан как учебный пример Data Engineering и демонстрирует базовые принципы построения ETL-систем:

* Extract — получение данных из внешнего API
* Transform — нормализация и преобразование данных
* Load — загрузка данных в хранилище
* Логирование
* Разделение кода по слоям

---

# Архитектура проекта

```text
Riot API
    │
    ▼
extract.py
    │
    ▼
transform.py
    │
    ▼
load.py
    │
    ▼
CSV    
```

Проект реализован по классической схеме ETL и разделён на независимые слои.

---

# Структура проекта

```text
lol_etl/
│
├── config.py
├── data_pipeline.py
├── merge.py
├── requirements.txt
└── README.md
├── logs/
├── lol_output_*_*/
├── out/

```

---

# Используемые технологии

* Python 3.11+
* Pandas
* Requests
* Logging

---

# Установка

Клонировать репозиторий:

```bash
git clone https://github.com/sunmario/lol_dashboard

cd lol-etl
```

Установить зависимости:

```bash
pip install -r requirements.txt
```

---

# Настройка API

Создать файл:

```text
config.py
```

На основе шаблона:

```text
RIOT_API_KEY=YOUR_API_KEY
SERVERS = [
    {"name": "americas", "region": "na1"},
    {"name": "americas", "region": "br1"},
    {"name": "americas", "region": "la1"},
    {"name": "americas", "region": "la2"},

    {"name": "europe", "region": "euw1"},
    {"name": "europe", "region": "eun1"},
    {"name": "europe", "region": "ru"},
    {"name": "europe", "region": "tr1"},

    {"name": "asia", "region": "kr"},
    {"name": "asia", "region": "jp1"},

    {"name": "sea", "region": "oc1"},
    {"name": "sea", "region": "sg2"},
] # региональный хост (euw1, na1, ru, ...) + маршрутизирующий хост (europe, americas, asia)
PLAYERS_COUNT    =  # сколько топ-игроков брать
MATCHES_PER_PLAYER =  # сколько матчей на игрока
OUTPUT_DIR_BASE = "lol_output" # папка для CSV-файлов
PROJECT_DIR = "lol_dashboard" #папка проекта
BASE_DIR = "lol_proj" #корневая папка репозитория
```

Получить API-ключ можно на:

[RIOT DEVELOPERS](https://developer.riotgames.com)

---

# Запуск проекта

Запуск с параметрами по умолчанию:

```bash
python main.py
```

По умолчанию:

* players = 3
* matches = 2
* save_csv = yes

---

Получить данные для 10 игроков:

```bash
python main.py --players 10
```

Получить по 5 матчей на игрока:

```bash
python main.py --players 10 --matches 5
```


Полный пример:

```bash
python main.py \
    --players 20 \
    --matches 10 \
    --save-csv yes \
```

---

# Результаты работы

После выполнения будут созданы файлы для отдельных серверов и объединенные файлы по всем серверам:

```text
lol_dashboard
├──lol_output_ROUTING_REGION_REGION/
├──── players.csv
├──── matches.csv
└──── participants.csv
└── all_players.csv
└── all_matches.csv
└── all_participants.csv
```


---

# Логирование

Логи сохраняются в:

```text
logs/log_00_31_06_07_2026.log
```

Пример записи:

```text
2026-06-07 12:30:15 | INFO | EXTRACT started
2026-06-07 12:30:24 | INFO | Matches loaded: 50
2026-06-07 12:30:25 | INFO | TRANSFORM completed
2026-06-07 12:30:25 | INFO | LOAD completed
```


# Data Model

## players

Список уникальных игроков.

| Поле           |
| -------------- |
| region         |
| routing_region |
| puuid          |

---

## matches

Информация о матчах.

| Поле          |
| ------------- |
| region        |
| routing_region|
| match_id      |
| game_mode     |
| game_version  |
| game_duration |
| game_start_ts |

---

## participants

Статистика игроков в матчах.

| Поле                      |
| ------------------------- |
| region                    |
| routing_region            |
| match_id                  |
| puuid                     |
| champion                  |
| kills                     |
| deaths                    |
| assists                   |
| gold_earned               |
| total_damage_to_champions |
| vision_score              |
| win                       |

---

# Качество кода

Проект следует рекомендациям:

* PEP 8
* Single Responsibility Principle
* Логирование вместо print()
* Документирование функций через Docstring


---

# Автор

Проект создан в рамках мастерской анализа данных "Создание аналитической панели LoL",
как учебное пособие для Data Engineering части работы.

Основная цель проекта — демонстрация принципов построения ETL-пайплайнов, работы с внешними API и организации кода в production-style структуре.




