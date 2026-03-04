FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install django gunicorn whitenoise
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

#optional
RUN useradd -m myuser
RUN chown -R 1000:1000 /app
USER myuser

EXPOSE 8000


CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn --bind 0.0.0.0:8000 config.wsgi:application"]
