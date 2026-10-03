# Tweets

A Django mini social app for creating photo/text tweets, following users, replying to tweets, and liking replies.

## Features

- Register, log in, and log out.
- Create, edit, and delete your own tweets (up to 240 characters, with an optional photo).
- Search tweets by text or username.
- Browse public and followed-user feeds.
- Find user profiles and follow/unfollow users.
- Open a tweet in a detail modal, zoom its photo, and read or post replies.
- Like/unlike replies. Each user can like a reply once.

## Tech stack

- Python 3.14
- Django 6.1
- SQLite
- Pillow for uploaded images
- Bootstrap 5
- Docker Compose (optional)

## Run locally

From the repository root in PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Set-Location .\tweets
python manage.py migrate
python manage.py check
python manage.py runserver
```

Open <http://127.0.0.1:8000/tweet/>. Other useful URLs:

- People: <http://127.0.0.1:8000/tweet/people/>
- Login: <http://127.0.0.1:8000/accounts/login/>
- Admin: <http://127.0.0.1:8000/admin/>

To create an admin account, run `python manage.py createsuperuser` from the `tweets` folder.

Run tests from that same folder:

```powershell
python manage.py test tweet
```

## Run with Docker Compose

From the repository root, with Docker Desktop running:

```powershell
docker compose up --build
```

Open <http://localhost:8000/tweet/>. The image collects static assets at build time. Compose applies migrations on startup and persists the SQLite database and uploaded photos in named Docker volumes.

```powershell
docker compose logs -f web
docker compose exec web python manage.py test tweet
docker compose down
```

`docker compose down -v` also deletes the persistent database and uploaded-photo volumes. Use it only when you intentionally want to remove that data.

## Configuration

Settings can be configured with environment variables:

- `DJANGO_SECRET_KEY`: Django signing key. Required when `DJANGO_DEBUG=0`.
- `DJANGO_DEBUG`: defaults to `1` for local development. Set to `0` in deployment.
- `DJANGO_ALLOWED_HOSTS`: comma-separated hostnames; defaults to `localhost,127.0.0.1`.
- `DJANGO_SECURE_SSL_REDIRECT`: defaults to on when debug is off.
- `DJANGO_SECURE_HSTS_SECONDS`: HSTS duration in seconds; production default is `3600`.
- `DJANGO_EMAIL_BACKEND`: optional mail backend override; production defaults to SMTP, local development to console output.
- `DATABASE_PATH`: optional SQLite database file path.
- `MEDIA_ROOT`: optional directory for user-uploaded photos.

For Docker Compose, these variables can be set in the shell or an untracked root `.env` file. Never commit real secrets.

## Project structure

```text
.
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── tweets/
    ├── manage.py
    ├── tweets/               # Django project settings and root URLs
    ├── tweet/                # App: models, views, forms, tests, migrations
    ├── templates/            # Shared layout and authentication templates
    └── media/                # Local uploads (ignored by Git)
```
