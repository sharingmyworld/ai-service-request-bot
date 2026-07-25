# AI Service Request Bot

[![Tests](https://github.com/sharingmyworld/ai-service-request-bot/actions/workflows/tests.yml/badge.svg)](https://github.com/sharingmyworld/ai-service-request-bot/actions/workflows/tests.yml)

An AI-powered backend application that receives service requests through Telegram, classifies them with OpenAI, creates response drafts, and allows an administrator to approve or reject messages before they are sent back to the user.

The project demonstrates backend development with FastAPI, PostgreSQL, SQLAlchemy, Alembic, external API integrations, structured AI output validation, automated tests, Docker, and continuous integration.

## Main workflow

```text
Telegram user
    ↓
Telegram webhook
    ↓
Service request saved in PostgreSQL
    ↓
OpenAI classifies the request
    ↓
Pydantic validates the AI response
    ↓
Draft response created
    ↓
Administrator approves or rejects the draft
    ↓
Approved response sent through Telegram
    ↓
Every action saved in the activity log
```

## Features

- Receive service requests through a Telegram webhook
- Validate Telegram webhook requests with a secret token
- Prevent duplicate processing using Telegram `update_id`
- Save service requests in PostgreSQL
- Classify requests with OpenAI
- Validate structured AI responses with Pydantic
- Detect:
  - problem category
  - urgency level
  - location
  - summary
- Generate a draft response
- Allow an administrator to approve the AI draft
- Allow an administrator to edit the response before approval
- Allow an administrator to reject the response with a reason
- Send approved responses through Telegram Bot API
- Store all important actions in an activity log
- Mock OpenAI and Telegram APIs in tests
- Run the complete application with Docker Compose
- Run migrations and tests automatically with GitHub Actions

## Supported problem categories

- `plumbing`
- `electrical`
- `heating`
- `elevator`
- `security`
- `cleaning`
- `other`

## Supported urgency levels

- `low`
- `medium`
- `high`
- `critical`

## Service request statuses

```text
new
drafted
approved
rejected
sent
```

## Technology stack

- Python 3.14
- FastAPI
- PostgreSQL
- SQLAlchemy 2
- Alembic
- Pydantic 2
- OpenAI API
- Telegram Bot API
- HTTPX
- Pytest
- Docker
- Docker Compose
- GitHub Actions

## Architecture

```mermaid
flowchart TD
    A[Telegram user] --> B[Telegram webhook]
    B --> C[FastAPI]
    C --> D[(PostgreSQL)]
    C --> E[OpenAI service]
    E --> F[Pydantic validation]
    F --> D
    G[Administrator] --> C
    C --> H[Telegram Bot API]
    H --> A
    C --> I[Activity log]
    I --> D
```

## Project structure

```text
ai-service-request-bot/
├── .github/
│   └── workflows/
│       └── tests.yml
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── models/
│   │   ├── activity_log.py
│   │   └── service_request.py
│   ├── routers/
│   │   ├── service_requests.py
│   │   └── telegram_webhook.py
│   ├── schemas/
│   │   ├── activity_log.py
│   │   ├── admin_review.py
│   │   ├── ai_analysis.py
│   │   ├── service_request.py
│   │   └── telegram_update.py
│   ├── services/
│   │   ├── openai_service.py
│   │   └── telegram_service.py
│   ├── config.py
│   ├── database.py
│   └── main.py
├── tests/
├── .dockerignore
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Running the project with Docker

### Requirements

Install:

- Docker Desktop
- Docker Compose
- Git

### 1. Clone the repository

```bash
git clone https://github.com/sharingmyworld/ai-service-request-bot.git
cd ai-service-request-bot
```

### 2. Create the environment file

PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux or macOS:

```bash
cp .env.example .env
```

### 3. Configure environment variables

Open `.env` and provide your configuration:

```env
POSTGRES_DB=ai_service_request
POSTGRES_USER=service_request_user
POSTGRES_PASSWORD=change_me
POSTGRES_PORT=5433

DATABASE_URL=postgresql+psycopg://service_request_user:change_me@localhost:5433/ai_service_request

OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5-mini

TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_WEBHOOK_SECRET=change_me_webhook_secret
```

Never commit the real `.env` file or API keys.

### 4. Build and start the containers

```bash
docker compose up --build -d
```

### 5. Check the containers

```bash
docker compose ps
```

Both services should be healthy:

```text
ai_service_request_api
ai_service_request_db
```

### 6. Open the API documentation

```text
http://127.0.0.1:8000/docs
```

### 7. Stop the application

```bash
docker compose down
```

To also delete the PostgreSQL volume and all local database data:

```bash
docker compose down -v
```

## Running locally without the application container

PostgreSQL can run in Docker while FastAPI runs directly on the local machine.

### 1. Create a virtual environment

```powershell
python -m venv .venv
```

### 2. Activate it

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Start PostgreSQL

```powershell
docker compose up -d db
```

### 5. Run database migrations

```powershell
alembic upgrade head
```

### 6. Start FastAPI

```powershell
python -m uvicorn app.main:app --reload
```

## API endpoints

### Health checks

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Checks whether the API is running |
| GET | `/health/database` | Checks the PostgreSQL connection |

### Service requests

| Method | Endpoint | Description |
|---|---|---|
| POST | `/service-requests` | Creates a service request |
| GET | `/service-requests` | Returns all service requests |
| GET | `/service-requests/{request_id}` | Returns one service request |
| POST | `/service-requests/{request_id}/analyze` | Runs AI classification |
| POST | `/service-requests/{request_id}/approve` | Approves a draft response |
| POST | `/service-requests/{request_id}/reject` | Rejects a draft response |
| POST | `/service-requests/{request_id}/send` | Sends an approved response |
| GET | `/service-requests/{request_id}/activity-logs` | Returns the activity history |

### Telegram

| Method | Endpoint | Description |
|---|---|---|
| POST | `/telegram/webhook` | Receives Telegram updates |

## Example service request

```json
{
  "telegram_chat_id": 123456789,
  "telegram_user_id": 987654321,
  "user_message": "Water is leaking under the kitchen sink in apartment 12."
}
```

## Example validated AI result

```json
{
  "category": "plumbing",
  "urgency": "high",
  "location": "Kitchen, apartment 12",
  "summary": "Water is leaking under the kitchen sink.",
  "draft_response": "Thank you for reporting the leak. The maintenance team will review your request."
}
```

The OpenAI response is validated using a strict Pydantic model. Invalid categories, urgency values, missing required fields, and unexpected fields are rejected.

## Administrator review

Approve an AI draft without changing it:

```json
{
  "admin_id": "admin-1"
}
```

Approve with an edited response:

```json
{
  "admin_id": "admin-1",
  "approved_response": "Thank you for your report. The maintenance team will review the issue shortly."
}
```

Reject a draft:

```json
{
  "admin_id": "admin-1",
  "reason": "The response contains an unconfirmed promise."
}
```

## Activity log

The application records actions including:

```text
service_request_created
ai_analysis_completed
ai_analysis_failed
service_request_approved
service_request_rejected
telegram_message_sent
telegram_update_duplicate_ignored
```

Activity log entries contain:

- service request ID
- action name
- actor type
- actor ID
- additional JSON details
- creation timestamp

## Tests

Run all tests:

```bash
pytest -q
```

The test suite covers:

- health endpoints
- PostgreSQL integration
- service request creation and retrieval
- Pydantic AI response validation
- OpenAI service mocking
- AI classification workflow
- administrator approval and rejection
- Telegram API mocking
- approved message delivery
- Telegram webhook validation
- duplicate Telegram updates
- activity logs
- complete end-to-end workflow

External OpenAI and Telegram requests are mocked, so automated tests do not require real API keys and do not generate API costs.

## Database migrations

Create a migration after changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "migration description"
```

Apply all migrations:

```bash
alembic upgrade head
```

Check the current migration:

```bash
alembic current
```

## Continuous integration

GitHub Actions runs automatically after every push to `main` or `master` and for every pull request.

The workflow:

1. starts PostgreSQL,
2. configures Python,
3. installs dependencies,
4. runs Alembic migrations,
5. runs the complete Pytest suite.

Workflow file:

```text
.github/workflows/tests.yml
```

## Security notes

- API keys are loaded from environment variables.
- The `.env` file is excluded from Git.
- Telegram webhook requests require a secret header.
- Duplicate Telegram updates are protected by a unique database constraint.
- AI output is validated before it is saved.
- Responses require administrator approval before they can be sent.
- External APIs are mocked during automated tests.

## Current limitations

- Administrator authentication has not been implemented yet.
- There is no graphical administration panel.
- The Telegram webhook requires a public HTTPS address in production.
- AI processing currently happens inside the webhook request.
- Message delivery is not handled by a background task queue.
- There is no production deployment configuration yet.

## Planned improvements

- JWT authentication for administrators
- Role-based access control
- Web administration dashboard
- Background jobs with Celery or another task queue
- Automatic retry handling
- Rate limiting
- Structured application logging
- Production deployment
- Monitoring and error tracking
- Additional service request categories

## License

This project is currently provided for portfolio and educational purposes.