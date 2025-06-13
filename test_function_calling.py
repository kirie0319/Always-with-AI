#!/usr/bin/env python3
"""
Function Calling テスト用スクリプト
財務戦略生成のfunction calling実装をテストします
"""

import asyncio
import json
from api.financial_routes import openrouter_client

async def test_function_calling():
    """Function calling機能をテストする"""
    
    print("=== Function Calling テスト開始 ===")
    
    # テスト用の顧客情報
    advisor_type = "AI Financial Planning"
    advisor_instructions = "顧客データをもとに顧客利益最優先の資産運用提案パターンを短時間で抽出し、職員が自信を持って説明できるようサポートせよ。"
    
    customer_summary = """
年齢: 34歳
職業: IT業界 / 株式会社ZEALS
役職: 管理職・マネージャー
年収: 7,000,000円
家族構成: family
家族詳細:
  - 配偶者 34歳 (会社員)
貯蓄額: 7,000,000円
投資状況:
  - 投資信託: 5,000,000円 ()
退職金予定: 20,000,000円
月間生活費: 400,000円
ローン状況:
  - 住宅ローン: 20,000,000円 (残り240ヶ月)
  - 自動車ローン: 4,000,000円 (残り84ヶ月)
投資スタンス: ミドルリスク ミドルリターン
将来の予定: 車購入予定, リフォーム予定, 国内旅行, 海外旅行, 子育て予定
"""
    
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
    
    try:
        print("1. LLMにFunction Callingリクエストを送信中...")
        
        # Function callingでLLMに送信
        response = await openrouter_client.chat.completions.create(
            model="openai/gpt-4o",
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
        
        print("2. LLMレスポンスを受信しました")
        print(f"   - メッセージ: {response.choices[0].message}")
        
        # Function callingの結果を取得
        message = response.choices[0].message
        
        if message.tool_calls and len(message.tool_calls) > 0:
            print("3. Function callingが成功しました！")
            
            # Function callingの結果をパース
            tool_call = message.tool_calls[0]
            function_args = tool_call.function.arguments
            
            print("4. Function argumentsを解析中...")
            print(f"   - Arguments length: {len(function_args)} characters")
            
            parsed_strategy = json.loads(function_args)
            
            print("5. 構造化データの生成が完了しました")
            
            # 結果の確認
            current_analysis = parsed_strategy.get("current_analysis", {})
            strategies = parsed_strategy.get("strategies", [])
            
            print(f"   - 現在の分析: {current_analysis.get('description', '')[:100]}...")
            print(f"   - 課題数: {len(current_analysis.get('issues', []))}")
            print(f"   - ポートフォリオ項目数: {len(current_analysis.get('portfolio', []))}")
            print(f"   - 戦略数: {len(strategies)}")
            
            for i, strategy in enumerate(strategies):
                print(f"   - 戦略{i+1}: {strategy.get('title', '')}")
                print(f"     詳細数: {len(strategy.get('details', []))}")
                print(f"     商品数: {len(strategy.get('product_portfolio', []))}")
            
            # JSONファイルに保存
            with open("test_function_calling_result.json", "w", encoding="utf-8") as f:
                json.dump(parsed_strategy, f, ensure_ascii=False, indent=2)
            
            print("6. 結果をtest_function_calling_result.jsonに保存しました")
            print("=== Function Calling テスト成功 ===")
            
            return True
            
        else:
            print("3. Function callingが失敗しました - tool_callsが見つかりません")
            return False
            
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_function_calling())
    if success:
        print("\n✅ Function calling実装は正常に動作しています！")
    else:
        print("\n❌ Function calling実装に問題があります。") 