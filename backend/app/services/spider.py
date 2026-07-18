import os
import re
import time
import uuid
import json
import logging
from typing import Dict, Tuple, Optional, Any
from DrissionPage import ChromiumPage, ChromiumOptions
from curl_cffi import requests
from app.core.config import settings

logger = logging.getLogger("wattdash.spider")

# Global dict to store active browser page instances for MFA verification
browser_pool: Dict[str, ChromiumPage] = {}

class SpiderService:
    @staticmethod
    def get_chromium_options() -> ChromiumOptions:
        co = ChromiumOptions()
        
        # If CHROMIUM_PATH is set (e.g. on Linux), use it
        if settings.CHROMIUM_PATH:
            co.set_browser_path(settings.CHROMIUM_PATH)
            
        # Linux headless optimizations
        co.set_argument('--headless=new')
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-setuid-sandbox')
        co.set_argument('--disable-gpu')
        co.set_argument('--disable-dev-shm-usage')
        co.set_argument('--window-size=1920,1080')
        co.set_argument('--disable-extensions')
        co.set_argument('--no-first-run')
        co.set_argument('--no-default-browser-check')
        
        # Use a persistent profile directory so that 'Trust this device' cookies and states are preserved,
        # but aggressively delete the Chromium lock file (SingletonLock) before startup to prevent hangs/crashes.
        profile_dir = os.path.join(settings.CHROMIUM_USER_DATA, "persistent_profile")
        os.makedirs(profile_dir, exist_ok=True)
        
        lock_file = os.path.join(profile_dir, "SingletonLock")
        if os.path.islink(lock_file) or os.path.exists(lock_file):
            try:
                os.unlink(lock_file)
                logger.info("Removed Chromium SingletonLock file to prevent startup lock crash.")
            except Exception as e:
                logger.warning(f"Could not remove lock file: {e}")
                
        co.set_user_data_path(profile_dir)
        co.set_user_agent(
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        return co

    @staticmethod
    def read_token() -> Optional[str]:
        if settings.TOKEN_FILE.exists():
            try:
                with open(settings.TOKEN_FILE, 'r') as f:
                    return f.read().strip()
            except Exception as e:
                logger.error(f"Error reading token: {e}")
        return None

    @staticmethod
    def write_token(token: str) -> None:
        try:
            with open(settings.TOKEN_FILE, 'w') as f:
                f.write(token)
        except Exception as e:
            logger.error(f"Error writing token: {e}")

    @classmethod
    def save_diagnostic_screenshot(cls, page, name: str):
        """
        Save a diagnostic screenshot to database/screenshots directory to track browser steps.
        Overwrites previous runs to keep disk footprint minimal.
        """
        try:
            screenshots_dir = settings.DATABASE_DIR / "screenshots"
            # Clear screenshots directory on start of a new login flow
            if name == "01_load_cas.png" and screenshots_dir.exists():
                import shutil
                shutil.rmtree(screenshots_dir, ignore_errors=True)
                
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = screenshots_dir / name
            page.get_screenshot(path=str(screenshot_path))
            logger.info(f"Saved diagnostic screenshot: {screenshot_path}")
        except Exception as e:
            logger.error(f"Failed to save diagnostic screenshot {name}: {e}")

    @classmethod
    def login_step1(cls, student_id: str, password: str, query_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Step 1: Start Chromium, check for automatic login, or fill credentials.
        Returns 'success' (direct login or automatic refresh) or 'need_sms' (MFA).
        """
        logger.info(">>> [Phase 1] Initializing browser for login...")
        co = cls.get_chromium_options()
        page = None
        try:
            page = ChromiumPage(co)
            page.get('https://wxy.swjtu.edu.cn/')
            
            time.sleep(2)
            cls.save_diagnostic_screenshot(page, "01_load_cas.png")
            
            # Check if we were NOT redirected to CAS login, meaning the browser's active session
            # (or CAS SSO cookie) is still valid. In this case, JSESSIONID will be fetched automatically.
            if 'cas.swjtu.edu.cn' not in page.url:
                logger.info("--- Active SSO session detected! Extracting cookie directly...")
                jsessionid = next((c.get('value') for c in page.cookies() if c.get('name') == 'JSESSIONID'), None)
                if jsessionid:
                    cls.write_token(jsessionid)
                    cls.save_diagnostic_screenshot(page, "04_trusted_direct.png")
                    # Take success screenshot if requested
                    if query_config and query_config.get("save_login_screenshot"):
                        try:
                            screenshot_path = settings.DATABASE_DIR / "success_screenshot.png"
                            page.get_screenshot(path=str(screenshot_path))
                            logger.info(f"Saved success login screenshot to {screenshot_path}")
                        except Exception as se:
                            logger.error(f"Failed to save success screenshot: {se}")
                    page.quit()
                    return {"status": "success", "msg": "检测到本地SSO授权依然有效，自动静默刷新Cookie成功！"}
            
            # If we are redirected to CAS portal, we need credentials
            if 'cas.swjtu.edu.cn' in page.url:
                logger.info("--- Portal login page detected, entering credentials...")
                
                # Check for standard credentials input fields
                if page.ele('#username', timeout=5):
                    page.ele('#username').clear() 
                    page.ele('#username').input(student_id)
                    page.ele('#password').input(password) 
                    page.ele('#login_submit').click()
                
                time.sleep(2.5)
                cls.save_diagnostic_screenshot(page, "02_submit_credentials.png")
                
                # Check if MFA (SMS / WeChat work) verification is requested (first login or new device)
                if page.ele('#dynamicCode', timeout=3):
                    cls.save_diagnostic_screenshot(page, "03_mfa_prompt.png")
                    logger.info("MFA detected! Clicking to get WeChat Work code...")
                    page.ele('#getDynamicCode').click()
                    
                    # Store browser session in the pool
                    session_id = str(uuid.uuid4())
                    browser_pool[session_id] = page
                    
                    return {
                        "status": "need_sms",
                        "session_id": session_id,
                        "msg": "检测到二次验证已触发，验证码已发送至企业微信。"
                    }
                
                # If MFA was NOT requested, it means this device is already trusted!
                # Wait for redirection to complete and fetch token
                logger.info("--- Device already trusted. Waiting for redirection...")
                page.wait.url_change('cas.swjtu.edu.cn', timeout=10)
                cls.save_diagnostic_screenshot(page, "04_trusted_direct.png")
                jsessionid = next((c.get('value') for c in page.cookies() if c.get('name') == 'JSESSIONID'), None)
                
                if jsessionid:
                    cls.write_token(jsessionid)
                    # Take success screenshot if requested
                    if query_config and query_config.get("save_login_screenshot"):
                        try:
                            screenshot_path = settings.DATABASE_DIR / "success_screenshot.png"
                            page.get_screenshot(path=str(screenshot_path))
                            logger.info(f"Saved success login screenshot to {screenshot_path}")
                        except Exception as se:
                            logger.error(f"Failed to save success screenshot: {se}")
                    page.quit()
                    return {"status": "success", "msg": "使用已信任设备直接登录成功！"}
                
                page.quit()
                return {"status": "error", "msg": "跳转成功，但未捕获到登录 JSESSIONID。"}
            
            page.quit()
            return {"status": "error", "msg": "未知的跳转页面，未能提取 JSESSIONID。"}
            
        except Exception as e:
            logger.error(f"Error in login_step1: {e}")
            if page:
                try:
                    page.quit()
                except Exception:
                    pass
            return {"status": "error", "msg": f"Step1 异常: {str(e)}"}

    @classmethod
    def login_step2(cls, session_id: str, sms_code: str, query_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Step 2: Retrieve the page instance from pool, input SMS code, handle 'Trust Device', and save cookie.
        """
        if session_id not in browser_pool:
            return {"status": "error", "msg": "会话已过期，请重新刷新网页发起查询。"}
            
        page = browser_pool[session_id]
        logger.info(f">>> [Phase 2] Submitting SMS code: {sms_code}")
        
        try:
            # Click and clear to focus input field safely in headless mode
            input_el = page.ele('#dynamicCode')
            input_el.click()
            input_el.clear()
            input_el.input(sms_code)
            time.sleep(0.5)  # 0.5s pause to let input handler settle
            
            page.ele('#reAuthSubmitBtn').click()
            time.sleep(1.5)
            cls.save_diagnostic_screenshot(page, "05_submit_sms.png")
            
            logger.info("--- Waiting for redirection and handling trust prompt...")
            
            # Wait up to 25 seconds and automatically click 'Trust Device'
            wait_time = 0
            url_changed = False
            
            while wait_time < 25:
                if 'cas.swjtu.edu.cn' not in page.url:
                    url_changed = True
                    logger.info("✅ Redirection successful!")
                    break
                    
                # Try locating by class, English text, or Chinese text to support multilingual browser environments
                trust_btn = page.ele('.trust-device-sub-btn', timeout=1)
                if not trust_btn:
                    trust_btn = page.ele('text:Trust this device', timeout=1)
                if not trust_btn:
                    trust_btn = page.ele('text:信任此设备', timeout=1)
                
                if trust_btn:
                    modal = page.ele('.trust-device-modal')
                    is_visible = not modal or 'display: block' in (modal.attr('style') or '')
                    if is_visible:
                        logger.info("🎯 Found visible trust button! Clicking it...")
                        cls.save_diagnostic_screenshot(page, "06_trust_modal.png")
                        # Use direct JS click to prevent click interception issues in headless mode
                        trust_btn.click(by_js=True)
                        time.sleep(1)
                
                wait_time += 1

            if not url_changed:
                # Capture screenshot on failure to aid debugging
                try:
                    screenshot_path = settings.DATABASE_DIR / "error_screenshot.png"
                    page.get_screenshot(path=str(screenshot_path))
                    logger.info(f"Saved error screenshot to {screenshot_path}")
                except Exception as se:
                    logger.error(f"Failed to save screenshot: {se}")
                return {
                    "status": "error", 
                    "msg": "验证超时，页面未跳转，可能是动态码错误。已在 backend_data 目录中保存 error_screenshot.png 截图以供排查。"
                }
                
            # Allow time for cookies to settle
            time.sleep(1.5)
            cls.save_diagnostic_screenshot(page, "07_success.png")
            
            jsessionid = next((c.get('value') for c in page.cookies() if c.get('name') == 'JSESSIONID'), None)
            
            if jsessionid:
                cls.write_token(jsessionid)
                # Take success screenshot if requested
                if query_config and query_config.get("save_login_screenshot"):
                    try:
                        screenshot_path = settings.DATABASE_DIR / "success_screenshot.png"
                        page.get_screenshot(path=str(screenshot_path))
                        logger.info(f"Saved success login screenshot to {screenshot_path}")
                    except Exception as se:
                        logger.error(f"Failed to save success screenshot: {se}")
                return {"status": "success", "msg": "动态码验证通过，授权成功！"}
            
            return {"status": "error", "msg": "跳转成功，但未下发 JSESSIONID。"}
            
        except Exception as e:
            logger.error(f"Error in login_step2: {e}")
            return {"status": "error", "msg": f"验证时发生错误: {str(e)}"}
        finally:
            try:
                page.quit()
            except Exception:
                pass
            if session_id in browser_pool:
                del browser_pool[session_id]

    @classmethod
    def execute_query(cls, jsessionid: str, query_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute raw API query using curl_cffi to match client fingerprints.
        Supports up to 3 automatic retries for transient network timeouts/failures.
        """
        import time
        max_retries = 3
        last_error_msg = "未知数据拉取错误"
        
        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                logger.info(f"Retrying electricity query (attempt {attempt}/{max_retries})...")
            
            res = cls._execute_query_raw(jsessionid, query_config)
            if res.get("status") in ["success", "expired"]:
                return res
            
            last_error_msg = res.get("msg", "未完成查询")
            if attempt < max_retries:
                time.sleep(2)
                
        return {"status": "error", "msg": last_error_msg}

    @classmethod
    def _execute_query_raw(cls, jsessionid: str, query_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        query_url = "https://wxy.swjtu.edu.cn/wechat/basicQuery/queryElecRoomInfo.html"
        headers = {
            'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            'X-Requested-With': "XMLHttpRequest",
            'Cookie': f"JSESSIONID={jsessionid}" 
        }
        
        # Default query config if not provided
        default_config = {
            'aid': "0030000000002503",
            'area': '{"area":"犀浦校区","areaname":"犀浦校区"}',
            'building': '{"building":"鸿哲斋4号楼","buildingid":"1"}',
            'floor': '{"floorid":"","floor":""}',
            'room': '{"room":"","roomid":"041313"}'
        }
        
        payload = query_config if query_config else default_config
        
        try:
            response = requests.post(
                query_url, 
                headers=headers, 
                data=payload, 
                impersonate="chrome110", 
                verify=False, 
                allow_redirects=False,
                timeout=15
            )
            
            logger.info(f"Raw query response - Status: {response.status_code}, Length: {len(response.text)}, Preview: {response.text[:250]}")
            
            if response.status_code == 302 or 'cas.swjtu.edu.cn' in response.text:
                return {"status": "expired"}
                
            res_json = response.json()
            
            if res_json.get("retcode") == "91001" or "超时" in res_json.get("errmsg", ""):
                return {"status": "expired"}
                
            if res_json.get("retcode") == "0":
                msg = res_json.get("errmsg", "")
                match = re.search(r"(\d+(\.\d+)?)", msg)
                if match:
                    return {"status": "success", "power": float(match.group(1))}
                return {"status": "error", "msg": f"解析余额数值失败: {msg}"}
                
            return {"status": "error", "msg": f"接口业务报错: {res_json}"}
            
        except json.JSONDecodeError:
            if response.status_code == 302 or 'cas.swjtu.edu.cn' in response.text:
                return {"status": "expired"}
            return {"status": "error", "msg": "接口返回了非 JSON 数据"}
        except Exception as e:
            logger.error(f"Error executing electricity query: {e}")
            return {"status": "error", "msg": f"请求网络异常: {str(e)}"}
