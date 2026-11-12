# ViOCR cho Windows

Bộ OCR tiếng Việt chạy cục bộ, lấy cảm hứng từ cách Light OCR trả văn bản theo dòng kèm vị trí. Phiên bản này dùng Tesseract 5 (LSTM), mô hình vie của tessdata_fast và PDFium. Bộ mã hóa CVNSS4.0 audit-safe 5.0.0 do chủ dự án cung cấp. Thư mục này độc lập với mã PaddleOCR tại gốc kho.

## Cài trên Windows 10/11 x64

Trong PowerShell, cài Git, Python 3.12, Node.js 22+ và Tesseract 5 nếu máy còn thiếu. Với winget:

~~~powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.12 -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id UB-Mannheim.TesseractOCR -e
~~~

Mở lại PowerShell. Dùng sparse checkout để chỉ tải phần ViOCR:

~~~powershell
git clone --depth 1 --filter=blob:none --sparse https://github.com/xulytiengviet/ViOCR.git
cd ViOCR
git sparse-checkout set viocr
cd viocr
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
node --version
.\.venv\Scripts\python run.py examples\scan.pdf -o ketqua.jsonl
Get-Content -Encoding utf8 ketqua.jsonl | ForEach-Object { ($_ | ConvertFrom-Json).text }
~~~

Chương trình tự tìm tesseract.exe trong PATH hoặc Program Files\Tesseract-OCR. Nếu cài nơi khác, thêm thư mục chứa tesseract.exe vào PATH. Trọng số tiếng Việt đã có trong models/. Sau bước cài đặt có thể ngắt mạng. Mở index.html bằng trình duyệt để xem trang dự án và thử bộ mã hóa.

## Ba loại đầu vào

| Chế độ | Nội dung in trên ảnh/PDF | Xử lý |
|---|---|---|
| unicode (mặc định) | Tiếng Việt | OCR → Unicode NFC → CVNSS4.0 → ID → khôi phục mã và Unicode. Nếu mã giải ra khác chữ đọc được, giữ chữ OCR trong sourceOverride. |
| cvss | tizb vidf | OCR chữ mã → Base27 → CVNSS4.0 → tiếng việt theo chính sách giải mã chuẩn |
| base27 | 19 08 25 01 26 21 08 03 05 | OCR chữ số → tách từng cặp 00–26 → tizb vidf → tiếng việt |

~~~powershell
.\.venv\Scripts\python run.py examples\base27.png --mode base27 -o ma.jsonl
.\.venv\Scripts\python run.py "C:\Du lieu\bien ban.pdf" --dpi 200 -o bienban.jsonl
~~~

A=0, Z=25, khoảng trắng=26. Mỗi ID có đúng ba trit thường 0/1/2, ví dụ T=19=201 cơ số 3. Bảng mã số không lưu hoa/thường nên chế độ base27 mặc định chữ thường. Ký tự ngoài bảng như dấu câu được giữ bằng literal khi xử lý văn bản. Trong chế độ unicode, sourceOverride giữ được kết quả OCR khi mã nhiều nghĩa, kể cả từ nước ngoài. Lỗi đọc dấu của OCR vẫn cần đối chiếu ảnh. Trit là biểu diễn ký hiệu, tầng thị giác dùng LSTM của Tesseract. 

## Dữ liệu cho LLM

Mỗi dòng JSONL tương ứng một trang theo thứ tự, đánh số từ 1. Trường text là văn bản ghép từ các dòng. lines[].raw giữ nguyên chuỗi các từ OCR trước khi chuyển mã, lines[].tokens giữ dấu vết chuyển đổi và lines[].words chứa text, confidence (thang Tesseract 0–100), box [x,y,rộng,cao] theo pixel, gốc trái trên. width/height là kích thước ảnh đã xoay theo EXIF hoặc đã raster hóa. Các thuật toán tóm tắt có thể đọc text và truy lại vùng ảnh qua page và words. Thứ tự dòng theo phân đoạn của Tesseract. Bản này chưa tái dựng ô bảng, công thức hay trường nghiệp vụ. Ảnh hỗ trợ theo Pillow (PNG, JPEG, TIFF nhiều trang, BMP…), PDF được OCR từng trang, kể cả PDF đã có lớp chữ. PDF mã hóa cần mở khóa trước.

## Đo hai ngưỡng

~~~powershell
.\.venv\Scripts\python bench.py examples\trang.png examples\trang.txt
.\.venv\Scripts\python bench.py examples\scan.pdf examples\scan.txt
~~~

Đối chiếu trang trắng/nội dung sai, số trang và văn bản tham chiếu sau chuẩn hóa NFC và khoảng trắng. Mã thoát 0 khi khớp, mô hình <30.000.000 byte và P95 suy luận <0,5 s/trang. Với tài liệu riêng, tách các trang của tệp đáp án UTF-8 bằng ký tự form feed U+000C. Mỗi lần nhận dạng khởi động Tesseract mới. inference_s tính từ gọi tiến trình đến khi nhận TSV, gồm nạp mô hình; mean_wall_s_per_page gồm cả mở tệp, giải mã ảnh/PDF, chuyển mã và ghi JSONL. Kích thước mô hình chỉ tính vie.traineddata; Python, Node.js, PDFium, Tesseract và kết quả xuất được tính riêng.

| Tệp mẫu | Số trang đo | P95 OCR | Trung bình toàn trình | Văn bản |
|---|---:|---:|---:|---|
| trang.png | 10 | 0,270 s | 0,334 s/trang | Khớp |
| scan.pdf | 20 | 0,240 s | 0,328 s/trang | Khớp |

CPU AMD EPYC 9V74, Linux x86-64, Tesseract 5.5.0, OMP_THREAD_LIMIT=1. Ảnh tổng hợp 1240×1754 gồm 4 dòng in sạch; PDF lặp cùng trang hai lần, render 150 DPI. Kích thước mô hình 531.275 byte. Số liệu thô ở examples/*-benchmark.json. PC Windows, ảnh chụp nghiêng, trang dày chữ, tài liệu viết tay và bố cục phức tạp cần đo riêng.

## Nguồn

- [Light OCR](https://github.com/arcships/light-ocr)
- [Tesseract](https://github.com/tesseract-ocr/tesseract) và [trọng số vie.traineddata](https://github.com/tesseract-ocr/tessdata_fast/blob/main/vie.traineddata), Apache-2.0, kèm models/LICENSE.
- CVNSS4.0 của Kiều Trường Lâm và Trần Tư Bình. converter.js giữ nguyên tệp đính kèm.
