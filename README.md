# Finance Advisory Project

AIを活用した金融アドバイザリーシステム。Claude 3.7 SonnetやGPT-4などの大規模言語モデルを使用して、金融に関する質問に回答し、アドバイスを提供します。

## 機能

- AIを活用した金融アドバイス
- 複数のAIプロバイダー（Anthropic Claude、OpenAI GPT）のサポート
- ユーザー認証システム
- チャット履歴の保存と管理
- 非同期タスク処理（Celery）
- RESTful API
- フロントエンドインターフェース

## 技術スタック

- **バックエンド**: Python, Flask, FastAPI
- **データベース**: PostgreSQL
- **AI/ML**: Anthropic Claude, OpenAI GPT
- **タスクキュー**: Celery, Redis
- **認証**: JWT
- **その他**: LangChain, SQLAlchemy

## セットアップ

1. リポジトリのクローン
```bash
git clone [repository-url]
cd finance-advisory-project
```

2. 仮想環境の作成と有効化
```bash
python -m venv venv
source venv/bin/activate  # Linuxの場合
# または
.\venv\Scripts\activate  # Windowsの場合
```

3. 依存関係のインストール
```bash
pip install -r requirements.txt
```

4. 環境変数の設定
`.env`ファイルを作成し、以下の変数を設定：
```
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key
DEBUG=True
HOST=0.0.0.0
PORT=5001
```

5. データベースのセットアップ
```bash
flask db upgrade
```

6. アプリケーションの起動
```bash
python wsgi.py
```

## プロジェクト構造

```
finance-advisory-project/
├── api/            # APIエンドポイント
├── auth/           # 認証関連
├── models/         # データベースモデル
├── templates/      # HTMLテンプレート
├── static/         # 静的ファイル
├── utils/          # ユーティリティ関数
├── prompts/        # AIプロンプト
├── data/           # データファイル
├── migrations/     # データベースマイグレーション
├── app.py          # アプリケーションエントリーポイント
├── config.py       # 設定ファイル
├── database.py     # データベース設定
├── requirements.txt # 依存関係
└── wsgi.py         # WSGIサーバー設定
```

## 環境変数

主要な環境変数：
- `ANTHROPIC_API_KEY`: Anthropic APIキー
- `OPENAI_API_KEY`: OpenAI APIキー
- `DEBUG`: デバッグモード（True/False）
- `HOST`: ホストアドレス
- `PORT`: ポート番号
- `DEFAULT_AI_PROVIDER`: デフォルトのAIプロバイダー
- `MAX_TOKENS`: 最大トークン数
- `MAX_RETRIES`: 最大リトライ回数

## ライセンス

[ライセンス情報を追加]

## 貢献

[貢献ガイドラインを追加]