# Live Quiz Backend

Django + DRF backend for a real-time mini-test platform. Teachers can create quizzes, start live sessions, and receive live updates while students join with a room code, answer questions in real time, and see final rankings.

## Features

- JWT authentication for teachers (phone + password)
- Quiz builder with nested questions and 2-4 answer variants
- Unique room code per quiz
- Real-time updates for joins, quiz start/finish, and leaderboard updates via WebSockets (Django Channels)
- Student joining flow with live roster updates
- Submission endpoint that accepts batched answers (send once or per question)
- Automatic scoreboard calculation and optional Telegram summary (Top 3 + total participants)
- Django admin and Swagger/OpenAPI docs included

## Tech Stack

- Django 5 + Django REST Framework
- Django Channels (in-memory or Redis channel layer)
- PostgreSQL (via `DATABASE_URL`), falls back to SQLite for local development
- JWT auth with `djangorestframework-simplejwt`
- Swagger UI provided by `drf-yasg`

## Getting Started

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create superuser (for admin access)
python manage.py createsuperuser --phone <phone> --full_name "Teacher" --email example@example.com

# Run development server (HTTP + WebSocket via ASGI)
python manage.py runserver 0.0.0.0:8000
```

Swagger docs will be available at [`/swagger/`](http://localhost:8000/swagger/). Django admin lives at `/admin/`.

## Environment Variables

| Variable | Description |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django secret key (defaults to a local-only unsafe value). |
| `DJANGO_DEBUG` | Set to `true` to enable debug mode. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames. Defaults to `*`. |
| `DATABASE_URL` | Database connection string (e.g. `postgres://user:pass@host:5432/db`). |
| `REDIS_URL` | Redis connection string for Channels (optional, defaults to in-memory layer). |
| `JWT_ACCESS_MINUTES` | Access token lifetime in minutes (default: 60). |
| `JWT_REFRESH_DAYS` | Refresh token lifetime in days (default: 7). |
| `TELEGRAM_BOT_TOKEN` | Bot token used to send quiz summary messages (optional). |
| `TELEGRAM_CHAT_ID` | Telegram chat ID that should receive quiz summary messages (optional). |

Create a `.env` file if needed:

```
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true
DATABASE_URL=postgres://user:password@localhost:5432/livequiz
```

## Deployment Notes

- Use an ASGI server such as `daphne` or `uvicorn` (via `python -m daphne quiz_backend.asgi:application`).
- Configure Redis and set `REDIS_URL` for production-ready WebSocket scaling.
- Run `python manage.py collectstatic` if serving static files from Django.
- Railway deployment can run migrations via `python manage.py migrate` during release.

## Key API Endpoints

### Auth (Teacher)

- `POST /api/auth/register/` – register a teacher account (`phone`, `full_name`, `password`).
- `POST /api/auth/login/` – obtain access + refresh tokens (returns user profile).
- `POST /api/auth/refresh/` – refresh access token.
- `GET /api/auth/profile/` – current teacher profile.

### Teacher Quiz Management (JWT protected)

- `GET /api/quizzes/` – list teacher quizzes.
- `POST /api/quizzes/` – create quiz with nested questions and choices.
- `POST /api/quizzes/{id}/start/` – start a quiz (optionally update `duration_seconds`).
- `POST /api/quizzes/{id}/finish/` – end quiz manually.
- `GET /api/quizzes/{id}/status/` – live quiz status and scoreboard.
- `GET /api/quizzes/{id}/results/` – final results snapshot.
- `GET /api/quizzes/leaderboard/{id}/` – simplified ranking list.

### Student Flow (public)

- `POST /api/quizzes/join/` – join by room code + name (returns student ID for session).
- `GET /api/quizzes/room/{code}/` – fetch quiz state/questions.
- `POST /api/quizzes/room/{code}/students/{student_id}/answers/` – submit answers in bulk (supports send-once or per-question).
- WebSocket: `ws://<host>/ws/quizzes/{code}/` – subscribe for real-time events (joins, start, finish, scoreboard updates).

### Real-time Events

Payloads broadcast over the WebSocket channel include:

- `quiz_created`
- `student_joined`
- `quiz_started`
- `scoreboard_updated`
- `quiz_finished`

Each payload contains the necessary metadata (`quiz` snapshot, `time_remaining`, `scoreboard`, etc.) for the front-end to update immediately.

## Testing

Run Django test suite (requires installing dependencies first):

```bash
python manage.py test
```

## License

MIT
