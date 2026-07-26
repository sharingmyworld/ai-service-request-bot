# AI Service Request Bot

[![Tests](https://github.com/sharingmyworld/ai-service-request-bot/actions/workflows/tests.yml/badge.svg)](https://github.com/sharingmyworld/ai-service-request-bot/actions/workflows/tests.yml)

An AI-powered backend application that receives service requests through Telegram, classifies them with OpenAI, creates response drafts, and allows an authenticated administrator to review and send responses.

The project demonstrates backend development with FastAPI, PostgreSQL, SQLAlchemy, Alembic, JWT authentication, structured AI output validation, external API integrations, automated testing, Docker, and continuous integration.

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
Pydantic validates the structured AI response
    ↓
Draft response created
    ↓
Authenticated administrator reviews the request
    ↓
Administrator approves, edits, or rejects the draft
    ↓
Approved response sent through Telegram
    ↓
Every important action saved in the activity log
```

## Features

### Telegram integration

- Receive service requests through a Telegram webhook
- Validate webhook requests with a secret token
- Ignore unsupported non-text updates
- Prevent duplicate processing using Telegram `update_id`
- Send approved responses through the Telegram Bot API

### AI classification

- Analyze service requests with OpenAI
- Validate structured AI output using Pydantic
- Detect:
  - problem category
  - urgency level
  - location
  - summary
- Generate a response draft
- Reject malformed or unexpected AI output

### Administrator authentication

- Create administrator accounts from the command line
- Hash passwords using Argon2
- Log in using OAuth2 password form
- Generate signed JWT access tokens
- Validate token expiration and signature
- Retrieve the currently authenticated administrator
- Reject inactive administrator accounts
- Change an administrator password
- Prevent password reuse

### Request management

- List service requests
- Filter requests by:
  - status
  - category
  - urgency
  - search text
- Paginate results using `offset` and `limit`
- Read full request details
- Read request activity history
- Approve an AI-generated draft
- Edit a response before approval
- Reject a response with a reason
- Send an approved response through Telegram
- Prevent invalid status transitions

### Administration dashboard

- Total number of requests
- Requests grouped by status
- Requests grouped by category
- Requests grouped by urgency
- Requests waiting for administrator review
- Approved requests waiting to be sent
- Number of critical requests

### Testing and infrastructure

- PostgreSQL integration tests
- Mocked OpenAI API requests
- Mocked Telegram API requests
- Complete workflow tests
- Authentication and authorization tests
- Docker and Docker Compose support
- Automated database migrations
- GitHub Actions continuous integration
- 85 automated tests

## Supported problem categories

```text
plumbing
electrical
heating
elevator
security
cleaning
other
```

## Supported urgency levels

```text
low
medium
high
critical
```

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
- PostgreSQL 17
- SQLAlchemy 2
- Alembic
- Pydantic 2
- OpenAI API
- Telegram Bot API
- HTTPX
- PyJWT
- pwdlib with Argon2
- Pytest
- Docker
- Docker Compose
- GitHub Actions

## Architecture

```mermaid
flowchart TD
    A[Telegram user] --> B[Telegram webhook]
    B --> C[FastAPI application]
    C --> D[(PostgreSQL)]
    C --> E[OpenAI service]
    E --> F[Pydantic validation]
    F --> D

    G[Administrator] --> H[JWT authentication]
    H --> C

    C --> I[Telegram Bot API]
    I --> A

    C --> J[Activity log]
    J --> D
```

## Security model

The application separates public request intake from administrative operations.

### Public operations

- Telegram webhook
- Manual service request creation
- Health checks
- Administrator login

### Protected operations

The following operations require a valid JWT Bearer token:

- administrator profile
- password change
- dashboard statistics
- request listing and filtering
- request details
- activity logs
- manual AI analysis
- draft approval
- draft rejection
- Telegram message delivery

Passwords are never stored directly. Only Argon2 password hashes are saved in PostgreSQL.

JWT tokens contain the administrator ID in the `sub` claim. Passwords and password hashes are never included in tokens.

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
│   ├── cli/
│   │   └── create_admin.py
│   ├── dependencies/
│   │   └── auth.py
│   ├── models/
│   │   ├── activity_log.py
│   │   ├── admin_user.py
│   │   └── service_request.py
│   ├── routers/
│   │   ├── admin_dashboard.py
│   │   ├── admin_service_requests.py
│   │   ├── auth.py
│   │   ├── service_requests.py
│   │   └── telegram_webhook.py
│   ├── schemas/
│   │   ├── activity_log.py
│   │   ├── admin_dashboard.py
│   │   ├── admin_review.py
│   │   ├── admin_service_requests.py
│   │   ├── admin_user.py
│   │   ├── ai_analysis.py
│   │   ├── auth.py
│   │   ├── service_request.py
│   │   └── telegram_update.py
│   ├── services/
│   │   ├── admin_service.py
│   │   ├── openai_service.py
│   │   ├── password_service.py
│   │   ├── telegram_service.py
│   │   └── token_service.py
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

## Running with Docker

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

Open `.env` and configure:

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

JWT_SECRET_KEY=change_me_with_a_long_random_secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Generate a secure JWT secret:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Never commit the real `.env` file, passwords, access tokens, or API keys.

### 4. Build and start the containers

```bash
docker compose up --build -d
```

The application container automatically runs:

```text
alembic upgrade head
```

before starting FastAPI.

### 5. Check container status

```bash
docker compose ps
```

Expected services:

```text
ai_service_request_api
ai_service_request_db
```

### 6. Open Swagger UI

```text
http://127.0.0.1:8000/docs
```

### 7. Stop the application

```bash
docker compose down
```

This stops the containers without deleting PostgreSQL data.

To also delete the database volume:

```bash
docker compose down -v
```

Warning: using `-v` permanently removes the local database data.

## Creating an administrator

Create an administrator inside the application container:

```powershell
docker compose exec app python -m app.cli.create_admin --username portfolio-admin
```

The terminal asks for the password twice:

```text
Administrator password:
Confirm administrator password:
```

Password input is hidden. The password must contain at least 12 characters.

Passwords are not passed as command-line arguments, so they are not stored in terminal command history.

## Administrator login

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

Click:

```text
Authorize
```

Provide the administrator username and password.

FastAPI sends the credentials to:

```text
POST /auth/login
```

A successful login returns:

```json
{
  "access_token": "signed-jwt-token",
  "token_type": "bearer"
}
```

The token is then used in the HTTP header:

```text
Authorization: Bearer signed-jwt-token
```

## Running locally without the application container

PostgreSQL can run in Docker while FastAPI runs directly on the host machine.

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

### 5. Apply migrations

```powershell
alembic upgrade head
```

### 6. Start FastAPI

```powershell
python -m uvicorn app.main:app --reload
```

## API endpoints

### Health checks

| Method | Endpoint | Authentication | Description |
|---|---|---:|---|
| GET | `/health` | No | Checks whether the API is running |
| GET | `/health/database` | No | Checks the PostgreSQL connection |

### Authentication

| Method | Endpoint | Authentication | Description |
|---|---|---:|---|
| POST | `/auth/login` | No | Logs in an administrator |
| GET | `/auth/me` | Bearer | Returns the current administrator |
| POST | `/auth/change-password` | Bearer | Changes the administrator password |

### Administration

| Method | Endpoint | Authentication | Description |
|---|---|---:|---|
| GET | `/admin/dashboard` | Bearer | Returns dashboard statistics |
| GET | `/admin/service-requests` | Bearer | Returns a filtered and paginated list |
| GET | `/admin/service-requests/{request_id}` | Bearer | Returns request details |
| GET | `/admin/service-requests/{request_id}/activity-logs` | Bearer | Returns request activity history |

### Service requests

| Method | Endpoint | Authentication | Description |
|---|---|---:|---|
| POST | `/service-requests` | No | Creates a service request |
| GET | `/service-requests` | Bearer | Returns all service requests |
| GET | `/service-requests/{request_id}` | Bearer | Returns one service request |
| POST | `/service-requests/{request_id}/analyze` | Bearer | Runs AI classification |
| POST | `/service-requests/{request_id}/approve` | Bearer | Approves a draft |
| POST | `/service-requests/{request_id}/reject` | Bearer | Rejects a draft |
| POST | `/service-requests/{request_id}/send` | Bearer | Sends an approved response |
| GET | `/service-requests/{request_id}/activity-logs` | Bearer | Returns activity history |

### Telegram

| Method | Endpoint | Authentication | Description |
|---|---|---:|---|
| POST | `/telegram/webhook` | Secret header | Receives Telegram updates |

## Filtering service requests

Administrative requests can be filtered using query parameters.

### Status

```text
GET /admin/service-requests?status=drafted
```

### Category

```text
GET /admin/service-requests?category=plumbing
```

### Urgency

```text
GET /admin/service-requests?urgency=critical
```

### Text search

Searches in the user message and location:

```text
GET /admin/service-requests?search=kitchen
```

### Pagination

```text
GET /admin/service-requests?offset=0&limit=20
```

### Combined filters

```text
GET /admin/service-requests?status=drafted&urgency=critical&limit=10
```

The maximum allowed `limit` is `100`.

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

The OpenAI result is validated using a strict Pydantic model.

The application rejects:

- unsupported categories
- unsupported urgency values
- missing required fields
- unexpected fields
- malformed structured output

## Administrator review

Approve the AI draft without changes:

```json
{}
```

Approve with an edited response:

```json
{
  "approved_response": "Thank you for your report. The maintenance team will review the issue shortly."
}
```

Reject a draft:

```json
{
  "reason": "The response contains an unconfirmed promise."
}
```

The administrator ID is not accepted from the request body. It is taken from the verified JWT token.

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

Administrator actions also record the authenticated administrator username.

## Tests

Run all tests:

```bash
pytest -q
```

Current test result:

```text
85 passed
```

The test suite covers:

- API health checks
- PostgreSQL integration
- Alembic-compatible database models
- administrator creation
- Argon2 password hashing
- administrator login
- JWT creation and validation
- expired and invalid tokens
- inactive administrator accounts
- administrator profile
- password changes
- protected endpoint access
- dashboard statistics
- request filtering
- pagination
- request details
- activity history
- service request creation
- AI output validation
- mocked OpenAI integration
- administrator approval
- administrator rejection
- mocked Telegram delivery
- Telegram webhook validation
- duplicate Telegram updates
- complete request workflow

External OpenAI and Telegram requests are mocked during tests. Automated tests do not require real API keys and do not generate external API costs.

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

GitHub Actions runs after:

- every push to `main` or `master`
- every pull request

The workflow:

1. starts PostgreSQL,
2. configures Python,
3. installs dependencies,
4. applies Alembic migrations,
5. runs the complete Pytest suite.

Workflow file:

```text
.github/workflows/tests.yml
```

## Manual verification

The Dockerized application has been manually verified using Swagger UI.

The following endpoints returned HTTP `200`:

```text
GET /health/database
GET /auth/me
GET /admin/dashboard
GET /admin/service-requests
```

## Current limitations

- There is no graphical administration frontend.
- Forgotten passwords require creation of another administrator or a database-level reset.
- The Telegram webhook requires a public HTTPS address in production.
- AI processing currently happens inside the webhook request.
- Message delivery is not handled through a background task queue.
- Access tokens cannot currently be revoked before expiration.
- Refresh tokens have not been implemented.
- Production deployment has not yet been configured.

## Possible future improvements

- Web administration dashboard
- Password reset command
- Refresh tokens
- Access-token revocation
- Role-based access control
- Background jobs
- Automatic retries
- Rate limiting
- Structured production logging
- Monitoring and error tracking
- Production deployment
- Additional service request categories

## License

This project is provided for portfolio and educational purposes.