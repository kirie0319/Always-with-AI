pip install -r requirements.txtをする
その後に仮想環境を落とす
その後
python wsgi.py
celery -A worker worker --loglevel=info