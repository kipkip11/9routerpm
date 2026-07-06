import os
import subprocess
import csv
import re
from backend import pm2_manager

def scan_system():
    """Quét các Scheduled Tasks cũ và các tiến trình PM2 đang chạy ngầm trên máy."""
    result = {
        "scheduled_tasks": [],
        "pm2_processes": []
    }
    
    # 1. Quét Scheduled Tasks bằng schtasks (bỏ /v để chạy siêu nhanh, tránh treo)
    try:
        res = subprocess.run(
            ["cmd.exe", "/c", "schtasks /query /fo CSV"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=8
        )
        if res.returncode == 0:
            lines = res.stdout.strip().split("\n")
            if lines:
                reader = csv.reader(lines)
                header = next(reader)
                
                name_idx = 0
                run_idx = -1
                status_idx = -1
                
                for idx, col in enumerate(header):
                    col_lower = col.lower()
                    if "taskname" in col_lower or "tên tác vụ" in col_lower or "tên" in col_lower:
                        name_idx = idx
                    elif "task to run" in col_lower or "tác vụ thực thi" in col_lower or "chương trình" in col_lower or "run" in col_lower:
                        run_idx = idx
                    elif "status" in col_lower or "trạng thái" in col_lower:
                        status_idx = idx
                
                for row in reader:
                    if len(row) <= name_idx:
                        continue
                    task_name = row[name_idx]
                    
                    if task_name.startswith("\\Microsoft\\") or task_name.startswith("Microsoft\\"):
                        continue
                        
                    task_run = row[run_idx] if run_idx != -1 and run_idx < len(row) else ""
                    task_status = row[status_idx] if status_idx != -1 and status_idx < len(row) else "N/A"
                    
                    name_check = task_name.lower()
                    run_check = task_run.lower()
                    
                    is_match = False
                    if "hermes" in name_check or "9router" in name_check:
                        is_match = True
                    elif ("proxy" in name_check or "agent" in name_check) and not task_name.startswith("\\Microsoft\\Windows"):
                        is_match = True
                    elif "hermes" in run_check or "9router" in run_check:
                        is_match = True
                        
                    if is_match:
                        result["scheduled_tasks"].append({
                            "name": task_name.lstrip("\\"),
                            "status": task_status,
                            "command": task_run
                        })
    except subprocess.TimeoutExpired:
        print("[CLEANUP] Quét Scheduled Tasks bị timeout (quá 8 giây).")
    except Exception as e:
        print(f"[CLEANUP] Lỗi quét Scheduled Tasks: {e}")
        
    # 2. Quét các tiến trình PM2 (node.exe)
    try:
        res = subprocess.run(
            ["cmd.exe", "/c", "wmic process where \"name='node.exe'\" get ProcessID,CommandLine /format:list"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=8
        )
        if res.returncode == 0:
            # Parse output wmic format list
            blocks = res.stdout.strip().split("\n\n")
            for block in blocks:
                lines = block.strip().split("\n")
                pid = None
                cmdline = ""
                for line in lines:
                    if "=" in line:
                        parts = line.split("=", 1)
                        key = parts[0].strip().lower()
                        val = parts[1].strip()
                        if key == "processid":
                            pid = int(val) if val.isdigit() else None
                        elif key == "commandline":
                            cmdline = val
                
                # Lọc tiến trình node.exe liên quan đến pm2/Daemon.js
                if pid and cmdline:
                    cmd_lower = cmdline.lower()
                    if "pm2" in cmd_lower or "daemon.js" in cmd_lower:
                        # Kiểm tra xem đây có phải là PM2 hiện tại của chúng ta hay không
                        # (để người dùng dễ phân biệt)
                        is_current = False
                        current_pm2_home = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".pm2"))
                        if current_pm2_home.lower() in cmd_lower:
                            is_current = True
                            
                        result["pm2_processes"].append({
                            "pid": pid,
                            "command_line": cmdline,
                            "is_current": is_current
                        })
    except subprocess.TimeoutExpired:
        print("[CLEANUP] Quét tiến trình PM2 (node.exe) bị timeout (quá 8 giây).")
    except Exception as e:
        print(f"[CLEANUP] Lỗi quét tiến trình PM2: {e}")
        
    return result

def purge_system(tasks_to_delete=None, pids_to_kill=None):
    """Xóa các Scheduled Tasks được chỉ định và tiêu diệt các tiến trình PM2 được chỉ định."""
    purge_results = {
        "tasks_deleted": [],
        "pids_killed": [],
        "errors": []
    }
    
    # 1. Xóa Scheduled Tasks
    if tasks_to_delete:
        for task in tasks_to_delete:
            try:
                # Chạy schtasks /delete /tn "task" /f qua cmd.exe
                # Thử với tên gốc nhận được trước
                res = subprocess.run(
                    ["cmd.exe", "/c", f"schtasks /delete /tn \"{task}\" /f"],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore'
                )
                
                # Nếu không tìm thấy, thử thêm dấu gạch chéo ngược ở đầu
                if res.returncode != 0 and not task.startswith("\\"):
                    alt_task = f"\\{task}"
                    res = subprocess.run(
                        ["cmd.exe", "/c", f"schtasks /delete /tn \"{alt_task}\" /f"],
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='ignore'
                    )
                
                if res.returncode == 0:
                    purge_results["tasks_deleted"].append(task)
                else:
                    err_msg = res.stderr.strip() or res.stdout.strip()
                    if "Access is denied" in err_msg or "truy cập bị từ chối" in err_msg.lower():
                        err_msg += " (Yêu cầu API Server chạy dưới quyền Administrator hoặc Windows Service)"
                    purge_results["errors"].append(f"Lỗi xóa task '{task}': {err_msg}")
            except Exception as e:
                purge_results["errors"].append(f"Không thể xóa task '{task}': {e}")
                
    # 2. Tiêu diệt tiến trình PM2 (node.exe)
    if pids_to_kill:
        for pid in pids_to_kill:
            try:
                res = subprocess.run(
                    ["cmd.exe", "/c", f"taskkill /F /PID {pid}"],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore'
                )
                if res.returncode == 0:
                    purge_results["pids_killed"].append(pid)
                else:
                    # Kiểm tra xem tiến trình đã tự tắt chưa
                    purge_results["errors"].append(f"Lỗi kill PID {pid}: {res.stderr.strip() or res.stdout.strip()}")
            except Exception as e:
                purge_results["errors"].append(f"Không thể kill PID {pid}: {e}")
                
    return purge_results
