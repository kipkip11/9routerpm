import os
import json
import time
import threading
import requests
from backend import pm2_manager

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alerts_config.json"))

def load_config():
    """Tải cấu hình cảnh báo từ file JSON và tự động đồng bộ hóa các profile thực tế trên máy."""
    from backend import hermes_manager
    
    config = {
        "global_enabled": True,
        "check_interval_seconds": 30,
        "profiles": {}
    }
    
    # 1. Đọc cấu hình hiện tại từ file nếu có
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    config.update(loaded)
        except Exception as e:
            print(f"[ALERTS] Lỗi đọc file cấu hình: {e}")

    # 2. Lấy danh sách profile thực tế hiện tại trên máy
    actual_profiles = []
    try:
        profiles_info = hermes_manager.get_all_profiles()
        actual_profiles = [p["name"] for p in profiles_info if "name" in p]
    except Exception as e:
        print(f"[ALERTS] Lỗi lấy danh sách profile thực tế từ hermes_manager: {e}")

    # 3. Tự động đồng bộ hóa danh sách profile thực tế vào config
    if "profiles" not in config:
        config["profiles"] = {}
        
    config_changed = False
    
    # Thêm cấu hình mặc định cho các profile thực tế chưa có trong config
    for p_name in actual_profiles:
        if p_name not in config["profiles"]:
            config["profiles"][p_name] = {
                "enabled": False,
                "bot_type": "telegram",
                "telegram_token": "",
                "telegram_chat_id": "",
                "zalo_url": "http://localhost:3000/send",
                "zalo_params": '{"message": "{message}"}',
                "last_status": "unknown"
            }
            config_changed = True

    # (Tùy chọn) Lưu lại cấu hình nếu có sự thay đổi/thêm mới profile
    if config_changed:
        save_config(config)
        
    return config

def save_config(config):
    """Lưu cấu hình cảnh báo vào file JSON."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ALERTS] Lỗi ghi file cấu hình: {e}")
        return False

def send_telegram_alert(token, chat_id, message):
    """Gửi tin nhắn cảnh báo qua Telegram Bot."""
    if not token or not chat_id:
        return False, "Thiếu Token hoặc Chat ID Telegram."
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            return True, "Gửi tin nhắn Telegram thành công."
        return False, f"Lỗi Telegram API: {res.text}"
    except Exception as e:
        return False, f"Lỗi kết nối Telegram: {str(e)}"

def send_zalo_alert(url, params_template, message):
    """Gửi tin nhắn cảnh báo qua Zalo Bot (Webhook cục bộ)."""
    if not url:
        return False, "Thiếu URL Webhook Zalo."
    try:
        # Thay thế placeholder {message} trong chuỗi cấu hình JSON
        payload_str = params_template.replace("{message}", message)
        try:
            payload = json.loads(payload_str)
        except Exception:
            # Nếu params không phải JSON hợp lệ, gửi thô làm text
            payload = {"message": message}
            
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code in [200, 201]:
            return True, "Gửi tin nhắn Zalo thành công."
        return False, f"Lỗi Zalo Webhook API: {res.text}"
    except Exception as e:
        return False, f"Lỗi kết nối Zalo Webhook: {str(e)}"

def send_alert(profile_name, profile_cfg, message):
    """Tự động phân phối gửi tin nhắn theo cấu hình của profile."""
    bot_type = profile_cfg.get("bot_type", "telegram")
    if bot_type == "telegram":
        token = profile_cfg.get("telegram_token")
        chat_id = profile_cfg.get("telegram_chat_id")
        return send_telegram_alert(token, chat_id, message)
    elif bot_type == "zalo":
        zalo_url = profile_cfg.get("zalo_url")
        zalo_params = profile_cfg.get("zalo_params", '{"message": "{message}"}')
        return send_zalo_alert(zalo_url, zalo_params, message)
    return False, f"Loại bot '{bot_type}' không được hỗ trợ."

# Khai báo biến dừng thread Watchdog
watchdog_running = False

def start_watchdog():
    """Khởi động luồng giám sát Watchdog."""
    global watchdog_running
    if watchdog_running:
        return
        
    watchdog_running = True
    thread = threading.Thread(target=watchdog_loop, name="AlertsWatchdog")
    thread.daemon = True
    thread.start()
    print("[ALERTS] Đã kích hoạt luồng giám sát Alerts Watchdog.")

def watchdog_loop():
    """Vòng lặp giám sát trạng thái PM2 và gửi cảnh báo."""
    global watchdog_running
    
    # Đợi 10 giây ban đầu để hệ thống ổn định rpc.sock
    time.sleep(10)
    
    while watchdog_running:
        try:
            config = load_config()
            if not config.get("global_enabled", True):
                time.sleep(config.get("check_interval_seconds", 30))
                continue
                
            # Lấy danh sách tiến trình đang chạy từ PM2
            pm2_list = []
            try:
                pm2_list = pm2_manager.get_pm2_list()
            except Exception as e:
                print(f"[ALERTS-WATCHDOG] Lỗi lấy danh sách PM2: {e}")
                time.sleep(15)
                continue
                
            # Tạo map trạng thái từ PM2 list để tra cứu nhanh
            # pm2_list là list dict, ví dụ: [{"name": "hermes-default", "status": "online"}, ...]
            pm2_status_map = {}
            for app in pm2_list:
                app_name = app.get("name")
                if app_name:
                    pm2_status_map[app_name] = app.get("status", "unknown")
            
            config_changed = False
            
            for profile_name, p_cfg in config.get("profiles", {}).items():
                if not p_cfg.get("enabled", False):
                    continue
                    
                pm2_app_name = f"hermes-{profile_name}"
                
                # Xác định trạng thái hiện tại
                current_pm2_status = pm2_status_map.get(pm2_app_name)
                
                # Trạng thái logic: online nếu trạng thái PM2 là online
                if current_pm2_status == "online":
                    current_status = "online"
                else:
                    current_status = "offline"
                    
                last_status = p_cfg.get("last_status", "unknown")
                
                # Bỏ qua lần quét đầu tiên khi trạng thái là unknown để tránh spam alert khi mới bật server
                if last_status == "unknown":
                    p_cfg["last_status"] = current_status
                    config_changed = True
                    continue
                    
                # Phát hiện chuyển đổi trạng thái
                if last_status == "online" and current_status == "offline":
                    # Gửi cảnh báo Offline
                    msg = (
                        f"🔴 <b>CẢNH BÁO MẤT KẾT NỐI</b>\n\n"
                        f"Dịch vụ: <b>Hermes Agent</b>\n"
                        f"Profile: <code>{profile_name}</code>\n"
                        f"Trạng thái: <pre>OFFLINE (Đã tắt/Lỗi)</pre>\n"
                        f"Thời gian: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    success, err_msg = send_alert(profile_name, p_cfg, msg)
                    if success:
                        print(f"[ALERTS-WATCHDOG] Đã gửi cảnh báo OFFLINE cho profile '{profile_name}'.")
                    else:
                        print(f"[ALERTS-WATCHDOG] Lỗi gửi cảnh báo OFFLINE cho profile '{profile_name}': {err_msg}")
                        
                    p_cfg["last_status"] = "offline"
                    config_changed = True
                    
                elif last_status == "offline" and current_status == "online":
                    # Gửi thông báo khôi phục Online
                    msg = (
                        f"🟢 <b>THÔNG BÁO KHÔI PHỤC</b>\n\n"
                        f"Dịch vụ: <b>Hermes Agent</b>\n"
                        f"Profile: <code>{profile_name}</code>\n"
                        f"Trạng thái: <pre>ONLINE (Hoạt động bình thường)</pre>\n"
                        f"Thời gian: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    success, err_msg = send_alert(profile_name, p_cfg, msg)
                    if success:
                        print(f"[ALERTS-WATCHDOG] Đã gửi cảnh báo ONLINE cho profile '{profile_name}'.")
                    else:
                        print(f"[ALERTS-WATCHDOG] Lỗi gửi cảnh báo ONLINE cho profile '{profile_name}': {err_msg}")
                        
                    p_cfg["last_status"] = "online"
                    config_changed = True
                    
            if config_changed:
                save_config(config)
                
            time.sleep(config.get("check_interval_seconds", 30))
        except Exception as ex:
            print(f"[ALERTS-WATCHDOG] Lỗi vòng lặp giám sát: {ex}")
            time.sleep(30)
