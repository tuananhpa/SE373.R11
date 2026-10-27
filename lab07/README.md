# Lab 07 — Memory và Context Management

Bài làm cho **Challenge A** (slide 14–15) và **Challenge B: B1 + B2** (slide 32–33) trong tài liệu `slide.pdf`. Hai challenge nằm ở hai thư mục độc lập; có thể chép từng thư mục sang máy khác để chạy. README này giải thích chung cả hai bài. Không cần package Python ngoài thư viện chuẩn.

- **Challenge A:** agent ghi nhớ quy ước qua các session mới, thay thế quy ước lỗi thời và giữ lịch sử.
- **Challenge B1:** compact một context dài thành checkpoint, rồi cho model tiếp tục xác định lỗi, cách đã thử và bước tiếp.
- **Challenge B2:** agent phân tích cùng nhiều file log theo hai cách; đo `usage.input_tokens` giữa đọc từng file và Code Mode.
- Có giao diện local, CLI, unit/integration tests, đối chứng và minh chứng model thật trong từng thư mục `evidence/live-validation/`.

## Kết quả mới nhất qua 9Router

Đã kiểm chứng model thật `cx/gpt-5.6-sol` qua tài khoản 9Router đã cập nhật:

- A: đủ 5 session độc lập, lưu JWT → thay bằng cookie; đối chứng thiếu memory trả lời chưa biết.
- B1: 43.325 → 391 input tokens, giảm **99,10%**, vẫn giữ đúng state để tiếp tục.
- B2: 249.901 → 1.131 tổng input tokens, giảm **99,55%**; cả hai mode trả đúng top 3 và code context không chứa raw log.

Xem [report A qua 9Router](challenge-a/evidence/router-validation/report.json), [report B qua 9Router](challenge-b/evidence/router-validation-v2/report.json) và [VALIDATION.md](VALIDATION.md). Các bảng CLI ở phần sau là minh chứng lịch sử và được ghi nhãn riêng. Có **29 kiểm thử tự động**; lệnh chung `python -X utf8 -B verify.py` kiểm chứng cả bộ cũ và mới.

## 1. Chạy nhanh — 9Router

Yêu cầu **Python 3.10+**. Backend gọi **9Router qua OpenAI-compatible Chat Completions API**, không cần Codex CLI hay package Python ngoài thư viện chuẩn. Offline không cần router hoặc key.

File `.env` nằm ở thư mục lab07. Nếu chép riêng một challenge, đặt `.env` ngay trong folder challenge đó. Có thể xem `.env.example` để biết tên biến:

```dotenv
OPENAI_API_KEY=your-9router-key
OPENAI_BASE_URL=http://localhost:20128/v1
OPENAI_MODEL=cx/gpt-5.6-sol
```

Ứng dụng đọc `.env` mỗi lần gọi model. Biến environment của process ưu tiên hơn file. Key chỉ được gửi qua Authorization header tới endpoint đã cấu hình; không gửi ra frontend, prompt hoặc artifact. `.env` và các biến thể private được gitignore loại khỏi Git; `.env.example` chỉ chứa giá trị mẫu.

**Model phải được tài khoản upstream hỗ trợ.** `/v1/models` của router có thể quảng bá ID mà upstream vẫn từ chối. Nếu gặp HTTP 400, kiểm tra model/connection trên dashboard 9Router; không tự thay model hay fallback để làm sai phép so sánh.

Bật router trước (nếu chưa chạy):

```powershell
9router --host 127.0.0.1 --no-browser --skip-update
```

Mở terminal tại lab07 để chạy A:

```powershell
cd challenge-a
python -X utf8 -B ui_server.py
```

Mở <http://127.0.0.1:8765>. Terminal khác, từ lab07:

```powershell
cd challenge-b
python -X utf8 -B ui_server.py
```

Mở <http://127.0.0.1:8766>. Nếu đang ở challenge-a, dùng `cd ../challenge-b`. Trùng cổng: thêm `--port 8767` và dùng đúng URL được in. Dùng địa chỉ `127.0.0.1`, vì server kiểm tra HTTP Host.

Mặc định **offline**: action/final giả lập có nhãn `scripted_offline`, `usage=null`, không dùng quota. Tick **Gọi model thật qua 9Router** để model tự chọn action và viết code. Câu nói tự nhập ở A cần chế độ model thật; mỗi lần gửi là session mới. Memory nhập tay và các demo 5 session nằm ở kho riêng.

Từ thư mục challenge tương ứng:

```powershell
python -X utf8 -B demo.py
python -X utf8 -B demo.py --live
# Chỉ áp dụng Challenge B:
python -X utf8 -B demo.py --live --part b1
python -X utf8 -B demo.py --live --part b2
```

`--output duong-dan-moi` chọn thư mục evidence mới; không ghi đè demo đã có. Khi sửa source Python, restart UI server. Khi chỉ sửa `.env`, request kế tiếp sẽ đọc cấu hình mới.

## 2. Cấu trúc

```text
lab07/
├── README.md
├── VALIDATION.md
├── verify.py                 # Kiểm chứng cả hai bài, không gọi model
├── slide.pdf                 # Tài liệu môn học, không phải phụ thuộc chạy
├── challenge-a/
│   ├── memory.py             # Store JSON, active/superseded, atomic write
│   ├── agent.py              # Agent loop và allowlist memory tools
│   ├── runtime.py            # 9Router HTTP transport + scripted test double
│   ├── session.py            # Mỗi invocation là một process/session mới
│   ├── demo.py               # Năm session và --verify
│   ├── app.py, ui_server.py  # Giao diện, API, background job
│   ├── web/                  # HTML, CSS, JavaScript không phụ thuộc ngoài
│   ├── tests/
│   └── evidence/live-validation/
└── challenge-b/
    ├── compaction.py         # Typed event → structured checkpoint
    ├── logs.py               # Fixture, read_file/list_files có kiểm tra path
    ├── code_runtime.py       # Python subset chạy trong child process
    ├── runtime.py            # Transport tự chứa để chạy độc lập
    ├── demo.py               # B1/B2, agent loop, đo usage
    ├── verify.py             # Kiểm lại evidence tại vị trí hiện tại
    ├── app.py, ui_server.py
    ├── web/
    ├── tests/
    └── evidence/live-validation/
```

Hai bản `runtime.py` và các file giao diện/server giống nhau được giữ cục bộ để mỗi folder chạy độc lập. Dữ liệu UI nằm trong `data/ui/`; demo CLI mới nằm trong `evidence/<timestamp>/`. Hai bộ `live-validation` (CLI cũ) và `router-validation` / `router-validation-v2` (9Router) được chọn làm minh chứng; `.gitignore` loại dữ liệu phát sinh khác.

## 3. Challenge A — Persistent memory

### Agent loop

```text
User hiện tại + active memory từ JSON (không chat cũ)
  → model trả action JSON
    ├── read_memory → Python đọc các record active
    ├── remember_memory → Python kiểm tra đối số, lưu revision mới
    │                      và đánh dấu revision cũ superseded
    └── final → câu trả lời tiếng Việt
        ↑
Action/tool result trong cùng session được gửi lại cho model
```

Vòng lặp ở `agent.run_session()`, tối đa 6 lượt model. Session tiếp theo chỉ nạp **active memory**; không truyền transcript session cũ. Mỗi bước model là một HTTP request độc lập tới 9Router, không gửi conversation ID hoặc resume thread. Python gửi context và các action/result của chính session ứng dụng hiện tại.

Memory có `id, key, value, evidence, source_session, created_at, status, superseded_by`. Key chủ đề authentication là `auth`. Ví dụ JWT → session cookie: JWT giữ nguyên nguồn và thời điểm nhưng chuyển sang `superseded`, liên kết tới ID mới. Chỉ cookie được inject ở session sau. Vì giá trị mới có thể là “cookie thay cho JWT”, không được chỉ dò chữ JWT để kết luận memory cũ còn hiệu lực.

### Kịch bản năm session

| Session | User | Kết quả cần chứng minh |
|---|---|---|
| 1 | Nhớ authentication dùng JWT | Model tự gọi tool ghi; record có nguồn |
| 2 | Dự án hiện dùng cơ chế authentication nào? | Session mới nhận JWT từ memory |
| 3 | Chốt đổi sang session cookie thay JWT | Model ghi revision mới, JWT bị thay thế |
| 4 | Câu hỏi giống session 2 | Session mới dùng cookie |
| 5 | Câu hỏi giống session 2, tắt memory | Không inject và không có memory tools; model nói thiếu thông tin |

`demo.py` chạy cả năm bước bằng **năm tiến trình Python riêng**, đọc cùng store. Bộ minh chứng Codex CLI trước khi đổi provider có **7 lượt model**, 5 session, mỗi context ghi `history_messages: 0`. Session 2 trả lời JWT; session 4 trả lời cookie; session 5 nói chưa có thông tin. Xem [report A](challenge-a/evidence/live-validation/report.json).

Tool ghi đòi `evidence` trích nguyên văn user hiện tại; model được hướng dẫn không lưu câu hỏi, giả định hoặc trích dẫn thành quy ước. Kiểm tra nguồn là biện pháp truy vết, không tự chứng minh model đã hiểu đúng ý định; cần đọc action và answer. Store không bị reset khi JSON hỏng. Ghi atomic bằng file tạm + `os.replace`. JSON store phục vụ **một writer**; UI tuần tự hóa job trong một server, không đồng bộ nhiều server/CLI cùng ghi.

Giới hạn: tối đa 6 bước, kiểm tra thời gian giữa các bước 300 giây, mỗi model call tối đa 120 giây. Do kiểm tra giữa bước, thời gian thực có thể vượt mốc tổng tối đa một call. Lỗi trả `failed`, giữ trace và không tự retry. Nếu memory đã ghi rồi lượt sau lỗi, record vẫn tồn tại; không tự rollback thay đổi đã thực hiện.

## 4. Challenge B1 — Compaction

Fixture mô phỏng điều tra lỗi refresh token có 32 kết quả tool lớn cùng mục tiêu và state. Harness ghi sự kiện có kiểu; các trường quan trọng được lấy từ ledger, không suy luận lại bằng tìm từ khóa trong log.

Ngưỡng minh họa là **60.000 ký tự**; fixture có 162.725 ký tự. Đây là ngưỡng kích thước dữ liệu, **không phải số token** hay một bộ tự động quản lý context window production.

| Giữ | Rút gọn / bỏ khỏi active context |
|---|---|
| goal, error, current_state | Raw test output lớn |
| constraints, findings | Log lặp và dữ liệu có thể tái tạo |
| failed_attempts, files, next_action | Giữ kết luận cách đã thử, bỏ toàn bộ output của lần thử |

Raw history vẫn nằm trong `archive.json`. `checkpoint.json` chứa structured state. Trường scalar lấy cập nhật cuối; các trường list hợp nhất và bỏ trùng. Nếu thiếu trường bắt buộc, compact thất bại thay vì đoán. Lịch sử cập nhật/xóa list phức tạp chưa được mô hình hóa trong fixture.

Ba lần continuation độc lập cùng yêu cầu:

1. Đọc context đầy đủ.
2. Đọc checkpoint, không gửi raw history cũ.
3. Đối chứng chỉ giữ tin nhắn cuối để cho thấy cắt ngây thơ mất state.

Model phải trả lại đủ lỗi, constraint, cách đã thử, file và next action. Checker so chính xác với fixture; đối chứng thứ ba phải thiếu state. **Không có yêu cầu model sửa code auth thật:** tiêu chí trong bài là tiếp tục xác định chính xác trạng thái và hành động kế tiếp.

Lần chạy thật lưu từ backend Codex CLI trước khi chuyển 9Router: input **62.293 → 19.359 token**, giảm **68,92%**; kích thước context do bài gửi giảm **99,52%**. Hai cách đầu đều giữ đúng state, cách cắt tin cũ thất bại như dự kiến. Các số token vẫn gồm prompt/harness nội bộ CLI, nên không bằng tỷ lệ giảm ký tự. Compact ở đây là biến đổi có cấu trúc bằng Python, không cần LLM summarizer và không có phí model cho bước tạo checkpoint.

## 5. Challenge B2 — Code Mode

Tạo **6 file, 402 dòng/file** gồm INFO, ERROR và hai dòng nhiễu. Cùng dataset, cùng regex và cùng câu hỏi: top 3 mã lỗi cùng số lần. Kết quả chuẩn:

```text
ERR_DB_TIMEOUT 180
ERR_AUTH_EXPIRED 120
ERR_RATE_LIMIT 60
```

### Đối chứng read_file

Model gọi `list_files`, rồi `read_file` từng log. Python trả nội dung thô vào history. Model tự tổng hợp và trả `final.errors`; harness không tính sẵn kết quả cho model thật. Final bị chặn nếu chưa đọc đủ mọi file.

### Code Mode

Model chọn `run_code` và **tự viết chương trình Python**. Runtime đọc file qua các wrapper trong harness, chỉ đưa stdout đã tổng hợp vào context model. Trace vẫn lưu từng lời gọi đọc bên trong và số byte, không trả raw nội dung vào model.

Một chương trình có thể gửi:

```python
import glob, re, collections

codes = collections.Counter()
for path in glob.glob("logs/*.log"):
    for line in open(path):
        m = re.search(r" ERROR \S+ (ERR_[A-Z0-9_]+)\b", line)
        if m:
            codes[m.group(1)] += 1

for code, n in codes.most_common(3):
    print(code, n)
```

Khi agent có bash trên Linux, có thể chạy code trên bằng `python3 - <<'PY' ... PY`: đó là Code Mode tối giản. Trong lab này máy Windows chạy child process Python trực tiếp, không yêu cầu bash. `open` và `glob` của code được proxy về harness; code không được nhận credential model.

Runtime kiểm tra AST trước khi chạy, chỉ cho phép subset cần cho bài: for/if, import glob/re/collections, regex/Counter, đọc `logs/*.log` và đóng stream bằng `close()`. Cấm import OS/network, tên private/dunder, while, khai báo hàm; kiểm tra đường dẫn, giới hạn 100 file và 1 MB/file, stdout 16 KB, timeout 5 giây. Child process loại env credential và bật UTF-8 rõ ràng.

**Giới hạn bảo mật:** Python subset/AST + process riêng là guardrail của demo, không phải sandbox production. Chưa có hard RAM limit hoặc OS container isolation; không dùng để chạy code không tin cậy từ Internet. Cần sandbox OS, memory/CPU quota và permission model đầy đủ nếu mở dịch vụ. Chương trình hợp lệ có thể bị chặn vì nằm ngoài subset; lỗi được lưu, không tự mở rộng quyền.

### Cách đo

Lưu `step-NN.input.txt`, `.request.json` (không chứa Authorization), `.response.json`, `.answer.json` và event chuẩn hóa. 9Router trả `usage.prompt_tokens` / `completion_tokens`; backend ánh xạ thành `input_tokens` / `output_tokens`, cached input từ `prompt_tokens_details.cached_tokens`. Thiếu usage hợp lệ thì dừng, không tự ước lượng. JSONL `turn.completed` của provider 9Router là event do ứng dụng tạo để verifier dùng chung; raw response được giữ riêng. Usage phản ánh số router báo, không tự bảo đảm upstream thực sự tính bằng tokenizer nào.

Bảng dưới là **minh chứng lịch sử qua Codex CLI**, chưa phải số đo lại qua 9Router.

| Lần đo model thật | read_file | Code Mode |
|---|---:|---:|
| Số lượt model | 8 | 2 |
| Tổng usage.input_tokens của toàn bộ agent loop | 401.691 | 39.070 |
| usage.input_tokens ở lượt final | 89.666 | 19.609 |
| Tổng ký tự prompt do bài gửi qua các lượt | 705.189 | 2.606 |
| Top 3 đúng | Có | Có |
| Raw marker trong input context | Có | Không |

Giảm tổng input tokens: `(1 - 39070 / 401691) * 100 = 90,27%`. Số lượt giảm và raw history không lặp lại là hai nguồn giảm. Đây là **một lần đo trên fixture**, không phải bảo đảm cho mọi model/dataset. Cached input vẫn thuộc tổng input; số đo này không phải phần trăm tiết kiệm tiền. Bảng ghi cả tổng loop và final call để tránh so hai đại lượng khác nhau.

Offline gọi code/đọc file thật nhưng dùng action và final giả lập có nhãn. `model_calls=0`, `usage=null`, `input_token_saving_percent=null`. Không dùng kết quả offline để chứng minh model biết tự viết chương trình.

### Bash script và Code Mode đầy đủ

| Tiêu chí | Bash + script thường | Code Mode qua tools.* | Bản lab |
|---|---|---|---|
| Dữ liệu | OS/file/network trực tiếp | Proxy về harness | Wrapper glob/open → Tools |
| Permission | Quyền process | Từng tool và tham số | Allowlist, kiểm tra path/size |
| API/MCP | Script tự gọi API, quản credential | Hàm SDK, harness giữ credential | Chỉ log local; không làm proxy API/MCP tổng quát |
| Trace | Lệnh, stdout; cần tự instrument | Từng tool call | Inner list/read call + số byte |
| Runtime | Đã có nếu agent có shell | Cần runtime/proxy | Python subset trong child process |

Transport hiện tại gửi `POST /chat/completions` tới base URL 9Router, kèm JSON schema trong request và system message. Backend kiểm tra schema trước khi dispatch Python tool. Đây là **giao thức action JSON của ứng dụng**, không phải native function calling hay SDK JS `tools.*` đầy đủ. Xem [endpoint chính thức của 9Router](https://github.com/decolua/9router/blob/master/skills/9router-chat/SKILL.md) và [Chat Completions API](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

## 6. Quan hệ Memory, Compaction và Code Mode

- **Persistent memory (A):** giữ quy ước cần sống qua session; retrieve + inject vào context mới.
- **Compaction (B1):** sau khi history đã lớn, thay working context bằng checkpoint đủ để tiếp tục.
- **Code Mode (B2):** ngay khi xử lý tools, giữ intermediate data trong runtime, chỉ đưa findings vào model.

B1 xử lý dữ liệu **đã tích lũy**; B2 giảm dữ liệu **sẽ tích lũy**. Có thể kết hợp cả hai. Prompt caching là chủ đề khác: cached tokens vẫn ở trong input context; bài này không thực hiện cache router của Challenge C.

## 7. Kiểm thử và xem minh chứng

Từ thư mục lab07:

```powershell
python -X utf8 -B verify.py
```

Lệnh này chạy test của hai folder và kiểm lại minh chứng được lưu; **không gọi model, không dùng quota**. Kiểm riêng:

```powershell
cd challenge-a
python -X utf8 -B -m unittest discover -s tests -v
python -X utf8 -B demo.py --verify evidence/live-validation
node --check web/app.js

cd ../challenge-b
python -X utf8 -B -m unittest discover -s tests -v
python -X utf8 -B verify.py evidence/live-validation
node --check web/app.js
```

Node chỉ cần cho kiểm tra cú pháp JS, không cần chạy ứng dụng. Xem [VALIDATION.md](VALIDATION.md) để phân biệt kiểm thử tự động, chạy model thật và kiểm tra trình duyệt.

Minh chứng A: `context.json, trace.json, result.json` của từng session; `memory.json`; `step-NN.input.txt, .schema.json, .answer.json, .events.jsonl, .stderr.txt`.

Minh chứng B1: `archive.json, checkpoint.json, before/after/truncated.input.txt`, model answer/events/usage và report. B2: fixture `logs/`, `expected.json`, input/action/events từng mode, `trace.json`, `result.json` và report.

Đường dẫn tuyệt đối trong report ghi môi trường gốc. Các verifier tìm file tương đối dưới thư mục minh chứng hiện tại, nên có thể kiểm lại sau khi copy project. Minh chứng chứa log giả lập của bài; trace UI mới có thể chứa câu bạn nhập.

## 8. Các quyết định thực thi

Key nằm ở backend. HTTP chỉ được dùng với loopback; endpoint từ xa cần HTTPS. Không chấp nhận URL nhúng credential/query/fragment và không follow redirect mang Authorization sang đích khác. Không tự retry/fallback khi provider lỗi. HTTP error artifact chỉ lưu status, không lưu error body có thể chứa credential. Response/request được che key trước khi ghi artifact.

Request không đưa native tools cho provider. Python kiểm tra action theo JSON schema (type, required, enum, extra fields), rồi thực thi tool thuộc allowlist. Mỗi request có timeout 120 giây; response giới hạn 2 MB. Response bị cắt, refusal, native tool call hoặc thiếu usage đều là lỗi, không giả completed.

Server chỉ phục vụ frontend định sẵn và API; kiểm tra Host/Origin, JSON size/type, chặn job trùng và không đọc file tùy ý qua HTTP. Mỗi demo tạo thư mục mới. UI không tự resume job sau reload/restart; file evidence vẫn còn. Runtime Code Mode không nhận environment credential.

Các file `evidence/live-validation/` được giữ nguyên để kiểm lại minh chứng lịch sử qua Codex CLI. Không sửa số liệu cũ thành kết quả của 9Router. Chạy mới với `--live --output evidence/router-<ten-moi>` để tạo phép đo của provider hiện tại.
