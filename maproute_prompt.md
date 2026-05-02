# 🗺️ MapRoute — Туристичний Геопортал
### Технічне завдання та промт для розробки

---

## 📌 Загальна концепція

Я хочу створити **повноцінний туристичний веб-геопортал** під назвою **MapRoute**,
який дозволяє користувачам планувати, зберігати та переглядати туристичні маршрути
на інтерактивній карті. Платформа орієнтована на туристів, мандрівників і організаторів
екскурсій. Стек — трирівнева веб-ГІС архітектура.

---

## 🏗️ Архітектура застосунку

### Рівень 1 — База даних (`#Database_Layer`)

| Компонент | Роль |
|-----------|------|
| **PostgreSQL 16** | Реляційна СУБД. Зберігає атрибутивні дані маршрутів, POI, користувачів, фото |
| **PostGIS 3.4** | Просторова надбудова. Типи `GEOMETRY`/`GEOGRAPHY`, GiST-індекси, топологічні функції |
| **Spatial Index** | Прискорює `ST_Within`, `ST_Distance`, `ST_Intersects` для геозапитів |

**Ключові PostGIS функції:**
- `ST_Length(geom)` — розрахунок довжини маршруту в км
- `ST_Distance(a, b)` — відстань між точками Timeline
- `ST_Within(poi, bbox)` — фільтрація POI у видимій зоні карти
- `ST_AsGeoJSON()` — серіалізація геометрії для REST API
- `ST_Intersects()` — пошук маршрутів у заданому регіоні

---

### Рівень 2 — Серверний (`#Application_Layer`)

| Компонент | Роль |
|-----------|------|
| **Python 3.12 + Django 5.x** | Маршрутизація, автентифікація, адмін-панель |
| **GeoDjango** | ORM для просторових полів: `PointField`, `LineStringField`, `PolygonField` |
| **Django REST Framework + GIS** | `GeoFeatureModelSerializer` → GeoJSON response |
| **Celery + Redis** | Async задачі: обробка фото, кеш тайлів |
| **Gunicorn** | WSGI сервер у Docker контейнері |

---

### Рівень 3 — Клієнтський (`#Presentation_Layer`)

| Компонент | Роль |
|-----------|------|
| **Leaflet.js** | Інтерактивна карта: TileLayer, векторні шари, маркери, polyline |
| **HTML5 / CSS3** | Структура та адаптивний стиль UI |
| **Vanilla JS** | Логіка перемикання шарів, Timeline, фото-стрічки |

---

## 🐳 Інфраструктура

```
Docker Compose
├── service: web        → Django + Gunicorn
├── service: db         → kartoza/postgis (PostgreSQL + PostGIS)
├── service: redis      → Celery broker
└── service: nginx      → Reverse proxy + SSL

GitHub
├── CI/CD: GitHub Actions
│   └── lint → test → build image → push GHCR
└── Deploy: docker-compose pull && up -d
```

---

## 🗄️ Моделі бази даних

```python
# Основні Django/GeoDjango моделі

class Route(models.Model):
    name        = models.CharField(max_length=200)
    description = models.TextField()
    geom        = LineStringField(srid=4326)   # просторова геометрія маршруту
    color       = models.CharField(max_length=7, default='#E8316E')
    created_by  = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at  = models.DateTimeField(auto_now_add=True)
    duration_h  = models.FloatField()
    distance_km = models.FloatField(blank=True, null=True)

class Waypoint(models.Model):
    route     = models.ForeignKey(Route, related_name='waypoints', on_delete=models.CASCADE)
    order     = models.PositiveIntegerField()
    geom      = PointField(srid=4326)
    label     = models.CharField(max_length=100)
    timestamp = models.TimeField()
    note      = models.TextField(blank=True)

class POI(models.Model):
    CATEGORY_CHOICES = [
        ('rest',       'Місця відпочинку'),
        ('wc',         'WC туалети'),
        ('church',     'Собори'),
        ('restaurant', 'Ресторани'),
        ('hospital',   'Госпіталі'),
        ('bike',       'Велопарковки'),
        ('hotel',      'Готелі'),
        ('interest',   'Точки інтересу'),
        ('cafe',       'Кафе'),
        ('bunker',     'Бункери'),
        ('bar',        'Бари'),
        ('park',       'Парки'),
    ]
    name     = PointField(srid=4326)          # геопозиція
    geom     = PointField(srid=4326)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    label    = models.CharField(max_length=200)
    icon     = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

class Photo(models.Model):
    route    = models.ForeignKey(Route, related_name='photos', on_delete=models.CASCADE)
    geom     = PointField(srid=4326, null=True, blank=True)
    image    = models.ImageField(upload_to='photos/')
    caption  = models.CharField(max_length=300, blank=True)
    taken_at = models.DateTimeField(null=True, blank=True)
```

---

## 🔌 REST API Ендпоінти

| Метод | URL | Опис |
|-------|-----|------|
| `GET` | `/api/routes/` | Список всіх маршрутів (GeoJSON FeatureCollection) |
| `POST` | `/api/routes/` | Створити новий маршрут |
| `GET` | `/api/routes/{id}/` | Деталі маршруту |
| `GET` | `/api/routes/{id}/waypoints/` | Точки маршруту |
| `GET` | `/api/pois/?layer=cafe&bbox=x1,y1,x2,y2` | POI з фільтрацією по шару і bbox |
| `GET` | `/api/photos/?route={id}` | Фото маршруту з геоприв'язкою |
| `GET` | `/api/layers/` | Доступні шари карти |
| `GET` | `/api/weather/?point=lat,lng` | Погода в точці (зовнішній API) |
| `POST` | `/api/export/?format=gpx` | Експорт маршруту у GPX / GeoJSON |

---

## 🖥️ UI Компоненти (макет)

```
┌─────────────────────────────────────────────────────────────────┐
│ [Logo]  [🌐 Список областей ▾]  [📷📷📷📷📷📷📷]           ФОТО  │  ← TopBar
├────────────┬────────────────────────────────────┬───────────────┤
│ Маршрути   │                                    │ 📋 КАРТИ      │
│ ──────── 2 │         LEAFLET MAP CANVAS         │ ─────────     │
│            │                                    │ Провайдер:    │
│ 🏔 Гірськ. │   ①────②────③────④────⑤          │ ◉ Бінг        │
│    трекінг │   (pink polyline + markers)        │ ○ Гугл        │
│            │                                    │ ○ ОСМ         │
│ 🏙 Міськ.  │  ┌──────────────────┐             │               │
│    тур Київ│  │ ІНСТРУМЕНТИ      │             │ POI шари:     │
│            │  │ ✈ Прокласти      │             │ ☑ Відпочинок  │
│  [+ ···]   │  │ 📍 Геолокація    │             │ ☑ Ресторани   │
│  [+ ···]   │  │ 🔍 Пошук         │             │ ☑ Кафе        │
│            │  │ 🌤 Погода        │             │ ☐ Готелі      │
│            │  │ ⬇ Експорт       │             │ ☑ Бари        │
│            │  └──────────────────┘             │ ☐ Парки ...   │
│            │                                    │               │
│            │                                    │ [Мінікарта]   │
│ [+ Додати] │                                    │ М 1:2000      │
├────────────┴────────────────────────────────────┴───────────────┤
│ ▶  ①────────────②────────────③────────────④────────────⑤       │
│   10:30        11:30         12:30         13:30        14:30   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Структура проєкту

```
geodjango-app/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── routes/
│   │   ├── models.py       # Route, Waypoint
│   │   ├── serializers.py  # GeoFeatureModelSerializer
│   │   ├── views.py        # ViewSet
│   │   ├── urls.py
│   │   └── admin.py        # GeoModelAdmin
│   ├── pois/
│   │   ├── models.py       # POI
│   │   ├── serializers.py
│   │   └── views.py
│   ├── photos/
│   │   └── models.py       # Photo + geom
│   └── users/
│       └── models.py       # Profile
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── main.css
│   └── js/
│       ├── map.js          # Leaflet init
│       ├── layers.js       # POI шари
│       ├── timeline.js     # Timeline UI
│       └── api.js          # fetch → REST API
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── nginx/
│       └── default.conf
├── .github/
│   └── workflows/
│       └── ci.yml          # lint → test → build → push GHCR
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
├── .env.example
├── .gitignore
├── README.md
└── manage.py
```

---

## ⚙️ Docker Compose конфігурація

```yaml
version: '3.9'

services:
  db:
    image: kartoza/postgis:16-3.4
    environment:
      POSTGRES_DB: maproute_db
      POSTGRES_USER: maproute
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  web:
    build:
      context: .
      dockerfile: docker/Dockerfile
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
      - media:/app/media
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - db
      - redis

  redis:
    image: redis:7-alpine

  nginx:
    image: nginx:alpine
    volumes:
      - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf
      - media:/app/media
    ports:
      - "80:80"
    depends_on:
      - web

volumes:
  pgdata:
  media:
```

---

## 🔧 Ключові залежності (`requirements/base.txt`)

```txt
Django>=5.0
djangorestframework>=3.15
djangorestframework-gis>=1.0
django-filter>=24.0
psycopg[binary]>=3.1
Pillow>=10.0
celery>=5.3
redis>=5.0
gunicorn>=21.0
python-decouple>=3.8
gdal>=3.7
```

---

## 🚀 GitHub Actions CI/CD (`.github/workflows/ci.yml`)

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgis:
        image: kartoza/postgis:16-3.4
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements/local.txt
      - run: flake8 apps/
      - run: pytest --cov=apps --cov-report=xml

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:latest
```

---

## 🎯 Пріоритети розробки (MVP → Full)

### MVP (Мінімально життєздатний продукт)
- [ ] Django проєкт + GeoDjango налаштування
- [ ] Моделі `Route`, `Waypoint`, `POI`
- [ ] REST API: маршрути та POI в GeoJSON
- [ ] Leaflet карта з відображенням маршруту
- [ ] Docker Compose: web + db
- [ ] GitHub репозиторій + базовий CI

### v1.0
- [ ] Авторизація користувачів
- [ ] Малювання маршруту на карті (draw mode)
- [ ] Фільтрація POI по категорії
- [ ] Перемикання тайл-провайдерів (Google / Bing / OSM)
- [ ] Timeline компонент

### v2.0
- [ ] Завантаження фото з геоприв'язкою
- [ ] Прогноз погоди (OpenWeather API)
- [ ] Експорт маршруту у GPX / KML
- [ ] Кластеризація маркерів
- [ ] Мобільна адаптація + PWA

---

## 📝 .env.example

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=maproute_db
DB_USER=maproute
DB_PASSWORD=your-db-password
DB_HOST=db
DB_PORT=5432

# GDAL/GEOS (для локальної розробки без Docker)
GDAL_LIBRARY_PATH=/usr/lib/libgdal.so
GEOS_LIBRARY_PATH=/usr/lib/libgeos_c.so

# Redis
REDIS_URL=redis://redis:6379/0

# Media
MEDIA_ROOT=/app/media
```

---

> **Стек:** Python 3.12 · Django 5 · GeoDjango · PostgreSQL 16 · PostGIS 3.4 · DRF-GIS · Leaflet.js · Docker · GitHub Actions  
> **Тип:** Туристичний веб-геопортал · REST API · GeoJSON · Просторова база даних  
> **Стандарти:** NSDI-сумісне зберігання · OGC GeoJSON · WGS84 (SRID 4326)
