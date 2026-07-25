FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt /code/requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install \
        --no-cache-dir \
        -r /code/requirements.txt

COPY alembic.ini /code/alembic.ini
COPY alembic /code/alembic
COPY app /code/app

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"]