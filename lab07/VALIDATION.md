# Kiểm chứng backend 9Router

Sau khi đổi tài khoản upstream, request với model `cx/gpt-5.6-sol` trong `.env` đã thành công. Giữ nguyên model cấu hình; không fallback sang model khác. Backend gọi 9Router v0.5.81 tại loopback, không còn cần Codex CLI cho chế độ live.

Bộ kiểm thử hiện tại có **29 test** (A: 13, B: 16), gồm test mới cho phép đóng file wrapper bằng `close()`. Lần chạy B đầu tiên dừng vì model gọi `close()` trong khi AST allowlist chưa cho phép; đã bổ sung thao tác an toàn này, chạy test RED/GREEN và chạy lại B vào thư mục mới. Không sửa kết quả lỗi thành thành công và không nới quyền truy cập file/network.

## Kết quả model thật qua 9Router

| Bài / chế độ | Kết quả | Input tokens do router báo |
|---|---|---:|
| A: 5 session độc lập | JWT → cookie; đối chứng không có memory | 3.650 tổng cộng |
| B1 full history | Đủ state | 43.325 |
| B1 checkpoint | Đủ state, giảm 99,10% | 391 |
| B2 đọc raw log | Top 3 đúng, 8 lượt model | 249.901 |
| B2 Code Mode | Top 3 đúng, 2 lượt model, giảm 99,55% | 1.131 |

B1 đối chứng chỉ giữ tin cuối mất state như dự kiến. B2 đọc đủ 6 file và Code Mode không đưa raw log vào context; chỉ stdout top 3 được trả cho model. `usage.prompt_tokens`/`completion_tokens` từ API được chuẩn hóa thành `input_tokens`/`output_tokens`; không ước lượng token từ ký tự. Số liệu phản ánh router báo, không là bảo đảm về cách upstream tính token hoặc tỷ lệ tiết kiệm tiền.

Minh chứng hiện tại:

- [Report A](challenge-a/evidence/router-validation/report.json).
- [Report B](challenge-b/evidence/router-validation-v2/report.json).
- Request không chứa header Authorization, raw response được che key, schema, input, answer và event usage chuẩn hóa được lưu từng bước.
- `python -X utf8 -B verify.py` kiểm tra cả minh chứng 9Router này và minh chứng CLI cũ.

API key chỉ được đọc ở backend; `.env` và `.env.*` private bị gitignore loại khỏi Git. `.env.example` không chứa key thật. Bộ minh chứng mới được quét kiểm tra không có chuỗi API key; không in key trong kết quả quét.

Bên dưới là kết quả lịch sử **Codex CLI trước khi chuyển provider**, giữ nguyên để đối chiếu. Không dùng số liệu CLI cũ để thay thế phép đo 9Router mới.

---

# Kiểm chứng Lab 07

Ngày kiểm chứng: 27/10/2026. Các số dưới đây lấy từ test output và artifact thực tế, không phải số liệu dự kiến.

## Kiểm thử tự động

Đã chạy từ thư mục lab07:

```powershell
python -X utf8 -B verify.py
```

Kết quả: **20/20 test đạt** — Challenge A có 9 test, Challenge B có 11 test. Hai verifier evidence đều trả `passed: true`; tiến trình kiểm chứng chung kết thúc với exit code 0. Lệnh này không gọi model và không chạy code do model sinh trong bộ evidence.

Phạm vi test: memory revision và nguồn ghi; JSON hỏng không bị reset; active memory ở session mới; đối chứng tắt memory; giới hạn bước; ghi thành công trước khi lượt sau thất bại; checkpoint giữ state và bỏ raw output; cập nhật next action; top 3 lỗi; đọc đủ file; chặn path escape, import và private attribute; stdout limit; timeout; offline không giả usage; evidence sau khi chuyển thư mục và checkpoint bị sửa; HTTP static/API, Host/Origin và chặn gửi trùng.

Hai lệnh kiểm tra cú pháp JavaScript đều đạt:

```powershell
node --check challenge-a/web/app.js
node --check challenge-b/web/app.js
```

## Challenge A: model thật

Bộ minh chứng: [challenge-a/evidence/live-validation/report.json](challenge-a/evidence/live-validation/report.json).

Đã chạy `demo.py --live --output evidence/live-validation`: 5 tiến trình Python/session độc lập, 7 lượt gọi model. Tổng input tokens là **136.656**. Mỗi session ghi `history_messages: 0`.

| Session | Kết quả thực tế |
|---|---|
| 1 | Model gọi remember_memory, lưu authentication dùng JWT |
| 2 | Context mới inject JWT; câu trả lời dùng JWT |
| 3 | Model ghi cookie thay JWT; revision JWT chuyển superseded |
| 4 | Context mới chỉ inject revision active; câu trả lời dùng session cookie |
| 5 | Tắt injection và memory tools; model trả lời chưa có thông tin |

Đã đọc action, tool result, store và câu trả lời. Cookie có thể nhắc JWT trong câu “thay cho JWT”; không dùng việc có từ JWT để suy ra memory cũ còn active. Verifier A kiểm tra cấu trúc và từ khóa, không thay thế việc đánh giá ngữ nghĩa.

## Challenge B1: model thật

Bộ minh chứng: [report B1](challenge-b/evidence/live-validation/b1/report.json), [checkpoint](challenge-b/evidence/live-validation/b1/checkpoint.json).

| Context | Input tokens | Đủ state để tiếp tục |
|---|---:|---|
| Full history | 62.293 | Có |
| Structured checkpoint | 19.359 | Có |
| Chỉ giữ tin cuối | 19.284 | Không |

Compact giảm kích thước prompt của bài **99,52%** và input tokens thực **68,92%**. Trước/sau giữ nguyên goal, error, current state, constraints, findings, failed attempts, files và next action. Đối chứng không phục hồi được lỗi/cách đã thử/bước tiếp. Bài kiểm tra continuation bằng structured state, không tuyên bố đã sửa một hệ thống authentication thật.

Checkpoint do Python chọn từ typed event ledger, không dùng LLM summarizer. Raw history được giữ trong archive. Đây là fixture có chủ đích, không phải benchmark compaction tổng quát.

## Challenge B2: model thật

Bộ minh chứng: [report B2](challenge-b/evidence/live-validation/b2/report.json), [code model viết](challenge-b/evidence/live-validation/b2/code/step-01.answer.json).

| Chỉ số | Đọc log thô | Code Mode |
|---|---:|---:|
| Model calls | 8 | 2 |
| Tổng input tokens | 401.691 | 39.070 |
| Input tokens lượt final | 89.666 | 19.609 |
| Tổng ký tự prompt qua các lượt | 705.189 | 2.606 |
| Đọc đủ 6 file | Có | Có |
| Trả đúng top 3 | Có | Có |
| Raw marker đi vào model context | Có | Không |

Code do model thật sinh đã chạy trong runtime. Stdout chỉ có:

```text
ERR_DB_TIMEOUT 180
ERR_AUTH_EXPIRED 120
ERR_RATE_LIMIT 60
```

Mức giảm tổng input tokens là **90,27%**. Verifier tính lại từ JSONL usage, kiểm tra action với trace, đếm lại log và đối chiếu các input snapshot. Đây là một lần đo; không đồng nghĩa giảm chi phí tiền cùng tỷ lệ, do cache và số lượt gọi khác nhau.

## Kiểm tra trình duyệt

Đã mở hai giao diện trong trình duyệt tích hợp tại `127.0.0.1:8765` và `127.0.0.1:8766`.

- A: bấm chạy 5 session offline; giao diện hoàn tất và hiển thị kết quả từng session, memory inject và trace.
- B: bấm chạy so sánh B1/B2 offline; giao diện báo trước/sau checkpoint đủ state, truncation thiếu state, hai cách phân tích log đều đúng. Offline hiển thị “Không gọi LLM” và không tạo token savings giả.
- A với model thật: gửi “Hãy nhớ quy ước dự án: database dùng PostgreSQL.”; model gọi tool và xác nhận lưu. Sau đó gửi “Dự án dùng database nào?” trong session mới: model trả “Dự án dùng PostgreSQL.”, `history_messages: 0`, memory inject có 1 record. Lượt ghi dùng 39.002 input tokens; lượt hỏi dùng 19.505 input tokens.

Minh chứng UI mới được lưu trong `challenge-a/data/ui/custom/` và `challenge-b/data/ui/`; các thư mục này bị gitignore loại khỏi Git theo thiết kế. Bộ model thật dùng làm minh chứng chính vẫn nằm trong `evidence/live-validation/`.

## Giới hạn của kiểm chứng

Offline dùng scripted test double; không phải bằng chứng LLM tự chọn action hay tự viết code. Các verifier kiểm tra nhất quán artifact, không phải chữ ký chống giả mạo. Python subset của Code Mode có giới hạn AST/path/stdout/timeout nhưng chưa có hard RAM limit hoặc sandbox OS production. Store JSON dành cho một writer. UI không tự resume job sau khi reload/restart.

Chưa kiểm thử trên Linux/macOS, chưa kiểm thử giao diện ở nhiều kích thước màn hình và chưa chạy audit accessibility tự động. Lệnh kiểm tra bổ sung phiên bản CLI bị hệ thống duyệt tự động từ chối thực thi vì hết hạn mức duyệt; không ghi một phiên bản CLI chưa xác minh vào báo cáo.
