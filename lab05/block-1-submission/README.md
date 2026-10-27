# Bài nộp Block 1 — Tra cứu chính sách đúng phiên bản

Bản sao stage 00–02; project mẫu được giữ nguyên. Xem analysis.md để đọc kết quả và vị trí bằng chứng.

## Nội dung

- stage-01-files/tools/files.py và stage-02-skills/tools/files.py: list_files, dùng chung bộ xử lý đường dẫn với read_file.
- tools/__init__.py và agent.py ở hai stage: export và đăng ký tool trong TOOLS.
- workspace/data/policies/: hai chính sách; fixtures cũng có bản sao để reset workspace không làm mất bài.
- stage-02-skills/workspace/skills/refund-policy/: SKILL.md và references/answer-template.md.
- check_tools.py: kiểm tra trực tiếp filesystem; tool-check-results.json: kết quả thực tế.
- run_cases.py: chạy model thật, mỗi trường hợp có lịch sử mới; tự đổi tên chính sách, chạy A/B rồi khôi phục tên.

## Chạy lại

Từ thư mục bản nộp, cài dependency:

```powershell
uv sync --project stage-02-skills
```

Dùng môi trường stage 02 để chạy các stage. Cấu hình được đọc từ file .env bên ngoài bài nộp:

```powershell
.\stage-02-skills\.venv\Scripts\python.exe run_cases.py stage-00-chat --env ..\agent-tools-skills-lab\.env
.\stage-02-skills\.venv\Scripts\python.exe run_cases.py stage-01-files --env ..\agent-tools-skills-lab\.env
.\stage-02-skills\.venv\Scripts\python.exe run_cases.py stage-02-skills --env ..\agent-tools-skills-lab\.env
```

Chạy UI: đặt cấu hình .env riêng trong stage cần mở, rồi dùng uv run streamlit run app.py tại stage đó. Tải lại trang và tạo cuộc trò chuyện mới sau khi đổi skill hoặc tên tài liệu.

Không nộp .env, API key, .venv hoặc .runtime. Traces chỉ chứa nội dung câu hỏi, model request, tool result và câu trả lời.
