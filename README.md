# 9routerpm - Công cụ quản lý tiến trình nhiều Proxy 9router

Công cụ Web Dashboard cao cấp giúp bạn tự động hóa việc khởi tạo, cấu hình và quản lý nhiều instance proxy 9router chạy ngầm bằng **PM2** trên hệ điều hành Windows.

---

## 🚀 Hướng dẫn Cài đặt & Khởi động nhanh (Cho mọi máy tính Windows & Mọi ổ đĩa)

Dự án này được thiết kế theo cơ chế **đường dẫn tương đối động (Dynamic Relative Paths)**, hoạt động **Plug-and-Play (Cắm là chạy)**. Bạn có thể sao chép (copy) thư mục `9routerpm` này sang bất kỳ ổ đĩa nào khác (ổ C, ổ D, ổ E,...) hoặc bất kỳ thư mục nào trên máy tính và thực hiện:

 1. **Khởi chạy ứng dụng:**
    * **Cách 1 (Chạy nổi bằng cửa sổ đen CMD):** Click đúp chuột vào file **`run.bat`** ở thư mục gốc. Khi tắt cửa sổ CMD này, web quản trị sẽ dừng hoạt động.
    * **Cách 2 (Chạy ẩn/chạy ngầm hoàn toàn - KHÔNG BỊ TẮT):** Click đúp chuột vào file **`run_background.bat`** ở thư mục gốc.
      * Web server sẽ tự động được đăng ký chạy ẩn và giám sát bằng **PM2**. Cửa sổ đen CMD sẽ tự động đóng sau khi khởi động xong. Bạn có thể tắt CMD thoải mái mà server vẫn chạy ngầm ổn định.
      * Để dừng hẳn Web Server chạy ngầm này, hãy click đúp vào file **`stop_background.bat`**.
    * *Yêu cầu duy nhất:* Máy tính cần cài đặt sẵn **Python** và **Node.js** (để chạy proxy). Nếu chưa cài, script sẽ đưa ra liên kết tải về trực tiếp.

2. **Truy cập Dashboard:**
   * Sau khi hoàn tất tự động thiết lập (ở lần chạy đầu tiên), trình duyệt Web sẽ tự động mở trang quản trị tại địa chỉ: **`http://localhost:20127`**.

---

## 🛠️ Hướng dẫn sử dụng các chức năng trên Giao diện Web

* **Thêm Proxy Instance Mới:**
  * Bấm nút **"Thêm Proxy mới"** trên góc phải.
  * Nhập tên proxy (ví dụ: `vlog-proxy-1`).
  * Nhập đường dẫn thư mục chứa mã nguồn 9router gốc trên máy của bạn.
  * Nhập cổng mạng (hoặc để trống để hệ thống tự động tìm cổng TCP trống).
  * Nhập API Key của 9router của bạn và nhấn **Tạo & Khởi chạy**.
  * *Hệ thống sẽ tự động:* Nhân bản thư mục code vào thư mục `instances/` của dự án tại ổ đĩa hiện tại, tạo tệp cấu hình `.env` với cổng và API Key tương ứng, đồng thời đăng ký chạy ngầm và giám sát tự động bằng PM2.

* **Quản lý & Điều khiển:**
  * Bạn có thể bấm nút **Start (Chạy)**, **Stop (Dừng)**, hoặc **Restart (Khởi động lại)** trực tiếp trên mỗi Card Proxy.
  * Theo dõi dung lượng RAM và phần trăm CPU thực tế của từng proxy theo thời gian thực (tự động cập nhật mỗi 5 giây).

* **Xem Logs:**
  * Bấm biểu tượng Terminal trên Card Proxy để xem nhật ký hoạt động thời gian thực được trích xuất trực tiếp từ log của PM2, giúp bạn dễ dàng chẩn đoán khi proxy bị lỗi kết nối hoặc sập mạng.

* **Chỉnh sửa file cấu hình `.env`:**
  * Bấm biểu tượng Sửa (Edit) trên Card để chỉnh sửa nhanh các giá trị cấu hình trong file `.env` (như API Key hoặc thay đổi PORT) ngay trên Web. Giao diện sẽ tự động lưu lại và khởi động lại proxy để áp dụng cấu hình mới.

---

## 📂 Cấu trúc thư mục

* `backend/`: Chứa mã nguồn API Server (FastAPI) điều khiển PM2 và hệ thống file.
* `frontend/`: Giao diện Web Dashboard Premium (HTML, CSS, JS).
* `venv/`: Môi trường ảo Python của ứng dụng (được tự động tạo khi chạy `run.bat` tương đối).
* `instances/`: Thư mục lưu trữ các bản proxy 9router được nhân bản ra để hoạt động tại ổ đĩa hiện tại.
* `instances.json`: Cơ sở dữ liệu lưu danh sách thông tin cấu hình các proxy.
* `run.bat`: Trình khởi động và tự động cài đặt hệ thống.
