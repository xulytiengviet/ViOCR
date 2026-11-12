# ViOCR cho Windows

Bộ OCR tiếng Việt chạy cục bộ, lấy cảm hứng từ cách Light OCR trả văn bản theo dòng kèm vị trí. Phiên bản này dùng Tesseract 5 (LSTM), mô hình vie của tessdata_fast và PDFium. Bộ mã hóa CVNSS4.0 audit-safe 5.0.0 do chủ dự án cung cấp. Thư mục này độc lập với mã PaddleOCR tại gốc kho.

## Mở tài liệu và xuất kết quả

**[Chạy ViOCR trên trình duyệt](https://xulytiengviet.github.io/ViOCR/)**. Chọn kiểu chữ trên tài liệu (mặc định tiếng Việt), bấm **Mở tài liệu…** hoặc thả một tệp vào khung. OCR bắt đầu tự động. Sau khi đọc xong, bấm **Lưu Word**, **Lưu TXT** hoặc **Lưu JSONL**. Word giữ ngắt trang; TXT dùng UTF-8 có BOM và ký tự ngắt trang. JSONL giữ tọa độ và độ tin cậy. Edge/Chrome có hộp chọn thư mục và tên tệp; với trình duyệt dùng cơ chế tải xuống, bật “Hỏi nơi lưu mỗi tệp”. Ảnh và PDF được xử lý trong trình duyệt. Cần mạng để tải các thư viện OCR, đọc PDF/TIFF và xuất Word. GIF và ảnh động trên web dùng khung hình đầu. PDF và TIFF hỗ trợ nhiều trang. AVIF phụ thuộc bộ giải mã của trình duyệt.

**Ứng dụng Windows**. Sau khi cài các công cụ và tải thư mục viocr theo hướng dẫn dưới đây, bấm đúp **ViOCR.cmd**. Lần đầu chương trình tạo môi trường Python và cài thư viện. Những lần sau có thể chạy ngoại tuyến. Bấm **Mở tài liệu…**, chọn ảnh/PDF, đợi kết quả và dùng **Lưu Word** hoặc **Lưu TXT** để chọn nơi lưu bằng hộp thoại Windows. Muốn dùng dòng lệnh hoặc đo hiệu năng, xem các lệnh bên dưới.

**Tác giả và giấy phép.** Long Ngo phát triển phần mềm ViOCR dựa trên dự án CVNSS4.0. Mã giao diện, bộ tích hợp, công cụ xuất và kiểm chuẩn do Long Ngo phát hành theo [MIT](LICENSE). Bộ chuyển đổi CVNSS4.0 được cung cấp riêng; mô hình tessdata_fast giữ Apache-2.0. Mã PaddleOCR ở gốc kho và các thư viện bên thứ ba giữ giấy phép tương ứng. Kết quả tốc độ trong bảng bên dưới đo trên bộ xử lý OCR của bản PC; tốc độ WebAssembly trên trình duyệt cần đo riêng.

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
