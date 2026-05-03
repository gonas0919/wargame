from flask import Flask, request, render_template, session
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
import uuid
import time
import os
import codecs
import re

SECRET_FLAG_VALUE = "MSG{**redacted**}"

banlist = ["+", "`", "'", "content", "replace", "[", "]",
            "alert", "prompt", "confirm",
            "fetch", "XMLHttp", "navigator.sendBeacon",
            "location", "href", "src", "window", "open", "meta", "eval", "javascript", "@", "!", "%",
            "img", "iframe", "svg", "math", "div", "video", "audio", "form", "input", "textarea", "button",
            "onerror", "onload", "oonclick", "onmouseover", "onfocus", "oninput", "onchange", "onanimationstart", "onpageshow"]
app = Flask(__name__)


def bot_visit_url(target_url: str) -> bool:
    try:
        service = Service(executable_path="/usr/local/bin/chromedriver")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(3)
        driver.set_page_load_timeout(6)
        driver.get("http://127.0.0.1/")
        driver.add_cookie({'name':'flag','value':SECRET_FLAG_VALUE, 'domain':'127.0.0.1'})
        driver.get(target_url)
        time.sleep(1)
    except Exception as e:
        if driver:
            driver.quit()
        return False
    if driver:
        driver.quit()
    return True


@app.route('/')
def home():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    return render_template('index.html', user_id=session['user_id'])

@app.route('/test', methods=['GET'])
def test():
    payload = request.args.get('testing')
    
    if payload is None:
        payload = "그 정도 노력으론 영수의 돈을 받을 수 없어"
    payload = payload.lower()
    if re.search(r'\\u[0-9A-Fa-f]{4}', payload):
        payload = "그 정도 노력으론 영수의 돈을 받을 수 없어"
    

    is_banned = False
    for banned_word in banlist:
        if banned_word in payload:
            is_banned = True
            break

    if is_banned:
        payload = "그 정도 노력으론 영수의 돈을 받을 수 없어"
    else:
        payload = payload

    html_content = f"""
    <!DOCTYPE html>
    <html lang=\"ko\">
    <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <title>영수 돈 받기</title>
        <style>
            html, body {{ margin:0; padding:0; height:100%; }}
            body {{ background:#c9d8e8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans KR', sans-serif; color:#1f1f1f; }}
            .wrap {{ display:flex; align-items:flex-start; justify-content:center; padding:28px 12px; }}
            .msg {{ display:flex; gap:10px; max-width:760px; width:100%; }}
            .avatar {{ width:32px; height:32px; border-radius:50%; background:#3C1E1E; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; }}
            .bubble {{ background:#fff; border:1px solid #e5e5e5; border-radius:18px; padding:14px 16px; position:relative; box-shadow:0 1px 2px rgba(0,0,0,.04); }}
            .bubble::after {{ content:''; position:absolute; left:-6px; bottom:10px; width:12px; height:12px; background:#fff; border-left:1px solid #e5e5e5; border-bottom:1px solid #e5e5e5; transform:rotate(45deg); }}
            .name {{ font-size:12px; color:#6b6b6b; margin-left:42px; margin-bottom:4px; }}
            .time {{ font-size:11px; color:#6b6b6b; margin-top:6px; text-align:right; }}
            code {{ background:#f6f8fa; border:1px solid #eaecef; border-radius:6px; padding:0 .25em; }}
        </style>
    </head>
    <body>
        <div class=\"wrap\">
            <div style=\"width:100%; max-width:760px;\">
                <div class=\"name\">영수</div>
                <div class=\"msg\">
                    <div class=\"avatar\">영</div>
                    <div class=\"bubble\">
                        {payload}
                        <div class=\"time\">봇이 확인 중...</div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

@app.route('/yeongsu', methods=['GET'])
def yeongsu_click_handler():
    payload = request.args.get('msg')
    target = f"http://127.0.0.1/test?testing={payload}" if payload else None

    did_click = bool(payload) and bot_visit_url(target)
    return "계좌 확인해봐. 돈 입금 됐을 지도~" if did_click else "돈 받기 싫어?"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)