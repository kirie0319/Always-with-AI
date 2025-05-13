# api/financial_routes.py
from  fastapi import APIRouter, HTTPException, Depends, Request, Form, Body
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
import json
import os
from datetime import datetime
from auth.jwt_auth import get_current_user
from models.users import User
from openai import AsyncOpenAI

from utils.file_operations import load_json, save_json, to_pretty_json, clear_cache

CRM_DATA_PATH = "crm_dummy_data"

router = APIRouter(prefix="/financial")

openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_api_key
)


@router.get("/crm-data/{cif_id}")
async def get_crm_data(
    cif_id: str,
    current_user: User = Depends(get_current_user)
):
    try:
        crm_file_path = os.path.join(CRM_DATA_PATH, "financial_dummy_data.json")
        if not os.path.exists(crm_file_path):
            raise HTTPException(
                status_code=404,
                detail="CRMデータが見つかりません"
            )
        crm_data = await load_json(crm_file_path, {})
        if cif_id not in crm_data:
            return JSONResponse(
                content={
                    "success": False,
                    "message": f"指定されたCIF IDのデータが見つかりません: {cif_id}"
                },
                status_code=404
            )
        return JSONResponse(
            content={
                "success": True,
                "data": crm_data[cif_id]
            },
            status_code=200
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"エラーが発生しました: {str(e)}"
        )
            
            
@router.post("/submit")
async def submit_financial_data(
    request: Request,
    financial_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user)
):
    """財務情報フォームの送信を処理するエンドポイント"""
    try:
        # 受け取ったデータをログに出力
        print("=== 財務フォーム送信データ ===")
        print(f"ユーザーID: {current_user.id}")
        print(f"ユーザー名: {current_user.username}")
        print(f"送信時刻: {datetime.now().isoformat()}")
        
        # 詳細データをプリント
        hearing_prompt = f"""

        You are a financial life plan advisor AI for a bank. Based on the customer financial data provided below, please generate a natural and easy-to-understand profile text in Japanese.

        First, please think through and organize the information in the following stages:
        ---
        [Step 1] Understand the person's profile:
        - Extract age, industry, workplace, position, job type, annual income, and explain what kind of person they are in one sentence.
        - Organize the family structure (spouse, children, etc.), including the number of family members and an overview.

        [Step 2] Organize the financial situation:
        - Summarize savings amount, presence of investments and their content/risk, and expected retirement benefits.
        - Describe owned assets (car, home ownership) and living expenses (monthly).
        - List outstanding debts such as mortgage and car loans with their remaining amounts and repayment periods.

        [Step 3] Confirm the desires and intentions regarding lifestyle:
        - Check for plans regarding car purchase, home renovation, travel, pets, nursing care, and other expenditures, and summarize in natural text.

        [Step 4] Structurally organize educational policies (if there are children):
        - Specify planned education from kindergarten to university in order, if applicable.
        ---

        Finally, based on the information organized above, please output a Japanese text in the following format:
        ---
        [Natural Text Output Format]
        ① Customer profile (1-2 sentences)
        ② Key points of financial situation (bullet points)
        ③ Future lifestyle intentions (1 paragraph)
        ④ Educational policy (only if they have children)
        ---
        [Structured Data]
        {financial_data}
        """
        hearing_response = await openrouter_client.chat.completions.create(
                model="openai/gpt-4.1",
                messages=[
                    {"role": "system", "content": hearing_prompt}
                ],
                max_tokens=4000,
            )
        hearing_data =  hearing_response.choices[0].message.content
        simulation_prompt = f"""
        # 資産運用提案AIアシスタント

        ## 目的
        Based on {hearing_data}, あなたは金融機関職員が顧客に対して資産運用提案を行うための、シミュレーション・戦略・商品提案支援を一貫して行うAIガイド。顧客の利益最優先で、論理的かつ納得感ある説明を行う。

        ## フェーズ詳細

        ### 1. シミュレーション (simulation)
        **説明**: ヒアリング情報を基に、将来のキャッシュフロー・資産推移を5年単位でシミュレーション。ネガティブケース（支出過大・運用益なし）を前提とし、年金受給も含めて資産寿命を明示。

        **入力情報**:
        - **現在情報**: 年齢、勤務先、役職、年収、貯蓄額、保有資産、家族構成、支出
        - **将来情報**: 住宅購入、車購入、教育進学、旅行頻度、退職金予定
        - **年金情報**: 本人・配偶者の受給年齢と額（なければモデルで推定）

        **出力内容**:
        - **表**:
        - 5年ごとの収支推移表（年齢、年金額、収入、支出、単年収支、累積資産、イベント）
        - 支出カテゴリ別内訳（教育、医療、旅行、住宅、生活費）
        - **チャート**:
        - 累積資産推移グラフ（資産寿命マーカー付き）
        - **インサイト**:
        - いつから資産切り崩しが始まるか
        - 赤字連続年は何年か
        - 何歳で資産が枯渇する可能性があるか

        **話法ガイダンス**: 顧客の不安を煽らず、共感を持って危機を共有する。「今から備えることで改善可能です」など安心感を含めた話法を使う。

        ### 2. 戦略提案 (strategy_proposal)
        **説明**: シミュレーション結果と顧客の運用方針に基づき、3つの資産運用戦略を提案。リスク許容度と必要利回りを踏まえ、パターンごとの根拠を明示。

        **入力情報**:
        - **リスク許容度**: 安定型、バランス型、成長型
        - **目標ギャップ**: 資金が不足するタイミングと額

        **出力内容**:
        - **戦略**:
        1. **低リスク安定型**
            - 目標リターン: 2.5%
            - 構成要素: 債券、元本保証保険
            - 根拠: 短期での支出過多リスクがあり、安全性重視で補完
        2. **中リスクバランス型**
            - 目標リターン: 4.0%
            - 構成要素: 投信積立、定期預金
            - 根拠: 10年以内に大きな教育費を補完
        3. **高リスク成長型**
            - 目標リターン: 6.0%
            - 構成要素: 株式投資、外国債券
            - 根拠: 長期の資産形成で老後資金を確保

        **話法ガイダンス**: 選択肢を対等に提示しつつ、目的との整合性と実現性を客観的に説明。「この選択肢は◯年後の出費に備える形になります」など生活に結びつけた言葉を使う。

        ### 3. 商品提案 (product_proposal)
        **説明**: 選ばれた運用戦略に基づいて、千葉銀行の実際の商品で構成されたポートフォリオを提案。商品のリスク・手数料・今後の見通しを含めて顧客の利益視点で説明。

        **入力情報**:
        - **選択された戦略**: strategy_proposalの出力

        **出力内容**:
        - **ポートフォリオ表**:
        - 商品名、投資金額、商品種別、主な特徴、リスク、コスト、今後の見通し
        - **トーキングポイント**:
        - 顧客の不安や目的と商品特徴の接続
        - 提案の納得感を高める比較表現
        - 「預金よりリスクはありますが…」などのバランスある話法

        **話法ガイダンス**: 商品を売る姿勢でなく、課題解決手段として紹介する。納得感を重視し、リスク説明と生活文脈をセットで話す。

        ## 💡 シミュレーション結果（ネガティブケース前提）

        | 年 | 年齢 | 年金受給額 | 世帯収入 | 支出 | 単年収支 | 資産残高 | イベント |
        |----|------|-------------|-----------|--------|------------|--------------|-----------|
        | 2040 | 60歳 | 0万円 | 900万円 | 950万円 | -50万円 | 1,200万円 | 教育費増加 |
        | 2045 | 65歳 | 250万円 | 250万円 | 360万円 | -110万円 | 800万円 | 年金開始 |

        📉 **資産寿命：75歳で枯渇予測**

        ### 🔍 インサイト
        - 2035年以降、単年収支がマイナスに転じます
        - 年金受給後も生活費を完全にはカバーできません
        - このままでは老後資金が約10年で不足します

        ### 🗣 話法（顧客説明例）
        > 「このまま現在のライフスタイルを維持すると、年金受給後も資産の取り崩しが続き、75歳前後で資金が底をつく可能性があります。ですが、今のうちに少しずつ準備すれば十分に改善可能です。」
        """
        simulation_response = await openrouter_client.chat.completions.create(
            model="openai/gpt-4.1",
            messages=[{"role": "system", "content": simulation_prompt}],
            max_tokens=4000,
        )
        simulation_data = simulation_response.choices[0].message.content

        output_prompt = f"""
        # 資産運用提案分析ツール

        ## 目的
        Based on this info {simulation_data}, please structure it into a tool that clearly decomposes and organizes the current analysis and proposed strategies.

        ## 指示内容
        提供された資産運用提案書の情報を以下の4つのカテゴリーに分類・整理します：
        1. 現運用分析：現状の課題と保有ポートフォリオ
        2. 戦略パターン：ユーザー固有の目的に最適化された3つの戦略案

        ## 出力形式

        ### 現運用
        #### 現状の課題
        * 老後資金準備状況
        * 教育資金準備状況
        * 資金需要集中期への対応
        * 投資効率
        * 目的別資産形成状況
        * その他の財務的課題

        #### 現在のポートフォリオ
        | 商品カテゴリー | 保有金額 | 特徴/備考 |
        |--------------|---------|----------|
        | [カテゴリー]  | [金額]   | [特徴]    |

        ### 戦略パターン{1, 2, 3}
        #### 提案理由
        * [リスク特性に関連した理由]
        * [資金需要タイミングとの整合性]
        * [顧客の選好や状況との適合性]

        #### 具体的な戦略
        * 資産配分アプローチ
        * 積立・一時投資の比率
        * 目的別資金の設定方法

        #### 期待効果
        * 教育資金達成見込み
        * 老後資金形成予測
        * 資産寿命延長効果

        #### 商品ポートフォリオ
        | 目的 | 商品名 | 投資金額/積立額 |
        |-----|-------|--------------|
        | [目的] | [商品名] | [金額] |

        ## Analysis Method
        1. Extract relevant information from the provided proposal
        2. Categorize information according to the defined categories
        3. If there is missing information, note it as "No information"
        4. Standardize information to allow for comparison of features for each strategy pattern

        ## Notes
        * The information displayed will be based on the content of the provided proposal
        * Extract numerical information as accurately as possible
        * Present the specific proposal content and product names as they are in the original text
        """
        output_response = await openrouter_client.chat.completions.create(
            model="openai/gpt-4.1",
            messages=[{"role": "system", "content": output_prompt}],
            max_tokens=4000,
        )
        output_data = output_response.choices[0].message.content
        print(output_data)

        current_analysis_prompt = f"""
        以下の出力から現在の運用分析に関するものをそのまま抜き出してください。
        ---
        {output_data}
        """
        current_analysis_response = await openrouter_client.chat.completions.create(
            model="openai/gpt-4.1",
            messages=[{"role": "system", "content": current_analysis_prompt}],
            max_tokens=4000,
        )
        current_analysis_data = current_analysis_response.choices[0].message.content
        strategy_1_prompt = f"""
        以下の出力から戦略パターン1に関するものをそのまま抜き出してください。
        ---
        {output_data}
        """
        strategy_1_response = await openrouter_client.chat.completions.create(
            model="openai/gpt-4.1",
            messages=[{"role": "system", "content": strategy_1_prompt}],
            max_tokens=4000,
        )
        strategy_1_data = strategy_1_response.choices[0].message.content
        strategy_2_prompt = f"""
        以下の出力から戦略パターン2に関するものをそのまま抜き出してください。
        ---
        {output_data}
        """
        strategy_2_response = await openrouter_client.chat.completions.create(
            model="openai/gpt-4.1",
            messages=[{"role": "system", "content": strategy_2_prompt}],
            max_tokens=4000,
        )
        strategy_2_data = strategy_2_response.choices[0].message.content
        strategy_3_prompt = f"""
        以下の出力から戦略パターン3に関するものをそのまま抜き出してください。
        ---
        {output_data}
        """
        strategy_3_response = await openrouter_client.chat.completions.create(
            model="openai/gpt-4.1",
            messages=[{"role": "system", "content": strategy_3_prompt}],
            max_tokens=4000,
        )
        strategy_3_data = strategy_3_response.choices[0].message.content
        print(f"current_analysis_data: {current_analysis_data}")
        print(f"strategy_1_data: {strategy_1_data}")
        print(f"strategy_2_data: {strategy_2_data}")
        print(f"strategy_3_data: {strategy_3_data}")

        strategy_data = {
            "current_analysis": current_analysis_data,
            "strategy_1": strategy_1_data,
            "strategy_2": strategy_2_data,
            "strategy_3": strategy_3_data
        }
        cache_data = await load_json(f"data/strategy_{current_user.id}.json", {})
        cache_data[datetime.now().isoformat()] = strategy_data
        await save_json(f"data/strategy_{current_user.id}.json", cache_data)
        
        return JSONResponse(
            content={
                "success": True,
                "message": "財務情報が正常に送信されました",
                "user_id": current_user.id,
                "timestamp": datetime.now().isoformat(),
                "strategy_data": strategy_data
            },
            status_code=200
        )
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"財務情報送信エラー: {e}")
        print(error_details)
        raise HTTPException(
            status_code=500,
            detail=f"財務情報の送信中にエラーが発生しました: {str(e)}"
        )
    
@router.get("/get-strategy")
async def get_strategy(
    current_user: User = Depends(get_current_user)
):
    try:
        strategy_data = await load_json(f"data/strategy_{current_user.id}.json", {})
        if not strategy_data:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "Not found strategy data, please submit financial data first"
                },
                status_code=404
            )
        
        return JSONResponse(
            content={
                "success": True,
                "strategy_data": strategy_data
            },
            status_code=200
        )
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"エラーが発生しました: {str(e)}"
        )
            