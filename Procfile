# Procfile
web: gunicorn -k uvicorn.workers.UvicornWorker wsgi:app -c gunicorn.conf.py
worker: celery -A worker worker --loglevel=info