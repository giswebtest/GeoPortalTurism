Listed directory GeoPortalTurism
Viewed .env:1-11
Viewed compose.yaml:1-35

Ось що я знайшов у проекті. Ось покрокова інструкція для підключення до бази даних через **pgAdmin**:

---

## 🗄️ Параметри підключення до БД

З файлів `.env` і `compose.yaml` витягнуті такі дані:

| Параметр | Значення |
|---|---|
| **Host** | `localhost` |
| **Port** | `5432` |
| **Database** | `geodjango1` |
| **Username** | `postgres` |
| **Password** | `postgres` |

> [!IMPORTANT]
> БД запущена в Docker-контейнері (`postgis/postgis:16-3.4`). Щоб підключитися через pgAdmin, **контейнер має бути запущений**.

---

## 🚀 Кроки підключення

### 1. Переконайся що Docker-контейнери запущені
```powershell
cd d:\GeoPortalTurism\GeoPortalTurism
docker compose up -d db
```

### 2. Перевір що порт 5432 доступний
```powershell
docker ps
```
Маєш побачити контейнер `db` зі статусом `Up`.

> [!NOTE]
> В `compose.yaml` порт `5432` не пробрасується на хост! Тобто pgAdmin **не зможе** підключитися зовні, поки не додати маппінг портів.

### 3. Додай маппінг порту до `compose.yaml`

У сервісі `db` потрібно додати секцію `ports`:

```yaml
services:
  db:
    image: postgis/postgis:16-3.4
    env_file: .env
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"   # ← додай цей рядок
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

Після зміни — перезапусти:
```powershell
docker compose up -d db
```

### 4. Підключення в pgAdmin

1. Відкрий **pgAdmin 4**
2. Правою кнопкою → **Register → Server...**
3. Вкладка **General**:
   - Name: `MapRoute (Docker)`
4. Вкладка **Connection**:
   - **Host**: `localhost`
   - **Port**: `5432`
   - **Maintenance database**: `geodjango1`
   - **Username**: `postgres`
   - **Password**: `postgres`
   - ✅ Постав галочку **Save password**
5. Натисни **Save**

---

> [!TIP]
> База використовує **PostGIS** розширення. У pgAdmin можна перевірити через SQL Query Tool: `SELECT PostGIS_Version();` — має повернути версію PostGIS.

---

## 📁 Структура папок проекту

```text
Folder PATH listing
Volume serial number is 404F-3187
D:.
+---.idea
|   \---inspectionProfiles
+---accounts
|   \---migrations
+---docker
+---geoportal
+---maps
|   \---migrations
+---media
|   +---guides
|   \---locations
+---src
+---static
|   \---css
+---staticfiles
|   +---admin
|   |   +---css
|   |   |   \---vendor
|   |   |       \---select2
|   |   +---img
|   |   \---js
|   |       +---admin
|   |       \---vendor
|   |           +---jquery
|   |           +---select2
|   |           |   \---i18n
|   |           \---xregexp
|   +---css
|   \---gis
|       +---css
|       +---img
|       \---js
\---templates
    +---maps
    \---registration
```