import subprocess
import json
import os
import shutil

# Thiết lập PM2_HOME nội bộ dự án
PARENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.environ["PM2_HOME"] = os.path.abspath(os.path.join(PARENT_DIR, ".pm2"))

def run_cmd(args, env=None):
    """Chạy lệnh hệ thống và trả về stdout, stderr, exit code (tự động cấu hình PATH và đồng bộ môi trường)."""
    if env is None:
        env = os.environ.copy()
        
    # Đồng bộ hóa các biến môi trường của Admin sang biến chuẩn của Windows phục vụ Service SYSTEM
    for key in ["APPDATA", "LOCALAPPDATA", "USERPROFILE"]:
        user_key = f"{key}_USER"
        if user_key in env and env[user_key]:
            env[key] = env[user_key]
            
    if "USERPROFILE" in env and env["USERPROFILE"]:
        env["HOME"] = env["USERPROFILE"]
        
    # Tự động bổ sung đường dẫn NPM Global vào PATH trên Windows để tìm thấy pm2
    appdata = env.get("APPDATA")
    if appdata:
        npm_path = os.path.abspath(os.path.join(appdata, "npm"))
        if npm_path not in env.get("PATH", ""):
            env["PATH"] = env.get("PATH", "") + os.pathsep + npm_path
            
    # Sử dụng shell=True trên Windows để nhận diện các lệnh npm, pm2
    result = subprocess.run(args, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', env=env)
    return result.stdout, result.stderr, result.returncode

def is_pm2_installed():
    """Kiểm tra xem PM2 đã được cài đặt chưa (bền bỉ, tránh lỗi rpc.sock)."""
    # 1. Chạy thử where pm2
    _, _, code = run_cmd("where pm2")
    if code == 0:
        return True
        
    # 2. Kiểm tra trực tiếp tệp pm2.cmd trong thư mục AppData
    appdata = os.environ.get("APPDATA_USER") or os.environ.get("APPDATA")
    if appdata:
        pm2_path = os.path.join(appdata, "npm", "pm2.cmd")
        if os.path.exists(pm2_path):
            return True
            
    # 3. Dự phòng check version
    stdout, stderr, code_ver = run_cmd("pm2 --version")
    if code_ver == 0 or "pm2" in stdout.lower() or "rpc.sock" in stderr.lower():
        return True
        
    return False

def get_pm2_list():
    """Lấy danh sách các ứng dụng đang được PM2 quản lý."""
    stdout, _, code = run_cmd("pm2 jlist")
    if code != 0 or not stdout.strip():
        return []
    try:
        # Trích xuất dòng chứa JSON thực tế (dòng bắt đầu bằng '[' và kết thúc bằng ']')
        json_str = ""
        lines = stdout.strip().split('\n')
        for line in reversed(lines):
            line_stripped = line.strip()
            if line_stripped.startswith('[') and line_stripped.endswith(']'):
                json_str = line_stripped
                break
        
        if not json_str:
            # Fallback nếu không tìm thấy dòng khớp hoàn toàn
            start_idx = stdout.find('[')
            if start_idx != -1:
                json_str = stdout[start_idx:]
            else:
                return []
                
        data = json.loads(json_str)
        apps = []
        for app in data:
            pm2_env = app.get("pm2_env", {})
            monit = app.get("monit", {})
            
            # Lấy biến môi trường PORT từ PM2 env nếu có
            env_vars = pm2_env.get("env", {}) or {}
            
            apps.append({
                "name": app.get("name"),
                "pid": app.get("pid"),
                "status": pm2_env.get("status"), # online, stopped, errored, etc.
                "cpu": monit.get("cpu", 0),
                "memory": monit.get("memory", 0), # in bytes
                "uptime": pm2_env.get("pm_uptime"),
                "restart_count": pm2_env.get("restart_time", 0),
                "out_log": pm2_env.get("pm_out_log_path"),
                "err_log": pm2_env.get("pm_err_log_path"),
                "cwd": pm2_env.get("pm_cwd"),
                "env": env_vars
            })
        return apps
    except Exception as e:
        print(f"Error parsing pm2 jlist: {e}")
        return []

def save_pm2_state():
    """Lưu trạng thái hiện tại của PM2 để khôi phục khi khởi động lại."""
    run_cmd("pm2 save")

def get_port_by_app_name(name, cwd=None):
    """Lấy số cổng của một ứng dụng dựa trên tên và cấu hình của nó."""
    # 1. Nếu là profile Hermes gateway
    if name.startswith("hermes-"):
        profile_name = name.replace("hermes-", "")
        user_profile = os.environ.get("USERPROFILE_USER") or os.environ.get("USERPROFILE")
        if user_profile:
            if profile_name == "default":
                profile_path = os.path.join(user_profile, "AppData", "Local", "hermes")
            else:
                profile_path = os.path.join(user_profile, "AppData", "Local", "hermes", "profiles", profile_name)
            
            yaml_path = os.path.join(profile_path, "config.yaml")
            if os.path.exists(yaml_path):
                try:
                    # Đọc config.yaml tìm gateway port thủ công
                    with open(yaml_path, 'r', encoding='utf-8', errors='ignore') as f:
                        in_gateway = False
                        for line in f:
                            line_strip = line.strip()
                            if line_strip.startswith("gateway:"):
                                in_gateway = True
                                continue
                            if in_gateway and line.startswith(("", " " * 0)) and not line.startswith(" "):
                                if line_strip and not line_strip.startswith("#"):
                                    in_gateway = False
                            if in_gateway and "port:" in line_strip:
                                parts = line_strip.split(":")
                                if len(parts) >= 2:
                                    val = parts[1].strip()
                                    if "#" in val:
                                        val = val.split("#")[0].strip()
                                    val = val.replace("'", "").replace('"', '').replace("«", "").replace("»", "")
                                    return int(val)
                except Exception as e:
                    print(f"[CHECK] Lỗi parse config.yaml cho {profile_name}: {e}")
        # Fallback mặc định
        if profile_name == "default":
            return 8642
        elif profile_name == "zalo":
            return 20128
        elif profile_name == "editvideo":
            return 7742
            
    # 2. Nếu là instance 9router proxy
    else:
        # Thử đọc instances.json
        instances_json_path = os.path.join(PARENT_DIR, "instances.json")
        if os.path.exists(instances_json_path):
            try:
                with open(instances_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if name in data and "port" in data[name]:
                        return int(data[name]["port"])
            except:
                pass
                
        # Thử đọc file .env trực tiếp từ cwd nếu có
        if cwd:
            env_path = os.path.join(cwd, ".env")
            if os.path.exists(env_path):
                try:
                    with open(env_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            line_strip = line.strip()
                            if line_strip.startswith("PORT="):
                                return int(line_strip.split("=")[1].strip())
                except:
                    pass
    return None

def kill_process_occupying_port(port, pm2_name):
    """
    Kiểm tra và tiêu diệt tiến trình ngoài PM2 đang chiếm dụng cổng TCP để tránh xung đột.
    """
    if not port:
        return
        
    print(f"[CHECK] Đang kiểm tra xung đột cổng {port} cho ứng dụng '{pm2_name}'...")
    
    # 1. Tìm PID chiếm cổng bằng netstat (Windows)
    cmd = f'netstat -ano | findstr LISTENING | findstr :{port}'
    stdout, _, code = run_cmd(cmd)
    
    if code != 0 or not stdout.strip():
        print(f"[CHECK] Cổng {port} đang trống. Không có xung đột.")
        return
        
    # Phân tích PID
    lines = stdout.strip().split('\n')
    pids_to_kill = set()
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 5:
            local_addr = parts[1]
            pid_str = parts[-1]
            # Đảm bảo khớp cổng chính xác ở cuối địa chỉ local
            if local_addr.endswith(f":{port}"):
                try:
                    pids_to_kill.add(int(pid_str))
                except ValueError:
                    pass
                    
    if not pids_to_kill:
        return
        
    # 2. Lấy danh sách PID của PM2 hiện tại
    pm2_pids = set()
    try:
        apps = get_pm2_list()
        for app in apps:
            # Bỏ qua app hiện tại đang chuẩn bị start/restart
            if app["name"] == pm2_name:
                continue
            if app.get("pid"):
                try:
                    pm2_pids.add(int(app["pid"]))
                except:
                    pass
    except Exception as e:
        print(f"[CHECK] Lỗi lấy danh sách PM2: {e}")
        
    # 3. Kill các PID xung đột nếu không phải của PM2 hoặc thuộc app PM2 khác
    for pid in pids_to_kill:
        if pid in pm2_pids:
            print(f"[CONFLICT] Cổng {port} bị chiếm bởi app PM2 khác (PID: {pid}). Tiêu diệt để nhường quyền chạy...")
            run_cmd(f"taskkill /F /PID {pid}")
        else:
            print(f"[CONFLICT] Phát hiện tiến trình mồ côi ngoài PM2 chiếm cổng {port} (PID: {pid}). Tiến hành dừng xóa...")
            stdout_kill, stderr_kill, code_kill = run_cmd(f"taskkill /F /PID {pid}")
            if code_kill == 0:
                print(f"[SUCCESS] Đã tiêu diệt tiến trình chiếm cổng: PID {pid}")
            else:
                print(f"[ERROR] Thất bại khi kill PID {pid}: {stderr_kill or stdout_kill}")

def start_app(name, cwd, script="npm", args="start", env=None):
    """Khởi chạy ứng dụng trong PM2 (có kiểm tra xung đột cổng)."""
    # Đảm bảo đường dẫn tuyệt đối cho cwd
    cwd = os.path.abspath(cwd)
    
    # Kiểm tra và giải phóng cổng trước khi chạy
    port = get_port_by_app_name(name, cwd)
    if port:
        kill_process_occupying_port(port, name)
        
    # Chuẩn bị lệnh chạy
    if script == "npm":
        # Trên Windows, chạy npm start cần thêm dấu -- trước args
        cmd = f'pm2 start npm --name "{name}" --cwd "{cwd}" -- {args}'
    else:
        # Nếu script là file js (ví dụ app.js)
        script_path = os.path.join(cwd, script)
        cmd = f'pm2 start "{script_path}" --name "{name}" --cwd "{cwd}"'
        if args:
            cmd += f' -- {args}'
            
    # Hợp nhất môi trường chạy nếu có
    subprocess_env = os.environ.copy()
    if env:
        subprocess_env.update(env)
        
    stdout, stderr, code = run_cmd(cmd, env=subprocess_env)
    if code != 0:
        raise Exception(f"Failed to start app {name}: {stderr or stdout}")
    save_pm2_state()
    return True

def stop_app(name):
    """Dừng ứng dụng trong PM2."""
    stdout, stderr, code = run_cmd(f'pm2 stop "{name}"')
    if code != 0:
        raise Exception(f"Failed to stop app {name}: {stderr or stdout}")
    save_pm2_state()
    return True

def restart_app(name):
    """Khởi động lại ứng dụng trong PM2 (có kiểm tra xung đột cổng)."""
    # Kiểm tra và giải phóng cổng trước khi khởi động lại
    port = get_port_by_app_name(name)
    if port:
        kill_process_occupying_port(port, name)
        
    stdout, stderr, code = run_cmd(f'pm2 restart "{name}"')
    if code != 0:
        raise Exception(f"Failed to restart app {name}: {stderr or stdout}")
    save_pm2_state()
    return True

def delete_app(name):
    """Xóa ứng dụng khỏi danh sách PM2."""
    stdout, stderr, code = run_cmd(f'pm2 delete "{name}"')
    if code != 0:
        # Nếu app không tồn tại thì coi như đã xóa
        if "not found" in (stderr or stdout).lower():
            return True
        raise Exception(f"Failed to delete app {name}: {stderr or stdout}")
    save_pm2_state()
    return True

def get_app_logs(name, max_lines=150):
    """Đọc file log của ứng dụng từ PM2."""
    apps = get_pm2_list()
    app = next((a for a in apps if a["name"] == name), None)
    if not app:
        return f"Application '{name}' not found in PM2."
        
    out_log_path = app.get("out_log")
    err_log_path = app.get("err_log")
    
    logs = []
    
    # Hàm đọc n dòng cuối của file
    def read_tail(filepath, label):
        if not filepath or not os.path.exists(filepath):
            return [f"--- {label} File not found or empty ---"]
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                tail_lines = lines[-max_lines:]
                return [f"[{label}] {line.strip()}" for line in tail_lines]
        except Exception as e:
            return [f"Error reading {label} logs: {str(e)}"]

    # Đọc cả log output và log error
    if out_log_path:
        logs.extend(read_tail(out_log_path, "STDOUT"))
    if err_log_path:
        logs.extend(read_tail(err_log_path, "STDERR"))
        
    if not logs:
        return "No logs found."
        
    return "\n".join(logs)
