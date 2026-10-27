# Phân tích Block 1

## Phạm vi thay đổi

Bài làm nằm trong `block-1-submission/`, là bản sao stage 00–02. Project mẫu được giữ nguyên. Chỉ thay đổi mã tool, export/đăng ký tool và cập nhật kiểm tra tương ứng; không chèn tên file chính sách hoặc đáp án vào system prompt.

`list_files(path)` ở stage 01 và 02 dùng `_resolve` và `_error` của tool file hiện có. Kết quả gồm `ok`, `path`, `entries`; mỗi mục có `name`, `path` tương đối workspace và `type`. Chỉ liệt kê mục trực tiếp, sắp xếp theo tên. Đường dẫn file, không tồn tại, tuyệt đối hoặc thoát workspace trả lỗi. Mỗi entry được resolve lại để từ chối symlink trỏ ra ngoài.

Skill `refund-policy` được đặt trong `stage-02-skills/workspace/skills/refund-policy/`, có frontmatter và reference mẫu trả lời. Skill tìm tài liệu trong `data/policies/`, đọc phạm vi hiệu lực, chọn theo ngày mua, hỏi lại khi thiếu ngày hoặc trạng thái kích hoạt. Không dùng Bash/script. Fixtures cũng có chính sách và skill để reset workspace không xóa bài làm.

## Kết quả kiểm tra tool thực tế

Đã chạy `python check_tools.py`: PASS cho cả stage 01 và 02. Bằng chứng: `tool-check-results.json`.

| Đầu vào | Kết quả |
|---|---|
| `data/policies` | Hai mục file, tên được sắp xếp, đường dẫn tương đối đúng |
| `data/policies/policy-before-oct.md` | `NOT_A_DIRECTORY` |
| `data/does-not-exist` | `DIRECTORY_NOT_FOUND` |
| `../outside` | `PATH_OUTSIDE_WORKSPACE` |
| Đường dẫn tuyệt đối workspace | `PATH_OUTSIDE_WORKSPACE` |
| Thư mục có file và thư mục con | Liệt kê trực tiếp, không đưa file nằm sâu vào kết quả |
| Symlink ra ngoài | SKIPPED: Windows từ chối tạo symlink (`WinError 1`) |

Kiểm tra trực tiếp chỉ thay decorator LangChain bằng decorator đồng nhất để chạy mã filesystem thật không cần dependency. Đây không phải bằng chứng model gọi tool. Các test pytest bổ sung kiểm tra tool schema, decorator thật và agent middleware; kết quả chạy pytest cần xác nhận từ môi trường thực thi.

## Các trường hợp và bằng chứng trace

`run_cases.py` chạy agent/model thật theo `.env` bên ngoài bài nộp. Mỗi câu hỏi bắt đầu bằng lịch sử mới và conversation ID mới. Script tạo trace JSONL qua ObserverMiddleware/TraceWriter hiện có và file `<case>-index.json` chỉ vị trí trace. Khi đổi tên chính sách, script dùng `terms-legacy.md` và `terms-current.md`, chạy lại A/B rồi khôi phục tên bằng `finally`.

| Trường hợp | Kết quả cần đạt | Vị trí bằng chứng cần đối chiếu |
|---|---|---|
| Stage 00, A | Không có khả năng truy cập tài liệu; không thể kết luận có căn cứ | `stage-00-chat/traces/A-index.json`; snapshot `model_request` có tools rỗng, không có `tool_finished` đọc tài liệu |
| Stage 01/02, A | Chính sách trước tháng 10; 8 ngày; không đủ điều kiện | `stage-01-files/traces/A-index.json`, `stage-02-skills/traces/A-index.json`; `list_files`, `read_file` chính sách và `run_completed.answer` |
| Stage 01/02, B | Chính sách từ tháng 10; 10 ngày; đủ điều kiện, không phí | `B-index.json`; stage 02 phải có đọc SKILL.md, reference và policy trong `tool_finished`, đồng thời nội dung được đưa vào snapshot `model_request` sau đó |
| A sau đổi tên | 8 ngày; không đủ điều kiện; dẫn `terms-legacy.md` | `A-renamed-index.json`; `list_files` tìm tên mới, `read_file` đọc tên mới; snapshot đầu chỉ có câu hỏi mới |
| B sau đổi tên | 10 ngày; đủ điều kiện, không phí; dẫn `terms-current.md` | `B-renamed-index.json`; đọc skill, reference, file tên mới và câu trả lời cuối |
| Thiếu thông tin | Hỏi trạng thái kích hoạt; chưa kết luận | `missing-index.json`; `run_completed.answer` |

**Trạng thái xác minh:** Các lượt chạy model thật và pytest đã được khởi động sau khi tìm thấy `.env` người dùng thêm. Công cụ thực thi sau đó lỗi khởi tạo (`0xc0000142` và `helper_unknown_error`), nên chưa đọc được kết quả cuối. Bảng trên ghi kỳ vọng và vị trí tra cứu, không khẳng định các trace đã đạt. Cần kiểm tra trace thực tế trước khi nộp; không tạo trace giả hay dùng mock như bằng chứng model thật.

## Giới hạn stage 00

Stage 00 không có tools hoặc skill catalog. Agent thiếu khả năng liệt kê và đọc tài liệu nội bộ; thiếu nội dung hai phiên bản chính sách để áp dụng thời hạn, phí và điều kiện kích hoạt. Câu trả lời từ kiến thức sẵn có không chứng minh đã đọc chính sách. Bằng chứng đúng phải là tool result trong lịch sử, mà stage này không thể có.

## Trả lời câu hỏi cuối bài

Tool cung cấp khả năng hành động: liệt kê thư mục để khám phá tên tài liệu hiện có, sau đó đọc nội dung thật. Skill cung cấp quy trình ra quyết định: đọc phạm vi hiệu lực, chọn phiên bản theo ngày mua, tính chênh lệch ngày lịch theo ngày yêu cầu trong câu hỏi, kiểm tra trạng thái kích hoạt và trình bày kết luận có dẫn nguồn.

Nếu thiếu tool tìm file, chỉ sửa prompt không giải quyết đầy đủ yêu cầu đổi tên file. Prompt có thể bảo agent tìm nhưng không tạo khả năng truy cập filesystem. Ghi tên file cố định sẽ hỏng khi đổi tên; nhét nội dung chính sách vào prompt vi phạm giới hạn bài và không chứng minh agent đọc tài liệu hiện có. Vì vậy cần cả tool tìm/đọc dữ liệu và skill hướng dẫn áp dụng dữ liệu đó.

## Bảo mật bài nộp

Không sao chép `.env` hoặc API key vào bản nộp. Khi đóng gói, loại `.venv`, `.runtime`, cache và `__pycache__`; giữ source, policies, skill, test, trace thật đã xác minh, kết quả tool và tài liệu này.
