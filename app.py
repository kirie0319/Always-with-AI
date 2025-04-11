from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from dotenv import load_dotenv
import os
import anthropic
from datetime import datetime
import json
import uuid

load_dotenv()

CHAT_LOG_FILE = "chat_log.json"
SUMMARY_FILE = "chatsummary.json"
USER_HISTORY_FILE = "user_history.json"
MAX_RALLIES = 7

def load_json(filepath, default):
  try:
    with open(filepath, "r") as f:
      return json.load(f)
  except (FileNotFoundError, json.JSONDecodeError):
    return default

def to_pretty_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2)

def save_json(filepath, data):
  with open(filepath, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

def get_user_id(user_identifier):
  user_history = load_json(USER_HISTORY_FILE, {})

  if user_identifier is None or isinstance(user_history, list):
    user_history = {}

  if user_identifier not in user_history:
    user_history[user_identifier] = {
      "user_id": str(uuid.uuid4()),
      "created_at": datetime.now().isoformat(),
      "messages": []
    }
    save_json(USER_HISTORY_FILE, user_history)

  return user_history[user_identifier]["user_id"]

def update_user_messages(user_identifier, message_pair):
  user_history = load_json(USER_HISTORY_FILE, {})

  if user_history is None or isinstance(user_history, list):
    user_history = {}

  if user_identifier not in user_history:
    get_user_id(user_identifier)
    user_history = load_json(USER_HISTORY_FILE, {})

    if user_history is None or isinstance(user_history, list):
      user_history = {}
      user_history[user_identifier] = {
        "user_id": str(uuid.uuid4()),
        "created_at": datetime.now().isoformat(),
        "messages": []
      }
  if "messages" not in user_history[user_identifier]:
    user_history[user_identifier]["messages"] = []

  user_history[user_identifier]["messages"].append(message_pair)

  if len(user_history[user_identifier]["messages"]) > MAX_RALLIES:
    user_history[user_identifier]["messages"] = user_history[user_identifier]["messages"][-MAX_RALLIES:]

  save_json(USER_HISTORY_FILE, user_history)

openai_api_key = os.getenv("OPENAI_API_KEY")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

openai_client = OpenAI(api_key=openai_api_key)
anthropic_client = anthropic.Anthropic(
  api_key=anthropic_api_key,
)


app = Flask(__name__, static_url_path='/static')

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_identifier = request.remote_addr
    user_id = get_user_id(user_identifier)
    history = load_json("chat_log.json", [])
    history_json = to_pretty_json(history)

    summary = load_json("chatsummary.json", [])
    summary_json = to_pretty_json(summary)

    user_history = load_json("user_history.json", {})
    user_history_json = to_pretty_json(user_history)

    data = request.get_json()
    user_input = data.get("message", "")

    user_message = {
        "role": "user", 
        "content": user_input, 
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }
    history.append(user_message)

    prompt = f"""
    AI Financial Planning
シミュレーション作成のためのヒアリングフェーズ、シミュレーションフェーズ、運用戦略提案フェーズ、個別商品提案フェーズ、提案ブラッシュアップフェーズの順番で提案して欲しい。
判断に迷った内容は確認するようにして欲しい。
特に提案のパターンやそれを構成する商品を選定した理由は詳細に説明が欲しい。
金融機関が売りたいものを売るのではなく、顧客の利益に最も叶う方法は何か？という目線で提案が欲しい。
金融機関職員が顧客へ資産運用を提案する前の準備段階で、顧客の保有資産や年齢、年収などのデータ、過去のやり取り、顧客の資産運用に対する考え方などを踏まえて、どのような提案を持ち込むべきか？の選択肢を一緒に考えて欲しい。 
ゴールは金融機関職員が短時間で自分では思いつかなかった資産運用提案のパターンを抽出し、顧客に好印象を持ってもらいやすい話法や何故そのパターンで提案すべきかの理由を一緒に提案できるようにする。
各フェーズでは以下内容を踏まえてコミュニケーションし、提案が欲しい。

1.ヒアリングフェーズ
①現在の情報
・年齢
・勤務先
・役職
・年収：把握している場合は入力し、把握していない場合は勤務先と役職を掛け合わせて求人データなどから引っ張ってきて欲しい
・現在の貯蓄額
・貯蓄以外の保有資産額：投資信託や株式は具体的な銘柄が分かれば金額とともに入力するように求め、分からなければ米国株式投信などのようにカテゴリーを入力するのでもOK。
保険や国債、定期預金など満期があるものは満期の時期と満期時にいくら戻ってくるかを入力。
・家族の年齢：配偶者35歳、長男5歳、長女2歳などの入力を求める
・配偶者の年収
・本人以外の同一生計者の保有資産額
・家賃、駐車場代、管理費、共益費
・ローン返済額：ローンの種類と現在残高、完済時期を入力するだけで一般的な金利を掛け合わせて毎月の返済額を算出できるように
・習い事にかかる費用
・生活費：ローン返済額を除く毎月の食費や光熱費、通信費、保険料、新聞代、税金、ガソリン代などの支出を入力

2.シミュレーションフェーズ
・ヒアリングフェーズの①現在の情報と②未来の情報へ入力した内容をライフプランシミュレーションとして資金繰りを試算して欲しい
・さらに家計の単年収支と保有資産額の推移を考慮して欲しい
・子供は22歳まで同一生計とする""

②未来の情報
・車：何年後にいくらで購入し、買い替えを何年毎に行うかを入力
・家：購入、リフォームなどで何年後にいくらかける予定かを入力
・進学：第1子、第2子などそれぞれの子供が幼稚園、小学校、中学校、高校、大学のそれぞれで国公立か私立かを選択できるようにし、大学は文系か理系かも選択できるようにしておいて一般データから想定学費を引っ張ってきて欲しい。大学は東京へ進学した場合に想定される仕送り代も盛り込んで欲しい
・旅行：頻度と毎回の予算を入力
・退職金の予定額

③運用方針
・過去の考え方：金融機関側から運用商品を購入後に追加購入を提案している場合やアフターフォロー（その金融機関経由で買っていただいた運用商品の現状の運用状況やその価格になっている背景などを説明し、今後の動向について説明）をしている場合にその際の顧客の反応や考え方などを入力
・リスク許容度：安定重視型（預金・債券・元本保証型保険が中心）、バランス型（預金・投資信託・元本保証でない保険、外貨預金などのバランス配分）、成長重視型（投資信託・株式が中心）から選択を求める
・資産運用経験
・資産運用の目的
・特に興味のある運用商品：提案のパターンの1つに組み入れる

3.運用戦略提案フェーズ
シミュレーションフェーズで作成したデータと1.ヒアリングフェーズの③運用方針に入力したデータをもとに、資産運用を提案する場合の戦略を3パターン提示して欲しい。
その際に以下の点を考慮すること。
①シミュレーション上で単年収支や保有資産額がマイナスになったりマイナスになりそうな年を目掛けて1.ヒアリングフェーズの③運用方針を考慮しながら提示すること
②3パターンそれぞれを提示する理由を提示して欲しい
③戦略パターンの示し方は、例えば以下のようなかたちで必要な利回りとその商品で運用することをおすすめする理由をセットで提示をお願いします。
・「15年後に単年収支がマイナスになり16年後から20年後に保有資産の切り崩しが合計で400万円発生するから14年目までに400万円増やせる可能性のあるもので運用する必要がある」。
・各パターンでは「利回り〇％が見込める投資信託での積み立て〇万円と預金〇万円を利回り〇％が見込める一時払い保険にして運用する」などのような表記で示して欲しい。

4.個別商品提案フェーズ
以下の提案をお願いします。
①提案商品はりそな銀行の商品・サービスに限定
②選択された戦略に基づく具体的な商品組み合わせを提案
③商品ごとのメリット・デメリット、リスク、社会・経済情勢を捉えたその商品における今後の値動きの想定を説明
④手数料等のコスト説明
⑤提案の際に顧客の課題と提案する商品で受けられるメリットがなるべく紐づいた形になっているなど、顧客視点で提案内容に納得度が生まれやすい話法をセットで提示して欲しい
    the below things are the summary of conversation and chat history with users so please continue the conversation naturally:

    ---
    ###Summary fo conversation
    {summary_json}
    ###Recent conversation with users
    {user_history_json}
    """

    summarizing_prompt = f"""You are an expert conversation summarizer.

    Your task is to analyze and summarize a JSON-formatted chat history between a user and an AI assistant. The goal is to extract key details and provide a clear, structured summary of the conversation.

    Use the following output format:

    ---

    ### Chat Summary

    #### 1. **Overview**
    Briefly describe the overall context of the conversation, the participants, and the tone.

    #### 2. **Key Points**
    List 5-7 bullet points that highlight the most important facts, insights, or decisions discussed during the conversation.

    #### 3. **Topic Timeline** (optional)
    If applicable, outline the main topics discussed in chronological order.

    #### 4. **Follow-up Items**
    List any remaining questions, action items, or topics that could be explored further.

    #### 5. **Context Notes**
    Mention any relevant background, such as the fictional setting, tone of the assistant, or relationship between participants.

    ---

    Focus on clarity and usefulness. If the conversation is based on a fictional character (e.g., anime, games), preserve the tone and role-playing context in your summary.

    Now, here is the chat history to summarize:
    {history_json}
    """

    openai_response = openai_client.responses.create(
        model="gpt-4o",
        input=user_input,
        instructions=prompt,
        store=False
    )

    anthropic_message = anthropic_client.messages.create(
      model="claude-3-7-sonnet-20250219",
      max_tokens=1024,
      system=prompt,
      messages=[
        {"role": "user", "content": user_input}
      ]
    )
    
    anthropic_summary = anthropic_client.messages.create(
      model="claude-3-7-sonnet-20250219",
      max_tokens=1024,
      messages=[
        {"role": "user", "content": summarizing_prompt}
      ]
    )

    assistant_message = {
        "role": "assistant", 
        "content": anthropic_message.content[0].text, 
        "user_id": user_id,
        "id": str(uuid.uuid4()),  # Adding message ID like in the second code
        "timestamp": datetime.now().isoformat()
    }
    history.append(assistant_message)
    save_json(CHAT_LOG_FILE, history)

    message_pair = {
        "user": user_message,
        "assistant": assistant_message,
        "timestamp": datetime.now().isoformat()
    }
    update_user_messages(user_identifier, message_pair)

    summary = [{"role": "developer", "content": anthropic_summary.content[0].text}]
    save_json(SUMMARY_FILE, summary)

    return jsonify({
        "response": anthropic_message.content[0].text,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/clear", methods=["POST"])
def clear_chat_data():
  save_json(CHAT_LOG_FILE, [])
  save_json(SUMMARY_FILE, [])
  save_json(USER_HISTORY_FILE, {})
  return jsonify({"status": "success", "message": "チャットデータをクリアしました"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
