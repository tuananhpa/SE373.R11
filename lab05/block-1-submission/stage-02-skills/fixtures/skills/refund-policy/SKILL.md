---
name: refund-policy
description: Tra cứu chính sách hoàn tiền và xác định điều kiện, phí theo ngày mua khi khách hàng hỏi về hoàn tiền hoặc đổi phiên bản chính sách.
---

# Tra cứu chính sách hoàn tiền

Nếu thiếu ngày mua, ngày yêu cầu hoàn hoặc trạng thái kích hoạt, hỏi thông tin còn thiếu trước khi kết luận; không tự giả định trạng thái.

Dùng list_files với đường dẫn data/policies/ để tìm tài liệu hiện có. Không đoán hoặc ghi nhớ tên file từ cuộc trò chuyện khác. Dùng read_file đọc các tài liệu và phạm vi hiệu lực, chọn phiên bản theo **ngày mua**, không theo ngày yêu cầu hoàn hay ngày hiện tại. Nếu tài liệu thiếu, phạm vi chồng lấn hoặc không bao phủ ngày mua, nêu vấn đề và hỏi lại thay vì đoán chính sách.

Tính số ngày bằng chênh lệch ngày lịch giữa ngày yêu cầu trong câu hỏi và ngày mua. Bằng đúng giới hạn vẫn đạt điều kiện thời gian. Nếu ngày yêu cầu trước ngày mua, hỏi xác nhận ngày. Kiểm tra cả thời hạn và điều kiện kích hoạt trong tài liệu đã chọn. Chỉ nêu phí hoàn tiền khi đủ điều kiện; thiếu giá trị đơn thì nêu tỷ lệ hoặc mức phí theo tài liệu, không tự tính số tiền.

Trước khi trả lời, đọc [mẫu trả lời](references/answer-template.md) bằng read_file tại skills/refund-policy/references/answer-template.md và dùng các trường trong mẫu. Không cần Bash hoặc script.
