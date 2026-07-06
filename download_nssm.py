import urllib.request
import zipfile
import io
import os

def download_nssm():
    nssm_url = "https://nssm.cc/release/nssm-2.24.zip"
    bin_dir = "D:/9routerpm/bin"
    os.makedirs(bin_dir, exist_ok=True)
    nssm_exe_path = os.path.join(bin_dir, "nssm.exe")
    if os.path.exists(nssm_exe_path):
        print("nssm.exe already exists.")
        return True
        
    print("Downloading NSSM...")
    try:
        req = urllib.request.Request(
            nssm_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            zip_data = response.read()
        
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_ref:
            # Tìm file nssm.exe trong thư mục win64 của file zip
            for file_info in zip_ref.infolist():
                if "win64/nssm.exe" in file_info.filename:
                    # Đọc nội dung file
                    with zip_ref.open(file_info) as f_in:
                        with open(nssm_exe_path, "wb") as f_out:
                            f_out.write(f_in.read())
                    print("Extracting nssm.exe success!")
                    return True
    except Exception as e:
        print(f"Error downloading NSSM: {e}")
        return False

if __name__ == "__main__":
    download_nssm()
