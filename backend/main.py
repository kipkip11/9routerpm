import os
import shutil
import sys
import asyncio

# Khắc phục lỗi ConnectionResetError [WinError 10054] làm sập asyncio trên Windows
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception as e:
        pass

from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict

# Đảm bảo thư mục cha của 'backend' nằm trong sys.path khi chạy trực tiếp script
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Thiết lập biến môi trường PM2_HOME nội bộ dự án để chạy 24/7 đồng bộ tài khoản SYSTEM và User
os.environ["PM2_HOME"] = os.path.abspath(os.path.join(parent_dir, ".pm2"))

from backend import pm2_manager
from backend import file_manager
from backend import hermes_manager

# Mô hình dữ liệu cho Hermes Agent
class HermesProfileCreate(BaseModel):
    name: str
    default: str
    provider: str
    base_url: str
    api_key: str
    context_length: Optional[int] = 70000

class HermesProfileAction(BaseModel):
    action: str  # start, stop, restart

class HermesProfileUpdate(BaseModel):
    default: str
    provider: str
    base_url: str
    api_key: str
    context_length: Optional[int] = 70000

app = FastAPI(title="9router PM2 Manager", description="API quản lý nhiều instance proxy 9router")

@app.on_event("startup")
async def startup_event():
    import threading
    print("----- [STARTUP] KHOI DONG HE THONG TU DONG -----")
    
    def run_startup_tasks():
        import subprocess
        try:
            # Hợp nhất môi trường chạy và thêm NPM PATH để tìm thấy lệnh pm2
            env = os.environ.copy()
            appdata = os.environ.get("APPDATA")
            if appdata:
                npm_path = os.path.abspath(os.path.join(appdata, "npm"))
                if npm_path not in env.get("PATH", ""):
                    env["PATH"] = env.get("PATH", "") + os.pathsep + npm_path
            
            # Cài đặt PM2 toàn cục nếu chưa có
            try:
                print("[STARTUP] Kiem tra và đảm bảo PM2 duoc cai dat...")
                subprocess.run("npm install -g pm2", shell=True, capture_output=True, env=env, timeout=30, encoding='utf-8', errors='ignore')
            except subprocess.TimeoutExpired:
                print("[STARTUP] npm install -g pm2 bi qua han (timeout).")
            except Exception as e:
                print(f"[STARTUP] Loi kiem tra npm install: {e}")
                
            # Phục hồi các tiến trình PM2 cũ đã lưu
            try:
                print("[STARTUP] Dang goi pm2 resurrect de khoi phuc cac tien trinh cu...")
                res = subprocess.run("pm2 resurrect", shell=True, capture_output=True, text=True, env=env, timeout=20, encoding='utf-8', errors='ignore')
                print(f"[STARTUP] PM2 resurrect stdout: {res.stdout.strip()}")
                if res.stderr:
                    print(f"[STARTUP] PM2 resurrect stderr: {res.stderr.strip()}")
            except subprocess.TimeoutExpired:
                print("[STARTUP] pm2 resurrect bi qua han (timeout).")
            except Exception as e:
                print(f"[STARTUP] Loi khi tu dong PM2 resurrect: {e}")
        except Exception as startup_err:
            print(f"[STARTUP] Loi tong quat trong thread startup: {startup_err}")
        print("----- [STARTUP] HOAN TAT KHOI DONG BACKGROUND -----")
        
        # Kích hoạt Watchdog giám sát Online/Offline của các profile Hermes
        try:
            from backend import alerts_manager
            alerts_manager.start_watchdog()
        except Exception as e:
            print(f"[STARTUP] Loi khoi dong Alerts Watchdog: {e}")
        
    threading.Thread(target=run_startup_tasks, daemon=True).start()

# Đường dẫn tới thư mục frontend
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

# Mô hình dữ liệu cho các request API
class InstanceCreate(BaseModel):
    name: str
    src_dir: str
    port: Optional[int] = None
    api_key: str
    script: Optional[str] = "npm"
    args: Optional[str] = "start"

class ActionRequest(BaseModel):
    action: str  # start, stop, restart, delete
    delete_files: Optional[bool] = False

class PurgeRequest(BaseModel):
    tasks: Optional[list] = []
    pids: Optional[list] = []

# API endpoints
@app.get("/api/alerts/config")
def get_alerts_config():
    """Lấy cấu hình cảnh báo hiện tại."""
    from backend import alerts_manager
    return alerts_manager.load_config()

@app.post("/api/alerts/config")
def post_alerts_config(config: dict = Body(...)):
    """Lưu cấu hình cảnh báo mới."""
    from backend import alerts_manager
    success = alerts_manager.save_config(config)
    if not success:
        raise HTTPException(status_code=500, detail="Không thể ghi cấu hình cảnh báo.")
    return {"success": True, "message": "Lưu cấu hình cảnh báo thành công."}

@app.post("/api/alerts/test")
def post_alerts_test(req: dict = Body(...)):
    """Gửi thử tin nhắn test đến bot của một profile cụ thể."""
    from backend import alerts_manager
    profile_name = req.get("profile_name")
    
    config = alerts_manager.load_config()
    profiles = config.get("profiles", {})
    if profile_name not in profiles:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy profile '{profile_name}' trong cấu hình.")
        
    p_cfg = profiles[profile_name]
    msg = (
        f"🔔 <b>TIN NHẮN KIỂM TRA (TEST BOT)</b>\n\n"
        f"Profile: <code>{profile_name}</code>\n"
        f"Nội dung: Kết nối thành công! Hệ thống cảnh báo tự động hoạt động tốt.\n"
        f"Thời gian: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    success, msg_err = alerts_manager.send_alert(profile_name, p_cfg, msg)
    if not success:
        raise HTTPException(status_code=400, detail=msg_err)
    return {"success": True, "message": "Gửi tin nhắn kiểm tra thành công."}

@app.get("/api/cleanup/scan")
def get_cleanup_scan():
    """Quét các tiến trình PM2 cũ và các tác vụ lên lịch Scheduler xung đột."""
    from backend import cleanup_manager
    return cleanup_manager.scan_system()

@app.post("/api/cleanup/purge")
def post_cleanup_purge(req: PurgeRequest):
    """Xóa bỏ Scheduled Tasks và tiêu diệt tiến trình PM2 cũ được chọn."""
    from backend import cleanup_manager
    return cleanup_manager.purge_system(tasks_to_delete=req.tasks, pids_to_kill=req.pids)

@app.get("/api/status")
def get_system_status():
    """Lấy trạng thái tổng quan của hệ thống và PM2."""
    pm2_installed = pm2_manager.is_pm2_installed()
    pm2_apps = pm2_manager.get_pm2_list() if pm2_installed else []
    
    total_apps = len(pm2_apps)
    running_apps = sum(1 for app in pm2_apps if app["status"] == "online")
    
    return {
        "pm2_installed": pm2_installed,
        "total_instances": total_apps,
        "running_instances": running_apps,
        "os": "Windows"
    }

@app.get("/api/instances")
def get_all_instances():
    """Lấy danh sách các instance kết hợp cấu hình và tự động import các proxy 9router đang chạy ngầm trong PM2."""
    configs = file_manager.load_instances()
    pm2_apps = pm2_manager.get_pm2_list()
    pm2_dict = {app["name"]: app for app in pm2_apps}
    
    config_changed = False
    
    # Tự động quét và import các tiến trình PM2 đang chạy chứa chữ '9router'
    for app in pm2_apps:
        app_name = app.get("name")
        if not app_name:
            continue
            
        # Kiểm tra xem app này đã nằm trong instances.json chưa
        if app_name not in configs:
            # Điều kiện nhận dạng: Tên app chứa '9router' và không phải là tiến trình web quản lý '9routerpm' hay 'main'
            is_9router_proxy = "9router" in app_name.lower() and app_name.lower() not in ["9routerpm", "main"]
            
            # Hoặc thư mục cwd chứa '9router' hoặc 'instances'
            cwd_path = app.get("cwd") or ""
            is_in_instances_dir = "instances" in cwd_path.lower() or "9router" in cwd_path.lower()
            
            if is_9router_proxy or (cwd_path and is_in_instances_dir):
                # Tự động phân giải PORT của app PM2
                port = None
                env_port = app.get("env", {}).get("PORT")
                if env_port:
                    try:
                        port = int(env_port)
                    except:
                        pass
                
                # Nếu không lấy được port từ env, thử quét file .env của nó
                if not port and cwd_path and os.path.exists(os.path.join(cwd_path, ".env")):
                    try:
                        with open(os.path.join(cwd_path, ".env"), 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                if line.strip().startswith("PORT="):
                                    port = int(line.strip().split("=")[1].strip())
                                    break
                    except:
                        pass
                
                # Thêm vào config
                configs[app_name] = {
                    "name": app_name,
                    "port": port or 20128,  # Fallback port mặc định
                    "path": cwd_path or os.path.abspath(os.path.join(file_manager.INSTANCES_DIR, app_name)),
                    "script": "npm",
                    "args": "start",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                config_changed = True
                print(f"[AUTO-IMPORT] Đã tự động nhận dạng và nạp proxy '{app_name}' đang chạy ngầm vào danh sách quản lý.")
                
    if config_changed:
        file_manager.save_instances(configs)
        
    result = []
    for name, cfg in configs.items():
        pm2_info = pm2_dict.get(name, {
            "status": "offline",
            "cpu": 0,
            "memory": 0,
            "pid": None,
            "restart_count": 0,
            "uptime": None
        })
        
        result.append({
            "name": name,
            "port": cfg.get("port"),
            "path": cfg.get("path"),
            "script": cfg.get("script", "npm"),
            "args": cfg.get("args", "start"),
            "created_at": cfg.get("created_at"),
            "status": pm2_info.get("status"),
            "cpu": pm2_info.get("cpu"),
            "memory": pm2_info.get("memory"),
            "pid": pm2_info.get("pid"),
            "restart_count": pm2_info.get("restart_count"),
            "uptime": pm2_info.get("uptime")
        })
        
    return result

@app.post("/api/instances")
def create_instance(data: InstanceCreate):
    """Tạo mới một instance 9router proxy."""
    # Làm sạch tên instance (chỉ cho phép chữ, số, gạch ngang, gạch dưới)
    name = "".join(c for c in data.name if c.isalnum() or c in ('-', '_')).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tên instance không hợp lệ.")
        
    configs = file_manager.load_instances()
    if name in configs:
        raise HTTPException(status_code=400, detail=f"Instance với tên '{name}' đã tồn tại.")
        
    # Tìm cổng trống nếu không chỉ định
    port = data.port
    if not port:
        port = file_manager.find_unused_port()
        if not port:
            raise HTTPException(status_code=500, detail="Không tìm thấy cổng TCP nào trống.")
    else:
        # Kiểm tra xem cổng này đã được đăng ký cho instance nào khác chưa (kể cả khi đang offline)
        used_ports = {cfg.get("port") for cfg in configs.values() if cfg.get("port")}
        if port in used_ports:
            raise HTTPException(status_code=400, detail=f"Cổng {port} đã được đăng ký bởi một instance khác trong danh sách.")
        if file_manager.is_port_in_use(port):
            raise HTTPException(status_code=400, detail=f"Cổng {port} đang được sử dụng bởi một ứng dụng khác ngoài hệ thống.")
        
    try:
        # 1. Nhân bản thư mục và cấu hình .env
        dst_dir = file_manager.create_instance_files(
            name=name,
            src_dir=data.src_dir,
            port=port,
            api_key=data.api_key
        )
        
        # 2. Khởi chạy với PM2
        pm2_manager.start_app(
            name=name,
            cwd=dst_dir,
            script=data.script,
            args=data.args,
            env={
                "PORT": str(port),
                "API_KEY": data.api_key
            }
        )
        
        # 3. Lưu thông tin vào database json
        configs[name] = {
            "name": name,
            "port": port,
            "path": dst_dir,
            "script": data.script,
            "args": data.args,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        file_manager.save_instances(configs)
        
        return {"success": True, "detail": f"Đã tạo và chạy thành công instance '{name}' tại cổng {port}."}
    except Exception as e:
        # Rollback dọn dẹp thư mục nếu tạo lỗi
        dst_dir = os.path.join(file_manager.INSTANCES_DIR, name)
        if os.path.exists(dst_dir):
            try:
                shutil.rmtree(dst_dir)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo instance: {str(e)}")

@app.post("/api/instances/{name}/action")
def execute_instance_action(name: str, req: ActionRequest):
    """Thực hiện các thao tác start, stop, restart, delete đối với proxy."""
    configs = file_manager.load_instances()
    if name not in configs and req.action != "delete":
        raise HTTPException(status_code=404, detail=f"Không tìm thấy instance '{name}'.")
        
    try:
        if req.action == "start":
            cfg = configs[name]
            env_path = os.path.join(cfg["path"], ".env")
            env_data = file_manager.read_env_file(env_path)
            pm2_manager.start_app(
                name, 
                cfg["path"], 
                cfg.get("script", "npm"), 
                cfg.get("args", "start"),
                env=env_data
            )
        elif req.action == "stop":
            pm2_manager.stop_app(name)
        elif req.action == "restart":
            pm2_manager.restart_app(name)
        elif req.action == "delete":
            # 1. Xóa khỏi PM2
            try:
                pm2_manager.delete_app(name)
            except Exception as e:
                print(f"Lưu ý: Không thể xóa app '{name}' khỏi PM2 (có thể app chưa từng chạy): {e}")
                
            # 2. Xóa cấu hình khỏi database JSON
            path_to_delete = None
            if name in configs:
                path_to_delete = configs[name].get("path")
                del configs[name]
                file_manager.save_instances(configs)
                
            # 3. Xóa thư mục files nếu người dùng yêu cầu
            if req.delete_files and path_to_delete and os.path.exists(path_to_delete):
                print(f"Xóa thư mục instance: {path_to_delete}")
                shutil.rmtree(path_to_delete, ignore_errors=True)
                
            return {"success": True, "detail": f"Đã xóa hoàn toàn instance '{name}'."}
        else:
            raise HTTPException(status_code=400, detail="Hành động không hợp lệ.")
            
        return {"success": True, "detail": f"Hành động '{req.action}' thực hiện thành công."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi thực thi: {str(e)}")

@app.get("/api/instances/{name}/logs")
def get_instance_logs(name: str):
    """Lấy log thời gian thực của instance."""
    logs = pm2_manager.get_app_logs(name)
    return {"name": name, "logs": logs}

@app.get("/api/instances/{name}/config")
def get_instance_config(name: str):
    """Đọc file cấu hình .env của instance."""
    configs = file_manager.load_instances()
    if name not in configs:
        raise HTTPException(status_code=404, detail="Không tìm thấy instance.")
    env_path = os.path.join(configs[name]["path"], ".env")
    env_data = file_manager.read_env_file(env_path)
    return env_data

@app.put("/api/instances/{name}/config")
def update_instance_config(name: str, config_data: Dict[str, str]):
    """Cập nhật lại file cấu hình .env của instance."""
    configs = file_manager.load_instances()
    if name not in configs:
        raise HTTPException(status_code=404, detail="Không tìm thấy instance.")
        
    env_path = os.path.join(configs[name]["path"], ".env")
    try:
        # Đọc cấu hình cũ để kiểm tra xem có đổi cổng không
        old_config = file_manager.read_env_file(env_path)
        old_port = int(old_config.get("PORT", 0))
        new_port = int(config_data.get("PORT", 0))
        
        # Nếu đổi sang cổng mới, phải check xem cổng mới có bị chiếm dụng không
        if new_port != old_port and file_manager.is_port_in_use(new_port):
            raise HTTPException(status_code=400, detail=f"Cổng mới {new_port} đang được sử dụng bởi ứng dụng khác.")
            
        file_manager.write_env_file(env_path, config_data)
        
        # Cập nhật cổng mới vào instances.json
        configs[name]["port"] = new_port
        file_manager.save_instances(configs)
        
        # Tự động restart để áp dụng cấu hình mới
        try:
            pm2_manager.restart_app(name)
        except Exception:
            pass
            
        return {"success": True, "detail": "Cập nhật cấu hình thành công."}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Lỗi cập nhật cấu hình: {str(e)}")

@app.get("/api/detect-sources")
def detect_source_directories():
    """Tự động phát hiện các thư mục nguồn 9router/workspace khả dụng."""
    return file_manager.detect_source_directories()

# --- Hermes Agent API Endpoints ---

@app.get("/api/hermes/status")
def get_hermes_status():
    """Lấy trạng thái cài đặt chung của Hermes Agent và tiến trình cài đặt hiện tại."""
    installed = hermes_manager.is_hermes_installed()
    install_state = hermes_manager.get_install_state()
    return {
        "installed": installed,
        "install_state": install_state
    }

@app.post("/api/hermes/install")
def install_hermes(background_tasks: BackgroundTasks):
    """Kích hoạt cài đặt Hermes Agent tự động chạy ngầm."""
    state = hermes_manager.get_install_state()
    if state["status"] == "running":
        return {"success": False, "detail": "Quá trình cài đặt đang diễn ra."}
        
    success = hermes_manager.install_hermes_agent_async()
    if success:
        return {"success": True, "detail": "Đã bắt đầu cài đặt Hermes Agent ở chế độ chạy ngầm."}
    else:
        return {"success": False, "detail": "Không thể bắt đầu cài đặt."}

@app.get("/api/hermes/install/progress")
def get_hermes_install_progress():
    """Lấy log và tiến trình cài đặt chi tiết."""
    return hermes_manager.get_install_state()

@app.get("/api/hermes/profiles")
def get_hermes_profiles():
    """Lấy danh sách tất cả các profile Hermes."""
    if not hermes_manager.is_hermes_installed():
        raise HTTPException(status_code=400, detail="Hermes Agent chưa được cài đặt.")
    return hermes_manager.get_all_profiles()

@app.post("/api/hermes/profiles")
def create_hermes_profile(data: HermesProfileCreate):
    """Tạo mới một profile Hermes Agent."""
    if not hermes_manager.is_hermes_installed():
        raise HTTPException(status_code=400, detail="Hermes Agent chưa được cài đặt.")
        
    try:
        model_config = {
            "default": data.default,
            "provider": data.provider,
            "base_url": data.base_url,
            "api_key": data.api_key,
            "model": data.default,  # model name giống default
            "context_length": data.context_length or 70000
        }
        hermes_manager.create_profile(data.name, model_config)
        return {"success": True, "detail": f"Đã tạo thành công profile Hermes '{data.name}'."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/hermes/profiles/{name}")
def update_hermes_profile(name: str, data: HermesProfileUpdate):
    """Cập nhật cấu hình config.yaml của profile Hermes."""
    if not hermes_manager.is_hermes_installed():
        raise HTTPException(status_code=400, detail="Hermes Agent chưa được cài đặt.")
        
    if name == "default":
        yaml_path = os.path.join(hermes_manager.HERMES_DIR, "config.yaml")
    else:
        yaml_path = os.path.join(hermes_manager.PROFILES_DIR, name, "config.yaml")
        
    if not os.path.exists(yaml_path):
        raise HTTPException(status_code=404, detail="Không tìm thấy profile.")
        
    try:
        model_config = {
            "default": data.default,
            "provider": data.provider,
            "base_url": data.base_url,
            "api_key": data.api_key,
            "model": data.default,
            "context_length": data.context_length or 70000
        }
        hermes_manager.write_profile_config(yaml_path, model_config)
        
        # Tự động restart gateway trong PM2 để áp dụng
        try:
            hermes_manager.restart_profile_gateway(name)
        except Exception:
            pass
            
        return {"success": True, "detail": f"Cập nhật cấu hình profile '{name}' thành công."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/hermes/profiles/{name}")
def delete_hermes_profile(name: str):
    """Xóa profile Hermes khỏi đĩa và PM2."""
    if not hermes_manager.is_hermes_installed():
        raise HTTPException(status_code=400, detail="Hermes Agent chưa được cài đặt.")
        
    if name == "default":
        raise HTTPException(status_code=400, detail="Không thể xóa profile default.")
        
    try:
        hermes_manager.delete_profile(name)
        return {"success": True, "detail": f"Đã xóa hoàn toàn profile '{name}'."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hermes/profiles/{name}/action")
def execute_hermes_profile_action(name: str, req: HermesProfileAction):
    """Điều khiển tiến trình chạy ngầm PM2 của profile Hermes (start, stop, restart)."""
    if not hermes_manager.is_hermes_installed():
        raise HTTPException(status_code=400, detail="Hermes Agent chưa được cài đặt.")
        
    try:
        if req.action == "start":
            hermes_manager.start_profile_gateway(name)
        elif req.action == "stop":
            hermes_manager.stop_profile_gateway(name)
        elif req.action == "restart":
            hermes_manager.restart_profile_gateway(name)
        else:
            raise HTTPException(status_code=400, detail="Hành động không hợp lệ.")
            
        return {"success": True, "detail": f"Thực hiện thành công '{req.action}' cho profile '{name}'."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hermes/profiles/{name}/logs")
def get_hermes_profile_logs(name: str):
    """Lấy logs hoạt động của profile Hermes từ PM2."""
    pm2_name = f"hermes-{name}"
    logs = pm2_manager.get_app_logs(pm2_name)
    return {"name": name, "logs": logs}

# Serve Static Files (Frontend UI)
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/")
    def read_root():
        return {"detail": "Thư mục frontend chưa được khởi tạo. Vui lòng tạo thư mục frontend."}
