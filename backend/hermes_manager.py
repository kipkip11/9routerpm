import os
import shutil
import subprocess
import threading
import json
import socket
from datetime import datetime
from backend import pm2_manager

# Xác định đường dẫn động trong AppData (tương thích chạy dưới dạng Windows Service)
LOCAL_APP_DATA = os.environ.get("LOCALAPPDATA_USER") or os.environ.get("LOCALAPPDATA") or os.path.expandvars(r"%LOCALAPPDATA%")
HERMES_DIR = os.path.abspath(os.path.join(LOCAL_APP_DATA, "hermes"))
HERMES_AGENT_DIR = os.path.join(HERMES_DIR, "hermes-agent")
PROFILES_DIR = os.path.join(HERMES_DIR, "profiles")

VENV_PYTHON = os.path.join(HERMES_AGENT_DIR, "venv", "Scripts", "python.exe")
VENV_HERMES_EXE = os.path.join(HERMES_AGENT_DIR, "venv", "Scripts", "hermes.exe")

# Trạng thái cài đặt toàn cục
install_state = {
    "status": "idle",       # idle, running, success, failed
    "progress": 0,
    "log": ""
}
install_lock = threading.Lock()

def get_install_state():
    with install_lock:
        return install_state.copy()

def set_install_state(status, progress, log_msg, append=True):
    with install_lock:
        global install_state
        install_state["status"] = status
        install_state["progress"] = progress
        if append and install_state["log"]:
            install_state["log"] += f"\n[{datetime.now().strftime('%H:%M:%S')}] {log_msg}"
        else:
            install_state["log"] = f"[{datetime.now().strftime('%H:%M:%S')}] {log_msg}"

def is_hermes_installed():
    """Kiểm tra xem Hermes Agent đã được cài đặt môi trường ảo và file thực thi chưa."""
    return os.path.exists(VENV_HERMES_EXE) and os.path.exists(VENV_PYTHON)

def read_profile_config(yaml_path):
    """Đọc cấu hình model từ file config.yaml bằng xử lý chuỗi thuần túy."""
    if not os.path.exists(yaml_path):
        return {}
    
    config = {}
    try:
        with open(yaml_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        in_model_section = False
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            
            indent = len(line) - len(line.lstrip())
            
            if stripped == "model:":
                in_model_section = True
                continue
            
            if in_model_section:
                if indent == 0:
                    in_model_section = False
                else:
                    if ':' in stripped:
                        k, v = stripped.split(':', 1)
                        k = k.strip()
                        v = v.strip().strip("'").strip('"')
                        config[k] = v
    except Exception as e:
        print(f"Error reading yaml config {yaml_path}: {e}")
        
    return {
        "default": config.get("default", ""),
        "provider": config.get("provider", "custom"),
        "base_url": config.get("base_url", ""),
        "api_key": config.get("api_key", ""),
        "model": config.get("model", ""),
        "context_length": config.get("context_length", "70000")
    }

def write_profile_config(yaml_path, model_config):
    """Ghi đè cấu hình model vào file config.yaml mà không làm hỏng các phần khác."""
    try:
        lines = []
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
        new_lines = []
        model_written = False
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            if stripped == "model:":
                new_lines.append(line)
                new_lines.append(f"  default: {model_config.get('default', 'default')}\n")
                new_lines.append(f"  provider: {model_config.get('provider', 'custom')}\n")
                new_lines.append(f"  base_url: {model_config.get('base_url', '')}\n")
                new_lines.append(f"  api_key: {model_config.get('api_key', '')}\n")
                new_lines.append(f"  context_length: {int(model_config.get('context_length', 70000))}\n")
                new_lines.append(f"  model: {model_config.get('model', 'default')}\n")
                model_written = True
                i += 1
                
                # Bỏ qua các dòng cũ của model section
                while i < len(lines):
                    next_line = lines[i]
                    next_indent = len(next_line) - len(next_line.lstrip())
                    next_stripped = next_line.strip()
                    if next_stripped and next_indent == 0:
                        break
                    i += 1
                continue
                
            new_lines.append(line)
            i += 1
            
        if not model_written:
            # Thêm mới model section vào cuối nếu chưa có
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            new_lines.append("\nmodel:\n")
            new_lines.append(f"  default: {model_config.get('default', 'default')}\n")
            new_lines.append(f"  provider: {model_config.get('provider', 'custom')}\n")
            new_lines.append(f"  base_url: {model_config.get('base_url', '')}\n")
            new_lines.append(f"  api_key: {model_config.get('api_key', '')}\n")
            new_lines.append(f"  context_length: {int(model_config.get('context_length', 70000))}\n")
            new_lines.append(f"  model: {model_config.get('model', 'default')}\n")
            
        # Đảm bảo thư mục cha tồn tại
        os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    except Exception as e:
        print(f"Error writing yaml config {yaml_path}: {e}")
        raise e

def get_all_profiles():
    """Lấy danh sách profile kết hợp trạng thái PM2 và config.yaml."""
    if not is_hermes_installed():
        return []
        
    profiles = ["default"]
    if os.path.exists(PROFILES_DIR):
        for item in os.listdir(PROFILES_DIR):
            if os.path.isdir(os.path.join(PROFILES_DIR, item)):
                profiles.append(item)
                
    pm2_apps = pm2_manager.get_pm2_list()
    pm2_dict = {app["name"]: app for app in pm2_apps}
    
    result = []
    for name in profiles:
        if name == "default":
            profile_path = HERMES_DIR
        else:
            profile_path = os.path.join(PROFILES_DIR, name)
            
        yaml_path = os.path.join(profile_path, "config.yaml")
        cfg = read_profile_config(yaml_path)
        
        pm2_name = f"hermes-{name}"
        pm2_info = pm2_dict.get(pm2_name, {
            "status": "offline",
            "cpu": 0,
            "memory": 0,
            "pid": None,
            "restart_count": 0,
            "uptime": None
        })
        
        result.append({
            "name": name,
            "path": profile_path,
            "model_default": cfg.get("default"),
            "provider": cfg.get("provider"),
            "base_url": cfg.get("base_url"),
            "model": cfg.get("model"),
            "context_length": cfg.get("context_length"),
            "status": pm2_info.get("status"),
            "cpu": pm2_info.get("cpu"),
            "memory": pm2_info.get("memory"),
            "pid": pm2_info.get("pid"),
            "restart_count": pm2_info.get("restart_count"),
            "uptime": pm2_info.get("uptime")
        })
    return result

def create_profile(name, model_config):
    """Tạo mới một profile Hermes Agent."""
    name = "".join(c for c in name if c.isalnum() or c in ('-', '_')).strip()
    if not name:
        raise Exception("Tên profile không hợp lệ.")
        
    if name == "default":
        raise Exception("Profile 'default' là mặc định của hệ thống.")
        
    profile_path = os.path.join(PROFILES_DIR, name)
    if os.path.exists(profile_path):
        raise Exception(f"Profile '{name}' đã tồn tại.")
        
    os.makedirs(profile_path, exist_ok=True)
    yaml_path = os.path.join(profile_path, "config.yaml")
    
    # Thử copy config.yaml mặc định từ profile default làm template nếu có
    default_yaml = os.path.join(HERMES_DIR, "config.yaml")
    if os.path.exists(default_yaml):
        shutil.copy(default_yaml, yaml_path)
        
    # Ghi đè cấu hình model mới
    write_profile_config(yaml_path, model_config)
    
    # Khởi chạy ngầm với PM2
    start_profile_gateway(name)
    return True

def start_profile_gateway(name):
    """Khởi chạy Gateway cho một profile bằng PM2 (có kiểm tra giải phóng cổng)."""
    if not is_hermes_installed():
        raise Exception("Hermes Agent chưa được cài đặt.")
        
    pm2_name = f"hermes-{name}"
    
    # Kiểm tra giải phóng cổng để tránh xung đột
    port = pm2_manager.get_port_by_app_name(pm2_name)
    if port:
        try:
            pm2_manager.kill_process_occupying_port(port, pm2_name)
        except Exception as e:
            print(f"[CHECK] Cảnh báo lỗi khi kiểm tra giải phóng cổng {port}: {e}")
            
    # Lệnh chạy qua PM2 sử dụng hermes.exe trong venv
    cmd = f'pm2 start "{VENV_HERMES_EXE}" --name "{pm2_name}" --cwd "{HERMES_DIR}" -- -p {name} gateway run --replace'
    
    # Chạy lệnh
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if res.returncode != 0:
        raise Exception(f"Lỗi khởi chạy PM2 cho profile '{name}': {res.stderr or res.stdout}")
    
    # Lưu trạng thái PM2
    try:
        pm2_manager.save_pm2_state()
    except Exception as e:
        print(f"Lưu ý: Không thể lưu trạng thái PM2 sau khi chạy profile gateway '{name}': {e}")
    return True

def stop_profile_gateway(name):
    """Dừng Gateway của profile trong PM2."""
    pm2_name = f"hermes-{name}"
    pm2_manager.stop_app(pm2_name)
    return True

def restart_profile_gateway(name):
    """Khởi động lại Gateway của profile trong PM2."""
    pm2_name = f"hermes-{name}"
    pm2_manager.restart_app(pm2_name)
    return True

def delete_profile(name):
    """Xóa hoàn toàn một profile Hermes."""
    if name == "default":
        raise Exception("Không thể xóa profile default của hệ thống.")
        
    pm2_name = f"hermes-{name}"
    # Xóa khỏi PM2
    try:
        pm2_manager.delete_app(pm2_name)
    except Exception as e:
        print(f"Lưu ý: Lỗi gỡ bỏ app PM2 '{pm2_name}': {e}")
        
    # Xóa thư mục profile
    profile_path = os.path.join(PROFILES_DIR, name)
    if os.path.exists(profile_path):
        shutil.rmtree(profile_path, ignore_errors=True)
    return True

def run_installation_worker():
    """Tác vụ cài đặt chạy ngầm (Git clone -> Venv -> Pip install)."""
    try:
        set_install_state("running", 10, "Bắt đầu cài đặt Hermes Agent...", append=False)
        os.makedirs(HERMES_DIR, exist_ok=True)
        
        # 1. Git clone
        if not os.path.exists(HERMES_AGENT_DIR):
            set_install_state("running", 20, "Đang tải mã nguồn Hermes Agent từ Github (NousResearch/hermes-agent)...")
            repo_url = "https://github.com/NousResearch/hermes-agent.git"
            
            # Sử dụng subprocess chạy git clone
            res = subprocess.run(f'git clone {repo_url} "{HERMES_AGENT_DIR}"', shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if res.returncode != 0:
                raise Exception(f"Lỗi git clone: {res.stderr or res.stdout}")
        else:
            set_install_state("running", 30, "Thư mục mã nguồn hermes-agent đã tồn tại, đang cập nhật mã nguồn mới nhất...")
            subprocess.run('git pull', shell=True, cwd=HERMES_AGENT_DIR, capture_output=True, encoding='utf-8', errors='ignore')
            
        # 2. Tạo Virtual Environment
        venv_dir = os.path.join(HERMES_AGENT_DIR, "venv")
        if not os.path.exists(VENV_PYTHON):
            set_install_state("running", 45, "Đang tạo môi trường ảo Python (virtualenv venv)...")
            res = subprocess.run(f'python -m venv "{venv_dir}"', shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if res.returncode != 0:
                raise Exception(f"Lỗi tạo venv: {res.stderr or res.stdout}")
                
        # 3. Pip install dependencies
        set_install_state("running", 65, "Đang cài đặt các dependencies thông qua pip install -e . (Quá trình này có thể mất 1-2 phút)...")
        # Upgrade pip trước
        subprocess.run(f'"{VENV_PYTHON}" -m pip install --upgrade pip', shell=True, capture_output=True, encoding='utf-8', errors='ignore')
        
        # Chạy pip install
        res = subprocess.run(f'"{VENV_PYTHON}" -m pip install -e .', shell=True, cwd=HERMES_AGENT_DIR, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if res.returncode != 0:
            raise Exception(f"Lỗi pip install: {res.stderr or res.stdout}")
            
        # 4. Ghi các file tiện ích bổ sung
        set_install_state("running", 85, "Đang cấu hình các file chạy ngầm mặc định...")
        
        # Ghi config.yaml mặc định cho profile default nếu chưa có
        default_yaml = os.path.join(HERMES_DIR, "config.yaml")
        if not os.path.exists(default_yaml):
            default_config = {
                "default": "default",
                "provider": "custom",
                "base_url": "http://localhost:20128/v1",
                "api_key": "default_key",
                "model": "default",
                "context_length": 70000
            }
            write_profile_config(default_yaml, default_config)
            
        # 5. Khởi chạy thử profile default với PM2
        set_install_state("running", 95, "Khởi chạy ngầm Hermes default profile bằng PM2...")
        try:
            start_profile_gateway("default")
        except Exception as e:
            set_install_state("running", 95, f"Lưu ý: Không thể khởi động profile default trong PM2: {e}")
            
        set_install_state("success", 100, "Cài đặt Hermes Agent thành công! Hệ thống đã sẵn sàng sử dụng.")
    except Exception as e:
        set_install_state("failed", 0, f"Quá trình cài đặt gặp lỗi: {str(e)}")

def install_hermes_agent_async():
    """Kích hoạt cài đặt Hermes Agent trong một thread riêng biệt."""
    state = get_install_state()
    if state["status"] == "running":
        return False
        
    thread = threading.Thread(target=run_installation_worker)
    thread.daemon = True
    thread.start()
    return True
