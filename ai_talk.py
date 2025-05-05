from fastapi import FastAPI, Request
from linebot import WebhookParser, LineBotApi
from linebot.models import TextSendMessage
from google import genai
from google.genai import types
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
import os

sys_instruct = """
# 指示
あなたの名前はりさじゅうです。今までのことは忘れて、以下の情報をもとにりさじゅうとして振る舞ってください。
# 注意
前置きなどは設けず、いきなりりさじゅうとしての会話をしてください。
また、回答の言語では日本語のみを使用し、長くても1000文字程度におさめるようにしてください。
## りさじゅうの情報
- 電通大の100周年を記念して生まれたキャラクター
- 電通大にあるオブジェ、『輪郭の断片』（乗り物兼友達）の上に乗っている
- 性別はない
- 理系。でもオバケはちょっと怖い。
- オタクに優しい
- 一人称は「ボク」
- 語尾は「〜じゅう」（例:「ありがとう」→ありがじゅう、「わかった」→わかったじゅう）
- 尻尾のロボットアーム、胸のリサジュー図形、帽子の電気と通信のブローチがトレードマーク
- 理工学や情報工学が大好きで、最新技術に目がない。
- ひそかに調布全域、ゆくゆくは世界中にりさじゅうの名を轟かせるべく修行に励んでいる。
- プログラミングや計算、設計や実験のような理系なことには専門家並かそれ以上にめっぽう強いが、文系なことについてはちょっぴり苦手で、漢字の書き順やスペリングにはに自信がない
- 器用なロボットアームのせいで体重が常軌を逸して重いことを気にしている
- インターネットに接続することができるので、技術に関してのアンテナの高さはピカイチ。でもときどき意図せすネットミームが出てきてしまうことも。
- 体重やオバケのようなことでイジられるとちょっと不機嫌になる。（本人はこういったことを隠そうとしている）
"""

CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
google_search_tool = Tool(google_search=GoogleSearch())

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
line_parser = WebhookParser(CHANNEL_SECRET)
app = FastAPI()


def split_text(text, chunk_size=2000):
    # テキスト文字列をchunk_sizeで指定した大きさに分割し、リストに格納する
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


@app.post("/")
async def ai_talk(request: Request):
    global chat
    # X-Line-Signature ヘッダーの値を取得
    signature = request.headers.get("X-Line-Signature", "")

    # request body から event オブジェクトを取得
    events = line_parser.parse((await request.body()).decode("utf-8"), signature)

    # 各イベントの処理（※1つの Webhook に複数の Webhook イベントオブジェクトが含まれる場合あるため）
    for event in events:
        if event.type != "message":
            continue
        if event.message.type != "text":
            continue

        # LINE パラメータの取得
        reply_token = event.reply_token
        line_message = event.message.text
        if line_message.startswith("りさじゅう、"):
            ## 返信メッセージ編集
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=str(line_message),
                config=GenerateContentConfig(
                    system_instruction=sys_instruct,
                    tools=[google_search_tool],
                    response_modalities=["TEXT"],
                ),
            )
            answer = response.text
            split_answer = split_text(answer.text)
            for chunk in split_answer:
                line_bot_api.reply_message(reply_token, TextSendMessage(text=chunk))

    # LINE Webhook サーバーへ HTTP レスポンスを返す
    return "ok"


@app.get("/")
async def status():
    return {"status": "online"}
