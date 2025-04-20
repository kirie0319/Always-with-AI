web: gunicorn wsgi:app -c gunicorn.conf.py
worker: celery -A worker worker --loglevel=info