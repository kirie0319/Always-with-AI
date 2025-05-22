# wsgi.py
from fastapi import FastAPI, Request, HTTPException, Depends, Response, BackgroundTasks, status, Form 
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json, uuid, traceback, os, anthropic, asyncio
from colorama import Fore, Style
from contextlib import asynccontextmanager
from openai import AsyncOpenAI
from typing import Dict, List, Any, Optional

# モジュールとクラスのインポート
from database import get_db, engine 
from models.users import User
from models.prompts import Prompt 
from auth.jwt_auth import (
  create_access_token,
  get_current_user,
  ACCESS_TOKEN_EXPIRE_MINUTES
)
from auth.auth_router import router as auth_router

# 新しいモジュールのインポート
from utils.file_operations import load_json, save_json, to_pretty_json, clear_cache
from utils.retry_logic import with_retry
from utils.ai_stream_client import AIStreamClient
from utils.chatroom_manager import ChatroomManager
from utils.openrouter_stream import AIOpenRouterStreamClient as OpenRouterStreamClient
from tasks import generate_summary_task

from api.financial_routes import router as financial_router

# 環境変数の読み込み
load_dotenv()

# 定数設定
DATA_DIR = "data"
MAX_RALLIES = 6
MAX_TOKENS_INPUT = 8_000
MAX_TOKENS_OUTPUT = 512
SAFETY_MARGIN = 500
OPENROUTER_MODELS = ["anthropic/claude-3.7-sonnet"]

# CORS設定
CORS_ORIGINS = os.getenv("CORS_ORIGINS").split(",")
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS").lower() == "true"
CORS_ALLOW_METHODS = os.getenv("CORS_ALLOW_METHODS").split(",")
CORS_ALLOW_HEADERS = os.getenv("CORS_ALLOW_HEADERS").split(",")

# ディレクトリの作成
os.makedirs(DATA_DIR, exist_ok=True)

# APIクライアントの初期化
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_api_key
)

# AIストリーミングクライアントの初期化
ai_stream_client = AIStreamClient(anthropic_client, openrouter_client)
openrouter_stream_client = OpenRouterStreamClient()

# チャットルームマネージャーの初期化
chatroom_manager = ChatroomManager(data_dir=DATA_DIR, max_rallies=MAX_RALLIES)

# データベース設定
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# FastAPIアプリケーションの起動時・終了時の処理
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.execute(select(1))
            print("データベース接続成功")
    except Exception as e:
        print(f"データベース接続エラー: {e}")
    yield 
    print("アプリケーションシャットダウン")

# FastAPIアプリケーションの初期化
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("FLASK_SECRET_KEY")
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(financial_router)
app.include_router(auth_router)

# データベース依存関数
async def get_db():
    async with async_session() as session:
        yield session

# ログイン・認証関連エンドポイント
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})

@app.post("/register")
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        # メールアドレスの重複チェック
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="このメールアドレスはすでに登録されています"
            )
        
        # ユーザー名の重複チェック
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="このusernameはすでに登録されています"
            )
        
        # 新規ユーザーの作成
        new_user = User(
            username=username,
            email=email
        )
        new_user.set_password(password)

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # ユーザー登録後、チャットルームを作成
        await chatroom_manager.get_or_create_chatroom(new_user.id)
        print(f"新規ユーザー {username}(ID: {new_user.id}) のチャットルームを作成しました")

        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    except HTTPException as e:
        # 既存のHTTPExceptionを再送信
        raise e
    except Exception as e:
        print(f"ユーザー登録エラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"ユーザー登録中にエラーが発生しました: {str(e)}"
        )

@app.get("/validate-token")
async def validate_token(current_user: User = Depends(get_current_user)):
    """トークンの検証用エンドポイント"""
    return {"valid": True, "username": current_user.username}

@app.get("/logout")
async def logout(request: Request):
    if "user_id" in request.session:
        del request.session["user_id"]
    if "username" in request.session:
        del request.session["username"]
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response

# メインアプリケーションエンドポイント
@app.get("/", response_class=HTMLResponse)
async def admin(request: Request, db: AsyncSession = Depends(get_db)):
    prompt_query = await db.execute(select(Prompt))
    available_prompts = prompt_query.scalars().all()
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("admin/admin.html", {"request": request, "available_prompts": available_prompts})

@app.get("/mobility", response_class=HTMLResponse)
async def mobility_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("mobility/mobility.html", {"request": request, "username": request.session.get("username")})

@app.get("/mobility/proposal", response_class=HTMLResponse)
async def proposal_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("mobility/proposal.html", {"request": request, "username": request.session.get("username")})

@app.get("/mobility/knowledge", response_class=HTMLResponse)
async def mobility_knowledge_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("mobility/knowledge.html", {"request": request, "username": request.session.get("username")})

@app.get("/financial", response_class=HTMLResponse)
async def financial_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("financial/financial.html", {"request": request, "username": request.session.get("username")})

@app.get("/conversation_history", response_class=HTMLResponse)
async def conversation_history(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    chatroom = await chatroom_manager.get_or_create_chatroom(user_id)
    history = await load_json(chatroom["files"]["chat_log"], [])
    return JSONResponse(content=history)

@app.post("/select_project")
async def select_project(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    prompt_id = data.get("prompt_id")
    project_id = data.get("project_id")
    print(f"Selected prompt ID: {prompt_id}")
    print(f"Selected project ID: {project_id}")

    if not prompt_id or not project_id:
        return JSONResponse(
            content={"success": False, "message": "プロンプトIDとプロジェクトIDが指定されていません"},
            status_code=400
        )
    request.session["selected_prompt_id"] = prompt_id
    redirect_url = f"/{project_id}"
    return JSONResponse(
        content={
            "success": True, 
            "redirect_url": redirect_url,
            "prompt_id": prompt_id,
            "project_id": project_id
            },
        status_code=200
    )

@app.get("/base", response_class=HTMLResponse)
async def base(request: Request):
    return templates.TemplateResponse("financial/index.html", {"request": request})
    

@app.post("/chat")
async def chat(
    request: Request, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    try:
        user_id = current_user.id
        data = await request.json()
        user_input = data.get("message", "")
        
        # チャットデータの取得
        history, summary, user_history, thread_history = await chatroom_manager.get_chat_data(user_id)
        
        is_fist_conversation = len(history) == 0
        if is_fist_conversation:
            print(f"{current_user.username} starts to have a conversation")
            user_message = {
            "role": "user", 
            "content": user_input, 
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
            }
            user_thread = {
                "role": "user", 
                "type": "first",
                "content": user_input, 
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
            await chatroom_manager.add_message(user_id, user_message)
            await chatroom_manager.add_thread(user_id, user_thread)
            financial_strategy_prompt = """# 投資戦略情報プロンプト

            ## 顧客の現状分析と投資戦略

            ### 現運用の状況と課題

            #### 現運用の主な課題点
            1. **教育資金準備の不足**
            - 現在の変額年金保険(80万円)では、長男・長女各800万円の目標に大幅に不足
            - 毎月の積立額2万円では大学入学時までに目標額に到達する可能性が低い

            2. **老後資金の準備不足**
            - 退職金がない中、iDeCo(月2.3万円)と定額保険だけでは65歳以降の年間276万円の赤字を賄うには不十分
            - 年金だけでは月々の支出をカバーできない

            3. **資金需要の集中時期への対応**
            - 55～60歳に子供の大学教育費とリフォーム費用が集中し、一時的な資金不足のリスクがある
            - 単年収支がマイナスとなる時期の資金確保が課題

            4. **投資効率の最適化**
            - 低金利(0.75%)の住宅ローンがある一方で、資産運用の効率化が図れていない
            - 現状の資産配分では成長重視型のリスク許容度を十分に活かしきれていない

            5. **目的別資産形成の明確化**
            - 現在の資産配分が、明確な目的別に最適化されていない
            - 投資目的に応じたリスク調整ができていない

            #### 現在のポートフォリオ
            | 商品カテゴリー | 保有金額 | 特徴/備考 |
            |------------|--------|---------|
            | 株式 | 250万円 | 運用期間17年 |
            | 投資信託 | 150万円 | 運用期間17年 |
            | 逓減定期保険 | 100万円 | 毎月2.5万円の保険料、60歳で解約返戻金600万円 |
            | 変額年金保険 | 80万円 | 毎月2万円積立、積立元本50万円 |
            | iDeCo | 80万円 | 毎月2.3万円積立中 |
            | 定額保険 | 190万円 | 60歳満期、解約返戻金約500万円 |
            | 普通預金等 | 500万円 | - |
            | 普通預金等 (配偶者名義) | 500万円 | - |
            | **合計** | **1,850万円** | |

            ### 提案戦略パターン

            ## 戦略パターン1: 子どもの教育資金準備と老後資金の両立

            ### 概要
            教育費のピークと老後の生活費双方に対応するバランス型戦略

            ### 提案理由
            55歳から60歳にかけて子どもの大学教育費で単年収支がマイナスになり、65歳以降も年金生活で収支がマイナスになるため、この2つの時期に向けた資産形成が必要。

            ### 具体的な戦略
            - 現在の貯蓄500万円のうち300万円を利回り5%が見込める投資信託で中長期運用
            - 毎月15万円の積立を開始し、10万円を利回り4%の投資信託、5万円を利回り3%の一時払い保険に配分
            - 子どもの教育資金は別枠で設定し、変額年金保険の毎月の積立を2万円から4万円に増額 (長男・長女用それぞれ2万円)

            ### 期待成果
            - 55歳時点で子どもの大学教育資金として約1,600万円確保
            - 65歳退職時には約6,000万円の資産形成が可能となり、年金と併せて安定した後生活が実現

            ### 商品ポートフォリオ
            | 目的 | 商品名 | 投資金額/積立額 |
            |-----|-------|--------------|
            | 子ども教育資金 | 荘内銀行変額年金保険 | 毎月4万円積立 (長男・長女各2万円) |
            | 中長期運用資金 | 荘内銀行投信ファンドラップ | 貯蓄から300万円 |
            | 安定資産形成 | 荘内バランスファンド | 毎月10万円積立 |
            | 退職準備資金 | 荘内銀行一時払い終身保険 | 毎月5万円 |
            | 老後資金補完 | 荘内銀行iDeCo | 毎月2.3万円から2.7万円に増額 |
            | 緊急予備資金 | 荘内スーパー定期 | 貯蓄から200万円 |

            ## 戦略パターン2: 住宅ローン繰上返済と資産運用の最適化

            ### 概要
            低金利の住宅ローンを活用し、余剰資金を積極的な資産運用に回す戦略

            ### 提案理由
            住宅ローンの金利が0.75%と低く、運用による利回りの方が高い可能性があるため、完済を急がず余剰資金を運用に回すことで、トータルでの資産形成を最大化できる。

            ### 具体的な戦略
            - 住宅ローンの繰上返済は見送り、余剰資金は運用に回す
            - 毎月20万円の積立を実施し、10万円を利回り5%の投資信託(グロース株中心)、6万円を利回り4%のバランス型投資信託、4万円を利回り2%の債券型投資信託に配分
            - iDeCoの拠出金額を月々2.3万円から2.7万円(上限)に引き上げ

            ### 期待成果
            - 資産運用による期待リターンが住宅ローン金利を上回り、55歳時点で約5,000万円の資産形成
            - 税制優遇のあるiDeCoを最大活用することで、退職時の資産を効率的に増やす

            ### 商品ポートフォリオ
            | 目的 | 商品名 | 投資金額/積立額 |
            |-----|-------|--------------|
            | 成長資産形成 | 荘内米国株式ファンド | 毎月10万円積立 |
            | バランス運用 | 荘内ESG投資ファンド | 毎月6万円積立 |
            | 安定運用 | 荘内日本国債ファンド | 毎月4万円積立 |
            | 退職後資金 | iDeCo | 毎月2.3万円から2.7万円に増額 |

            ## 戦略パターン3: リスク分散と目的別資金の明確化

            ### 概要
            リスク許容度に合わせて、各ライフイベントに必要な資金を明確に分けて準備する戦略

            ### 提案理由
            お客様は成長重視型のリスク許容度をお持ちですが、目的や時期によって適切なリスク水準は異なります。目的別に資金を分けて運用することで、必要なときに必要な資金を確保しやすくなります。

            ### 具体的な戦略
            - 住宅ローンの繰上返済は見送り、余剰資金は運用に回す
            - 毎月20万円の積立を実施。内訳は、目的別にリスク・リターンを考慮して配分
            - 教育資金向け: 比較的安定的ながら成長も期待できるファンド
            - リフォーム資金向け: 使用時期を考慮した安定運用
            - 老後資金向け: 長期的な成長を重視したファンド
            - iDeCoの拠出金額を月々2.3万円から2.7万円(上限)に引き上げ

            ### 期待成果
            - 各目的に応じた最適なリスク・リターンのバランスで資産形成
            - 55歳時点で教育資金約1,800万円、リフォーム資金約400万円を確保
            - 65歳退職時には退職後資金として約5,500万円の形成が可能

            ### 商品ポートフォリオ
            | 目的 | 商品名 | 投資金額/積立額 |
            |-----|-------|--------------|
            | 教育資金 | 荘内グローバル資産分散ファンド | 毎月6万円積立 |
            | リフォーム資金 | 荘内ワールド・ソブリンインカム | 現在の貯蓄から100万円 |
            | 退職後資金 | 荘内米国株式ファンド | 毎月10万円積立 |
            | 緊急予備資金 | 荘内普通預金 | 現在の貯蓄から200万円 |
            | 退職後資金(補完) | 荘内外貨定期預金(米ドル) | 既存の投資信託150万円を切替 |
            | iDeCo | iDeCo | 毎月2.7万円に増額 |
            """

            financial_lifeplan_prompt = """
            # ライフプランシミュレーション情報プロンプト

            ## 家族構成と年齢情報

            ### 現在の年齢情報（シミュレーション開始時点）
            - **本人**: 40歳
            - **配偶者**: 42歳
            - **子供1（長男）**: 10歳
            - **子供2（長女）**: 7歳

            ### 年齢シミュレーション
            シミュレーションは27年間（本人66歳まで）行われています。主な年齢マイルストーン：
            - **55歳時点**（本人）：子どもの大学教育費およびリフォーム費用が集中する時期
            - **60歳時点**（本人）：保険満期、職場定年の可能性
            - **65歳時点**（本人）：年金受給開始年齢

            ## 収入状況の詳細

            ### 収入の推移
            - **本人の想定年収**:
            - 40歳～49歳: 900万円/年
            - 50歳～54歳: 900万円/年
            - 55歳～64歳: 800万円/年
            - 65歳以降: 退職により収入なし

            - **配偶者の想定年収**:
            - 42歳～59歳: 150万円/年
            - 60歳以降: 退職により収入なし

            - **退職金**:
            - 本人: 65歳時に500万円
            - 配偶者: 計画では退職金なし

            - **年金収入**:
            - 本人: 65歳から500万円/年
            - 配偶者: 65歳から100万円/年

            - **住宅ローン控除**:
            - 40歳～49歳: 初年度40万円から徐々に減少（毎年1万円ずつ減少）
            - 50歳以降: 控除なし

            ### 収入合計の推移
            - 40歳: 1,090万円
            - 50歳: 1,050万円
            - 55歳: 950万円
            - 60歳: 950万円
            - 61歳～64歳: 800万円（配偶者退職）
            - 65歳: 800万円（本人退職金含む）
            - 66歳以降: 600万円（年金のみ）

            ## 支出状況の詳細

            ### 定常的な支出
            - **生活費**: 240万円/年（全期間共通）
            - **住宅関連費用**:
            - 40歳～49歳: 60万円/年
            - 50歳～59歳: 72万円/年
            - 60歳以降: 84万円/年

            - **ローン返済額**:
            - 40歳～59歳: 156万円/年
            - 60歳以降: 返済完了

            - **保険料積立額**:
            - 生命保険（終身）: 12万円/年（40歳～49歳）
            - 養老保険: 12万円/年（40歳～59歳）
            - iDeCo拠出額: 12万円/年（全期間）

            - **車両費**: 27.6万円/年（全期間）
            - **習い事**:
            - 40歳～54歳: 120万円/年
            - 55歳～59歳: 36万円/年
            - 60歳以降: 36万円/年（61歳～62歳のみ）

            - **税金**:
            - 40歳～59歳: 300万円/年
            - 60歳以降: 150万円/年

            ### 教育・イベント関連支出
            - **子供の学費（仕送り含む）**:
            - 基本: 24万円/年
            - 集中時期（44歳）: 174万円
            - 中学・高校時期（52歳）: 150万円
            - 大学時期（53歳～60歳）: 150万円～300万円/年

            - **実家のリフォーム**:
            - 41歳: 100万円
            - 43歳: 100万円
            - 45歳: 100万円
            - 49歳: 100万円
            - 53歳: 500万円（大規模リフォーム）
            - 62歳: 100万円

            - **旅行代**:
            - 44歳: 100万円
            - 46歳: 100万円

            ### 支出合計の推移
            - 40歳: 987.6万円
            - 44歳: 1,167.6万円（教育費・旅行増）
            - 53歳: 1,467.6万円（大規模リフォーム）
            - 60歳: 967.6万円（ローン完済）
            - 62歳: 867.6万円（子供教育費終了）
            - 65歳以降: 654万円（支出最小化）

            ## キャッシュフロー分析

            ### 年間の現金収支（収入 - 支出）
            - **黒字期**:
            - 40歳～43歳: +102.4万円, +1.4万円, +100.4万円, +39.4万円
            - 45歳: +37.4万円
            - 47歳～48歳: +35.4万円, +34.4万円
            - 62歳～65歳: +146万円/年

            - **赤字期**:
            - 44歳: -81.6万円
            - 46歳: -63.6万円
            - 49歳: -56.6万円
            - 50歳～59歳: -3.6万円～-417.6万円/年
            - 60歳～61歳: -17.6万円/年
            - 65歳以降: -154万円/年

            ### 貯蓄残高の推移
            貯蓄残高は年間の収支に基づいて変動し、53歳～56歳に大きなマイナスとなります。
            - 40歳: 700万円（初期資産）
            - 44歳: 943.6万円
            - 53歳: 1,214.2万円
            - 55歳: 796.6万円
            - 60歳: 308.6万円
            - 61歳: 1,637万円
            - 63歳以降: 減少傾向

            ## 重要な財務上の転機

            1. **44歳時点**: 
            - 子供の教育費増加と旅行費用により一時的な赤字（-81.6万円）
            
            2. **52歳～54歳時点**:
            - 子供の高校・大学教育費用が増加
            - 53歳に大規模リフォーム（500万円）で大幅赤字（-417.6万円）

            3. **55歳～59歳時点**:
            - 子供2人の大学教育費が同時期に発生
            - 本人の収入減少（900万円→800万円）
            - 年間100万円近い赤字が継続

            4. **60歳時点**:
            - 住宅ローン完済
            - 配偶者の収入喪失
            - 養老保険満期

            5. **65歳時点**:
            - 本人退職（退職金500万円）
            - 年金収入開始（本人500万円/年）
            - 長期的な収支は赤字（年間154万円の赤字）

            ## グラフデータの概要

            ### 統合グラフ：預金残高・資産残高・収支バランス
            グラフでは以下の傾向が視覚化されています：

            1. **預金残高（万円）**:
            - 40歳: 約800万円
            - 45歳: 約1,500万円
            - 50歳: 約2,200万円
            - 55歳: 約2,700万円
            - 60歳: 約2,900万円
            - 65歳: 約2,500万円
            - 70歳: 約1,700万円
            - 75歳: 約1,200万円
            - 80歳: 約800万円
            - 85歳: 約400万円

            2. **資産残高（万円）**:
            - 40歳: 約2,000万円
            - 45歳: 約2,800万円
            - 50歳: 約4,000万円
            - 55歳: 約4,800万円
            - 60歳: 約5,200万円
            - 65歳: 約5,000万円
            - 70歳: 約4,500万円
            - 75歳: 約4,000万円
            - 80歳: 約3,800万円
            - 85歳: 約3,500万円

            3. **収支バランス（万円）**:
            - 40歳～49歳: 約+250万円/年
            - 50歳～54歳: 約+250万円/年
            - 55歳～64歳: 約-50万円/年
            - 65歳～74歳: 約-250万円/年
            - 75歳以降: 約-50万円/年

            ## 資産形成および老後資金に関する留意点

            1. **教育資金の計画的準備**:
            - 現状では教育資金が不足する可能性が高い
            - 特に52歳～59歳の期間に集中的な資金需要がある

            2. **老後資金の不足リスク**:
            - 65歳以降、年間154万円の赤字が継続
            - 85歳時点の預金残高は約400万円まで減少
            - 長寿リスクを考慮した追加的な資産形成が必要

            3. **住宅ローン戦略**:
            - 低金利（0.75%）を活かした資産運用の検討
            - 60歳でローン完済予定

            4. **iDeCoおよび保険の活用**:
            - 現状の拠出額（年間12万円）では不十分な可能性
            - 終身保険は49歳で満期、養老保険は59歳で満期
            - 年金補完としての保険活用を検討
            """
            system_prompt = f"""
            あなたは荘内銀行の公式AIファイナンシャルプランナーです。顧客の財務状況に基づいて、個別の質問に答え、アドバイスを提供する役割を担っています。

            まず、顧客の財務戦略と人生設計シミュレーションを確認してください：

            <financial_strategy>
            {financial_strategy_prompt}
            </financial_strategy>

            <life_plan_simulation>
            {financial_lifeplan_prompt}
            </life_plan_simulation>

            以下の情報を参考にしてください：

            1. 荘内銀行プロフィール（2025年現在）：
            - 山形県鶴岡市に本店を置く創業140年以上の地方銀行
            - フィデアホールディングス傘下（2027年に北都銀行と合併予定、「フィデア銀行」へ商号変更）
            - 地域密着型で、中小企業のDX・GX支援に強み
            - JCR格付け「BBB+ / 安定的」、堅実な経営と商品開発

            2. 荘内銀行の主要商品・強み（2024年時点）：
            個人向け：投資信託、外貨預金、住宅ローン、保険、個人向け国債
            法人向け：ビジネスダイレクト、経営支援プラットフォーム、SDGs私募債、農業者向け融資

            3. 制約・留意点：
            - 金融庁ガイドラインを遵守すること
            - 投資・外貨・保険商品にはリスクと手数料を明示すること
            - 顧客属性（年齢、職業、リスク許容度など）に応じて提案内容を調整すること

            4. 資産形成および老後資金に関する留意点：
            - 教育資金の計画的準備の必要性
            - 老後資金の不足リスク
            - 住宅ローン戦略
            - iDeCoおよび保険の活用

            ユーザーからの質問に答える前に、以下の手順で分析を行ってください。この作業は思考ブロック内の<thinking_process>タグで行ってください：

            1. 財務戦略と人生設計シミュレーションの主要ポイントを要約する。
            2. ユーザーの質問を慎重に読み、財務戦略と人生設計シミュレーションの関連情報を特定する。
            3. 質問に関連する荘内銀行の商品やサービスを検討する。
            4. 顧客の年齢、職業、リスク許容度などの属性を考慮する。
            5. ユーザーの財務状況における潜在的なリスクや課題を特定する。
            6. 金融規制やガイドラインに沿った回答を準備する。
            7. リスクと手数料に関する必要な情報を含める。
            8. 提供するアドバイスの長期的な影響を考慮する。
            9. 回答が明確で簡潔であることを確認する。

            分析が完了したら、以下の形式で日本語で回答してください：

            1. ユーザーの質問に直接答える。
            2. 関連する荘内銀行の商品やサービスを推奨する（適切な場合）。
            3. リスクや手数料に関する必要な情報を提供する。
            4. 追加のアドバイスや注意点を述べる。

            それでは、ユーザーの質問に答えてください：

            <user_question>
            {user_input}
            </user_question>

            最終的な回答は、思考ブロックで行った作業を繰り返したり要約したりせず、上記の形式に従った回答のみを含めてください。
            """
            print(system_prompt)
            async def generate():
                """ストリーミングレスポンスを生成する非同期ジェネレータ"""
                resp = ""
                try:
                    # AIからのストリーミングレスポンスを取得
                    async for text in openrouter_stream_client.stream_response(user_input, system_prompt):
                        if isinstance(text, dict) and "error" in text:
                            yield f"data: {json.dumps(text)}\n\n"
                            return
                        resp += text
                        yield f"data: {json.dumps({'text': text})}\n\n"
                    
                    # アシスタントの応答を保存
                    assistant_text = resp
                    assistant_message = {
                        "role": "assistant", 
                        "content": assistant_text, 
                        "user_id": user_id,
                        "id": str(uuid.uuid4()),
                        "timestamp": datetime.now().isoformat()
                    }
                    try:
                        assistant_type_response = await openrouter_client.chat.completions.create(
                            model="openai/gpt-4.1",
                            messages=[
                                {"role": "system", "content": "Classify the intention of the next utterance using a one-word label."},
                                {"role": "user", "content": assistant_text} 
                            ],
                            max_tokens=4000,
                        )
                    except Exception as e:
                        print(f"Error: {e}")
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    try:
                        assistant_content_response = await openrouter_client.chat.completions.create(
                            model="openai/gpt-4.1",
                            messages=[
                                {"role": "system", "content": "Summarize the main point of the following utterance in one sentence, clearly identifying the subject and purpose."},
                                {"role": "user", "content": assistant_text} 
                            ],
                            max_tokens=4000,
                        )
                    except Exception as e:
                        print(f"Error: {e}")
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    assistant_thread = {
                        "role": "assistant", 
                        "type": assistant_type_response.choices[0].message.content,
                        "content": assistant_content_response.choices[0].message.content, 
                        "user_id": user_id,
                        "id": str(uuid.uuid4()),
                        "timestamp": datetime.now().isoformat()
                    }
                    await chatroom_manager.add_message(user_id, assistant_message)
                    await chatroom_manager.add_thread(user_id, assistant_thread)
                    
                    message_pair = {
                        "user": user_thread,
                        "assistant": assistant_thread,
                        "timestamp": datetime.now().isoformat()
                    }
                    await chatroom_manager.update_user_messages(user_id, message_pair)
                    
                    # 定期的にバックグラウンドでサマリーを更新
                    background_tasks.add_task(
                        generate_summary_task, 
                        await to_pretty_json(history),
                        user_id
                    )
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    error_details = traceback.format_exc()
                    print(f"Error in chat: {str(e)}\n{error_details}")
        else:
            print(f"{current_user.username} continues the conversation")
            threads = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history]
            if summary and len(summary) > 0:
                summary_content = summary[0]["content"]
            else:
                summary_content = "" 
            last_conversation = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history[-2:]]
            print(f"User input: {user_input[:50]}...")
            try:
                user_type_response = await openrouter_client.chat.completions.create(
                    model="openai/gpt-4.1",
                    messages=[
                        {"role": "system", "content": f"""Classify the intention of the next utterance using a one-word label. Based on the recent conversation with users {threads}"""},
                        {"role": "user", "content": user_input} 
                    ],
                    max_tokens=4000,
                )
            except Exception as e:
                print(f"Error: {e}")
                return JSONResponse(content={"error": str(e)}, status_code=500)
            try:
                user_content_response = await openrouter_client.chat.completions.create(
                    model="openai/gpt-4.1",
                    messages=[
                        {"role": "system", "content": f"""Summarize the main point of the following utterance in one sentence, clearly identifying the subject and purpose. Based on the recent conversation with users {threads}"""},
                        {"role": "user", "content": user_input} 
                    ],
                    max_tokens=4000,
                )
            except Exception as e:
                print(f"Error: {e}")
                return JSONResponse(content={"error": str(e)}, status_code=500)
            
            print("Type response:", user_type_response.choices[0].message.content)
            print("Content response:", user_content_response.choices[0].message.content)
            # ユーザーメッセージの追加
            user_message = {
                "role": "user", 
                "content": user_input, 
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
            user_thread = {
                "role": "user", 
                "type": user_type_response.choices[0].message.content,
                "content": user_content_response.choices[0].message.content, 
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }

            await chatroom_manager.add_message(user_id, user_message)
            await chatroom_manager.add_thread(user_id, user_thread)

            threads = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history]
            if summary and len(summary) > 0:
                summary_content = summary[0]["content"]
            else:
                summary_content = "" 
            
            financial_strategy_prompt = """# 投資戦略情報プロンプト

            ## 顧客の現状分析と投資戦略

            ### 現運用の状況と課題

            #### 現運用の主な課題点
            1. **教育資金準備の不足**
            - 現在の変額年金保険(80万円)では、長男・長女各800万円の目標に大幅に不足
            - 毎月の積立額2万円では大学入学時までに目標額に到達する可能性が低い

            2. **老後資金の準備不足**
            - 退職金がない中、iDeCo(月2.3万円)と定額保険だけでは65歳以降の年間276万円の赤字を賄うには不十分
            - 年金だけでは月々の支出をカバーできない

            3. **資金需要の集中時期への対応**
            - 55～60歳に子供の大学教育費とリフォーム費用が集中し、一時的な資金不足のリスクがある
            - 単年収支がマイナスとなる時期の資金確保が課題

            4. **投資効率の最適化**
            - 低金利(0.75%)の住宅ローンがある一方で、資産運用の効率化が図れていない
            - 現状の資産配分では成長重視型のリスク許容度を十分に活かしきれていない

            5. **目的別資産形成の明確化**
            - 現在の資産配分が、明確な目的別に最適化されていない
            - 投資目的に応じたリスク調整ができていない

            #### 現在のポートフォリオ
            | 商品カテゴリー | 保有金額 | 特徴/備考 |
            |------------|--------|---------|
            | 株式 | 250万円 | 運用期間17年 |
            | 投資信託 | 150万円 | 運用期間17年 |
            | 逓減定期保険 | 100万円 | 毎月2.5万円の保険料、60歳で解約返戻金600万円 |
            | 変額年金保険 | 80万円 | 毎月2万円積立、積立元本50万円 |
            | iDeCo | 80万円 | 毎月2.3万円積立中 |
            | 定額保険 | 190万円 | 60歳満期、解約返戻金約500万円 |
            | 普通預金等 | 500万円 | - |
            | 普通預金等 (配偶者名義) | 500万円 | - |
            | **合計** | **1,850万円** | |

            ### 提案戦略パターン

            ## 戦略パターン1: 子どもの教育資金準備と老後資金の両立

            ### 概要
            教育費のピークと老後の生活費双方に対応するバランス型戦略

            ### 提案理由
            55歳から60歳にかけて子どもの大学教育費で単年収支がマイナスになり、65歳以降も年金生活で収支がマイナスになるため、この2つの時期に向けた資産形成が必要。

            ### 具体的な戦略
            - 現在の貯蓄500万円のうち300万円を利回り5%が見込める投資信託で中長期運用
            - 毎月15万円の積立を開始し、10万円を利回り4%の投資信託、5万円を利回り3%の一時払い保険に配分
            - 子どもの教育資金は別枠で設定し、変額年金保険の毎月の積立を2万円から4万円に増額 (長男・長女用それぞれ2万円)

            ### 期待成果
            - 55歳時点で子どもの大学教育資金として約1,600万円確保
            - 65歳退職時には約6,000万円の資産形成が可能となり、年金と併せて安定した後生活が実現

            ### 商品ポートフォリオ
            | 目的 | 商品名 | 投資金額/積立額 |
            |-----|-------|--------------|
            | 子ども教育資金 | 荘内銀行変額年金保険 | 毎月4万円積立 (長男・長女各2万円) |
            | 中長期運用資金 | 荘内銀行投信ファンドラップ | 貯蓄から300万円 |
            | 安定資産形成 | 荘内バランスファンド | 毎月10万円積立 |
            | 退職準備資金 | 荘内銀行一時払い終身保険 | 毎月5万円 |
            | 老後資金補完 | 荘内銀行iDeCo | 毎月2.3万円から2.7万円に増額 |
            | 緊急予備資金 | 荘内スーパー定期 | 貯蓄から200万円 |

            ## 戦略パターン2: 住宅ローン繰上返済と資産運用の最適化

            ### 概要
            低金利の住宅ローンを活用し、余剰資金を積極的な資産運用に回す戦略

            ### 提案理由
            住宅ローンの金利が0.75%と低く、運用による利回りの方が高い可能性があるため、完済を急がず余剰資金を運用に回すことで、トータルでの資産形成を最大化できる。

            ### 具体的な戦略
            - 住宅ローンの繰上返済は見送り、余剰資金は運用に回す
            - 毎月20万円の積立を実施し、10万円を利回り5%の投資信託(グロース株中心)、6万円を利回り4%のバランス型投資信託、4万円を利回り2%の債券型投資信託に配分
            - iDeCoの拠出金額を月々2.3万円から2.7万円(上限)に引き上げ

            ### 期待成果
            - 資産運用による期待リターンが住宅ローン金利を上回り、55歳時点で約5,000万円の資産形成
            - 税制優遇のあるiDeCoを最大活用することで、退職時の資産を効率的に増やす

            ### 商品ポートフォリオ
            | 目的 | 商品名 | 投資金額/積立額 |
            |-----|-------|--------------|
            | 成長資産形成 | 荘内米国株式ファンド | 毎月10万円積立 |
            | バランス運用 | 荘内ESG投資ファンド | 毎月6万円積立 |
            | 安定運用 | 荘内日本国債ファンド | 毎月4万円積立 |
            | 退職後資金 | iDeCo | 毎月2.3万円から2.7万円に増額 |

            ## 戦略パターン3: リスク分散と目的別資金の明確化

            ### 概要
            リスク許容度に合わせて、各ライフイベントに必要な資金を明確に分けて準備する戦略

            ### 提案理由
            お客様は成長重視型のリスク許容度をお持ちですが、目的や時期によって適切なリスク水準は異なります。目的別に資金を分けて運用することで、必要なときに必要な資金を確保しやすくなります。

            ### 具体的な戦略
            - 住宅ローンの繰上返済は見送り、余剰資金は運用に回す
            - 毎月20万円の積立を実施。内訳は、目的別にリスク・リターンを考慮して配分
            - 教育資金向け: 比較的安定的ながら成長も期待できるファンド
            - リフォーム資金向け: 使用時期を考慮した安定運用
            - 老後資金向け: 長期的な成長を重視したファンド
            - iDeCoの拠出金額を月々2.3万円から2.7万円(上限)に引き上げ

            ### 期待成果
            - 各目的に応じた最適なリスク・リターンのバランスで資産形成
            - 55歳時点で教育資金約1,800万円、リフォーム資金約400万円を確保
            - 65歳退職時には退職後資金として約5,500万円の形成が可能

            ### 商品ポートフォリオ
            | 目的 | 商品名 | 投資金額/積立額 |
            |-----|-------|--------------|
            | 教育資金 | 荘内グローバル資産分散ファンド | 毎月6万円積立 |
            | リフォーム資金 | 荘内ワールド・ソブリンインカム | 現在の貯蓄から100万円 |
            | 退職後資金 | 荘内米国株式ファンド | 毎月10万円積立 |
            | 緊急予備資金 | 荘内普通預金 | 現在の貯蓄から200万円 |
            | 退職後資金(補完) | 荘内外貨定期預金(米ドル) | 既存の投資信託150万円を切替 |
            | iDeCo | iDeCo | 毎月2.7万円に増額 |
            """

            financial_lifeplan_prompt = """
            # ライフプランシミュレーション情報プロンプト

            ## 家族構成と年齢情報

            ### 現在の年齢情報（シミュレーション開始時点）
            - **本人**: 40歳
            - **配偶者**: 42歳
            - **子供1（長男）**: 10歳
            - **子供2（長女）**: 7歳

            ### 年齢シミュレーション
            シミュレーションは27年間（本人66歳まで）行われています。主な年齢マイルストーン：
            - **55歳時点**（本人）：子どもの大学教育費およびリフォーム費用が集中する時期
            - **60歳時点**（本人）：保険満期、職場定年の可能性
            - **65歳時点**（本人）：年金受給開始年齢

            ## 収入状況の詳細

            ### 収入の推移
            - **本人の想定年収**:
            - 40歳～49歳: 900万円/年
            - 50歳～54歳: 900万円/年
            - 55歳～64歳: 800万円/年
            - 65歳以降: 退職により収入なし

            - **配偶者の想定年収**:
            - 42歳～59歳: 150万円/年
            - 60歳以降: 退職により収入なし

            - **退職金**:
            - 本人: 65歳時に500万円
            - 配偶者: 計画では退職金なし

            - **年金収入**:
            - 本人: 65歳から500万円/年
            - 配偶者: 65歳から100万円/年

            - **住宅ローン控除**:
            - 40歳～49歳: 初年度40万円から徐々に減少（毎年1万円ずつ減少）
            - 50歳以降: 控除なし

            ### 収入合計の推移
            - 40歳: 1,090万円
            - 50歳: 1,050万円
            - 55歳: 950万円
            - 60歳: 950万円
            - 61歳～64歳: 800万円（配偶者退職）
            - 65歳: 800万円（本人退職金含む）
            - 66歳以降: 600万円（年金のみ）

            ## 支出状況の詳細

            ### 定常的な支出
            - **生活費**: 240万円/年（全期間共通）
            - **住宅関連費用**:
            - 40歳～49歳: 60万円/年
            - 50歳～59歳: 72万円/年
            - 60歳以降: 84万円/年

            - **ローン返済額**:
            - 40歳～59歳: 156万円/年
            - 60歳以降: 返済完了

            - **保険料積立額**:
            - 生命保険（終身）: 12万円/年（40歳～49歳）
            - 養老保険: 12万円/年（40歳～59歳）
            - iDeCo拠出額: 12万円/年（全期間）

            - **車両費**: 27.6万円/年（全期間）
            - **習い事**:
            - 40歳～54歳: 120万円/年
            - 55歳～59歳: 36万円/年
            - 60歳以降: 36万円/年（61歳～62歳のみ）

            - **税金**:
            - 40歳～59歳: 300万円/年
            - 60歳以降: 150万円/年

            ### 教育・イベント関連支出
            - **子供の学費（仕送り含む）**:
            - 基本: 24万円/年
            - 集中時期（44歳）: 174万円
            - 中学・高校時期（52歳）: 150万円
            - 大学時期（53歳～60歳）: 150万円～300万円/年

            - **実家のリフォーム**:
            - 41歳: 100万円
            - 43歳: 100万円
            - 45歳: 100万円
            - 49歳: 100万円
            - 53歳: 500万円（大規模リフォーム）
            - 62歳: 100万円

            - **旅行代**:
            - 44歳: 100万円
            - 46歳: 100万円

            ### 支出合計の推移
            - 40歳: 987.6万円
            - 44歳: 1,167.6万円（教育費・旅行増）
            - 53歳: 1,467.6万円（大規模リフォーム）
            - 60歳: 967.6万円（ローン完済）
            - 62歳: 867.6万円（子供教育費終了）
            - 65歳以降: 654万円（支出最小化）

            ## キャッシュフロー分析

            ### 年間の現金収支（収入 - 支出）
            - **黒字期**:
            - 40歳～43歳: +102.4万円, +1.4万円, +100.4万円, +39.4万円
            - 45歳: +37.4万円
            - 47歳～48歳: +35.4万円, +34.4万円
            - 62歳～65歳: +146万円/年

            - **赤字期**:
            - 44歳: -81.6万円
            - 46歳: -63.6万円
            - 49歳: -56.6万円
            - 50歳～59歳: -3.6万円～-417.6万円/年
            - 60歳～61歳: -17.6万円/年
            - 65歳以降: -154万円/年

            ### 貯蓄残高の推移
            貯蓄残高は年間の収支に基づいて変動し、53歳～56歳に大きなマイナスとなります。
            - 40歳: 700万円（初期資産）
            - 44歳: 943.6万円
            - 53歳: 1,214.2万円
            - 55歳: 796.6万円
            - 60歳: 308.6万円
            - 61歳: 1,637万円
            - 63歳以降: 減少傾向

            ## 重要な財務上の転機

            1. **44歳時点**: 
            - 子供の教育費増加と旅行費用により一時的な赤字（-81.6万円）
            
            2. **52歳～54歳時点**:
            - 子供の高校・大学教育費用が増加
            - 53歳に大規模リフォーム（500万円）で大幅赤字（-417.6万円）

            3. **55歳～59歳時点**:
            - 子供2人の大学教育費が同時期に発生
            - 本人の収入減少（900万円→800万円）
            - 年間100万円近い赤字が継続

            4. **60歳時点**:
            - 住宅ローン完済
            - 配偶者の収入喪失
            - 養老保険満期

            5. **65歳時点**:
            - 本人退職（退職金500万円）
            - 年金収入開始（本人500万円/年）
            - 長期的な収支は赤字（年間154万円の赤字）

            ## グラフデータの概要

            ### 統合グラフ：預金残高・資産残高・収支バランス
            グラフでは以下の傾向が視覚化されています：

            1. **預金残高（万円）**:
            - 40歳: 約800万円
            - 45歳: 約1,500万円
            - 50歳: 約2,200万円
            - 55歳: 約2,700万円
            - 60歳: 約2,900万円
            - 65歳: 約2,500万円
            - 70歳: 約1,700万円
            - 75歳: 約1,200万円
            - 80歳: 約800万円
            - 85歳: 約400万円

            2. **資産残高（万円）**:
            - 40歳: 約2,000万円
            - 45歳: 約2,800万円
            - 50歳: 約4,000万円
            - 55歳: 約4,800万円
            - 60歳: 約5,200万円
            - 65歳: 約5,000万円
            - 70歳: 約4,500万円
            - 75歳: 約4,000万円
            - 80歳: 約3,800万円
            - 85歳: 約3,500万円

            3. **収支バランス（万円）**:
            - 40歳～49歳: 約+250万円/年
            - 50歳～54歳: 約+250万円/年
            - 55歳～64歳: 約-50万円/年
            - 65歳～74歳: 約-250万円/年
            - 75歳以降: 約-50万円/年

            ## 資産形成および老後資金に関する留意点

            1. **教育資金の計画的準備**:
            - 現状では教育資金が不足する可能性が高い
            - 特に52歳～59歳の期間に集中的な資金需要がある

            2. **老後資金の不足リスク**:
            - 65歳以降、年間154万円の赤字が継続
            - 85歳時点の預金残高は約400万円まで減少
            - 長寿リスクを考慮した追加的な資産形成が必要

            3. **住宅ローン戦略**:
            - 低金利（0.75%）を活かした資産運用の検討
            - 60歳でローン完済予定

            4. **iDeCoおよび保険の活用**:
            - 現状の拠出額（年間12万円）では不十分な可能性
            - 終身保険は49歳で満期、養老保険は59歳で満期
            - 年金補完としての保険活用を検討
            """
            last_conversation = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history[-2:]]
            # システムプロンプトの構築
            system_prompt = f"""
            あなたは荘内銀行の公式AIファイナンシャルプランナーです。顧客の財務状況に基づいて、個別の質問に答え、アドバイスを提供する役割を担っています。

            まず、顧客との会話記録と財務戦略を確認してください：

            <summary>
            {summary_content}
            </summary>

            <threads>
            {threads}
            </threads>

            <last_conversation>
            {last_conversation}
            </last_conversation>

            <financial_strategy>
            {financial_strategy_prompt}
            </financial_strategy>  

            <financial_lifeplan_simulation>
            {financial_lifeplan_prompt}
            </financial_lifeplan_simulation>

            以下の情報を参考にしてください：

            1. 荘内銀行プロフィール（2025年現在）：
            - 山形県鶴岡市に本店を置く創業140年以上の地方銀行
            - フィデアホールディングス傘下（2027年に北都銀行と合併予定、「フィデア銀行」へ商号変更）
            - 地域密着型で、中小企業のDX・GX支援に強み
            - JCR格付け「BBB+ / 安定的」、堅実な経営と商品開発

            2. 荘内銀行の主要商品・強み（2024年時点）：
            個人向け：投資信託、外貨預金、住宅ローン、保険、個人向け国債
            法人向け：ビジネスダイレクト、経営支援プラットフォーム、SDGs私募債、農業者向け融資

            3. 制約・留意点：
            - 金融庁ガイドラインを遵守すること
            - 投資・外貨・保険商品にはリスクと手数料を明示すること
            - 顧客属性（年齢、職業、リスク許容度など）に応じて提案内容を調整すること

            4. 資産形成および老後資金に関する留意点：
            - 教育資金の計画的準備の必要性
            - 老後資金の不足リスク
            - 住宅ローン戦略
            - iDeCoおよび保険の活用

            ユーザーからの質問に答える前に、以下の手順で分析を行ってください。この作業は思考ブロック内の<thinking_process>タグで行ってください：

            1. 財務戦略と人生設計シミュレーションの主要ポイントを要約する。
            2. ユーザーの質問を慎重に読み、財務戦略と人生設計シミュレーションの関連情報を特定する。
            3. 質問に関連する荘内銀行の商品やサービスを検討する。
            4. 顧客の年齢、職業、リスク許容度などの属性を考慮する。
            5. ユーザーの財務状況における潜在的なリスクや課題を特定する。
            6. 金融規制やガイドラインに沿った回答を準備する。
            7. リスクと手数料に関する必要な情報を含める。
            8. 提供するアドバイスの長期的な影響を考慮する。
            9. 回答が明確で簡潔であることを確認する。

            分析が完了したら、以下の形式で日本語で回答してください：

            1. ユーザーの質問に直接答える。
            2. 関連する荘内銀行の商品やサービスを推奨する（適切な場合）。
            3. リスクや手数料に関する必要な情報を提供する。
            4. 追加のアドバイスや注意点を述べる。

            それでは、ユーザーの質問に答えてください：

            <user_question>
            {user_input}
            </user_question>

            最終的な回答は、思考ブロックで行った作業を繰り返したり要約したりせず、上記の形式に従った回答のみを含めてください。
        """
            print(system_prompt)
            async def generate():
                """ストリーミングレスポンスを生成する非同期ジェネレータ"""
                resp = ""
                try:
                    # AIからのストリーミングレスポンスを取得
                    async for text in openrouter_stream_client.stream_response(user_content_response.choices[0].message.content, system_prompt):
                        if isinstance(text, dict) and "error" in text:
                            yield f"data: {json.dumps(text)}\n\n"
                            return
                        resp += text
                        yield f"data: {json.dumps({'text': text})}\n\n"
                    
                    # アシスタントの応答を保存
                    assistant_text = resp
                    assistant_message = {
                        "role": "assistant", 
                        "content": assistant_text, 
                        "user_id": user_id,
                        "id": str(uuid.uuid4()),
                        "timestamp": datetime.now().isoformat()
                    }
                    try:
                        assistant_type_response = await openrouter_client.chat.completions.create(
                            model="openai/gpt-4.1",
                            messages=[
                                {"role": "system", "content": "Classify the intention of the next utterance using a one-word label."},
                                {"role": "user", "content": assistant_text} 
                            ],
                            max_tokens=4000,
                        )
                    except Exception as e:
                        print(f"Error: {e}")
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    try:
                        assistant_content_response = await openrouter_client.chat.completions.create(
                            model="openai/gpt-4.1",
                            messages=[
                                {"role": "system", "content": "Summarize the main point of the following utterance in one sentence, clearly identifying the subject and purpose."},
                                {"role": "user", "content": assistant_text} 
                            ],
                            max_tokens=4000,
                        )
                    except Exception as e:
                        print(f"Error: {e}")
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    assistant_thread = {
                        "role": "assistant", 
                        "type": assistant_type_response.choices[0].message.content,
                        "content": assistant_content_response.choices[0].message.content, 
                        "user_id": user_id,
                        "id": str(uuid.uuid4()),
                        "timestamp": datetime.now().isoformat()
                    }
                    await chatroom_manager.add_message(user_id, assistant_message)
                    await chatroom_manager.add_thread(user_id, assistant_thread)
                    
                    message_pair = {
                        "user": user_thread,
                        "assistant": assistant_thread,
                        "timestamp": datetime.now().isoformat()
                    }
                    await chatroom_manager.update_user_messages(user_id, message_pair)
                    
                    # 定期的にバックグラウンドでサマリーを更新
                    if len(history) % 7 == 0:
                        background_tasks.add_task(
                            generate_summary_task, 
                            await to_pretty_json(history),
                            user_id
                        )
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    error_details = traceback.format_exc()
                    print(f"Error in chat: {str(e)}\n{error_details}")
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error in chat: {str(e)}\n{error_details}")
        return JSONResponse(
            content={"error": str(e), "details": error_details},
            status_code=500
        )


@app.post("/mobility_chat")
async def mobility_chat(
    request: Request, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    try:
        user_id = current_user.id
        
        # チャットデータの取得
        history, summary, user_history, thread_history = await chatroom_manager.get_chat_data(user_id)
        
        threads = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history]
        if summary and len(summary) > 0:
            summary_content = summary[0]["content"]
        else:
            summary_content = "" 
        last_conversation = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history[-2:]]
        
        # ユーザー入力の取得
        data = await request.json()
        user_input = data.get("message", "")
        print(f"User input: {user_input[:50]}...")
        try:
            user_type_response = await openrouter_client.chat.completions.create(
                model="openai/gpt-4.1",
                messages=[
                    {"role": "system", "content": f"""Classify the intention of the next utterance using a one-word label. Based on the recent conversation with users
        {threads}"""},
                    {"role": "user", "content": user_input} 
                ],
                max_tokens=4000,
            )
        except Exception as e:
            print(f"Error: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
        try:
            user_content_response = await openrouter_client.chat.completions.create(
                model="openai/gpt-4.1",
                messages=[
                    {"role": "system", "content": f"""Summarize the main point of the following utterance in one sentence, clearly identifying the subject and purpose. Based on the recent conversation with users
        {threads}"""},
                    {"role": "user", "content": user_input} 
                ],
                max_tokens=4000,
            )
        except Exception as e:
            print(f"Error: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
        
        print("Type response:", user_type_response.choices[0].message.content)
        print("Content response:", user_content_response.choices[0].message.content)
        # ユーザーメッセージの追加
        user_message = {
            "role": "user", 
            "content": user_input, 
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
        user_thread = {
            "role": "user", 
            "type": user_type_response.choices[0].message.content,
            "content": user_content_response.choices[0].message.content, 
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }

        await chatroom_manager.add_message(user_id, user_message)
        await chatroom_manager.add_thread(user_id, user_thread)
        
        # 選択されたプロンプトの取得
        selected_prompt_id = request.session.get("selected_prompt_id")
        print(f"Selected prompt ID: {selected_prompt_id}")
        
        base_prompt = "you are helpful AI assistant"
        if selected_prompt_id:
            stmt = select(Prompt).where(Prompt.id == int(selected_prompt_id))
            result = await db.execute(stmt)
            prompt_obj = result.scalar_one_or_none()
            if prompt_obj:
                print(f"Found prompt: {prompt_obj.name}")
                base_prompt = prompt_obj.content
            else:
                print("Prompt object not found for ID:", selected_prompt_id)

        threads = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history]
        if summary and len(summary) > 0:
            summary_content = summary[0]["content"]
        else:
            summary_content = "" 
        last_conversation = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history[-2:]]
        # システムプロンプトの構築
        system_prompt = f"""
        {base_prompt}

        ---
        ###Summary of conversation
        {summary_content}
        ###Recent conversation with users
        {threads}
        ###Last conversation with users
        {last_conversation}
        """
        print(system_prompt)
        async def generate():
            """ストリーミングレスポンスを生成する非同期ジェネレータ"""
            resp = ""
            try:
                # AIからのストリーミングレスポンスを取得
                async for text in openrouter_stream_client.stream_response(user_content_response.choices[0].message.content, system_prompt):
                    if isinstance(text, dict) and "error" in text:
                        yield f"data: {json.dumps(text)}\n\n"
                        return
                    resp += text
                    yield f"data: {json.dumps({'text': text})}\n\n"
                
                # アシスタントの応答を保存
                assistant_text = resp
                assistant_message = {
                    "role": "assistant", 
                    "content": assistant_text, 
                    "user_id": user_id,
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat()
                }
                try:
                    assistant_type_response = await openrouter_client.chat.completions.create(
                        model="openai/gpt-4.1",
                        messages=[
                            {"role": "system", "content": "Classify the intention of the next utterance using a one-word label."},
                            {"role": "user", "content": assistant_text} 
                        ],
                        max_tokens=4000,
                    )
                except Exception as e:
                    print(f"Error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                try:
                    assistant_content_response = await openrouter_client.chat.completions.create(
                        model="openai/gpt-4.1",
                        messages=[
                            {"role": "system", "content": "Summarize the main point of the following utterance in one sentence, clearly identifying the subject and purpose."},
                            {"role": "user", "content": assistant_text} 
                        ],
                        max_tokens=4000,
                    )
                except Exception as e:
                    print(f"Error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                assistant_thread = {
                    "role": "assistant", 
                    "type": assistant_type_response.choices[0].message.content,
                    "content": assistant_content_response.choices[0].message.content, 
                    "user_id": user_id,
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat()
                }
                await chatroom_manager.add_message(user_id, assistant_message)
                await chatroom_manager.add_thread(user_id, assistant_thread)
                
                message_pair = {
                    "user": user_thread,
                    "assistant": assistant_thread,
                    "timestamp": datetime.now().isoformat()
                }
                await chatroom_manager.update_user_messages(user_id, message_pair)
                
                # 定期的にバックグラウンドでサマリーを更新
                if len(history) % 7 == 0:
                    background_tasks.add_task(
                        generate_summary_task, 
                        await to_pretty_json(history),
                        user_id
                    )
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                error_details = traceback.format_exc()
                print(f"Error in chat: {str(e)}\n{error_details}")
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error in chat: {str(e)}\n{error_details}")
        return JSONResponse(
            content={"error": str(e), "details": error_details},
            status_code=500
        )
    

@app.post("/message_chat")
async def message_chat(
    request: Request, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    try:
        user_id = current_user.id
        
        # チャットデータの取得
        history, summary, user_history, thread_history = await chatroom_manager.get_chat_data(user_id)
        
        threads = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history]
        if summary and len(summary) > 0:
            summary_content = summary[0]["content"]
        else:
            summary_content = "" 
        last_conversation = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history[-2:]]
        
        # ユーザー入力の取得
        data = await request.json()
        user_input = data.get("message", "")
        print(f"User input: {user_input[:50]}...")
        try:
            user_type_response = await openrouter_client.chat.completions.create(
                model="openai/gpt-4.1",
                messages=[
                    {"role": "system", "content": f"""Classify the intention of the next utterance using a one-word label. Based on the recent conversation with users
        {threads}"""},
                    {"role": "user", "content": user_input} 
                ],
                max_tokens=4000,
            )
        except Exception as e:
            print(f"Error: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
        try:
            user_content_response = await openrouter_client.chat.completions.create(
                model="openai/gpt-4.1",
                messages=[
                    {"role": "system", "content": f"""Summarize the main point of the following utterance in one sentence, clearly identifying the subject and purpose. Based on the recent conversation with users
        {threads}"""},
                    {"role": "user", "content": user_input} 
                ],
                max_tokens=4000,
            )
        except Exception as e:
            print(f"Error: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
        
        print("Type response:", user_type_response.choices[0].message.content)
        print("Content response:", user_content_response.choices[0].message.content)
        # ユーザーメッセージの追加
        user_message = {
            "role": "user", 
            "content": user_input, 
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
        user_thread = {
            "role": "user", 
            "type": user_type_response.choices[0].message.content,
            "content": user_content_response.choices[0].message.content, 
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }

        await chatroom_manager.add_message(user_id, user_message)
        await chatroom_manager.add_thread(user_id, user_thread)
        
        base_prompt = "you are helpful AI assistant"
        
        threads = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history]
        if summary and len(summary) > 0:
            summary_content = summary[0]["content"]
        else:
            summary_content = "" 
        last_conversation = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history[-2:]]
        # システムプロンプトの構築
        system_prompt = f"""
        {base_prompt}

        ---
        ###Summary of conversation
        {summary_content}
        ###Recent conversation with users
        {threads}
        ###Last conversation with users
        {last_conversation}
        """
        print(system_prompt)
        async def generate():
            """ストリーミングレスポンスを生成する非同期ジェネレータ"""
            resp = ""
            try:
                # AIからのストリーミングレスポンスを取得
                async for text in openrouter_stream_client.stream_response(user_content_response.choices[0].message.content, system_prompt):
                    if isinstance(text, dict) and "error" in text:
                        yield f"data: {json.dumps(text)}\n\n"
                        return
                    resp += text
                    yield f"data: {json.dumps({'text': text})}\n\n"
                
                # アシスタントの応答を保存
                assistant_text = resp
                assistant_message = {
                    "role": "assistant", 
                    "content": assistant_text, 
                    "user_id": user_id,
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat()
                }
                try:
                    assistant_type_response = await openrouter_client.chat.completions.create(
                        model="openai/gpt-4.1",
                        messages=[
                            {"role": "system", "content": "Classify the intention of the next utterance using a one-word label."},
                            {"role": "user", "content": assistant_text} 
                        ],
                        max_tokens=4000,
                    )
                except Exception as e:
                    print(f"Error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                try:
                    assistant_content_response = await openrouter_client.chat.completions.create(
                        model="openai/gpt-4.1",
                        messages=[
                            {"role": "system", "content": "Summarize the main point of the following utterance in one sentence, clearly identifying the subject and purpose."},
                            {"role": "user", "content": assistant_text} 
                        ],
                        max_tokens=4000,
                    )
                except Exception as e:
                    print(f"Error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                assistant_thread = {
                    "role": "assistant", 
                    "type": assistant_type_response.choices[0].message.content,
                    "content": assistant_content_response.choices[0].message.content, 
                    "user_id": user_id,
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat()
                }
                await chatroom_manager.add_message(user_id, assistant_message)
                await chatroom_manager.add_thread(user_id, assistant_thread)
                
                message_pair = {
                    "user": user_thread,
                    "assistant": assistant_thread,
                    "timestamp": datetime.now().isoformat()
                }
                await chatroom_manager.update_user_messages(user_id, message_pair)
                
                # 定期的にバックグラウンドでサマリーを更新
                if len(history) % 7 == 0:
                    background_tasks.add_task(
                        generate_summary_task, 
                        await to_pretty_json(history),
                        user_id
                    )
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                error_details = traceback.format_exc()
                print(f"Error in chat: {str(e)}\n{error_details}")
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error in chat: {str(e)}\n{error_details}")
        return JSONResponse(
            content={"error": str(e), "details": error_details},
            status_code=500
        )


@app.post("/clear")
async def clear_chat_data(current_user: User = Depends(get_current_user)):
    """チャット履歴をクリアするエンドポイント"""
    user_id = current_user.id
    await chatroom_manager.clear_chat_data(user_id)
    return JSONResponse(content={"status": "success", "message": "Clear chat history"})

# 以下、プロンプト管理関連のエンドポイント（変更なし）
@app.get("/prompt", response_class=HTMLResponse)
async def get_prompts(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt))
    prompts = result.scalars().all()
    return templates.TemplateResponse("components/list.html", {
        "request": request,
        "data": prompts
    })

@app.get("/prompt/{prompt_id}", response_class=HTMLResponse)
async def get_prompt(prompt_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()

    if not prompt:
        return templates.TemplateResponse("error.html", {"request": request, "message": "プロンプトが見つかりません"}, status_code=404)

    return templates.TemplateResponse("components/edit.html", {"request": request, "data": prompt})

@app.patch("/prompt/{prompt_id}")
async def update_prompt(prompt_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        return templates.TemplateResponse("error.html", {"request": request, "message": "プロンプトが見つかりません"}, status_code=404)
    
    p_data = await request.json()
    if "content" in p_data:
        prompt.content = p_data["content"]

    await db.commit()
    return templates.TemplateResponse("components/edit.html", {"request": request, "data": prompt})

@app.delete("/prompt/{prompt_id}")
async def delete_prompt(prompt_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()

    if not prompt:
        return templates.TemplateResponse("error.html", {"request": request, "message": "プロンプトが見つかりません"}, status_code=404)
    
    await db.delete(prompt)
    await db.commit()
    
    return templates.TemplateResponse("components/edit.html", {"request": request, "data": prompt})

@app.post("/prompts/create")
async def create_prompt(request: Request, db: AsyncSession = Depends(get_db)):
    p_data = await request.json()

    if not p_data or "content" not in p_data or not isinstance(p_data["content"], str):
        return templates.TemplateResponse("error.html", {"request": request, "message": "プロンプト情報が不足しています"}, status_code=400)

    new_prompt = Prompt(
        name=p_data["name"],
        content=p_data["content"],
        description=p_data["description"]    
    )
    
    db.add(new_prompt)
    await db.commit()
    await db.refresh(new_prompt)

    return templates.TemplateResponse("components/edit.html", {"request": request, "data": new_prompt})

@app.get("/select", response_class=HTMLResponse)
async def select_prompt_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt))
    prompts = result.scalars().all()
    return templates.TemplateResponse("components/select.html", {"request": request, "prompts": prompts})

@app.get("/api/prompt/{prompt_id}")
async def get_prompt_api(prompt_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()

    if not prompt:
        return JSONResponse(
            content={"error": "プロンプトが見つかりません"},
            status_code=404
        )
    
    return JSONResponse(content={
        "id": prompt.id,
        "name": prompt.name,
        "description": prompt.description,
        "content": prompt.content
    })

@app.post("/api/select-prompt")
async def select_prompt_api(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    prompt_id = data.get("prompt_id")

    if not prompt_id:
        return JSONResponse(
            content={"success": False, "message": "プロンプトIDが指定されていません"},
            status_code=400
        )

    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        return JSONResponse(
            content={"success": False, "message": "プロンプトが見つかりません"},
            status_code=404
        )

    print(f"selected_prompt_idを{prompt_id}に設定します")
    request.session["selected_prompt_id"] = prompt_id
    request.session["selected_prompt_name"] = prompt.name

    return JSONResponse(content={
        "success": True,
        "prompt_id": prompt_id,
        "prompt_name": prompt.name 
    })

if __name__ == '__main__':
    import uvicorn
    # port = int(os.environ.get('PORT', 5000))
    port = int(os.environ.get('PORT', 5001))
    uvicorn.run("wsgi:app", host="0.0.0.0", port=port, reload=True)