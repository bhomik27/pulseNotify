# PulseNotify

Flight price alert backend built with Django + DRF, Celery (worker + beat), Redis, PostgreSQL and JWT auth.
Users create price alerts; Celery Beat checks prices every 60 seconds against an internal mock price feed and fires async notifications when a threshold is met.

## Prerequisites
- Python 3.12+
- Docker Desktop
- Postman

## Setup
```
git clone <repo-url>
cd pulsenotify
python -m venv venv
venv\Scripts\activate          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # Linux/macOS: cp .env.example .env  (then fill in the values)
docker compose up -d           # PostgreSQL + Redis
python manage.py migrate
```

## Run (three terminals, venv activated in each)
```
python manage.py runserver
celery -A pulsenotify worker --loglevel=info --pool=solo   # --pool=solo is for Windows only
celery -A pulsenotify beat --loglevel=info
```
Create an alert with a high threshold (e.g. DEL-BOM at 7000). Within 60 seconds a `NotificationLog` row is written and the alert becomes `triggered`.

## Create an admin user
```
python manage.py shell -c "from django.contrib.auth.models import User; u=User.objects.create_user('pulse_admin','admin@example.com','adminpass123'); u.profile.role='admin'; u.profile.save()"
```
To promote an existing user: set `role` to `admin` in their `UserProfile` via the Django shell or PGAdmin.

## Tests
```
python manage.py test
```

## Postman
Import `PulseNotify.postman_collection.json`, make sure the server is running and the `pulse_admin` user exists, then run the collection with the Collection Runner (13 scenarios).
`make_postman.py` regenerates the collection file.

## Endpoints
| Method | Path | Auth |
|---|---|---|
| POST | /api/auth/register/ | public |
| POST | /api/auth/login/ | public |
| POST | /api/alerts/ | JWT |
| GET | /api/alerts/ | JWT |
| DELETE | /api/alerts/<id>/ | JWT |
| GET | /api/flights/price/?route=DEL-BOM | public |
| GET | /api/admin/summary/ | JWT + admin |