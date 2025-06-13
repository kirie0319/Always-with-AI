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

# 必要な構造化データの定義（TypeScript風のコメント）
"""
interface FinancialIssue {
    title: str
    details: List[str]
}

interface PortfolioItem {
    category: str
    amount: str
    notes: str
}

interface ProductPortfolioItem {
    purpose: str
    product: str
    amount: str
}

interface CurrentAnalysis {
    description: str
    issues: List[FinancialIssue]
    portfolio: List[PortfolioItem]
    total_amount: str
}

interface Strategy {
    title: str
    description: str
    reason: str
    details: List[str]
    expected_results: List[str]
    product_portfolio: List[ProductPortfolioItem]
}

interface FinancialStrategyData {
    advisor_type: str
    customer_info: str
    current_analysis: CurrentAnalysis
    strategies: List[Strategy]  # 3つの戦略
}
"""

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
    """財務情報フォームの送信を処理するエンドポイント（シンプル版）"""
    try:
        # 受け取ったデータをログに出力
        print("=== 財務フォーム送信データ ===")
        print(f"ユーザーID: {current_user.id}")
        print(f"ユーザー名: {current_user.username}")
        print(f"送信時刻: {datetime.now().isoformat()}")
        
        # プロンプト情報を抽出
        selected_prompt = financial_data.get('selectedPrompt')
        if selected_prompt:
            print(f"選択されたプロンプト: {selected_prompt['title']}")
            print(f"プロンプトID: {selected_prompt['id']}")
            print(f"プロンプト内容: {selected_prompt['content']}")
        else:
            print("プロンプトは選択されていません（デフォルトプロンプトを使用）")
        
        # 顧客情報を整理
        customer_summary = format_customer_info(financial_data)
        print("=== 顧客情報サマリー ===")
        print(customer_summary)
        
        # シンプルなプロンプト構築
        if selected_prompt:
            advisor_type = selected_prompt['title']
            advisor_instructions = selected_prompt['content']
        else:
            advisor_type = "バランス型アドバイザー"
            advisor_instructions = "顧客の状況に応じて、リスクとリターンのバランスを重視したアドバイスを提供してください。"

        simple_prompt = f"""
あなたは{advisor_type}として、以下の顧客情報を分析し、投資戦略を提案してください。

【アドバイザーの方針】
{advisor_instructions}

【顧客情報】
{customer_summary}

顧客の現在の運用状況を分析し、3つの戦略パターン（安定重視型、バランス型、成長重視型）を提案してください。
それぞれの戦略に対して、具体的な商品提案と期待効果を含めてください。
"""

        # Function calling用のスキーマ定義
        financial_strategy_function = {
            "name": "create_financial_strategy",
            "description": "顧客情報に基づいて財務戦略を作成する",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_analysis": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "現在の資産状況と主な課題点の概要"
                            },
                            "issues": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {
                                            "type": "string",
                                            "description": "課題のタイトル"
                                        },
                                        "details": {
                                            "type": "array",
                                            "items": {
                                                "type": "string"
                                            },
                                            "description": "課題の詳細説明のリスト"
                                        }
                                    },
                                    "required": ["title", "details"]
                                },
                                "description": "現在の運用における課題リスト"
                            },
                            "portfolio": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "category": {
                                            "type": "string",
                                            "description": "商品カテゴリー（例：株式、投資信託、保険等）"
                                        },
                                        "amount": {
                                            "type": "string",
                                            "description": "保有金額（例：250万円）"
                                        },
                                        "notes": {
                                            "type": "string",
                                            "description": "特徴や備考"
                                        }
                                    },
                                    "required": ["category", "amount", "notes"]
                                },
                                "description": "現在のポートフォリオ構成"
                            },
                            "total_amount": {
                                "type": "string",
                                "description": "総資産額"
                            }
                        },
                        "required": ["description", "issues", "portfolio", "total_amount"]
                    },
                    "strategies": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "戦略のタイトル（例：戦略パターン 1: 安定重視型の戦略名）"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "戦略の簡潔な説明"
                                },
                                "reason": {
                                    "type": "string",
                                    "description": "この戦略を提案する理由"
                                },
                                "details": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    },
                                    "description": "具体的な戦略の詳細リスト"
                                },
                                "expected_results": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    },
                                    "description": "期待される成果のリスト"
                                },
                                "product_portfolio": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "purpose": {
                                                "type": "string",
                                                "description": "投資目的（例：子ども教育資金、老後資金等）"
                                            },
                                            "product": {
                                                "type": "string",
                                                "description": "具体的な商品名（例：〇〇銀行変額年金保険）"
                                            },
                                            "amount": {
                                                "type": "string",
                                                "description": "投資金額または積立額"
                                            }
                                        },
                                        "required": ["purpose", "product", "amount"]
                                    },
                                    "description": "商品ポートフォリオの詳細"
                                }
                            },
                            "required": ["title", "description", "reason", "details", "expected_results", "product_portfolio"]
                        },
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "3つの戦略パターン（安定重視型、バランス型、成長重視型）"
                    }
                },
                "required": ["current_analysis", "strategies"]
            }
        }

        # Function callingでLLMに送信
        response = await openrouter_client.chat.completions.create(
            model="openai/gpt-4o",  # gpt-4oの方がfunction callingに対応している
                messages=[
                {
                    "role": "system", 
                    "content": f"あなたは{advisor_type}です。{advisor_instructions}"
                },
                {
                    "role": "user", 
                    "content": simple_prompt
                }
            ],
            tools=[{
                "type": "function",
                "function": financial_strategy_function
            }],
            tool_choice={"type": "function", "function": {"name": "create_financial_strategy"}},
            max_tokens=4000,
        )
        
        print("=== LLM生成結果 ===")
        print(response.choices[0].message)
        
        try:
            # Function callingの結果を取得
            message = response.choices[0].message
            
            if message.tool_calls and len(message.tool_calls) > 0:
                # Function callingの結果をパース
                tool_call = message.tool_calls[0]
                function_args = tool_call.function.arguments
                
                print("=== Function Arguments ===")
                print(function_args)
                
                import json
                parsed_strategy = json.loads(function_args)
                
                # 構造化データとして設定
                strategy_data = {
                    "advisor_type": advisor_type,
                    "customer_info": customer_summary,
                    "current_analysis": parsed_strategy.get("current_analysis", {}),
                    "strategies": parsed_strategy.get("strategies", [])
                }
                
                print("=== 構造化データ ===")
                print(strategy_data)
                
            else:
                # Function callingが失敗した場合のフォールバック
                raise Exception("Function calling failed - no tool calls in response")
            
        except Exception as e:
            print(f"Function calling パースエラー: {e}")
            # フォールバック - 手動プロンプトで再試行
            fallback_prompt = f"""
あなたは{advisor_type}として、以下の顧客情報を分析し、投資戦略を提案してください。

【アドバイザーの方針】
{advisor_instructions}

【顧客情報】
{customer_summary}

現在の運用状況を分析し、3つの戦略パターンを提案してください。簡潔に要点をまとめてください。
"""
            
            fallback_response = await openrouter_client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[{"role": "user", "content": fallback_prompt}],
                max_tokens=2000,
            )
            
            fallback_content = fallback_response.choices[0].message.content
            
            # フォールバック - 従来の方式
        strategy_data = {
                "advisor_type": advisor_type,
                "customer_info": customer_summary,
                "current_analysis": {
                    "description": "Function callingが失敗したため、簡易分析を表示しています。", 
                    "issues": [
                        {
                            "title": "詳細分析が必要",
                            "details": ["より詳細な分析のために再実行をお勧めします。"]
                        }
                    ], 
                    "portfolio": [], 
                    "total_amount": "分析中"
                },
                "strategies": [
                    {
                        "title": "戦略パターン 1: 安定重視型", 
                        "description": fallback_content[:200] + "..." if len(fallback_content) > 200 else fallback_content, 
                        "reason": "分析中...", 
                        "details": ["詳細分析中..."], 
                        "expected_results": ["結果分析中..."], 
                        "product_portfolio": []
                    },
                    {
                        "title": "戦略パターン 2: バランス型", 
                        "description": "バランス型戦略を準備中...", 
                        "reason": "分析中...", 
                        "details": ["詳細分析中..."], 
                        "expected_results": ["結果分析中..."], 
                        "product_portfolio": []
                    },
                    {
                        "title": "戦略パターン 3: 成長重視型", 
                        "description": "成長重視型戦略を準備中...", 
                        "reason": "分析中...", 
                        "details": ["詳細分析中..."], 
                        "expected_results": ["結果分析中..."], 
                        "product_portfolio": []
                    },
                ]
            }
        
        # キャッシュに保存
        cache_data = await load_json(f"data/strategy_{current_user.id}.json", {})
        cache_data[datetime.now().isoformat()] = strategy_data
        await save_json(f"data/strategy_{current_user.id}.json", cache_data)
        
        return JSONResponse(
            content={
                "success": True,
                "message": "財務戦略が正常に生成されました",
                "user_id": current_user.id,
                "timestamp": datetime.now().isoformat(),
                "strategy_data": strategy_data,
                "advisor_type": advisor_type
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
    
def format_customer_info(financial_data):
    """顧客情報をLLM用に整形（シンプル版）"""
    lines = []
    
    # 基本情報
    lines.append(f"年齢: {financial_data.get('age', 'N/A')}歳")
    lines.append(f"職業: {financial_data.get('industry', 'N/A')} / {financial_data.get('company', 'N/A')}")
    lines.append(f"役職: {financial_data.get('position', 'N/A')}")
    lines.append(f"年収: {financial_data.get('annualIncome', 0):,.0f}円")
    
    # 家族構成
    family_type = financial_data.get('familyType', 'single')
    lines.append(f"家族構成: {family_type}")
    
    family_members = financial_data.get('familyMembers', [])
    if family_members:
        lines.append("家族詳細:")
        for member in family_members:
            lines.append(f"  - {member.get('relation', '')} {member.get('age', '')}歳 ({member.get('occupation', '')})")
    
    # 資産状況
    lines.append(f"貯蓄額: {financial_data.get('savings', 0):,.0f}円")
    
    investments = financial_data.get('investments', [])
    if investments:
        lines.append("投資状況:")
        for inv in investments:
            lines.append(f"  - {inv.get('type', '')}: {inv.get('amount', 0):,.0f}円 ({inv.get('name', '')})")
    
    lines.append(f"退職金予定: {financial_data.get('retirementMoney', 0):,.0f}円")
    lines.append(f"月間生活費: {financial_data.get('monthlyExpenses', 0):,.0f}円")
    
    # ローン情報
    loans = financial_data.get('loans', [])
    if loans:
        lines.append("ローン状況:")
        for loan in loans:
            lines.append(f"  - {loan.get('type', '')}: {loan.get('balance', 0):,.0f}円 (残り{loan.get('remainingMonths', 0)}ヶ月)")
    
    # 投資方針
    lines.append(f"投資スタンス: {financial_data.get('investmentStance', 'N/A')}")
    
    # 将来の計画
    future_plans = []
    if financial_data.get('carPurchase'): future_plans.append("車購入予定")
    if financial_data.get('homeRemodel'): future_plans.append("リフォーム予定")
    if financial_data.get('domesticTravel'): future_plans.append("国内旅行")
    if financial_data.get('internationalTravel'): future_plans.append("海外旅行")
    if financial_data.get('wantsChildren'): future_plans.append("子育て予定")
    
    if future_plans:
        lines.append(f"将来の予定: {', '.join(future_plans)}")
    
    return "\n".join(lines)

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
            
@router.post("/generate-lifeplan")
async def generate_lifeplan_simulation(
    request: Request,
    financial_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user)
):
    """詳細なライフプランシミュレーションデータを生成（プロンプト対応版）"""
    try:
        print(f"受信したデータ: {financial_data}")
        
        basic_info = financial_data.get('basicInfo', {})
        family_info = financial_data.get('familyInfo', {})
        asset_info = financial_data.get('assetInfo', {})
        loan_info = financial_data.get('loanInfo', {})
        intentions = financial_data.get('intentions', {})
        selected_prompt = financial_data.get('selectedPrompt')
        
        print(f"basic_info: {basic_info}")
        print(f"family_info: {family_info}")
        print(f"asset_info: {asset_info}")
        print(f"intentions: {intentions}")
        print(f"selected_prompt: {selected_prompt}")
        
        # プロンプトに基づくパラメータ調整
        def get_advisor_parameters(selected_prompt, intentions):
            """アドバイザータイプと顧客意向に基づいてパラメータを調整"""
            params = {
                'income_growth_rate': 0.02,  # 年収成長率（デフォルト2%）
                'investment_return_rate': 0.03,  # 投資リターン率（デフォルト3%）
                'inflation_rate': 0.02,  # インフレ率（デフォルト2%）
                'retirement_age': 65,  # 退職年齢
                'life_expectancy': 90,  # 平均寿命
                'risk_buffer': 1.1,  # リスクバッファ（10%の余裕）
                'travel_frequency': 2,  # 旅行頻度（年）
                'renovation_cycle': 15,  # リフォーム周期（年）
                'car_replacement_cycle': 7,  # 車買い替え周期（年）
            }
            
            if selected_prompt:
                prompt_title = selected_prompt.get('title', '').lower()
                print(f"アドバイザータイプ: {prompt_title}")
                
                # 保守的アドバイザー
                if '保守' in prompt_title or 'conservative' in prompt_title or '安定' in prompt_title:
                    params['investment_return_rate'] = 0.02  # より保守的な2%
                    params['risk_buffer'] = 1.2  # 20%の余裕
                    params['travel_frequency'] = 1  # 旅行は控えめ
                    
                # 積極的アドバイザー
                elif '積極' in prompt_title or 'aggressive' in prompt_title or '成長' in prompt_title:
                    params['investment_return_rate'] = 0.05  # 積極的な5%
                    params['risk_buffer'] = 1.05  # 5%の余裕
                    params['travel_frequency'] = 3  # 旅行を楽しむ
                    
                # バランス型アドバイザー
                else:
                    # デフォルト値を使用
                    pass
            
            # 投資スタンスの反映
            investment_stance = intentions.get('investmentStance', '')
            if 'ローリスク' in investment_stance:
                params['investment_return_rate'] *= 0.7  # リターン率を下げる
                params['risk_buffer'] *= 1.1
            elif 'ハイリスク' in investment_stance:
                params['investment_return_rate'] *= 1.3  # リターン率を上げる
                params['risk_buffer'] *= 0.9
                
            return params
        
        # アドバイザーパラメータを取得
        advisor_params = get_advisor_parameters(selected_prompt, intentions)
        print(f"アドバイザーパラメータ: {advisor_params}")
        
        # 基本情報の取得（安全な取得方法）
        current_age = int(basic_info.get('age', 41))
        annual_income_man = basic_info.get('annualIncome', 900)  # 万円単位
        annual_income = int(annual_income_man) * 10000  # 円に変換
        
        spouse_info = family_info.get('hasSpouse', False)
        spouse_age = family_info.get('spouseAge', current_age + 1) if spouse_info else None
        spouse_income_man = family_info.get('spouseIncome', 150) if spouse_info else 0  # 万円単位
        spouse_income = int(spouse_income_man) * 10000  # 円に変換
        
        print(f"current_age: {current_age}, annual_income: {annual_income}")
        print(f"spouse_info: {spouse_info}, spouse_age: {spouse_age}, spouse_income: {spouse_income}")
        
        # 子供情報
        children = family_info.get('children', [])
        child1_age = int(children[0].get('age', 10)) if len(children) > 0 else None
        child2_age = int(children[1].get('age', 7)) if len(children) > 1 else None
        
        print(f"children: {children}, child1_age: {child1_age}, child2_age: {child2_age}")
        
        # 資産情報
        current_savings_man = asset_info.get('savings', 500)  # 万円単位
        current_savings = int(current_savings_man) * 10000  # 円に変換
        
        # 投資情報
        investments = asset_info.get('investments', [])
        total_investment_value = sum([inv.get('amount', 0) * 10000 for inv in investments])  # 万円を円に変換
        
        # ローン情報
        loans = loan_info.get('loans', [])
        total_loan_balance = sum([loan.get('balance', 0) * 10000 for loan in loans])  # 万円を円に変換
        
        print(f"current_savings: {current_savings}, investments: {total_investment_value}, loans: {total_loan_balance}")
        
        # 教育費計算関数
        def calculate_education_cost(child_age, education_preferences, inflation_rate, year_index):
            """子供の年齢と教育方針に基づいて教育費を計算"""
            if child_age < 3:
                return 0
            
            # 基本教育費（インフレ調整済み）
            base_costs = {
                'kindergarten': {'national': 200000, 'private': 400000},
                'elementary': {'national': 300000, 'private': 1200000},
                'middle': {'national': 400000, 'private': 1300000},
                'high': {'national': 450000, 'private': 1000000},
                'university': {'national': 800000, 'private': 1500000}
            }
            
            # 年齢に応じた教育段階の判定
            if 3 <= child_age <= 5:
                stage = 'kindergarten'
            elif 6 <= child_age <= 11:
                stage = 'elementary'
            elif 12 <= child_age <= 14:
                stage = 'middle'
            elif 15 <= child_age <= 17:
                stage = 'high'
            elif 18 <= child_age <= 21:
                stage = 'university'
            else:
                return 0
            
            # 教育方針の取得（デフォルトは国公立）
            school_type = education_preferences.get(stage, 'national')
            base_cost = base_costs[stage][school_type]
            
            # インフレ調整
            adjusted_cost = int(base_cost * ((1 + inflation_rate) ** year_index))
            
            return adjusted_cost
        
        # 顧客意向に基づく支出計画関数
        def calculate_intention_based_expenses(year, intentions, advisor_params):
            """顧客の意向に基づいて年間の特別支出を計算"""
            special_expenses = {}
            
            # 車購入
            if intentions.get('carPurchase', False):
                car_cycle = advisor_params['car_replacement_cycle']
                if year % car_cycle == 1:  # 最初の年と周期的に購入
                    special_expenses['car_purchase'] = 3000000  # 300万円
                    
            # リフォーム
            if intentions.get('homeRemodel', False):
                renovation_cycle = advisor_params['renovation_cycle']
                if year % renovation_cycle == 5:  # 5年目、20年目等
                    special_expenses['home_renovation'] = 2000000  # 200万円
                elif year % renovation_cycle == 0:  # 大規模リフォーム
                    special_expenses['home_renovation'] = 5000000  # 500万円
                    
            # 旅行
            travel_annual = 0
            if intentions.get('domesticTravel', False):
                travel_annual += 500000 * advisor_params['travel_frequency']  # 50万円×頻度
            if intentions.get('internationalTravel', False):
                travel_annual += 1000000 * advisor_params['travel_frequency']  # 100万円×頻度
            if travel_annual > 0:
                special_expenses['travel'] = travel_annual
                
            # ペット飼育
            if intentions.get('petOwnership', False):
                special_expenses['pet_expenses'] = 300000  # 年間30万円
                
            # その他支出
            if intentions.get('otherExpenses', False):
                special_expenses['other'] = 500000  # 年間50万円
                
            return special_expenses
        
        # シミュレーション期間（現在から65年後まで）
        years = list(range(1, 66))
        ages = list(range(current_age, current_age + 65))
        
        # データ配列初期化
        income_data = []
        expense_data = []
        savings_balance = []
        
        # 各年のシミュレーション
        for i, year in enumerate(years):
            age = ages[i]
            spouse_current_age = spouse_age + i if spouse_age else None
            
            # === 収入計算（アドバイザーパラメータ反映） ===
            # 本人の年収（成長率を反映）
            income_growth_rate = advisor_params['income_growth_rate']
            retirement_age = advisor_params['retirement_age']
            
            # 年収成長を反映した基本年収
            adjusted_annual_income = annual_income * ((1 + income_growth_rate) ** i)
            
            # 変数を初期化
            primary_income = 0
            primary_pension = 0
            
            if age <= retirement_age - 10:
                primary_income = int(adjusted_annual_income)
            elif age <= retirement_age - 5:
                primary_income = int(adjusted_annual_income * 0.95)  # 少し減少
            elif age <= retirement_age:
                primary_income = int(adjusted_annual_income * 0.85)  # 再雇用等
            elif age >= retirement_age + 1:
                # 年金開始（基本年収の30%程度）
                primary_income = 0
                primary_pension = int(adjusted_annual_income * 0.3)
            
            # 配偶者の年収
            spouse_annual_income = 0
            if spouse_current_age and spouse_current_age <= 60:
                spouse_growth_income = spouse_income * ((1 + income_growth_rate) ** i)
                spouse_annual_income = int(spouse_growth_income)
            
            # 投資リターン（既存投資の運用益）
            investment_return = 0
            if total_investment_value > 0:
                return_rate = advisor_params['investment_return_rate']
                investment_return = int(total_investment_value * return_rate * ((1 + return_rate) ** i))
            
            # 住宅ローン控除
            housing_deduction = 0
            if year <= 10 and total_loan_balance > 0:
                # ローン残高の1%（上限40万円）
                remaining_loan = max(0, total_loan_balance - (year - 1) * 1500000)
                housing_deduction = min(400000, int(remaining_loan * 0.01))
            
            total_income = (primary_income + primary_pension + 
                          spouse_annual_income + investment_return + housing_deduction)
            
            # === 支出計算（顧客意向反映） ===
            inflation_rate = advisor_params['inflation_rate']
            
            # 基本生活費（インフレ調整）
            base_monthly_expenses = asset_info.get('monthlyExpenses', 24) * 10000  # 万円を円に変換
            living_expenses = int(base_monthly_expenses * 12 * ((1 + inflation_rate) ** i))
            
            # 住宅関連費用（インフレ調整）
            base_housing = 600000
            housing_expenses = int(base_housing * ((1 + inflation_rate) ** i))
            
            # ローン返済額（実際のローン情報から計算）
            loan_repayment = 0
            for loan in loans:
                remaining_months = loan.get('remainingMonths', 0) - (year - 1) * 12
                if remaining_months > 0 and loan.get('remainingMonths', 0) > 0:
                    # 簡易計算：残高を残月数で割る
                    monthly_payment = (loan.get('balance', 0) * 10000) / loan.get('remainingMonths', 1)
                    loan_repayment += int(monthly_payment * 12)
            
            # 保険積立（アドバイザーパラメータ反映）
            insurance_total = 0
            risk_buffer = advisor_params['risk_buffer']
            if year <= 25:  # 長期積立
                insurance_total += int(360000 * risk_buffer)  # リスクバッファ反映
            
            # 車両費（顧客意向反映）
            vehicle_expenses = 0
            if intentions.get('carPurchase', False):
                base_vehicle_cost = 300000  # 年間維持費
                vehicle_expenses = int(base_vehicle_cost * ((1 + inflation_rate) ** i))
            
            # 習い事・教育費（子供の年齢と教育方針反映）
            education_expenses = 0
            child_education_preferences = intentions.get('childEducation', {})
            
            if child1_age:
                child1_current_age = child1_age + i
                education_expenses += calculate_education_cost(
                    child1_current_age, child_education_preferences, inflation_rate, i
                )
            
            if child2_age:
                child2_current_age = child2_age + i
                education_expenses += calculate_education_cost(
                    child2_current_age, child_education_preferences, inflation_rate, i
                )
            
            # 税金（年収に基づく概算）
            tax_expenses = 0
            if primary_income > 0:
                # 年収の約30%を税金・社会保険として概算
                tax_expenses = int((primary_income + spouse_annual_income) * 0.3)
            
            # 顧客意向に基づく特別支出
            special_expenses = calculate_intention_based_expenses(year, intentions, advisor_params)
            total_special_expenses = sum(special_expenses.values())
            
            total_expenses = (living_expenses + housing_expenses + loan_repayment + 
                            insurance_total + vehicle_expenses + education_expenses + 
                            tax_expenses + total_special_expenses)
            
            # 年間収支
            annual_balance = total_income - total_expenses
            
            # 累積貯蓄残高（投資運用も含む）
            if i == 0:
                cumulative_savings = current_savings + total_investment_value + annual_balance
            else:
                # 前年の残高 + 今年の収支 + 投資運用益
                cumulative_savings = savings_balance[-1] + annual_balance
            
            income_data.append(total_income)
            expense_data.append(total_expenses)
            savings_balance.append(cumulative_savings)
        
        # 新しい構造のライフプランデータを生成（プロンプト対応版）
        years_data = []
        
        # 計算済みデータを再構築
        for i in range(len(years)):
            year = years[i]
            age = ages[i]
            spouse_current_age = spouse_age + i if spouse_age else None
            child1_current = child1_age + i if child1_age else None
            child2_current = child2_age + i if child2_age else None
            
            # 既に計算された値を使用
            total_income_value = income_data[i] 
            total_expense_value = expense_data[i]
            cash_balance_value = savings_balance[i]
            annual_balance_value = total_income_value - total_expense_value
            
            # 収入詳細を再計算（表示用）
            income_growth_rate = advisor_params['income_growth_rate']
            retirement_age = advisor_params['retirement_age']
            adjusted_annual_income = annual_income * ((1 + income_growth_rate) ** i)
            
            primary_income_display = 0
            primary_pension_display = None
            
            if age <= retirement_age - 10:
                primary_income_display = int(adjusted_annual_income)
            elif age <= retirement_age - 5:
                primary_income_display = int(adjusted_annual_income * 0.95)
            elif age <= retirement_age:
                primary_income_display = int(adjusted_annual_income * 0.85)
            elif age >= retirement_age + 1:
                primary_pension_display = int(adjusted_annual_income * 0.3)
                
            # 配偶者収入
            spouse_income_display = None
            if spouse_current_age and spouse_current_age <= 60:
                spouse_growth_income = spouse_income * ((1 + income_growth_rate) ** i)
                spouse_income_display = int(spouse_growth_income)
            
            # ローン控除
            home_loan_deduction_display = None
            if year <= 10 and total_loan_balance > 0:
                remaining_loan = max(0, total_loan_balance - (year - 1) * 1500000)
                home_loan_deduction_display = min(400000, int(remaining_loan * 0.01))
            
            # 支出詳細を再計算（表示用）
            inflation_rate = advisor_params['inflation_rate']
            base_monthly_expenses = asset_info.get('monthlyExpenses', 24) * 10000
            living_expenses_display = int(base_monthly_expenses * 12 * ((1 + inflation_rate) ** i))
            
            base_housing = 600000
            housing_expenses_display = int(base_housing * ((1 + inflation_rate) ** i))
            
            # ローン返済額計算
            loan_repayment_display = 0
            for loan in loans:
                remaining_months = loan.get('remainingMonths', 0) - (year - 1) * 12
                if remaining_months > 0 and loan.get('remainingMonths', 0) > 0:
                    monthly_payment = (loan.get('balance', 0) * 10000) / loan.get('remainingMonths', 1)
                    loan_repayment_display += int(monthly_payment * 12)
            
            # 保険積立
            risk_buffer = advisor_params['risk_buffer']
            insurance_total_display = 0
            if year <= 25:
                insurance_total_display = int(360000 * risk_buffer)
            
            # 車両費
            vehicle_expenses_display = 0
            if intentions.get('carPurchase', False):
                base_vehicle_cost = 300000
                vehicle_expenses_display = int(base_vehicle_cost * ((1 + inflation_rate) ** i))
            
            # 教育費
            child_education_display = 0
            child_education_preferences = intentions.get('childEducation', {})
            
            if child1_age:
                child1_current_age = child1_age + i
                child_education_display += calculate_education_cost(
                    child1_current_age, child_education_preferences, inflation_rate, i
                )
            
            if child2_age:
                child2_current_age = child2_age + i
                child_education_display += calculate_education_cost(
                    child2_current_age, child_education_preferences, inflation_rate, i
                )
            
            # 税金
            tax_expenses_display = 0
            if primary_income_display > 0:
                tax_expenses_display = int((primary_income_display + (spouse_income_display or 0)) * 0.3)
            
            # 特別支出
            special_expenses = calculate_intention_based_expenses(year, intentions, advisor_params)
            
            years_data.append({
                'year': year,
                'primary_age': age,
                'spouse_age': spouse_current_age,
                'child1_age': child1_current,
                'child2_age': child2_current,
                'total_income': total_income_value,
                'primary_income': primary_income_display,
                'primary_pension': primary_pension_display,
                'spouse_income': spouse_income_display,
                'home_loan_deduction': home_loan_deduction_display,
                'total_expense': total_expense_value,
                'living_expenses': living_expenses_display,
                'housing_expenses': housing_expenses_display,
                'loan_repayment': loan_repayment_display,
                'insurance_total': insurance_total_display,
                'life_insurance': insurance_total_display // 3 if insurance_total_display > 0 else 0,
                'endowment_insurance': insurance_total_display // 3 if insurance_total_display > 0 else 0,
                'ideco_contribution': insurance_total_display // 3 if insurance_total_display > 0 else 0,
                'vehicle_expenses': vehicle_expenses_display,
                'hobby_lessons': 0,  # 習い事は教育費に統合
                'tax_expenses': tax_expenses_display,
                'child_education': child_education_display if child_education_display > 0 else None,
                'home_renovation': special_expenses.get('home_renovation'),
                'travel_expenses': special_expenses.get('travel'),
                'annual_balance': annual_balance_value,
                'cash_balance': cash_balance_value
            })
        
        # LLMを使った詳細分析
        async def generate_lifeplan_analysis(customer_data, years_data, advisor_params, selected_prompt):
            """LLMを使用してライフプランの詳細分析とアドバイスを生成"""
            
            # 重要な年代の抽出
            critical_years = []
            for i, data in enumerate(years_data):
                if data['cash_balance'] < 0:  # 赤字年
                    critical_years.append({'year': data['year'], 'age': data['primary_age'], 'issue': '資金不足', 'amount': data['cash_balance']})
                elif data['child_education'] and data['child_education'] > 5000000:  # 高額教育費
                    critical_years.append({'year': data['year'], 'age': data['primary_age'], 'issue': '高額教育費', 'amount': data['child_education']})
                elif data['home_renovation'] and data['home_renovation'] > 3000000:  # 大規模リフォーム
                    critical_years.append({'year': data['year'], 'age': data['primary_age'], 'issue': '大規模リフォーム', 'amount': data['home_renovation']})
            
            # 顧客プロファイル作成
            customer_profile = f"""
顧客プロファイル：
- 年齢: {customer_data['basicInfo']['age']}歳
- 年収: {customer_data['basicInfo']['annualIncome']}万円
- 業界: {customer_data['basicInfo'].get('industry', '不明')}
- 家族構成: {'配偶者あり' if customer_data['familyInfo']['hasSpouse'] else '単身'}
- 子供: {len(customer_data['familyInfo']['children'])}人
- 貯蓄: {customer_data['assetInfo']['savings']}万円
- 投資額: {sum([inv.get('amount', 0) for inv in customer_data['assetInfo']['investments']])}万円
- 月間支出: {customer_data['assetInfo']['monthlyExpenses']}万円

顧客の意向：
- 車購入: {'希望' if customer_data['intentions'].get('carPurchase') else '不要'}
- リフォーム: {'希望' if customer_data['intentions'].get('homeRemodel') else '不要'}
- 国内旅行: {'希望' if customer_data['intentions'].get('domesticTravel') else '不要'}
- 海外旅行: {'希望' if customer_data['intentions'].get('internationalTravel') else '不要'}
- 投資スタンス: {customer_data['intentions'].get('investmentStance', '未設定')}

選択されたアドバイザー：{selected_prompt['title'] if selected_prompt else '未選択'}
"""
            
            prompt = f"""
あなたは経験豊富なファイナンシャルプランナーです。以下の顧客情報と65年間のライフプランシミュレーション結果を分析し、詳細なアドバイスを提供してください。

{customer_profile}

重要な課題年：
{critical_years}

以下の形式でJSONレスポンスを提供してください：

{{
    "overall_assessment": "全体的な財務状況の評価（3-4文）",
    "risk_analysis": [
        {{"period": "○○年～○○年", "risk": "リスクの説明", "impact": "影響度（高/中/低）", "solution": "対策案"}}
    ],
    "opportunities": [
        {{"period": "○○年～○○年", "opportunity": "機会の説明", "benefit": "効果", "action": "具体的行動"}}
    ],
    "customized_advice": [
        {{"category": "投資戦略/保険/教育資金/老後資金", "advice": "具体的アドバイス", "priority": "優先度（高/中/低）"}}
    ],
    "chart_insights": {{
        "deposit_trend": "預金残高の傾向分析",
        "cash_flow_pattern": "収支パターンの特徴",
        "critical_periods": "注意すべき時期"
    }}
}}
"""

            try:
                # 分析用のFunction calling定義
                analysis_tool = {
                    "type": "function",
                    "function": {
                        "name": "analyze_lifeplan",
                        "description": "ライフプランの詳細分析とアドバイス生成",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "overall_assessment": {
                                    "type": "string",
                                    "description": "全体的な財務状況の評価（3-4文）"
                                },
                                "risk_analysis": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "period": {"type": "string", "description": "期間"},
                                            "risk": {"type": "string", "description": "リスクの説明"},
                                            "impact": {"type": "string", "enum": ["高", "中", "低"], "description": "影響度"},
                                            "solution": {"type": "string", "description": "対策案"}
                                        },
                                        "required": ["period", "risk", "impact", "solution"]
                                    },
                                    "description": "リスク分析"
                                },
                                "opportunities": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "period": {"type": "string", "description": "期間"},
                                            "opportunity": {"type": "string", "description": "機会の説明"},
                                            "benefit": {"type": "string", "description": "効果"},
                                            "action": {"type": "string", "description": "具体的行動"}
                                        },
                                        "required": ["period", "opportunity", "benefit", "action"]
                                    },
                                    "description": "機会分析"
                                },
                                "customized_advice": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "category": {"type": "string", "description": "カテゴリ"},
                                            "advice": {"type": "string", "description": "具体的アドバイス"},
                                            "priority": {"type": "string", "enum": ["高", "中", "低"], "description": "優先度"}
                                        },
                                        "required": ["category", "advice", "priority"]
                                    },
                                    "description": "カスタマイズされたアドバイス"
                                },
                                "chart_insights": {
                                    "type": "object",
                                    "properties": {
                                        "deposit_trend": {"type": "string", "description": "預金残高の傾向分析"},
                                        "cash_flow_pattern": {"type": "string", "description": "収支パターンの特徴"},
                                        "critical_periods": {"type": "string", "description": "注意すべき時期"}
                                    },
                                    "required": ["deposit_trend", "cash_flow_pattern", "critical_periods"]
                                }
                            },
                            "required": ["overall_assessment", "risk_analysis", "opportunities", "customized_advice", "chart_insights"]
                        }
                    }
                }
                
                response = await openrouter_client.chat.completions.create(
                    model="openai/gpt-4.1",
                    messages=[
                        {"role": "system", "content": "あなたは専門的なファイナンシャルプランナーです。顧客の65年間のライフプランを詳細に分析し、実用的なアドバイスを提供します。"},
                        {"role": "user", "content": prompt}
                    ],
                    tools=[analysis_tool],
                    tool_choice={"type": "function", "function": {"name": "analyze_lifeplan"}},
                    temperature=0.3
                )
                
                # Function callingの結果を取得
                import json
                message = response.choices[0].message
                if message.tool_calls and len(message.tool_calls) > 0:
                    tool_call = message.tool_calls[0]
                    if tool_call.function.name == "analyze_lifeplan":
                        try:
                            analysis_json = json.loads(tool_call.function.arguments)
                            print(f"✅ 分析Function calling成功")
                            return analysis_json
                        except json.JSONDecodeError as je:
                            print(f"❌ 分析Function calling JSON解析失敗: {je}")
                        except Exception as e:
                            print(f"❌ 分析Function calling処理エラー: {e}")
                
                # フォールバック
                return {
                    "overall_assessment": "システムにより詳細なライフプランが生成されました。",
                    "risk_analysis": [],
                    "opportunities": [],
                    "customized_advice": [],
                    "chart_insights": {
                        "deposit_trend": "預金残高は安定的に推移しています",
                        "cash_flow_pattern": "収支バランスは概ね良好です",
                        "critical_periods": "特に注意が必要な時期は見当たりません"
                    }
                }
                    
            except Exception as e:
                print(f"LLM分析エラー: {e}")
                # エラー時のフォールバック
                return {
                    "overall_assessment": f"アドバイザー「{selected_prompt['title'] if selected_prompt else 'システム'}」による詳細なライフプランが生成されました。",
                    "risk_analysis": [],
                    "opportunities": [],
                    "customized_advice": [],
                    "chart_insights": {
                        "deposit_trend": "預金残高の推移をご確認ください",
                        "cash_flow_pattern": "年間収支の変動に注意してください",
                        "critical_periods": "ライフステージの変化に合わせた計画が重要です"
                    }
                }

        # LLMベースのライフプラングラフ生成
        async def generate_llm_lifeplan_graph(customer_data, selected_prompt):
            """LLMを使用してカスタマイズされたライフプランのグラフデータを生成"""
            
            customer_profile = f"""
顧客プロファイル：
- 年齢: {customer_data['basicInfo']['age']}歳
- 年収: {customer_data['basicInfo']['annualIncome']}万円
- 業界: {customer_data['basicInfo'].get('industry', '不明')}
- 家族構成: {'配偶者あり' if customer_data['familyInfo']['hasSpouse'] else '単身'}
- 子供: {len(customer_data['familyInfo']['children'])}人
- 貯蓄: {customer_data['assetInfo']['savings']}万円
- 投資額: {sum([inv.get('amount', 0) for inv in customer_data['assetInfo']['investments']])}万円
- 月間支出: {customer_data['assetInfo']['monthlyExpenses']}万円

顧客の意向・希望：
- 車購入: {'希望' if customer_data['intentions'].get('carPurchase') else '不要'}
- リフォーム: {'希望' if customer_data['intentions'].get('homeRemodel') else '不要'}
- 国内旅行: {'希望' if customer_data['intentions'].get('domesticTravel') else '不要'}
- 海外旅行: {'希望' if customer_data['intentions'].get('internationalTravel') else '不要'}
- 投資スタンス: {customer_data['intentions'].get('investmentStance', '未設定')}
- 子供の教育方針: {customer_data['intentions'].get('childEducation', '未設定')}

選択されたファイナンシャルアドバイザー：
- タイプ: {selected_prompt['title'] if selected_prompt else 'システムデフォルト'}
- 特徴: {selected_prompt['description'] if selected_prompt else 'バランス型アプローチ'}
"""

            # 子供の年齢情報
            children_info = ""
            if customer_data['familyInfo']['children']:
                for i, child in enumerate(customer_data['familyInfo']['children']):
                    children_info += f"- 子供{i+1}: {child['age']}歳\n"

            prompt = f"""
【重要指示】必ず65年分の年間データ（year 1 から year 65まで）を生成してください。

あなたは選択されたアドバイザータイプ「{selected_prompt['title'] if selected_prompt else 'バランス型'}」として、顧客の実際の数値に基づいた完全カスタマイズ65年間ライフプランを作成します。

【顧客情報】
{customer_profile}
{children_info}

【実数値ベース】
- 現在年収: {customer_data['basicInfo']['annualIncome']}万円  
- 現在貯蓄: {customer_data['assetInfo']['savings']}万円
- 月間支出: {customer_data['assetInfo']['monthlyExpenses']}万円（年間{customer_data['assetInfo']['monthlyExpenses'] * 12}万円）
- 投資額: {sum([inv.get('amount', 0) for inv in customer_data['assetInfo'].get('investments', [])])}万円

【アドバイザー特性】
{'保守的アドバイザー: 投資リターン3-4%、安定重視' if selected_prompt and ('conservative' in (selected_prompt.get('title', '') + selected_prompt.get('description', '')).lower() or '保守' in (selected_prompt.get('title', '') + selected_prompt.get('description', '')).lower()) else '積極的アドバイザー: 投資リターン6-8%、成長重視' if selected_prompt and ('aggressive' in (selected_prompt.get('title', '') + selected_prompt.get('description', '')).lower() or '積極' in (selected_prompt.get('title', '') + selected_prompt.get('description', '')).lower()) else 'バランス型アドバイザー: 投資リターン4-6%、中庸'}

【65年分データ生成指示】
create_personalized_lifeplan関数を使用して、以下を含む65年間の完全なライフプランを作成してください：

1. yearly_projections配列に年1から年65まで65個のオブジェクトを必ず含める
2. 初年度は上記の実数値から開始
3. 各年で年齢・年収・支出・資産を論理的に計算
4. ライフイベント（結婚、出産、教育費、退職、年金等）を適切な年に配置
5. アドバイザー特性を数値に反映
6. 現実的で実行可能な数値のみ使用

【年間計算例】
年1: 年収{customer_data['basicInfo']['annualIncome']}万円 → 支出{customer_data['assetInfo']['monthlyExpenses'] * 12}万円 → 貯蓄{customer_data['assetInfo']['savings']}万円
年2: 年収成長率を反映 → インフレ調整支出 → 累積貯蓄計算
年3-64: 昇進・転職・退職・年金を段階的反映
年65: 完全退職状態の計算

function callingで確実に65年分の構造化データを生成してください。
"""

            try:
                print(f"🤖 LLMライフプラン生成開始 - アドバイザー: {selected_prompt['title'] if selected_prompt else 'デフォルト'}")
                print(f"📊 顧客データ: 年収{customer_data['basicInfo']['annualIncome']}万円, 貯蓄{customer_data['assetInfo']['savings']}万円")
                
                # Function calling用のツール定義
                lifeplan_tool = {
                    "type": "function",
                    "function": {
                        "name": "create_personalized_lifeplan",
                        "description": "顧客情報に基づいて65年間のパーソナライズされたライフプランを作成",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "simulation_approach": {
                                    "type": "string",
                                    "description": "この顧客とアドバイザータイプに基づく具体的アプローチ説明"
                                },
                                "key_assumptions": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "計算の前提条件リスト（年収成長率、投資リターン率等）"
                                },
                                "yearly_projections": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "year": {"type": "integer", "description": "年数（1-65）"},
                                            "age": {"type": "integer", "description": "年齢"},
                                            "annual_income": {"type": "number", "description": "年収（万円）"},
                                            "annual_expenses": {"type": "number", "description": "年間支出（万円）"},
                                            "special_events": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                                "description": "その年の特別イベント"
                                            },
                                            "savings_balance": {"type": "number", "description": "貯蓄残高（万円）"},
                                            "investment_value": {"type": "number", "description": "投資評価額（万円）"},
                                            "net_worth": {"type": "number", "description": "純資産（万円）"},
                                            "cash_flow": {"type": "number", "description": "年間キャッシュフロー（万円）"},
                                            "advisor_notes": {"type": "string", "description": "アドバイザーからのコメント"}
                                        },
                                        "required": ["year", "age", "annual_income", "annual_expenses", "savings_balance", "investment_value", "net_worth", "cash_flow"]
                                    },
                                    "description": "65年分の年間詳細データ"
                                },
                                "graph_highlights": {
                                    "type": "object",
                                    "properties": {
                                        "peak_wealth_age": {"type": "integer", "description": "ピーク資産年齢"},
                                        "retirement_readiness": {"type": "string", "description": "退職準備状況"},
                                        "cash_flow_turning_points": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "キャッシュフロー転換点"
                                        },
                                        "risk_periods": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "リスク期間"
                                        },
                                        "growth_opportunities": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "成長機会"
                                        }
                                    },
                                    "required": ["peak_wealth_age", "retirement_readiness"]
                                },
                                "personalized_insights": {
                                    "type": "object",
                                    "properties": {
                                        "wealth_building_strategy": {"type": "string", "description": "資産形成戦略"},
                                        "life_stage_planning": {"type": "string", "description": "ライフステージ別計画"},
                                        "contingency_planning": {"type": "string", "description": "リスク対策"}
                                    },
                                    "required": ["wealth_building_strategy", "life_stage_planning", "contingency_planning"]
                                }
                            },
                            "required": ["simulation_approach", "key_assumptions", "yearly_projections", "graph_highlights", "personalized_insights"]
                        }
                    }
                }
                
                response = await openrouter_client.chat.completions.create(
                    model="openai/gpt-4.1",
                    messages=[
                        {"role": "system", "content": f"あなたは「{selected_prompt['title'] if selected_prompt else 'バランス型'}」ファイナンシャルアドバイザーです。顧客の実際の数値に基づいて、完全カスタマイズされたライフプランを65年分作成してください。"},
                        {"role": "user", "content": prompt}
                    ],
                    tools=[lifeplan_tool],
                    tool_choice={"type": "function", "function": {"name": "create_personalized_lifeplan"}},
                    temperature=0.1
                )
                
                # Function callingの結果を取得
                import json
                
                message = response.choices[0].message
                if message.tool_calls and len(message.tool_calls) > 0:
                    tool_call = message.tool_calls[0]
                    if tool_call.function.name == "create_personalized_lifeplan":
                        try:
                            # Function callingで返されたJSONデータを解析
                            llm_data = json.loads(tool_call.function.arguments)
                            print(f"✅ Function calling成功")
                            
                            # データの妥当性チェック
                            if 'yearly_projections' in llm_data:
                                yearly_data = llm_data['yearly_projections']
                                print(f"🎯 LLMライフプラン生成成功: {len(yearly_data)}年分")
                                
                                # サンプルデータを表示
                                if len(yearly_data) > 0:
                                    sample = yearly_data[0]
                                    print(f"📈 初年度データサンプル: 年収{sample.get('annual_income', '?')}万円, 支出{sample.get('annual_expenses', '?')}万円")
                                
                                return llm_data
                            else:
                                print("⚠️ yearly_projectionsが見つかりません")
                                
                        except json.JSONDecodeError as je:
                            print(f"❌ Function calling JSON解析失敗: {je}")
                        except Exception as e:
                            print(f"❌ Function calling処理エラー: {e}")
                    else:
                        print(f"❌ 予期しない関数名: {tool_call.function.name}")
                else:
                    print("❌ Tool callsが見つかりません")
                
                print("❌ LLMデータ生成失敗 - フォールバックします")
                return None
                    
            except Exception as e:
                print(f"🚨 LLMライフプラン生成エラー: {e}")
                import traceback
                print(traceback.format_exc())
                return None

        # LLMベースのライフプラン生成を実行
        llm_lifeplan = await generate_llm_lifeplan_graph(
            {
                'basicInfo': basic_info,
                'familyInfo': family_info,
                'assetInfo': asset_info,
                'intentions': intentions
            },
            selected_prompt
        )

        # LLM分析を実行
        lifeplan_analysis = await generate_lifeplan_analysis(
            {
                'basicInfo': basic_info,
                'familyInfo': family_info,
                'assetInfo': asset_info,
                'intentions': intentions
            },
            years_data,
            advisor_params,
            selected_prompt
        )

        # LLMベースのチャートデータを生成（利用可能な場合）
        def create_llm_chart_data(llm_lifeplan, fallback_data):
            """LLMデータからチャート用データを作成、失敗時はfallbackを使用"""
            print(f"📊 チャートデータ作成開始...")
            
            # LLMデータの存在確認
            if not llm_lifeplan:
                print("❌ LLMライフプランデータが存在しません - 計算ベースを使用")
                return create_fallback_chart_data(fallback_data, 'calculation')
            
            if 'yearly_projections' not in llm_lifeplan:
                print("❌ yearly_projectionsが存在しません - 計算ベースを使用")
                return create_fallback_chart_data(fallback_data, 'calculation')
            
            try:
                yearly_data = llm_lifeplan['yearly_projections']
                print(f"✅ LLMデータ確認: {len(yearly_data)}年分のprojections")
                
                if len(yearly_data) < 5:
                    print(f"⚠️ データ不足: {len(yearly_data)}年分のみ - 計算ベースを使用")
                    return create_fallback_chart_data(fallback_data, 'calculation_insufficient')
                
                # 5年おきのデータを抽出（最大13ポイント）
                sample_indices = list(range(0, min(len(yearly_data), 65), 5))
                sample_data = [yearly_data[i] for i in sample_indices if i < len(yearly_data)]
                
                print(f"📈 サンプルデータ抽出: {len(sample_data)}ポイント")
                
                # データを数値として確実に処理
                age_labels = []
                deposit_balance = []
                asset_balance = []
                income_expense_balance = []
                
                for i, data in enumerate(sample_data):
                    try:
                        age = int(data.get('age', current_age + sample_indices[i]))
                        savings = float(data.get('savings_balance', 0))
                        net_worth = float(data.get('net_worth', savings))
                        cash_flow = float(data.get('cash_flow', 0))
                        
                        age_labels.append(age)
                        deposit_balance.append(savings)
                        asset_balance.append(net_worth)
                        income_expense_balance.append(cash_flow)
                        
                    except (ValueError, TypeError) as ve:
                        print(f"⚠️ データ変換エラー (年{i+1}): {ve}")
                        # デフォルト値を使用
                        age_labels.append(current_age + sample_indices[i])
                        deposit_balance.append(0)
                        asset_balance.append(0)
                        income_expense_balance.append(0)
                
                print(f"🎯 LLMチャートデータ作成成功:")
                print(f"   年齢範囲: {age_labels[0]}歳 〜 {age_labels[-1]}歳")
                print(f"   預金残高範囲: {min(deposit_balance):.1f} 〜 {max(deposit_balance):.1f}万円")
                print(f"   純資産範囲: {min(asset_balance):.1f} 〜 {max(asset_balance):.1f}万円")
                
                return {
                    'age_labels': age_labels,
                    'deposit_balance': deposit_balance,
                    'asset_balance': asset_balance,
                    'income_expense_balance': income_expense_balance,
                    'insights': lifeplan_analysis['chart_insights'],
                    'llm_highlights': llm_lifeplan.get('graph_highlights', {}),
                    'data_source': 'llm_generated'
                }
                
            except Exception as e:
                print(f"🚨 LLMチャートデータ作成エラー: {e}")
                import traceback
                print(traceback.format_exc())
                return create_fallback_chart_data(fallback_data, 'calculation_fallback')

        def create_fallback_chart_data(fallback_data, source_type):
            """フォールバック用のチャートデータ作成"""
            return {
                'age_labels': [age for age in ages[::5]],
                'deposit_balance': [data['cash_balance'] / 10000 for data in fallback_data[::5]],
                'asset_balance': [(data['cash_balance'] + total_investment_value) / 10000 for data in fallback_data[::5]],
                'income_expense_balance': [data['annual_balance'] / 10000 for data in fallback_data[::5]],
                'insights': lifeplan_analysis['chart_insights'],
                'data_source': source_type
            }

        # チャート用データ生成
        chart_summary = create_llm_chart_data(llm_lifeplan, years_data)
        
        # LLMデータ用の詳細テーブル作成
        def create_llm_years_data(llm_lifeplan, fallback_data):
            """LLMデータから詳細テーブル用データを作成"""
            print(f"📋 詳細テーブルデータ作成開始...")
            
            if not llm_lifeplan:
                print("❌ LLMライフプランデータなし - 計算ベースを使用")
                return fallback_data
                
            if 'yearly_projections' not in llm_lifeplan:
                print("❌ yearly_projectionsなし - 計算ベースを使用")
                return fallback_data
            
            try:
                yearly_data = llm_lifeplan['yearly_projections']
                print(f"✅ LLM年間データ処理: {len(yearly_data)}年分")
                
                if len(yearly_data) < 5:
                    print(f"⚠️ 年間データ不足: {len(yearly_data)}年分のみ - 計算ベースを使用")
                    return fallback_data
                
                llm_years = []
                
                # 最大65年分のデータを処理
                for i in range(min(65, len(yearly_data))):
                    year_data = yearly_data[i] if i < len(yearly_data) else {}
                    
                    try:
                        # 基本年情報
                        year_num = int(year_data.get('year', i + 1))
                        primary_age = int(year_data.get('age', current_age + i))
                        
                        # 配偶者・子供の年齢計算
                        spouse_age = None
                        if family_info.get('hasSpouse') and family_info.get('spouseAge'):
                            spouse_age = family_info['spouseAge'] + i
                        
                        child_ages = []
                        for child in family_info.get('children', []):
                            child_ages.append(child['age'] + i)
                        
                        # 財務データの安全な変換
                        def safe_convert(value, multiplier=10000, default=0):
                            """安全な数値変換"""
                            try:
                                if isinstance(value, str):
                                    # 文字列の場合は数値部分を抽出
                                    import re
                                    numbers = re.findall(r'[\d.]+', value)
                                    if numbers:
                                        value = float(numbers[0])
                                    else:
                                        return default
                                return float(value) * multiplier
                            except (ValueError, TypeError):
                                return default
                        
                        annual_income = safe_convert(year_data.get('annual_income', 0))
                        annual_expenses = safe_convert(year_data.get('annual_expenses', 0))
                        cash_flow = safe_convert(year_data.get('cash_flow', 0))
                        savings_balance = safe_convert(year_data.get('savings_balance', 0))
                        
                        # 特別イベントの処理
                        special_events = year_data.get('special_events', [])
                        if isinstance(special_events, str):
                            special_events = [special_events]
                        elif not isinstance(special_events, list):
                            special_events = []
                        
                        llm_year = {
                            'year': year_num,
                            'primary_age': primary_age,
                            'spouse_age': spouse_age,
                            'child1_age': child_ages[0] if len(child_ages) > 0 else None,
                            'child2_age': child_ages[1] if len(child_ages) > 1 else None,
                            'total_income': annual_income,
                            'primary_income': annual_income,
                            'primary_pension': None,
                            'spouse_income': None,
                            'home_loan_deduction': None,
                            'total_expense': annual_expenses,
                            'living_expenses': annual_expenses * 0.6,  # 推定60%
                            'housing_expenses': annual_expenses * 0.2,  # 推定20%
                            'loan_repayment': 0,
                            'insurance_total': annual_expenses * 0.1,  # 推定10%
                            'life_insurance': 0,
                            'endowment_insurance': 0,
                            'ideco_contribution': 0,
                            'vehicle_expenses': 0,
                            'hobby_lessons': 0,
                            'tax_expenses': annual_expenses * 0.1,  # 推定10%
                            'child_education': None,
                            'home_renovation': None,
                            'travel_expenses': None,
                            'annual_balance': cash_flow,
                            'cash_balance': savings_balance,
                            'llm_notes': year_data.get('advisor_notes', '')[:100] if year_data.get('advisor_notes') else '',  # 100文字制限
                            'special_events': special_events[:3]  # 最大3イベント
                        }
                        llm_years.append(llm_year)
                        
                    except Exception as ye:
                        print(f"⚠️ 年間データ処理エラー (年{i+1}): {ye}")
                        # フォールバックデータで補完
                        if i < len(fallback_data):
                            llm_years.append(fallback_data[i])
                        else:
                            # 基本的なデータ構造を作成
                            llm_years.append({
                                'year': i + 1,
                                'primary_age': current_age + i,
                                'spouse_age': spouse_age,
                                'child1_age': child_ages[0] if len(child_ages) > 0 else None,
                                'child2_age': child_ages[1] if len(child_ages) > 1 else None,
                                'total_income': 0,
                                'primary_income': 0,
                                'total_expense': 0,
                                'annual_balance': 0,
                                'cash_balance': 0,
                                'llm_notes': '',
                                'special_events': []
                            })
                
                print(f"🎯 LLM詳細データ作成成功: {len(llm_years)}年分")
                if llm_years:
                    sample = llm_years[0]
                    print(f"📈 初年度サンプル: 年収{sample['total_income']/10000:.0f}万円, 支出{sample['total_expense']/10000:.0f}万円")
                
                return llm_years
                
            except Exception as e:
                print(f"🚨 LLM年間データ作成エラー: {e}")
                import traceback
                print(traceback.format_exc())
                return fallback_data

        # LLMベースの年間データを作成
        final_years_data = create_llm_years_data(llm_lifeplan, years_data)
        
        # 新しい構造のライフプランデータ（LLM分析付き）
        lifeplan_data = {
            'customer_name': '顧客様',
            'family_type': 'family' if family_info.get('hasSpouse') else 'single',
            'years_data': final_years_data,
            'chart_summary': chart_summary,
            'llm_analysis': lifeplan_analysis,
            'llm_lifeplan': llm_lifeplan,  # LLMの完全なライフプランデータ
            'advisor_info': {
                'prompt_title': selected_prompt['title'] if selected_prompt else 'デフォルト',
                'prompt_description': selected_prompt['description'] if selected_prompt else 'システム標準の分析',
                'parameters_used': advisor_params
            }
        }
        
        cache_data = await load_json(f"data/lifeplan_{current_user.id}.json", {})
        cache_data[datetime.now().isoformat()] = lifeplan_data
        await save_json(f"data/lifeplan_{current_user.id}.json", cache_data)
        
        return JSONResponse(
            content={
                "success": True,
                "message": "ライフプランシミュレーションが生成されました",
                "lifeplan_data": lifeplan_data
            },
            status_code=200
        )
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ライフプランシミュレーション生成エラー: {e}")
        print(error_details)
        raise HTTPException(
            status_code=500,
            detail=f"ライフプランシミュレーションの生成中にエラーが発生しました: {str(e)}"
        )

@router.get("/get-lifeplan")
async def get_lifeplan(
    current_user: User = Depends(get_current_user)
):
    try:
        lifeplan_data = await load_json(f"data/lifeplan_{current_user.id}.json", {})
        if not lifeplan_data:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "ライフプランデータが見つかりません。まず財務情報を送信してください"
                },
                status_code=404
            )
        
        return JSONResponse(
            content={
                "success": True,
                "lifeplan_data": lifeplan_data
            },
            status_code=200
        )
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"エラーが発生しました: {str(e)}"
        )
            