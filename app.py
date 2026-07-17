import os
import re
import time
import uuid
import json
import datetime
from flask import Flask, jsonify, request, render_template_string
from DrissionPage import ChromiumPage, ChromiumOptions
from curl_cffi import requests

app = Flask(__name__)
TOKEN_FILE = 'token.txt'
browser_pool = {}

# ================= 读写 Token 辅助函数 =================
def read_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return f.read().strip()
    return None

def write_token(token):
    with open(TOKEN_FILE, 'w') as f:
        f.write(token)

# ================= 登录阶段 1：触发企业微信验证码 =================
@app.route('/api/login/step1', methods=['POST'])
def login_step1():
    print(">>> [Phase 1] 启动无头浏览器，准备触发验证码...")
    co = ChromiumOptions()
    co.set_browser_path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    co.set_user_data_path(r'C:\Users\Administrator\SWJTU_AutoLogin')  
    co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # ⚠️ 部署在服务器上挂机时，建议改为 True 实行完全静默。测试期间可以保持 False
    co.headless(False) 
    
    page = ChromiumPage(co)
    
    try:
        page.get('https://wxy.swjtu.edu.cn/')
        
        if 'cas.swjtu.edu.cn' in page.url:
            print("--- 检测到未登录，正在填入账号密码...")
            
            student_id = os.getenv("SWJTU_STUDENT_ID", "")
            password = os.getenv("SWJTU_PASSWORD", "")
            
            if not student_id or not password:
                print("❌ 错误：环境变量 SWJTU_STUDENT_ID 或 SWJTU_PASSWORD 未配置！")
                page.quit()
                return jsonify({"status": "error", "msg": "服务器未配置 SWJTU_STUDENT_ID 或 SWJTU_PASSWORD 环境变量，无法登录！"})
                
            # 1. 常规账密登录
            if page.ele('#username', timeout=2):
                page.ele('#username').clear() 
                page.ele('#username').input(student_id)
                page.ele('#password').input(password) 
                page.ele('#login_submit').click()
            
            time.sleep(2)
                
            # 2. 检查二次验证（MFA）页面
            if page.ele('#dynamicCode', timeout=3):
                print("触发二次验证！正在点击获取企业微信验证码...")
                page.ele('#getDynamicCode').click()
                
                session_id = str(uuid.uuid4())
                browser_pool[session_id] = page 
                
                return jsonify({
                    "status": "need_sms", 
                    "session_id": session_id, 
                    "msg": "企业微信动态码已发送，请在手机上查看并输入。"
                })
            
        # 如果极小概率不需要验证码，直接走这里
        page.wait.url_change('cas.swjtu.edu.cn', timeout=10)
        jsessionid = next((c.get('value') for c in page.cookies() if c.get('name') == 'JSESSIONID'), None)
        
        if jsessionid:
            write_token(jsessionid)
            page.quit()
            return jsonify({"status": "success", "msg": "无需二次验证，直接登录成功！"})
            
        page.quit()
        return jsonify({"status": "error", "msg": "登录状态异常，未能提取 JSESSIONID。"})
        
    except Exception as e:
        if page:
            page.quit()
        return jsonify({"status": "error", "msg": f"Step1 异常: {str(e)}"})

# ================= 登录阶段 2：提交验证码与信任设备 =================
@app.route('/api/login/step2', methods=['POST'])
def login_step2():
    data = request.json
    session_id = data.get('session_id')
    sms_code = data.get('sms_code')
    
    if session_id not in browser_pool:
        return jsonify({"status": "error", "msg": "会话已过期，请重新刷新网页发起查询。"})
        
    page = browser_pool[session_id]
    print(f">>> [Phase 2] 唤醒浏览器，准备填入验证码: {sms_code}")
    
    try:
        page.ele('#dynamicCode').input(sms_code)
        page.ele('#reAuthSubmitBtn').click()
        
        print("--- 开启智能巡航：等待页面跳转或拦截弹窗...")
        
        # 🌟 终极自适应等待循环 (最大等待 15 秒)
        wait_time = 0
        url_changed = False
        
        while wait_time < 15:
            # 1. 如果发现网址已经不在 cas 登录页了，说明成功放行，直接跳出循环！
            if 'cas.swjtu.edu.cn' not in page.url:
                url_changed = True
                print("✅ 页面已成功跳转！")
                break
                
            # 2. 只要网址没变，就疯狂扫视页面上有没有出现“信任此设备”
            # 这里的 timeout=1 意思是每次只花 1 秒钟找，找不到就立刻进入下一次循环
            trust_btn = page.ele('text:信任此设备', timeout=1) 
            if trust_btn:
                print("🎯 雷达捕获弹窗！执行自动爆破点击！")
                trust_btn.click()
                time.sleep(1) # 点完给服务器 1 秒钟的反应时间
            
            wait_time += 1

        # 如果循环了 15 秒网址还没变，说明真卡死了（比如验证码填错了）
        if not url_changed:
            return jsonify({"status": "error", "msg": "验证超时，页面未跳转，可能是动态码错误。"})
            
        # 离开循环，稍微等一下确保 Cookie 彻底写入
        time.sleep(1.5)
        
        jsessionid = next((c.get('value') for c in page.cookies() if c.get('name') == 'JSESSIONID'), None)
        
        if jsessionid:
            write_token(jsessionid)
            return jsonify({"status": "success", "msg": "动态码验证通过，战利品已获取！"})
        
        return jsonify({"status": "error", "msg": "跳转成功，但服务器未下发 Cookie。"})
        
    except Exception as e:
        return jsonify({"status": "error", "msg": f"验证时发生错误: {str(e)}"})
    finally:
        page.quit()
        del browser_pool[session_id]

# ================= 极速查询业务 =================
def do_query_request(jsessionid):
    query_url = "https://wxy.swjtu.edu.cn/wechat/basicQuery/queryElecRoomInfo.html"
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        'X-Requested-With': "XMLHttpRequest",
        'Cookie': f"JSESSIONID={jsessionid}" 
    }
    data = {
        'aid': "0030000000002503",
        'area': '{"area":"犀浦校区","areaname":"犀浦校区"}',
        'building': '{"building":"鸿哲斋4号楼","buildingid":"1"}',
        'floor': '{"floorid":"","floor":""}',
        'room': '{"room":"","roomid":"041313"}'
    }

    response = requests.post(query_url, headers=headers, data=data, impersonate="chrome110", verify=False, allow_redirects=False)
    
    try:
        res_json = response.json()
        
        if res_json.get("retcode") == "91001" or "超时" in res_json.get("errmsg", ""):
            print("检测到业务超时，准备通知前端启动重新登录...")
            return {"status": "expired"}
            
        if res_json.get("retcode") == "0":
            msg = res_json.get("errmsg", "")
            match = re.search(r"(\d+(\.\d+)?)", msg)
            if match:
                return {"status": "success", "power": float(match.group(1))}
            return {"status": "error", "msg": f"解析失败: {msg}"}
            
        return {"status": "error", "msg": f"业务报错: {res_json}"}
        
    except json.JSONDecodeError:
        if response.status_code == 302 or 'cas.swjtu.edu.cn' in response.text:
            return {"status": "expired"}
        return {"status": "error", "msg": "接口返回了非 JSON 数据"}

# ================= API 路由逻辑 =================
@app.route('/api/query', methods=['GET'])
def api_query():
    token = read_token()
    if not token:
        return jsonify({"status": "expired", "msg": "本地无可用凭证，需重新授权。"})
            
    result = do_query_request(token)
    return jsonify(result)

# ================= 前端页面路由 =================
@app.route('/')
def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>交大电费速查</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f7f7f7; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; width: 90%; max-width: 400px; }
            h2 { color: #333; margin-top: 0; }
            .room-info { color: #888; font-size: 14px; margin-bottom: 20px; }
            .power-display { font-size: 48px; font-weight: bold; color: #007aff; margin: 20px 0; }
            button { background-color: #007aff; color: white; border: none; padding: 12px 24px; font-size: 16px; border-radius: 8px; cursor: pointer; width: 100%; transition: background 0.3s; }
            button:disabled { background-color: #ccc; cursor: not-allowed; }
            button:active { background-color: #005bb5; }
            .error { color: red; font-size: 14px; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>⚡ 电费查询</h2>
            <div class="room-info">鸿哲斋 4号楼 - 041313</div>
            <div class="power-display" id="power-value">-- 元</div>
            <button id="query-btn" onclick="queryPower()">一键查询</button>
            <div class="error" id="error-msg"></div>
        </div>

        <script>
            async function queryPower() {
                const btn = document.getElementById('query-btn');
                const powerDisplay = document.getElementById('power-value');
                const errorMsg = document.getElementById('error-msg');
                
                btn.disabled = true;
                btn.innerText = "⚡ 正在极速查询...";
                powerDisplay.innerText = "-- 元";
                errorMsg.innerText = "";

                try {
                    let response = await fetch('/api/query');
                    let data = await response.json();
                    
                    // 只有在凭证过期的情况下，才去触发全自动接管流程
                    if (data.status === 'expired') {
                        errorMsg.innerText = "凭证已过期，正在联系服务器获取验证码...";
                        let step1Res = await fetch('/api/login/step1', {method: 'POST'});
                        let step1Data = await step1Res.json();
                        
                        if (step1Data.status === 'need_sms') {
                            let userCode = prompt(step1Data.msg + "\\n\\n请输入验证码：");
                            if (userCode) {
                                errorMsg.innerText = "正在提交验证码并授权...";
                                let step2Res = await fetch('/api/login/step2', {
                                    method: 'POST',
                                    headers: {'Content-Type': 'application/json'},
                                    body: JSON.stringify({
                                        session_id: step1Data.session_id,
                                        sms_code: userCode
                                    })
                                });
                                let step2Data = await step2Res.json();
                                
                                if (step2Data.status === 'success') {
                                    errorMsg.innerText = "授权成功！重新查询中...";
                                    response = await fetch('/api/query');
                                    data = await response.json();
                                } else {
                                    throw new Error(step2Data.msg);
                                }
                            } else {
                                throw new Error("您取消了验证码输入，查询中止。");
                            }
                        } else if (step1Data.status === 'success') {
                            // 无需验证码直接拿到了 Cookie
                            response = await fetch('/api/query');
                            data = await response.json();
                        } else {
                             throw new Error(step1Data.msg);
                        }
                    }

                    // 最终渲染环节
                    if (data.status === 'success') {
                        powerDisplay.innerText = data.power + ' 元';
                        errorMsg.innerText = "";
                    } else if (data.status === 'error') {
                        errorMsg.innerText = data.msg;
                    }
                    
                } catch (error) {
                    errorMsg.innerText = error.message || "网络请求失败，请检查服务器！";
                } finally {
                    btn.disabled = false;
                    btn.innerText = "重新查询";
                }
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9100)