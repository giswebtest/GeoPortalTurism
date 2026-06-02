# Файлова структура проекту GeoPortal Turism

## Корінь проекту

```
GeoPortalTurism/
├── manage.py                  # Django CLI — запуск команд (migrate, runserver тощо)
├── requirements.txt           # Python залежності
├── compose.yaml               # Docker Compose для розробки (runserver + nginx + geoserver + pycsw)
├── compose.prod.yaml          # Docker Compose для production (gunicorn + nginx + certbot + db)
├── .env                       # Змінні середовища (DB, SECRET_KEY, ALLOWED_HOSTS)
├── .env.prod.example          # Приклад .env для production
├── architecture.html          # Інтерактивна HTML-документація архітектури системи
├── SESSION_2026-06-02.md      # Підсумок сесії розробки
├── FILE_STRUCTURE.md          # Цей файл — опис файлової структури
├── save_chat.py               # Скрипт збереження чату в папку chats/
├── maproute_prompt.md         # Промпт для генерації маршрутів (допоміжний)
├── README.md                  # Загальний опис проекту
└── GEMINI.md                  # Нотатки для Gemini AI (застарілий)
```

---

## `geoportal/` — конфігурація Django проекту

```
geoportal/
├── settings.py     # Основні налаштування: БД, INSTALLED_APPS, MEDIA/STATIC, GDAL, ALLOWED_HOSTS
├── urls.py         # Головний URL-роутер: /admin/, / (maps), /accounts/
├── wsgi.py         # WSGI точка входу для Gunicorn (production)
└── asgi.py         # ASGI точка входу (для async, не використовується активно)
```

**`settings.py`** — ключові налаштування:
- `DATABASES` — PostGIS через `django.contrib.gis.db.backends.postgis`
- `GDAL_LIBRARY_PATH` — шлях до бібліотеки GDAL у Docker
- `ALLOWED_HOSTS` — читається з `.env` (підтримує ngrok, cloudflare, localhost)
- `MEDIA_ROOT` / `STATIC_ROOT` — папки для фото та CSS

---

## `maps/` — основний геопросторовий застосунок

```
maps/
├── models.py          # 10 моделей бази даних
├── views.py           # GeoJSON API endpoints (7 функцій)
├── ogc_views.py       # OGC API Features Part 1 (8 endpoints)
├── iso19115.py        # Генерація ISO 19115:2003/19139 XML метаданих
├── admin.py           # Адмін-панель Django (764 рядки, 11 класів)
├── urls.py            # URL маршрути застосунку maps
├── apps.py            # Конфігурація застосунку
└── management/
    └── commands/
        ├── sync_pycsw.py        # Синхронізація метаданих з PyCSW каталогом
        └── export_metadata.py   # Експорт ISO 19115 XML файлів у папку metadata/
```

### `models.py` — моделі бази даних

| Модель | Поле геометрії | Призначення |
|--------|---------------|-------------|
| `Region` | — | Регіони (Карпати, Поділля тощо) |
| `Category` | — | Категорії локацій з emoji та slug |
| `Location` | `PointField` | Туристичні локації з фото, описом, UUID |
| `Route` | `LineStringField` | Маршрути з дистанцією та тривалістю (auto PostGIS) |
| `RouteLocation` | — | M2M зв'язок Route↔Location з порядком |
| `POICategory` | — | Категорії POI з Overpass-запитами |
| `HystoryOb` | `PointField` | Культурні пам'ятки (unmanaged, legacy таблиця) |
| `Country` | — | Країни зі bbox extent |
| `CountryPolygon` | `MultiPolygonField` | Полігони кордонів країн |
| `Guide` | — | Туристичні гіди з контактами |

### `views.py` — GeoJSON API

| Функція | URL | Опис |
|---------|-----|------|
| `index` | `/` | Головна сторінка — рендер карти |
| `country_polygons_geojson` | `/api/countries/<id>/polygons/` | Полігони кордонів країни |
| `hystory_ob_geojson` | `/api/hystory-ob/` | GeoJSON пам'яток культури |
| `ivfrankdist_geojson` | `/api/ivfrankdist/` | GeoJSON районів ІФ обл. |
| `overpass_proxy` | `/api/overpass/` | Проксі до Overpass API |
| `route_elevation` | `/api/routes/<id>/elevation/` | Профіль висот через OpenTopoData |

### `ogc_views.py` — OGC API Features Part 1

| Функція | URL | Опис |
|---------|-----|------|
| `ogc_landing` | `/ogc/` | Landing page з link relations (QGIS сумісний) |
| `ogc_conformance` | `/ogc/conformance/` | Класи відповідності стандарту |
| `ogc_collections` | `/ogc/collections/` | Список колекцій з метаданими |
| `ogc_collection` | `/ogc/collections/<id>/` | Метадані однієї колекції |
| `ogc_locations` | `/ogc/collections/locations/items/` | Локації (bbox, limit, offset) |
| `ogc_routes` | `/ogc/collections/routes/items/` | Маршрути |
| `ogc_hystory_ob` | `/ogc/collections/hystory-ob/items/` | Пам'ятки |
| `ogc_districts` | `/ogc/collections/districts/items/` | Райони |
| `ogc_metadata` | `/ogc/collections/<id>/metadata/` | ISO 19115 XML |

### `iso19115.py` — генератор метаданих

Генерує XML файли стандарту ISO 19115:2003/19139 для кожної колекції.
Використовується в `ogc_metadata` view та management command `export_metadata`.

### `admin.py` — адмін-панель (764 рядки)

| Клас | Модель | Особливості |
|------|--------|-------------|
| `LocationAdmin` | Location | GIS Widget, імпорт GeoJSON, фільтри, публікація |
| `RouteAdmin` | Route | GIS Widget, імпорт GPX, Build OSRM, inline RouteLocation |
| `CountryAdmin` | Country | Імпорт полігонів GeoJSON, ST_Within фільтрація |
| `HystoryObAdmin` | HystoryOb | GIS Widget для legacy таблиці |
| `POICategoryAdmin` | POICategory | Управління Overpass-запитами |
| `GuideAdmin` | Guide | Управління гідами |

### Management Commands

| Команда | Запуск | Призначення |
|---------|--------|-------------|
| `sync_pycsw` | `python manage.py sync_pycsw` | Публікація ISO 19115 записів у PyCSW каталог через CSW-T |
| `export_metadata` | `python manage.py export_metadata` | Збереження XML метаданих у папку `metadata/` |

---

## `accounts/` — автентифікація

```
accounts/
├── views.py    # LoginView, LogoutView
├── urls.py     # /accounts/login/, /accounts/logout/
├── models.py   # Порожній (використовується django.contrib.auth.User)
└── admin.py    # Порожній
```

Використовує стандартну систему Django Auth. Доступ до `/admin/` тільки для `is_staff=True`.

---

## `templates/` — HTML шаблони

```
templates/
├── base.html                              # Базовий шаблон: Navbar, модальні вікна, JS/CSS
├── maps/
│   └── index.html                         # Головна сторінка карти (2296 рядків)
├── registration/
│   └── login.html                         # Сторінка входу
└── admin/maps/
    ├── location/
    │   ├── change_list.html               # Список локацій з кнопкою «Імпорт GeoJSON»
    │   └── import_geojson.html            # Форма масового імпорту локацій
    ├── route/
    │   ├── change_list.html               # Список маршрутів з кнопкою «Імпорт GPX»
    │   └── import_gpx.html               # Форма імпорту GPX файлів
    └── country/
        ├── change_form.html               # Форма країни з кнопкою «Build OSRM»
        ├── change_list.html               # Список країн
        ├── import_polygons.html           # Імпорт полігонів для однієї країни
        └── import_polygons_general.html   # Загальний імпорт полігонів
```

### `base.html` — базовий шаблон
- Navbar з кнопками: ☰ Сайдбар, 🚗 Маршрут, 🔗 Підключити дані
- Модальне вікно «Підключити дані» — WMS/WFS/WMTS/OGC API/CSW URL з копіюванням
- Модальне вікно «Google Calendar»
- Leaflet CSS/JS підключення

### `index.html` — головна карта (2296 рядків)
- **2D карта** — Leaflet.js з 4 базовими шарами
- **3D карта** — MapLibre GL з WebGL рендером
- **Сайдбар** — фільтри, локації, маршрути, гіди
- **Elevation Chart** — Chart.js з crosshair синхронізацією
- **POI** — завантаження через Overpass API
- **Routing** — Leaflet Routing Machine + OSRM

---

## `static/` — статичні файли

```
static/
└── css/
    └── style.css    # Кастомні стилі (505 рядків): navbar, sidebar, карта, popup,
                     # API dropdown, connect-modal, elevation panel
```

---

## `docker/` — конфігурація Docker

```
docker/
├── Dockerfile          # Python 3.12-slim + GDAL + PROJ + GeoDjango залежності
├── nginx.conf          # Nginx конфіг: routing /, /geoserver/, /csw + HTTPS блок
├── pycsw.cfg           # PyCSW конфіг: CSW 2.0.2/3.0, SQLite БД, ISO 19115, INSPIRE
└── geoserver_setup.sh  # Скрипт налаштування GeoServer workspace та DataStore
```

### `Dockerfile`
- `FROM python:3.12-slim`
- Встановлює: `gdal-bin`, `libgdal-dev`, `libproj-dev`, `binutils`
- Копіює `requirements.txt` та код застосунку

### `nginx.conf`
- `location /` → proxy_pass `http://web:8000` (Django)
- `location /geoserver/` → proxy_pass `http://geoserver:8080/geoserver/`
- `location /csw` → proxy_pass `http://pycsw:8000/csw`
- `location /static/` та `/media/` → роздача з volume
- Закоментований HTTPS блок (розкоментувати після Certbot)

### `pycsw.cfg`
- `database = sqlite:////home/pycsw/pycsw.db`
- `profiles = apiso` (ISO Application Profile)
- `transactions = true` (підтримка CSW-T для sync_pycsw)

---

## `metadata/` — ISO 19115 XML файли

```
metadata/
├── metadata_locations.xml      # ISO 19115 метадані колекції «Туристичні локації»
├── metadata_routes.xml         # ISO 19115 метадані колекції «Маршрути»
├── metadata_hystory-ob.xml     # ISO 19115 метадані колекції «Пам'ятки культури»
└── metadata_districts.xml      # ISO 19115 метадані колекції «Райони ІФ»
```

Генеруються командою `python manage.py export_metadata`.
Використовуються PyCSW для формування CSW каталогу.

---

## Конфігураційні файли

| Файл | Призначення |
|------|-------------|
| `.env` | Dev змінні: DB credentials, SECRET_KEY, ALLOWED_HOSTS, DEBUG=1 |
| `.env.prod.example` | Шаблон для production (DEBUG=0, реальні паролі) |
| `.gitignore` | Ігнорує: `.env`, `media/`, `staticfiles/`, `__pycache__/` |
| `.gitattributes` | Налаштування line endings для Windows/Linux |
| `requirements.txt` | Django, GeoDjango, psycopg2, Pillow, requests, python-decouple |

---

## Docker Compose файли

### `compose.yaml` — розробка
| Сервіс | Образ | Порт | Призначення |
|--------|-------|------|-------------|
| `web` | custom Dockerfile | 8000 (internal) | Django runserver |
| `nginx` | nginx:1.25-alpine | 80 | Reverse proxy |
| `geoserver` | kartoza/geoserver:2.24.0 | 8080 | WMS/WFS/WMTS |
| `pycsw` | geopython/pycsw:2.6.1 | 8001 | CSW каталог |

### `compose.prod.yaml` — production
| Сервіс | Додатково |
|--------|-----------|
| `web` | Gunicorn 3 workers, expose (не ports) |
| `nginx` | Порти 80+443, certbot volumes |
| `db` | postgis/postgis:16-3.4, healthcheck |
| `geoserver` | expose замість ports |
| `pycsw` | expose замість ports |
| `certbot` | Let's Encrypt SSL |

---

## Допоміжні файли

| Файл | Призначення |
|------|-------------|
| `save_chat.py` | Зберігає поточний чат у `chats/` у форматі MD |
| `chats/` | Архів збережених діалогів розробки |
| `src/` | Порожня папка (резерв) |
| `staticfiles/` | Зібрана статика після `collectstatic` (не в git) |
| `media/` | Завантажені фото локацій та гідів (не в git) |
