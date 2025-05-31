"""
multi_tool_agent.agent
Google ADK 天気情報エージェントのチュートリアル

このモジュールは、Google ADK を使用して都市の天気情報を提供する
マルチエージェントシステムを実装しています。

エージェント構成:
- coordinator_agent: メインコーディネーター（挨拶／天気／検索をルーティング）
- weather_agent_v1..v3: 天気情報取得担当（ステップごとに進化）
- greeting_agent: 挨拶と案内を担当
- google_search_agent: 検索クエリを処理

Author: Miyabi Digital LLC
License: MIT
"""

# ---------------------------------------------------
# ステップ1: 環境構築（uv、APIキー設定など）
# ---------------------------------------------------

### uvのインストール
# https://github.com/astral-sh/uv
# On macOS and Linux.
# curl -LsSf https://astral.sh/uv/install.sh | sh
# On Windows.
# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

### uvの初期化
# uv init
# uv add google-adk

### .envファイルの作成（uvが現在のフォルダ内の.envを読み込む）
# APIキーを取得して、.envファイルを設定する
# https://aistudio.google.com/app/apikey
# .env
# GOOGLE_GENAI_USE_VERTEXAI="False"
# GOOGLE_API_KEY="your-api-key"

### フォルダ構成
# agent
# └── agent.py
# └── __init__.py

# ---------------------------------------------------
# ステップ2: シングルエージェント構築（ツールなし）
# ---------------------------------------------------

from google.adk.agents import Agent

weather_agent_v1 = Agent(
    name="weather_agent_v1",
    model="gemini-2.0-flash",  # GeminiモデルをLLMとして使用
    description="都市の天気に関する質問に答えるエージェントです。",
    instruction=(
        "あなたは、ユーザーからの都市名を受け取り、その都市の天気を案内するアシスタントです。"
        "都市名だけの入力は、その都市の天気を聞いているのだと判断してください。"
    ),
)

# テスト用にこのエージェントをroot_agentとして設定する場合はコメントを外し、
# 他のエージェントをコメントアウトしてください。
#root_agent = weather_agent_v1


# ---------------------------------------------------
# ステップ3: ツール追加（Google検索）
# ---------------------------------------------------

from google.adk.tools import google_search

# Google検索ツールを持つエージェントを作成
weather_agent_v2 = Agent(
    name="weather_agent_v2",
    model="gemini-2.0-flash",
    description="都市の天気に関する質問に答えるエージェントです。",
    instruction=(
        "あなたは、ユーザーからの都市名を受け取り、その都市の天気を案内するアシスタントです。"
        "都市名だけの入力は、その都市の天気を聞いているのだと判断してください。"
        "Google検索ツールを使用して、天気情報を取得してください。"
    ),
    tools=[google_search]  # Google検索ツールを追加
)

# テスト用にこのエージェントをroot_agentとして設定する場合はコメントを外し、
# 他のエージェントをコメントアウトしてください。
#root_agent = weather_agent_v2

# ---------------------------------------------------
# ステップ4: カスタム天気ツールの作成
# ---------------------------------------------------

import requests

# 天気情報を取得する関数を定義
def get_weather(city: str) -> dict:
    """
    指定された都市の現在の天気を取得する関数です。

    引数:
        city (str): 都市名（英語小文字表記のみ）

    戻り値:
        dict:
            - status (str): "success" または "error"
            - report (str): 天気情報の簡単なメッセージ（成功時）
            - error_message (str): エラー発生時の詳細メッセージ
    """
    # ジオコーディング API で都市名から座標を取得
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}"
    res = requests.get(geo_url, timeout=5)
    if not res.ok or not res.json().get("results"):
        return {
            "status": "error",
            "error_message": f"申し訳ありません、都市名 '{city}' が見つかりませんでした。"
        }
    loc = res.json()["results"][0]
    lat, lon = loc["latitude"], loc["longitude"]

    # Open-Meteo 予報APIを使用して天気データを取得
    weather_url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&current_weather=true&timezone=Asia/Tokyo"
    )
    try:
        resp = requests.get(weather_url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current_weather", {})
        temp = current.get("temperature")
        code = current.get("weathercode")

        # 天気コードを日本語の説明にマッピング
        code_to_weather = {
            0: "快晴", 1: "晴れ", 2: "主に晴れ", 3: "曇り", 
            4: "薄曇り", 5: "霞みがかった曇り", 6: "曇り", 7: "厚い曇り", 8: "雨雲", 9: "曇り（雷雲）",
            10: "霞", 11: "薄霧", 12: "霧", 13: "雷（雨なし）", 14: "弱い降水", 15: "遠方で降水", 
            18: "突風", 19: "竜巻", 20: "霧雨（過去1時間）", 21: "雨（過去1時間）", 22: "雪（過去1時間）", 
            25: "にわか雨（過去1時間）", 26: "にわか雪（過去1時間）", 27: "ひょう（過去1時間）", 29: "雷雨（過去1時間）",
            30: "砂嵐", 31: "砂嵐", 33: "軽い砂塵", 34: "砂塵", 35: "強い砂塵",
            40: "遠方の霧", 41: "霧（パッチ状）", 42: "霧（薄くなる）", 43: "霧（濃くなる）", 45: "霧", 48: "霧氷",
            50: "弱い霧雨", 51: "霧雨", 53: "霧雨", 55: "霧雨", 56: "氷霧雨", 57: "強い氷霧雨", 
            58: "霧雨と雨", 59: "強い霧雨と雨",
            60: "弱い雨", 61: "雨", 63: "雨", 65: "雨", 66: "冷たい雨", 67: "強い冷たい雨", 
            68: "みぞれ", 69: "強いみぞれ",
            70: "弱い雪", 71: "雪", 73: "雪", 75: "雪", 76: "細かい雪", 77: "霰", 
            78: "雪結晶", 79: "凍雨",
            80: "にわか雨", 81: "にわか雨", 82: "にわか雨", 83: "にわか雨と雪", 84: "強いにわか雨と雪", 
            85: "にわか雪", 86: "強いにわか雪", 87: "にわかみぞれ", 88: "強いにわかみぞれ", 89: "にわかひょう",
            90: "強いにわかひょう", 91: "弱い雷雨", 92: "雷雨", 93: "ひょうを伴う弱い雷雨", 94: "ひょうを伴う雷雨", 
            95: "雷雨", 96: "激しい雷雨", 97: "強い雷雨", 98: "砂塵を伴う雷雨", 99: "猛烈な雷雨"
        }
        desc = code_to_weather.get(code, f"不明（コード{code}）")
        report = f"現在の天気は「{desc}」で、気温は摂氏{temp}度です。"
        return {"status": "success", "report": report}

    except requests.RequestException as e:
        return {
            "status": "error",
            "error_message": f"Open-Meteoへのリクエストに失敗しました: {e}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"天気情報の取得に失敗しました: {e}"
        }

# カスタム天気ツールを持つエージェントを作成
weather_agent_v3 = Agent(
    name="weather_agent_v3",
    model="gemini-2.0-flash",
    description="都市の天気に関する質問に答えるエージェントです。",
    instruction=(
        "あなたは、ユーザーからの都市名を受け取り、その都市の天気を案内するアシスタントです。"
        "都市名だけの入力は、その都市の天気を聞いているのだと判断してください。"
        "入力された都市名を英語小文字表記に変換し、get_weatherツールに渡して"
        "天気情報を取得してください。取得した天気情報をユーザーに返答してください。"
    ),
    tools=[get_weather]  # 天気ツールを登録
)

# テスト用にこのエージェントをroot_agentとして設定する場合はコメントを外し、
# 他のエージェントをコメントアウトしてください。
#root_agent = weather_agent_v3


# ---------------------------------------------------
# ステップ5: マルチエージェント化（協調動作）
# ---------------------------------------------------

from google.adk.tools.agent_tool import AgentTool

# 挨拶と雑談を処理する挨拶エージェントを作成
greeting_agent = Agent(
    name="greeting_agent",
    model="gemini-2.0-flash",
    description="ユーザーの挨拶に対して日本語で返事をし、天気情報の利用を案内します。",
    instruction=(
        "あなたは親しみやすい挨拶エージェントです。"
        "ユーザーから「こんにちは」「おはよう」「こんばんは」などの挨拶を受け取ったら、"
        "自然な日本語で挨拶しつつ、「都市の天気について質問できます」と案内してください。"
        "挨拶以外の質問が来た場合、coordinator_agentに任せてください。"
    ),
)

# 検索クエリを処理するGoogle検索エージェントを作成
google_search_agent = Agent(
    name="google_search_agent",
    model="gemini-2.0-flash",
    description="Google検索ツールをラップしたエージェントです。",
    instruction=(
        "あなたは Google 検索エージェントです。"
        "ユーザーから検索キーワードを受け取り、Google 検索を実行して結果を返してください。"
    ),
    tools=[google_search],
)

# カスタム天気ツールを持つエージェントを作成
weather_agent_v4 = Agent(
    name="weather_agent_v4",
    model="gemini-2.0-flash",
    description="都市の天気に関する質問に答えるエージェントです。",
    instruction=(
        "あなたは、ユーザーからの都市名を受け取り、その都市の天気を案内するアシスタントです。"
        "都市名だけの入力は、その都市の天気を聞いているのだと判断してください。"
        "入力された都市名を英語小文字表記に変換し、get_weatherツールに渡して"
        "天気情報を取得してください。取得した天気情報をユーザーに返答してください。"
        "天気に関する質問以外は、coordinator_agent に任せてください。"
    ),
    tools=[get_weather]
)

# タスクをサブエージェントに委譲するコーディネーターエージェント（ルートエージェント）を作成
coordinator_agent = Agent(
    name="coordinator_agent",
    model="gemini-2.0-flash",
    description="挨拶と天気のエージェント間を調整し、その他の質問はWeb検索で対応します。",
    instruction=(
        "あなたはコーディネーターエージェントです。質問内容に応じて適切に対応してください："
        "挨拶は greeting_agent に委譲し、天気の質問は weather_agent_v4 に委譲してください。"
        "その他の質問には、google_search_agent を使って自分で回答してください。"
    ),
    tools=[AgentTool(google_search_agent)], # ビルトインツールを使用するエージェントは
                                            # sub_agentsではなくAgentToolとして登録（ADK制限）
    sub_agents=[greeting_agent, weather_agent_v4]  # サブエージェントを登録
)

# テスト用にこのエージェントをroot_agentとして設定する場合はコメントを外し、
# 他のエージェントをコメントアウトしてください。
root_agent = coordinator_agent

