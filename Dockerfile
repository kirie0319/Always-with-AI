FROM python:3.11

WORKDIR /app

RUN apt-get update && apt-get install -y python3-dev

COPY requirements.txt .

RUN python -m pip install --upgrade pip && \
    python -m pip install setuptools wheel && \
    python -m pip install -r requirements.txt

COPY . .

CMD gunicorn app:app --bind 0.0.0.0:$PORT