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

## Deploy to Northflank

The Docker image runs Gunicorn, collects static files at build time, and applies migrations on container startup. In Northflank:

1. Connect the `dive0-bit/Tweets` GitHub repository and create a service that builds from the repository's `Dockerfile` at the root. The project root must be the build context.
2. Create a PostgreSQL database service. Check its plan/pricing and provision it in the same Northflank project/region as the web service.
3. Configure the web service to expose/route container port `8000` over HTTP.
4. Add runtime environment variables to the web service:
   - `DJANGO_SECRET_KEY`: generate a new private value.
   - `DJANGO_DEBUG`: `0`.
   - `DJANGO_ALLOWED_HOSTS`: the public Northflank domain/hostname (hostname only; no scheme).
   - `DATABASE_URL`: the PostgreSQL connection URL supplied for the Northflank database. Keep the credential private.
   - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`: all three Cloudinary values; required for persistent user-uploaded photos in production.
5. Deploy the service and check build/runtime logs. Startup runs `migrate --noinput`; the container then starts Gunicorn on port `8000`.
6. Open the public service domain and verify `/tweet/`, login, a tweet upload, and a reply.

The service needs a persistent PostgreSQL service and Cloudinary media storage; the container's local filesystem is not used for production database/photo persistence. The existing Render `messenger-db` should not be reused unless you create a separate database/schema for this app. Northflank pricing/free-tier availability can change, so confirm the database and service costs before provisioning.

For local Docker Compose, the Compose service overrides the production entrypoint and continues using Django's development server with its own persistent SQLite/media volumes.

## Configuration

Settings can be configured with environment variables:

- `DJANGO_SECRET_KEY`: Django signing key. Required when `DJANGO_DEBUG=0`.
- `DJANGO_DEBUG`: defaults to `1` for local development. Set to `0` in deployment.
- `DJANGO_ALLOWED_HOSTS`: comma-separated hostnames; defaults to `localhost,127.0.0.1`.
- `DJANGO_SECURE_SSL_REDIRECT`: defaults to on when debug is off.
- `DJANGO_SECURE_HSTS_SECONDS`: HSTS duration in seconds; production default is `3600`.
- `DJANGO_EMAIL_BACKEND`: optional mail backend override; production defaults to SMTP, local development to console output.
- `DATABASE_URL`: PostgreSQL URL. Required when `DJANGO_DEBUG=0`; without it, local development uses SQLite.
- `DATABASE_PATH`: optional SQLite database file path.
- `MEDIA_ROOT`: optional directory for user-uploaded photos.
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`: set all three to store uploaded photos on Cloudinary. They are required when `DJANGO_DEBUG=0`; local development uses filesystem storage.

For Docker Compose, these variables can be set in the shell or an untracked root `.env` file. Never commit real secrets.

## Deploy to Render

This repository is prepared for a Render **Python Web Service** (not the local Docker Compose service). In the Render Dashboard:

1. Create a managed PostgreSQL database. Copy its **internal** connection URL.
2. Create a Web Service and connect `dive0-bit/Tweets`, branch `main`. Leave Root Directory empty (repository root).
3. Set:
   - **Build Command:** `pip install -r requirements.txt && python tweets/manage.py collectstatic --noinput`
   - **Start Command:** `cd tweets && python manage.py migrate && gunicorn tweets.wsgi:application --bind 0.0.0.0:$PORT`
4. Add these Web Service environment variables:
   - `DJANGO_SECRET_KEY`: generate a new private value (Render's Generate option is suitable).
   - `DJANGO_DEBUG`: `0`
   - `DJANGO_ALLOWED_HOSTS`: the exact Render hostname, for example `tweets-example.onrender.com` (no `https://`).
   - `DATABASE_URL`: the PostgreSQL internal connection URL from step 1.
   - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`: copy these from the Cloudinary dashboard. Keep the API secret private.
5. Deploy. Open the Render service URL and check `/tweet/`; inspect deploy logs if build, migrations, or startup fail.

The build collects static assets and WhiteNoise serves them. Uploaded photos use Cloudinary; production startup intentionally fails if its credentials are missing. PostgreSQL and Cloudinary accounts must be provisioned separately. The Render database starts separately from the local SQLite database, so existing local users/tweets/photos are not copied automatically. Do not use the local `docker-compose.yml` as the Render production start command.

The service uses Gunicorn, requires PostgreSQL and Cloudinary in production, enables secure cookies and HTTPS redirection when debug is off, and selects SMTP instead of the development console email backend. Email is not currently used by the app. Before public production use, also review Django's deployment checklist, backups, Cloudinary access policy, and account/service plans.

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
