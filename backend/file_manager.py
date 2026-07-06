import os
import shutil
import json
import socket
import subprocess
from datetime import datetime

INSTANCES_JSON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "instances.json"))
INSTANCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "instances"))

def load_instances():
    """Đọc danh sách instances từ file instances.json (tự động căn chỉnh đường dẫn động)."""
    if not os.path.exists(INSTANCES_JSON):
        return {}
    try:
        with open(INSTANCES_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Tự động căn chỉnh đường dẫn tuyệt đối tương ứng với vị trí thư mục hiện tại (di động)
            for name, cfg in data.items():
                if "path" in cfg:
                    dir_name = os.path.basename(cfg["path"])
                    cfg["path"] = os.path.abspath(os.path.join(INSTANCES_DIR, dir_name))
            return data
    except Exception as e:
        print(f"Error loading instances.json: {e}")
        return {}

def save_instances(data):
    """Ghi danh sách instances vào file instances.json."""
    try:
        with open(INSTANCES_JSON, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving instances.json: {e}")
        return False

def is_port_in_use(port):
    """Kiểm tra xem một cổng TCP có đang được sử dụng hay không."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_unused_port(start_port=20128, max_port=20200):
    """Tìm cổng TCP trống gần nhất từ start_port (tránh các cổng đã đăng ký)."""
    configs = load_instances()
    used_ports = {cfg.get("port") for cfg in configs.values() if cfg.get("port")}
    
    port = start_port
    while port <= max_port:
        if port not in used_ports and not is_port_in_use(port):
            return port
        port += 1
    return None

def ensure_9router_installed(src_dir):
    """
    Kiểm tra và tự động cài đặt 9router globally qua npm nếu thư mục nguồn không tồn tại.
    """
    if os.path.exists(src_dir):
        return True
        
    # Kiểm tra xem đường dẫn có trỏ tới thư mục node_modules của 9router hay không
    if "9router" in src_dir.lower():
        print(f"Thư mục nguồn 9router không tồn tại. Đang tự động tải và cài đặt 9router qua npm...")
        try:
            # Chạy lệnh npm install -g 9router
            import subprocess
            res = subprocess.run("npm install -g 9router", shell=True, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                print("Cài đặt 9router thành công!")
                if os.path.exists(src_dir):
                    return True
            else:
                print(f"Lỗi cài đặt 9router: {res.stderr or res.stdout}")
        except Exception as e:
            print(f"Không thể tự động cài đặt 9router: {e}")
            
    return False

def create_instance_files(name, src_dir, port, api_key, additional_env=None):
    """
    Nhân bản thư mục proxy nguồn và tạo cấu hình .env mới (tự động cài đặt 9router nếu thiếu).
    """
    if not os.path.exists(src_dir):
        ensure_9router_installed(src_dir)
        
    if not os.path.exists(src_dir):
        raise Exception(f"Thư mục nguồn 9router không tồn tại: {src_dir}. Vui lòng kết nối Internet hoặc tự cài bằng lệnh: npm install -g 9router")
        
    # Tạo thư mục chứa các instance nếu chưa có
    if not os.path.exists(INSTANCES_DIR):
        os.makedirs(INSTANCES_DIR)
        
    dst_dir = os.path.join(INSTANCES_DIR, name)
    if os.path.exists(dst_dir):
        raise Exception(f"Thư mục instance '{name}' đã tồn tại: {dst_dir}")
        
    print(f"Copying {src_dir} to {dst_dir}...")
    # Nhân bản thư mục (bỏ qua node_modules để copy nhanh hơn, người dùng sẽ chạy npm install sau hoặc copy cả)
    # Tuy nhiên, để tiện cho người dùng chạy được ngay, ta nên copy toàn bộ, hoặc bỏ qua node_modules nếu muốn nhanh.
    # Thông thường, việc copy node_modules trên Windows rất lâu. Ta sẽ cho phép bỏ qua node_modules và tự động chạy `npm install` sau,
    # HOẶC copy toàn bộ nếu người dùng muốn. Ở đây, ta định nghĩa bộ lọc bỏ qua node_modules và .git.
    def ignore_patterns(path, names):
        ignored = []
        for name in names:
            if name in ('node_modules', '.git', '.env', 'dist', 'build'):
                ignored.append(name)
        return ignored

    shutil.copytree(src_dir, dst_dir, ignore=ignore_patterns)
    
    # Tạo/Ghi đè file .env mới
    env_path = os.path.join(dst_dir, ".env")
    env_data = {
        "PORT": str(port),
        "API_KEY": api_key
    }
    
    # Gộp thêm các biến môi trường bổ sung nếu có
    if additional_env:
        env_data.update(additional_env)
        
    # Ghi file .env
    with open(env_path, 'w', encoding='utf-8') as f:
        for k, v in env_data.items():
            f.write(f"{k}={v}\n")
            
    # Tự động quét và copy lại tất cả thư mục node_modules từ nguồn (bao gồm cả app/node_modules nếu có)
    for root, dirs, files in os.walk(src_dir):
        if "node_modules" in dirs:
            rel_path = os.path.relpath(os.path.join(root, "node_modules"), src_dir)
            src_nm = os.path.join(src_dir, rel_path)
            dst_nm = os.path.join(dst_dir, rel_path)
            
            print(f"Copying node_modules from {src_nm} to {dst_nm}...")
            os.makedirs(os.path.dirname(dst_nm), exist_ok=True)
            
            try:
                # Dùng robocopy trên Windows với R:1 W:1 để tránh treo file nếu gặp file bị khóa
                subprocess.run(f'robocopy "{src_nm}" "{dst_nm}" /E /R:1 /W:1 /NDL /NFL /NJH /NJS /nc /ns /np', shell=True)
            except Exception as e:
                print(f"Error copying {rel_path} with robocopy: {e}")
                try:
                    shutil.copytree(src_nm, dst_nm)
                except Exception as ex:
                    print(f"Failed to copy {rel_path}: {ex}")
                
    return dst_dir

def read_env_file(env_path):
    """Đọc file .env thành dictionary."""
    if not os.path.exists(env_path):
        return {}
    config = {}
    with open(env_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            config[k.strip()] = v.strip()
    return config

def write_env_file(env_path, config_dict):
    """Ghi dictionary vào file .env."""
    with open(env_path, 'w', encoding='utf-8') as f:
        for k, v in config_dict.items():
            f.write(f"{k}={v}\n")
    return True

def detect_source_directories():
    """Tự động tìm kiếm các thư mục nguồn 9router/workspace khả dụng trên ổ C, D, hoặc các thư mục profile."""
    sources = []
    
    # 1. Thư mục template tích hợp sẵn của 9routerpm
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "template"))
    if os.path.exists(template_dir):
        try:
            if len(os.listdir(template_dir)) > 0:
                sources.append({
                    "name": "Bản mẫu tích hợp (config/template)",
                    "path": template_dir
                })
        except Exception:
            pass
        
    # 2. Thư mục profiles của Hermes (Thường nằm ở ổ C: AppData)
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        hermes_profiles_dir = os.path.join(user_profile, "AppData", "Local", "hermes", "profiles")
        if os.path.exists(hermes_profiles_dir):
            try:
                for profile_name in os.listdir(hermes_profiles_dir):
                    p_path = os.path.join(hermes_profiles_dir, profile_name)
                    if not os.path.isdir(p_path):
                        continue
                    
                    # Kiểm tra workspace con trong profile
                    workspace_path = os.path.join(p_path, "workspace")
                    if os.path.exists(workspace_path):
                        sources.append({
                            "name": f"Hermes Profile: {profile_name} (workspace)",
                            "path": os.path.abspath(workspace_path)
                        })
                    
                    # Hoặc chính thư mục profile
                    sources.append({
                        "name": f"Hermes Profile: {profile_name} (gốc)",
                        "path": os.path.abspath(p_path)
                    })
            except Exception as e:
                print(f"Error scanning hermes profiles: {e}")
                
    # 2.5. Thư mục 9router cài đặt toàn cục qua npm (Global npm node_modules)
    appdata = os.environ.get("APPDATA")
    if appdata:
        global_9router = os.path.join(appdata, "npm", "node_modules", "9router")
        if os.path.exists(global_9router):
            sources.append({
                "name": "Bản mẫu 9router gốc hệ thống (NPM Global)",
                "path": os.path.abspath(global_9router)
            })
        else:
            sources.append({
                "name": "Bản mẫu 9router gốc hệ thống (NPM Global - Chưa cài, tự động tải khi chọn)",
                "path": os.path.abspath(global_9router)
            })
                
    # 3. Quét các thư mục lân cận cùng cấp với thư mục dự án hiện tại
    try:
        parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if os.path.exists(parent_dir):
            for item in os.listdir(parent_dir):
                item_path = os.path.join(parent_dir, item)
                if os.path.isdir(item_path) and item.lower() != "9routerpm" and not item.startswith("."):
                    if os.path.exists(os.path.join(item_path, "package.json")):
                        sources.append({
                            "name": f"Thư mục dự án: {item}",
                            "path": os.path.abspath(item_path)
                        })
    except Exception:
        pass
        
    return sources
