# Saints Distribution — Backend (Django + DRF)

Distribution-network API: brand ambassadors, inventory, cash-basis sales,
location check-ins, and demand forecasting. Product lines (manufacturer →
brand → product) are data, not code — CRP/Boss/RG ship as seed data, and
adding a new manufacturer or brand is an admin/API call, not a deploy.

## Setup

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py makemigrations accounts catalog inventory sales tracking alerts
python manage.py migrate
python manage.py createsuperuser        # your own admin login
python manage.py seed_demo              # CRP/Boss/RG + demo users, all password: changeme123

python manage.py runserver 0.0.0.0:8000
```

Visit `/admin/` to browse/edit everything by hand, or use the API below.

## Auth

JWT. Get a token:

```
POST /api/auth/token/          {"username": "ba_tapiwa", "password": "changeme123"}
POST /api/auth/token/refresh/  {"refresh": "<refresh_token>"}
```

Send `Authorization: Bearer <access_token>` on every other request.

## Key endpoints

| Endpoint | Who | Purpose |
|---|---|---|
| `GET /api/accounts/users/me/` | anyone | current user's profile |
| `GET /api/catalog/products/` | anyone | active product catalog |
| `GET /api/inventory/items/` | scoped by role | BA sees own stock, Supervisor sees team, Manager sees all |
| `POST /api/sales/sales/log_sale/` | BA | `{product, quantity, latitude, longitude}` — logs a cash sale **and** decrements stock atomically |
| `GET /api/sales/sales/` | scoped by role | sales history |
| `POST /api/tracking/checkins/` | BA | `{latitude, longitude, source: "MANUAL"|"PASSIVE"}` |
| `GET /api/analytics/dashboard/overview/` | Supervisor/Manager | KPIs, top BAs, region breakdown |
| `GET /api/analytics/demand-forecast/` | Supervisor/Manager | restock predictions per region × product |
| `POST /api/accounts/users/bulk_import/` | Supervisor/Manager | multipart CSV upload → creates users with temp passwords |
| `POST /api/accounts/users/set_password/` | anyone | `{new_password}` — self-service, also clears `must_change_password` |
| `POST /api/accounts/device-tokens/` | anyone | `{token, platform}` — register this device for push notifications |
| `GET /api/alerts/` | Supervisor/Manager | open (unresolved) alerts, scoped to team/everyone |
| `POST /api/alerts/{id}/resolve/` | Supervisor/Manager | acknowledge/dismiss an alert |
| `GET /api/analytics/live-map/` | Supervisor/Manager | every BA's last known position + quick status, for the map view |

## Alerts & push notifications

Alerts (out-of-stock, low-stock, inactive-BA) are **detected and
persisted**, not computed live on every request — this is what lets a
push notification fire exactly once per condition instead of every time
someone opens the app.

Run the detection job periodically (it's idempotent — safe to run as
often as you like):

```bash
python manage.py check_alerts
```

In production, put it on a schedule — cron is simplest to start with:
```cron
*/10 * * * * cd /path/to/backend && venv/bin/python manage.py check_alerts
```
(Celery beat is the natural upgrade if you're already running Celery for
something else — `check_alerts.py`'s logic doesn't change either way.)

The job creates an `Alert` row the first time a condition is seen, sends
a push to the affected BA's supervisor + all managers, and **auto-resolves**
the alert the moment the condition clears (restocked, checked back in) —
so `GET /api/alerts/` only ever shows what's still actually true.

**Push requires your own Firebase project** — nothing works with
placeholder credentials, by design (see `apps/alerts/push.py` for the
3-step setup: create a Firebase project, generate a service account key,
set `FIREBASE_CREDENTIALS_PATH`). Without that set, `check_alerts` still
runs and still creates/resolves Alert rows — the app's alerts screen
works either way — it just won't push a phone notification until Firebase
is configured.

## Live map

`GET /api/analytics/live-map/` returns every BA's last check-in location
(lat/lng), how long ago it was, today's cash collected, and a stock-health
count — everything the Flutter map screen needs in one call. A BA with
no check-in in the last 6 hours comes back with `is_stale: true` so the
map can visually distinguish "active in the field" from "gone quiet."

## Bulk-onboarding 500+ Brand Ambassadors

Two ways in, same logic under the hood (`apps/accounts/bulk_import.py`):

**Command line** (fastest for a one-time bulk load):
```bash
python manage.py import_bas path/to/your_bas.csv
```

**API** (for a future admin screen, or if a supervisor does their own region):
```bash
curl -X POST http://localhost:8000/api/accounts/users/bulk_import/ \
  -H "Authorization: Bearer <token>" \
  -F "file=@your_bas.csv"
```

CSV columns: `first_name,last_name,username,phone,region,supervisor_username,role`
— a filled-in example is at `ba_import_template.csv`. `username` and `role`
are optional (auto-generated / defaults to BA); `region` is created
automatically if it doesn't exist yet; `supervisor_username` must already exist.

Every created user gets a **random temporary password** printed once
(command line) or returned once in the response (API) — save it
immediately, it's never stored anywhere. Each new user has
`must_change_password=True` and must call `POST /users/set_password/`
before doing anything else — the Flutter app enforces this with a
"set your password" screen on first login (see `mobile_app/README.md`).

Role scoping (BA sees only their own data; Supervisor sees their team;
Manager/Admin see everything) is enforced server-side via
`RoleScopedQuerysetMixin` in `apps/accounts/permissions.py` — every new
ViewSet you add should use it.

## Testing

A real, runnable test suite — actual behavior checks, including the
three bugs found and fixed during review (see below):

```bash
python manage.py test
```

Coverage by app:
- `apps/sales/tests.py` — stock decrements correctly on a sale, a sale
  that exceeds available stock is rejected cleanly (400, not a crash)
  and leaves stock untouched, BA/Supervisor scoping on the sales list.
- `apps/accounts/tests.py` — BA/Supervisor/Manager user-list scoping,
  the bulk-import CSV path (success, duplicate username, unknown
  supervisor), first-login password reset clearing `must_change_password`.
- `apps/alerts/tests.py` — out-of-stock and inactive-BA alerts get
  created, restocking/checking-in auto-resolves them, running the
  detection job twice doesn't duplicate an open alert, supervisor/manager
  scoping on the alerts list, the resolve endpoint.
- `apps/analytics/tests.py` — demand-forecast sorting with multiple
  no-sales-history products (the None-comparison regression, see below),
  live-map scoping and the stale/recent check-in flag.

**Three real bugs were caught writing these and fixed in this delivery:**
1. `UserViewSet` scoped Supervisors and Managers correctly but not BAs —
   a BA hitting `GET /api/accounts/users/` would have seen the entire
   org's user list. Fixed to scope BAs to themselves only.
2. `DemandForecastView` sorted results with a key that could produce two
   `None` values needing direct comparison (`None < None`), which raises
   `TypeError` in Python 3 — this would have crashed the endpoint any
   time two or more products had stock but no sales history yet (i.e.
   likely on a fresh install). Fixed with a sentinel value for the sort.
3. `log_sale` let a plain `ValueError` (insufficient stock) fall through
   uncaught, returning a raw 500 instead of a clean validation error.
   Fixed to translate it to a proper 400 response.

I don't have Django, a database, or network access in the environment I
built this in, so I couldn't execute this suite myself — `python manage.py
test` on your machine is the first real confirmation these pass. If
anything fails, the traceback plus the test name should point straight
at the problem.

## Adding a new product line

No code change needed:

```bash
python manage.py shell
```
```python
from apps.catalog.models import Manufacturer, Brand, Product
m, _ = Manufacturer.objects.get_or_create(name="New Manufacturer")
b, _ = Brand.objects.get_or_create(manufacturer=m, name="New Brand")
Product.objects.create(brand=b, name="New Product 20s", sku="NEW-PROD-20", unit="carton", price=35.00)
```
...or do the same through `/admin/` or a `POST /api/catalog/products/` call once
you're a supervisor/manager.

## Moving to Postgres

Set env vars before `runserver`/deploy:
```
DB_ENGINE=django.db.backends.postgresql
DB_NAME=... DB_USER=... DB_PASSWORD=... DB_HOST=... DB_PORT=5432
```
SQLite (zero-setup default) is fine for dev and small pilots; move to
Postgres before onboarding the full 500+ BA rollout.
