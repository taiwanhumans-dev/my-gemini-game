from flask import Flask, render_template, request, jsonify, session
import json
import random
from google import genai
from google.genai import types
import os

app = Flask(__name__)
app.secret_key = "your_super_secret_key_for_cookie_encryption"

# 請確認這裡有你的 API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

game_story = """
{
  "stages": [
    {"id": 1, "task": "玄關晚歸", "speech": "你還知道要回來啊？現在幾點了？全家都在等你！"},
    {"id": 2, "task": "客廳電燈", "speech": "跟你講過幾次？進屋隨手關燈！家裡開銀行的喔？"},
    {"id": 3, "task": "餐桌手機", "speech": "坐下來還在滑手機！手機會餵你吃飯喔？收起來！"}
  ]
}
"""
STAGES = json.loads(game_story)["stages"]

def call_gemini_api(stage_task, parent_speech, user_reply, current_anger):
    system_instruction = """
    你現在正在扮演一場「家長怒氣生存遊戲」中的長輩。你性格硬核、不講理、擅長情緒勒索與連珠炮碎碎唸。
    【重要核心扣題限制】你必須現場根據當前場景任務主題和孩子的對話進行即興大罵。
    【輸出限制】你必須「嚴格」回傳一個標準的 JSON 物件結構。
    {
      "parent_comeback": "（由你現場即興大罵的反擊台詞）",
      "anger_change": (整數。頂嘴給 +20到+35；極度敷衍給 +15；態度極好給 -15到-25),
      "status": "NORMAL"
    }
    """
    prompt = f"""
    {system_instruction}
    ===== 現實遊戲即時狀態 =====
    * 當前場景任務主題: 【 {stage_task} 】
    * 家長上一句說的話: "{parent_speech}"
    * 孩子最新講的話(玩家輸入): "{user_reply}"
    * 目前長輩內心的怒氣值: {current_anger}
    ============================
    請立刻輸出符合上述格式要求的 JSON。
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text.strip())
    except Exception as e:
        return {"parent_comeback": "『你現在是裝聾作啞，不說話是什麼意思？』", "anger_change": 15}

@app.route("/")
def index():
    session["stage_idx"] = 0
    session["anger"] = 80
    session["current_speech"] = STAGES[0]["speech"]
    session["is_over"] = False
    session["is_win"] = False
    return render_template("index.html")

@app.route("/api/reply", methods=["POST"])
def reply():
    if session.get("is_over") or session.get("is_win"):
        return jsonify({"error": "遊戲已結束"}), 400

    req_data = request.get_json()
    user_reply = req_data.get("reply", "").strip()
    idx = session["stage_idx"]
    current_stage = STAGES[idx]

    ai_result = call_gemini_api(
        current_stage["task"], 
        session["current_speech"], 
        user_reply, 
        session["anger"]
    )
    
    comeback = ai_result.get("parent_comeback", "...")
    score = ai_result.get("anger_change", 10)

    session["anger"] = max(0, min(120, session["anger"] + score))
    session["current_speech"] = comeback
    result_status = "PROCEED"

    if session["anger"] >= 120:
        session["is_over"] = True
        result_status = "GAME_OVER"
    elif session["anger"] <= 0:
        session["stage_idx"] += 1
        if session["stage_idx"] >= len(STAGES):
            session["is_win"] = True
            result_status = "GAME_WIN"
        else:
            session["anger"] = random.randint(55, 75)
            session["current_speech"] = STAGES[session["stage_idx"]]["speech"]
            result_status = "NEXT_STAGE"

    return jsonify({
        "parent_speech": session["current_speech"],
        "anger": session["anger"],
        "stage_task": STAGES[session["stage_idx"]]["task"] if session["stage_idx"] < len(STAGES) else "完美通關",
        "status": result_status
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)