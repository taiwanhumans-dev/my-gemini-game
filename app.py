from flask import Flask, render_template, request, jsonify, session
import json
import os
from google import genai
from google.genai import types

app = Flask(__name__)
app.secret_key = "my_secret_key"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

game_story = """
{
  "stages": [
    {"id": 1, "task": "玄關晚歸", "desc": "半夜 12 點，你輕手輕腳地轉動鑰匙，沒想到客廳的燈是亮的。長輩正坐在沙發上，眼神像探照燈一樣掃射過來...", "speech": "你還知道要回來啊？現在幾點了？全家都在等你，你是把家當旅館是不是？"},
    {"id": 2, "task": "客廳電燈", "desc": "你才剛從廚房走出來，回頭發現客廳空無一人，但那盞 100 瓦的吊燈還在瘋狂燃燒...", "speech": "跟你講過幾次？進屋隨手關燈！家裡開銀行的喔？電費不用錢是不是？"},
    {"id": 3, "task": "餐桌手機", "desc": "剛坐下準備開動，你習慣性地把手機拿出來放在旁邊。長輩的手指已經指著你的鼻子...", "speech": "坐下來還在滑手機！手機會餵你吃飯喔？吃飯就好好吃飯，收起來！"},
    {"id": 4, "task": "晚餐遲到", "desc": "你在房間打遊戲太入迷，直到長輩在廚房怒吼了三次才慢吞吞走出來...", "speech": "這菜都涼了，喊你十分鐘才出來，還要人請幾次？你是不是覺得大家都要伺候你？"},
    {"id": 5, "task": "廚房洗碗", "desc": "你吃完飯想溜走，但轉身發現碗筷還疊在那。長輩那道足以穿透鋼板的目光，鎖定了你的背影...", "speech": "吃完碗就丟桌上？這家裡只有我是傭人是不是？手廢了還是沒長眼？拿去洗！"},
    {"id": 6, "task": "巷口垃圾", "desc": "垃圾車音樂從巷口傳來，你正窩在沙發上當馬鈴薯，長輩突然拿著那包發臭的垃圾塞到你懷裡...", "speech": "垃圾車來了啦！還在那邊看電視？還不快點去追！你是要等垃圾長腳自己跑出去喔？"},
    {"id": 7, "task": "換裝見人", "desc": "親戚要來家裡作客，你穿著破洞牛仔褲走出來，長輩瞬間覺得面子掛不住，臉色鐵青...", "speech": "穿這什麼破爛牛仔褲？乞丐是不是？等下親戚要來，你是想讓人家看我們家笑話喔？"},
    {"id": 8, "task": "房間整理", "desc": "長輩今天突然心情好幫你換床單，但一打開房門，那股積累了半年的髒衣服味道撲面而來...", "speech": "看你這房間，豬窩都比你乾淨！連下腳的地方都沒有，到底什麼時候要清？"},
    {"id": 9, "task": "開箱包裹", "desc": "玄關堆滿了網購商品，長輩正拿著美工刀站在旁邊，準備把包裹一一「驗屍」...", "speech": "這包裹又是什麼？整天買這些沒用的垃圾，錢多喔？賺那一點點錢都不夠你亂花！"},
    {"id": 10, "task": "深夜水果", "desc": "已經凌晨兩點，你還在螢幕前苦戰，長輩端著切好的蘋果走進來，語氣充滿威脅...", "speech": "蘋果切好了啦，吃一吃快點去睡覺，別再熬夜了，你是想把自己搞死是不是？"}
  ]
}
"""
STAGES = json.loads(game_story)["stages"]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/change_stage", methods=["POST"])
def change_stage():
    idx = request.json.get("stage_idx", 0)
    session["stage_idx"] = idx if 0 <= idx < len(STAGES) else 0
    session["anger"] = 80
    stage_data = STAGES[session["stage_idx"]]
    session["last_speech"] = stage_data["speech"]
    return jsonify({
        "parent_speech": stage_data["speech"], 
        "anger": 80, 
        "stage_task": stage_data["task"], 
        "desc": stage_data["desc"]
    })

@app.route("/api/reply", methods=["POST"])
def reply():
    user_reply = request.json.get("reply", "").strip()
    
    # AI 邏輯
    prompt = f"扮演硬核家長，場景:{STAGES[session['stage_idx']]['task']}，長輩說:{session['last_speech']}，孩子說:{user_reply}，怒氣:{session.get('anger', 80)}。JSON格式: {{\"parent_comeback\": \"...\", \"anger_change\": 10}}"
    
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
        ai_result = json.loads(response.text.strip())
    except:
        ai_result = {"parent_comeback": "『你現在是裝聾作啞，不說話是什麼意思？』", "anger_change": 10}

    score = ai_result.get("anger_change", 10)
    if any(k in user_reply.lower() for k in ["對不起", "抱歉", "我錯", "歹勢", "sorry"]):
        score = -30

    anger = max(0, min(120, session.get("anger", 80) + score))
    session["anger"] = anger
    session["last_speech"] = ai_result.get("parent_comeback", "...")
    status = "WIN" if anger <= 0 else ("LOSE" if anger >= 120 else "OK")
    
    return jsonify({"parent_speech": session["last_speech"], "anger": anger, "status": status})

if __name__ == "__main__":
    app.run(debug=True)