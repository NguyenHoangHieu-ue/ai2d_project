# 📚 STEM Scientific Diagram Knowledge Graph (AI2D-KG) 
## 📝 Giới thiệu Đề tài

### Tên đề tài: Phát hiện các đối tượng của ảnh khoa học minh họa trong giáo dục STEM.

Dự án này tập trung vào việc chuyển đổi dữ liệu phi cấu trúc từ bộ dữ liệu AI2D và AI2D-RST (bao gồm 1000 sơ đồ khoa học tự nhiên cấp tiểu học) thành một Đồ thị Tri thức (Knowledge Graph). Hệ thống giúp xác định mối quan hệ giữa các thực thể, xây dựng đồ thị ngữ cảnh và tự động tạo chú giải (captioning) cho ảnh khoa học dựa trên các template logic.

## ✨ Tính năng chính
- Data Pipeline hoàn chỉnh: Tự động hóa luồng xử lý từ dữ liệu thô JSON sang tri thức cấu trúc.
- Định danh thực thể (Entity Resolution): Kết hợp cấu trúc RST để gán nhãn chính xác cho các đối tượng hình ảnh (Blobs).
- Sắp xếp Logic (Topological Sort): Khôi phục trình tự phát triển tự nhiên trong các sơ đồ vòng đời (lifeCycles).
- Lưu trữ đa mô hình: Kết hợp sức mạnh của Neo4j (Quan hệ đồ thị), MongoDB (Metadata) và PostgreSQL (Tìm kiếm văn bản).
- Tự động chú giải: Sinh mô tả tự nhiên dựa trên các mối quan hệ thực tế trong sơ đồ.

## 🏗 Kiến trúc Hệ thống
Dự án được xây dựng dựa trên 3 tầng chính:
- Processing Layer: Lọc dữ liệu, chuẩn hóa tọa độ Bounding Box và xử lý logic đồ thị ngữ cảnh.
- Knowledge Storage Layer: Lưu trữ dữ liệu vào các hệ quản trị CSDL chuyên biệt.
- User Interaction Layer: Cung cấp RESTful API thông qua FastAPI để truy vấn và hiển thị đồ thị.

## 🛠 Công nghệ sử dụng
- Backend: Python, FastAPI.
- Databases: Neo4j (Graph), MongoDB (NoSQL), PostgreSQL (SQL).
- Data Processing: Pandas, NetworkX logic.
- Cloud Storage: Cloudflare R2 (Image hosting).

## 📂 Cấu trúc thư mục
ai2d_project/
├── app/
│   ├── api/            # Định nghĩa các API Endpoints
│   ├── core/           # Cấu hình hệ thống và kết nối DB
│   ├── models/         # Pydantic schemas cho dữ liệu
│   ├── scripts/        # Các script tiền xử lý và nạp dữ liệu
│   └── services/       # Logic nghiệp vụ (Ingestion Service)
├── data/               # Thư mục chứa dữ liệu AI2D (đã được gitignore)
├── main.py             # Entry point của ứng dụng
└── .env                # Biến môi trường bảo mật
🚀 Cài đặt và Sử dụng
1. Clone dự án:
  git clone https://github.com/NguyenHoangHieu-ue/ai2d_project.git
  cd ai2d_project
2. Cài đặt môi trường:
  python -m venv .venv
  source .venv/bin/activate  # Windows: .venv\Scripts\activate
  pip install -r requirements.txt
3. Cấu hình:
   Tạo file .env và điền các thông tin kết nối tới MongoDB, PostgreSQL và Neo4j.
4. Chạy Pipeline nạp dữ liệu:
   python -m app.scripts.seed_database
5. Khởi chạy API:
   uvicorn main:app --reload
   
