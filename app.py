from flask import Flask, render_template, request, jsonify, session
import json
import random
import os
from google import genai
from google.genai import types

app = Flask(__name__)
# 這是為了維護 Session 安全，請保持這行設定
app.secret_key = "secret_key_for_session"

# 從系統環境變數讀取 API Key (部署到 Render 時，請在 Render 後台設定此變數)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

game_story = """
{
  "stages": [
    {"id": 1, "task": "玄關晚歸", "speech": "你還知道要回來啊？現在幾點了？全家都在等你！"},
    {"id": 2, "task": "客廳電燈", "speech": "跟你講過幾次？進屋隨手關燈！家裡開銀行的喔？"},
    {"id": 3, "task": "餐桌手機", "speech": "坐下來還在滑手機！手機會餵你吃飯喔？收起來！"},
    {"id": 4, "task": "晚餐遲到", "speech": "這菜都涼了，喊你十分鐘才出來，還要人請幾次？"},
    {"id": 5, "task": "廚房洗碗", "speech": "吃完碗就丟桌上？這家裡只有我是傭人是不是？"},
    {"id": 6, "task": "巷口垃圾", "speech": "垃圾車來了啦！還在那邊看電視？還不快點去追！"},
    {"id": 7, "task": "換裝見人", "speech": "穿這什麼破爛牛仔褲？等下親戚要來，你不嫌丟臉喔？"},
    {"id": 8, "task": "房間整理", "speech": "看你這房間，豬窩都比你乾淨！到底什麼時候要清？"},
    {"id": 9, "task": "開箱包裹", "speech": "這包裹又是什麼？整天買這些沒用的垃圾，錢多喔？"},
    {"id": 10, "task": "深夜水果", "speech": "蘋果切好了啦，吃一吃快點去睡覺，別再熬夜了。"}
  ]
}
"""
STAGES = json.loads(game_story)["stages"]

def call_gemini_api(stage_task, parent_speech, user_reply, current_anger):
    system_instruction = """
    你正在扮演家長怒氣生存遊戲中的長輩。性格硬核、不講理、擅長情緒勒索。
    請嚴格根據場景主題大罵，並給予評分：
    1.【頂嘴反抗】+15~25；
    2.【找藉口】+5~15；
    3.【明確道歉/認錯】必須給 -20~-40。
    JSON格式: {"parent_comeback": "...", "anger_change": 10}
    """
    prompt = f"{system_instruction}\n主題:{stage_task}\n上句:{parent_speech}\n孩子說:{user_reply}\n目前怒氣:{current_anger}"
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text.strip())
    except:
        return {"parent_comeback": "『你現在是裝聾作啞，不說話是什麼意思？』", "anger_change": 10}

@app.route("/")
def index():
    session["stage_idx"] = 0
    session["anger"] = 80
    session["current_speech"] = STAGES[0]["speech"]
    return render_template("index.html")

@app.route("/api/change_stage", methods=["POST"])
def change_stage():
    new_idx = request.json.get("stage_idx", 0)
    session["stage_idx"] = new_idx if 0 <= new_idx < len(STAGES) else 0
    session["anger"] = 80
    session["current_speech"] = STAGES[session["stage_idx"]]["speech"]
    return jsonify({"parent_speech": session["current_speech"], "anger": 80, "stage_task": STAGES[session["stage_idx"]]["task"]})

@app.route("/api/reply", methods=["POST"])
def reply():
    user_reply = request.json.get("reply", "").strip()
    ai_result = call_gemini_api(STAGES[session["stage_idx"]]["task"], session["current_speech"], user_reply, session["anger"])
    
    score = ai_result.get("anger_change", 10)
    
    # 強制道歉降火機制
    if any(k in user_reply.lower() for k in ["對不起", "抱歉", "我錯", "歹勢", "sorry"]):
        score = -30

    session["anger"] = max(0, min(120, session["anger"] + score))
    session["current_speech"] = ai_result.get("parent_comeback", "...")
    
    status = "PROCEED"
    if session["anger"] >= 120: status = "GAME_OVER"
    elif session["anger"] <= 0:
        if session["stage_idx"] < len(STAGES) - 1:
            session["stage_idx"] += 1
            session["anger"] = 60
            session["current_speech"] = STAGES[session["stage_idx"]]["speech"]
            status = "NEXT_STAGE"
        else: status = "GAME_WIN"

    return jsonify({"parent_speech": session["current_speech"], "anger": session["anger"], "stage_task": STAGES[session["stage_idx"]]["task"], "status": status})

if __name__ == "__main__":
    app.run(debug=True)