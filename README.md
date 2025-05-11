# ファイナンス アドバイザリー プロジェクト

## プロジェクト概要
このアプリケーションは、高度な財務アドバイスと分析を提供するAIベースのファイナンスツールです。

## 必要条件
- Python 3.8+
- pip
- 仮想環境 (venv または conda)

## セットアップ手順

1. リポジトリをクローン
```bash
git clone https://github.com/your-username/finance-advisory-project.git
cd finance-advisory-project
```

2. 仮想環境を作成と有効化
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# または
venv\Scripts\activate  # Windows
```

3. 依存関係をインストール
```bash
pip install -r requirements.txt
```

4. アプリケーションの起動
```bash
# メインアプリケーションを起動
python wsgi.py

# バックグラウンドワーカーを別のターミナルで起動
celery -A worker worker --loglevel=info
```

## 主な機能
- AIを活用した財務アドバイス
- リアルタイムの財務分析
- インタラクティブな投資シミュレーション

## 技術スタック
- FastAPI
- Celery
- OpenAI API
- SQLAlchemy

## ライセンス
[適切なライセンスを追加]

## 貢献
プルリクエストは歓迎します。大きな変更を行う前に、まずissueで議論してください。

## 注意
本アプリケーションは参考情報のみを提供し、専門的な財務アドバイスの代替とはなりません。投資判断は慎重に行ってください。