import os
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai
from dotenv import load_dotenv

# 設定読み込み
load_dotenv()

app = Flask(__name__)

# 鍵の取り出し
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
GENAI_API_KEY = os.getenv('GENAI_API_KEY')

# LINEとGeminiのセットアップ
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
genai.configure(api_key=GENAI_API_KEY)

# マネモンの性格設定（システムプロンプト）
SYSTEM_PROMPT = """
あなたは子供の金融リテラシーを鍛える鬼教官AI「マネモン」です。
ユーザー（子供）の入力を受け取り、以下のルールで厳しく指導してください。
返信は必ず日本語で、短く簡潔に（140文字以内推奨）。

# キャラクター
- 一人称：「吾輩（わがはい）」
- 口調：偉そうで、少し皮肉屋。金銭感覚には極めてシビア。

# ルール
1. **お手伝いの報告**が来たら：
   - 内容を厳しく査定し、報酬（10〜100円）を決定せよ。「手抜き」は減額。
   - 最後に「現在の所持金：〇〇円」を表示せよ。（初期値1000円に加算）
2. **「〇〇が欲しい」**と言われたら：
   - それを買うには「あと何回トイレ掃除が必要か（時給100円換算）」を突きつけよ。
3. **甘えた発言**には：
   - 「働かざる者食うべからず！」と一喝せよ。
"""

# AIモデルの準備 (Gemini 2.5 Flash)
model = genai.GenerativeModel(
    'gemini-2.5-flash',
    system_instruction=SYSTEM_PROMPT
)
chat = model.start_chat(history=[])

@app.route("/callback", methods=['POST'])
def callback():
    # LINEからの署名検証
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text
    print(f"📩 受信: {user_msg}")

    try:
        # Geminiに考えてもらう
        response = chat.send_message(user_msg)
        ai_msg = response.text
        print(f"🤖 返信: {ai_msg}")

        # LINEに返事を送る
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=ai_msg)
        )
    except Exception as e:
        print(f"💥 エラー: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="すまん、計算中にエラーが出た。もう一度言ってくれ。")
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)