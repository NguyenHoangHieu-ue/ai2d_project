#  STEM Scientific Diagram Knowledge Graph (AI2D-KG) 
##  Giới thiệu Đề tài

### Tên đề tài: Phát hiện các đối tượng của ảnh khoa học minh họa trong giáo dục STEM.

Dự án này tập trung vào việc chuyển đổi dữ liệu phi cấu trúc từ bộ dữ liệu AI2D và AI2D-RST (bao gồm 1000 sơ đồ khoa học tự nhiên cấp tiểu học) thành một Đồ thị Tri thức (Knowledge Graph). Hệ thống giúp xác định mối quan hệ giữa các thực thể, xây dựng đồ thị ngữ cảnh và tự động tạo chú giải (captioning) cho ảnh khoa học dựa trên các template logic.

##  Tính năng chính
- Data Pipeline hoàn chỉnh: Tự động hóa luồng xử lý từ dữ liệu thô JSON sang tri thức cấu trúc.
- Định danh thực thể (Entity Resolution): Kết hợp cấu trúc RST để gán nhãn chính xác cho các đối tượng hình ảnh (Blobs).
- Sắp xếp Logic (Topological Sort): Khôi phục trình tự phát triển tự nhiên trong các sơ đồ vòng đời (lifeCycles).
- Lưu trữ đa mô hình: Kết hợp sức mạnh của Neo4j (Quan hệ đồ thị), MongoDB (Metadata) và PostgreSQL (Tìm kiếm văn bản).
- Tự động chú giải: Sinh mô tả tự nhiên dựa trên các mối quan hệ thực tế trong sơ đồ.

##  Kiến trúc Hệ thống
Hệ thống vận hành qua 3 tầng chính:
- Processing Layer: Lọc dữ liệu, chuẩn hóa tọa độ Bounding Box và xử lý logic đồ thị ngữ cảnh.
- Knowledge Storage Layer: Lưu trữ dữ liệu vào 3 hệ quản trị CSDL chuyên biệt và Cloudflare R2 cho hình ảnh.
- User Interaction Layer: Cung cấp RESTful API thông qua FastAPI để truy vấn và hiển thị đồ thị.

##  Công nghệ sử dụng
- Backend: Python, FastAPI.
- Databases: Neo4j (Graph), MongoDB (NoSQL), PostgreSQL (SQL).
- Data Processing: Pandas, NetworkX logic.
- Cloud Storage: Cloudflare R2 (Image hosting).

##  Cấu trúc thư mục
ai2d_project/
- ├── app/
- │   ├── api/
- │   │   └── endpoints.py                            # Định nghĩa các API routes (Diagrams, Search, Graph)
- │   ├── core/
- │   │   ├── config.py                               # Quản lý biến môi trường và cấu hình hệ thống
- │   │   └── database.py                             # Quản lý kết nối MongoDB, PostgreSQL, Neo4j
- │   ├── models/
- │   │   └── schemas.py                              # Pydantic models cho dữ liệu API
- │   ├── scripts/
- │   │   ├── 01_setup_mapping.py                     # Tạo file Excel quy tắc ánh xạ (Biology_Mapping_Rules.xlsx)
- │   │   ├── 02_standardize.py                       # Chuẩn hóa tọa độ Polygon sang Bounding Box
- │   │   ├── process_graph.py                        # Logic xử lý đồ thị, RST mapping và Topological Sort
- │   │   ├── seed_database.py                        # Script chính để nạp dữ liệu hàng loạt vào DB
- │   │   └── update_filtered.py                      # Lọc danh sách ID sơ đồ theo Category mục tiêu
- │   └── services/
- │       └── ingestion_service.py                    # Dịch vụ nạp dữ liệu đa tầng (Mongo, PG, Neo4j)
- ├── data/                                           # Chứa dữ liệu AI2D và AI2D-RST
- │   ├── ai2d/
- │   └── ai2d_rst/
- ├── main.py                                         # Entry point khởi chạy server FastAPI
- └── .env                                            # Lưu trữ thông tin xác thực và URI Database

## 🚀 Cài đặt và Sử dụng

1. Chuẩn bị Dữ liệu: 
Cần tải xuống bộ dữ liệu gốc để đưa vào thư mục data/:
- AI2D Dataset: Allen Institute for AI - AI2D
- AI2D-RST: Cấu trúc phân đoạn RST cho AI2D

2. Cài đặt môi trường: 
- git clone https://github.com/NguyenHoangHieu-ue/ai2d_project.git
- cd ai2d_project
- python -m venv .venv
- source .venv/bin/activate  # Windows: .venv\Scripts\activate
- pip install -r requirements.txt

3. Cấu hình:
Tạo file .env và điền các thông tin kết nối tới MongoDB, PostgreSQL và Neo4j.
- MONGO_URI=mongodb://localhost:27017
- MONGO_DB_NAME=ai2d_knowledge_graph
- NEO4J_URI=bolt://localhost:7687
- NEO4J_USER=neo4j
- NEO4J_PASSWORD=your_password
- POSTGRES_SERVER=localhost
- POSTGRES_USER=postgres
- POSTGRES_PASSWORD=your_password
- POSTGRES_DB=ai2d_db
- R2_BASE_URL=your_r2_url

4. Trình tự chạy Scripts xử lý dữ liệu:
- Thiết lập ánh xạ: python -m app.scripts.01_setup_mapping (Tạo file quy tắc Biology).
- Lọc dữ liệu: python -m app.scripts.update_filtered (Lọc các sơ đồ thuộc chủ đề mục tiêu).
- Chuẩn hóa: python -m app.scripts.02_standardize (Chuyển đổi tọa độ thô sang Bbox).
- Nạp Database: python -m app.scripts.seed_database (Xử lý đồ thị và đẩy vào 3 DB).

5. Khởi chạy API:
  - uvicorn main:app --reload
   
