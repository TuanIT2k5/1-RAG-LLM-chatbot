"""
[SP6-01] Kịch bản khởi tạo Bộ dữ liệu kiểm thử chuẩn (Golden Dataset - 75 câu hỏi)
và Bộ 4 tài liệu thực tế tiêu biểu (PDF 16-20 trang & DOCX) phục vụ đánh giá định lượng RAG.

Sản phẩm đầu ra:
1. docs/golden_dataset/documents/01_Bo_luat_Lao_dong_Trich_yeu.pdf (20 trang)
2. docs/golden_dataset/documents/02_Quy_che_Dao_tao_Tin_chi_Dai_hoc.pdf (18 trang)
3. docs/golden_dataset/documents/03_Tai_lieu_Kien_truc_Ky_thuat_CNTT_RAG.pdf (16 trang)
4. docs/golden_dataset/documents/04_So_tay_Chinh_sach_Nhan_su_va_ATTT.docx (15 mục & bảng biểu)
5. docs/golden_dataset/golden_dataset_75.json (75 câu hỏi: 40 trực tiếp, 20 tổng hợp, 15 ngoài phạm vi)
6. docs/golden_dataset/golden_dataset_75.csv (CSV UTF-8 BOM mở trực tiếp bằng Excel / Pandas)
7. docs/golden_dataset/README.md (Tài liệu mô tả chi tiết cấu trúc Golden Dataset)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from docx import Document as DocxDocument
import pymupdf as fitz

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = PROJECT_ROOT / "docs" / "golden_dataset"
DOCS_DIR = GOLDEN_DIR / "documents"

REFUSAL_STANDARD_ANSWER = (
    "Xin lỗi, tôi không tìm thấy thông tin liên quan trong các tài liệu hiện có "
    "để trả lời câu hỏi này."
)


# ==============================================================================
# 1. NỘI DUNG 4 TÀI LIỆU TIÊU BIỂU ([SP6-01.1] - ĐỘ DÀI 15-20 TRANG/TÀI LIỆU)
# ==============================================================================

DOC_01_FILENAME = "01_Bo_luat_Lao_dong_Trich_yeu.pdf"
DOC_01_PAGES: List[str] = [
    # Trang 1
    "BỘ LUẬT LAO ĐỘNG 2019 - TÀI LIỆU TRÍCH YẾU QUY CHUẨN\n"
    "Chương I: NHỮNG QUY ĐỊNH CHUNG\n"
    "Điều 1. Phạm vi điều chỉnh: Bộ luật Lao động quy định tiêu chuẩn lao động, quyền, nghĩa vụ, trách nhiệm của người lao động, người sử dụng lao động.\n"
    "Điều 2. Đối tượng áp dụng: Người lao động Việt Nam, người học nghề, tập nghề và người lao động nước ngoài làm việc tại Việt Nam.\n"
    "Điều 3. Giải thích từ ngữ: Người lao động là người làm việc cho người sử dụng lao động theo thỏa thuận, được trả lương và chịu sự quản lý, điều hành, giám sát của người sử dụng lao động. Độ tuổi lao động tối thiểu của người lao động là đủ 15 tuổi, trừ trường hợp quy định riêng.",
    # Trang 2
    "Chương II: HỢP ĐỒNG LAO ĐỘNG VÀ HÌNH THỨC GIAO KẾT\n"
    "Điều 13. Hợp đồng lao động là sự thỏa thuận giữa người lao động và người sử dụng lao động về việc làm có trả công, tiền lương, điều kiện lao động.\n"
    "Điều 14. Hình thức hợp đồng lao động: Hợp đồng lao động phải được giao kết bằng văn bản và được làm thành 02 bản, người lao động giữ 01 bản, người sử dụng lao động giữ 01 bản. Hợp đồng giao kết thông qua phương tiện điện tử dưới hình thức thông điệp dữ liệu có giá trị như hợp đồng bằng văn bản.\n"
    "Hai bên có thể giao kết hợp đồng lao động bằng lời nói đối với hợp đồng có thời hạn dưới 01 tháng, trừ các trường hợp công việc theo mùa vụ đặc biệt.",
    # Trang 3
    "Điều 20. Loại hợp đồng lao động:\n"
    "1. Hợp đồng lao động không xác định thời hạn là hợp đồng mà trong đó hai bên không xác định thời hạn, thời điểm chấm dứt hiệu lực của hợp đồng.\n"
    "2. Hợp đồng lao động xác định thời hạn là hợp đồng mà trong đó hai bên xác định thời hạn, thời điểm chấm dứt hiệu lực của hợp đồng trong thời gian không quá 36 tháng kể từ thời điểm có hiệu lực.\n"
    "Khi hợp đồng lao động xác định thời hạn hết hạn mà người lao động vẫn tiếp tục làm việc thì trong thời hạn 30 ngày kể từ ngày hết hạn, hai bên phải ký kết hợp đồng lao động mới; chỉ được ký thêm 01 lần hợp đồng lao động xác định thời hạn.",
    # Trang 4
    "Điều 24 và Điều 25. THỬ VIỆC VÀ THỜI GIAN THỬ VIỆC:\n"
    "Thời gian thử việc do hai bên thỏa thuận căn cứ vào tính chất và mức độ phức tạp của công việc nhưng chỉ được thử việc 01 lần đối với một công việc và bảo đảm điều kiện sau:\n"
    "1. Không quá 180 ngày đối với công việc của người quản lý doanh nghiệp theo quy định của Luật Doanh nghiệp.\n"
    "2. Không quá 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên (bao gồm trình độ đại học, thạc sĩ, tiến sĩ).\n"
    "3. Không quá 30 ngày đối với công việc cần trình độ chuyên môn, kỹ thuật trung cấp, công nhân kỹ thuật, nhân viên nghiệp vụ.\n"
    "4. Không quá 06 ngày làm việc đối với công việc khác.",
    # Trang 5
    "Điều 26 và Điều 27. TIỀN LƯƠNG THỬ VIỆC VÀ KẾT THÚC THỬ VIỆC:\n"
    "1. Tiền lương của người lao động trong thời gian thử việc do hai bên thỏa thuận nhưng ít nhất phải bằng 85% mức tiền lương của công việc đó.\n"
    "2. Khi kết thúc thời gian thử việc, người sử dụng lao động phải thông báo kết quả thử việc cho người lao động.\n"
    "3. Trong thời gian thử việc, mỗi bên có quyền hủy bỏ hợp đồng thử việc hoặc hợp đồng lao động đã giao kết mà không cần báo trước và không phải bồi thường.\n"
    "4. Không áp dụng thử việc đối với người lao động giao kết hợp đồng lao động có thời hạn dưới 01 tháng.",
    # Trang 6
    "Điều 29. CHUYỂN NGƯỜI LAO ĐỘNG LÀM CÔNG VIỆC KHÁC SO VỚI HỢP ĐỒNG LAO ĐỘNG:\n"
    "1. Khi gặp khó khăn đột xuất do thiên tai, hỏa hoạn, dịch bệnh nguy hiểm, người sử dụng lao động được quyền tạm thời chuyển người lao động làm công việc khác so với hợp đồng lao động nhưng không được quá 60 ngày làm việc cộng dồn trong 01 năm.\n"
    "2. Người sử dụng lao động phải báo cho người lao động biết trước ít nhất 03 ngày làm việc.\n"
    "3. Tiền lương theo công việc mới nếu thấp hơn tiền lương công việc cũ thì được giữ nguyên tiền lương của công việc cũ trong thời hạn 30 ngày làm việc; tiền lương mới ít nhất phải bằng 85% tiền lương công việc cũ.",
    # Trang 7
    "Điều 35. QUYỀN ĐƠN PHƯƠNG CHẤM DỨT HỢP ĐỒNG LAO ĐỘNG CỦA NGƯỜI LAO ĐỘNG:\n"
    "1. Người lao động có quyền đơn phương chấm dứt hợp đồng lao động nhưng phải báo trước cho người sử dụng lao động như sau:\n"
    "a) Ít nhất 45 ngày nếu làm việc theo hợp đồng lao động không xác định thời hạn;\n"
    "b) Ít nhất 30 ngày nếu làm việc theo hợp đồng lao động xác định thời hạn có thời hạn từ 12 tháng đến 36 tháng;\n"
    "c) Ít nhất 03 ngày làm việc nếu làm việc theo hợp đồng lao động xác định thời hạn có thời hạn dưới 12 tháng.\n"
    "2. Người lao động có quyền đơn phương chấm dứt hợp đồng không cần báo trước nếu không được trả đủ lương hoặc bị ngược đãi, quấy rối tại nơi làm việc.",
    # Trang 8
    "Điều 46 và Điều 47. TRỢ CẤP THÔI VIỆC VÀ TRỢ CẤP MẤT VIỆC LÀM:\n"
    "1. Trợ cấp thôi việc (Điều 46): Khi hợp đồng lao động chấm dứt hợp pháp đối với người lao động đã làm việc thường xuyên từ đủ 12 tháng trở lên, mỗi năm làm việc được trợ cấp một nửa tháng tiền lương (0.5 tháng lương/năm).\n"
    "2. Trợ cấp mất việc làm (Điều 47): Người sử dụng lao động trả trợ cấp mất việc làm cho người lao động đã làm việc thường xuyên từ đủ 12 tháng trở lên bị mất việc do thay đổi cơ cấu, công nghệ hoặc lý do kinh tế, cứ mỗi năm làm việc trả 01 tháng tiền lương nhưng ít nhất bằng 02 tháng tiền lương.",
    # Trang 9
    "Chương VI: TIỀN LƯƠNG VÀ HÌNH THỨC TRẢ LƯƠNG\n"
    "Điều 90 và Điều 91. Tiền lương bao gồm mức lương theo công việc hoặc chức danh, phụ cấp lương và các khoản bổ sung khác. Mức lương theo công việc hoặc chức danh không được thấp hơn mức lương tối thiểu vùng do Chính phủ quy định.\n"
    "Điều 94. Nguyên tắc trả lương: Người sử dụng lao động phải trả lương trực tiếp, đầy đủ, đúng hạn cho người lao động. Trường hợp vì lý do bất khả kháng mà không thể trả lương đúng hạn thì không được chậm quá 30 ngày; nếu trả lương chậm từ 15 ngày trở lên thì phải đền bù một khoản tiền ít nhất bằng số tiền lãi của số tiền trả chậm.",
    # Trang 10
    "Điều 98. TIỀN LƯƠNG LÀM THÊM GIỜ, LÀM VIỆC VÀO BAN ĐÊM:\n"
    "1. Người lao động làm thêm giờ được trả lương tính theo đơn giá tiền lương hoặc tiền lương thực trả theo công việc đang làm như sau:\n"
    "a) Vào ngày thường, ít nhất bằng 150%;\n"
    "b) Vào ngày nghỉ hằng tuần, ít nhất bằng 200%;\n"
    "c) Vào ngày nghỉ lễ, tết, ngày nghỉ có hưởng lương, ít nhất bằng 300% chưa kể tiền lương ngày lễ, tết đối với người lao động hưởng lương ngày.\n"
    "2. Người lao động làm việc vào ban đêm thì được trả thêm ít nhất bằng 30% tiền lương tính theo đơn giá tiền lương của ngày làm việc bình thường.",
    # Trang 11
    "Điều 101 và Điều 102. TẠM ỨNG TIỀN LƯƠNG VÀ KHẤU TRỪ TIỀN LƯƠNG:\n"
    "1. Người sử dụng lao động chỉ được khấu trừ tiền lương của người lao động để bồi thường thiệt hại do làm hư hỏng dụng cụ, thiết bị, tài sản của người sử dụng lao động.\n"
    "2. Mức khấu trừ tiền lương hằng tháng không được quá 30% tiền lương thực trả hằng tháng của người lao động sau khi trích nộp các khoản bảo hiểm xã hội bắt buộc, bảo hiểm y tế, bảo hiểm thất nghiệp, thuế thu nhập cá nhân.\n"
    "3. Người lao động có quyền được biết lý do mọi khoản khấu trừ tiền lương của mình.",
    # Trang 12
    "Chương VII: THỜI GIỜ LÀM VIỆC, THỜI GIỜ NGHỈ NGƠI\n"
    "Điều 105 và Điều 106. Thời giờ làm việc bình thường và Giờ làm việc ban đêm:\n"
    "1. Thời giờ làm việc bình thường không quá 08 giờ trong 01 ngày và không quá 48 giờ trong 01 tuần.\n"
    "2. Nhà nước khuyến khích người sử dụng lao động thực hiện tuần làm việc 40 giờ đối với người lao động.\n"
    "3. Giờ làm việc ban đêm được tính từ 22 giờ đến 06 giờ sáng ngày hôm sau.",
    # Trang 13
    "Điều 107. LÀM THÊM GIỜ VÀ GIỚI HẠN SỐ GIỜ LÀM THÊM:\n"
    "1. Bảo đảm số giờ làm thêm của người lao động không quá 50% số giờ làm việc bình thường trong 01 ngày; trường hợp áp dụng quy định thời giờ làm việc bình thường theo tuần thì tổng số giờ làm việc bình thường và số giờ làm thêm không quá 12 giờ trong 01 ngày; không quá 40 giờ trong 01 tháng.\n"
    "2. Bảo đảm số giờ làm thêm của người lao động không quá 200 giờ trong 01 năm.\n"
    "3. Trường hợp đặc biệt do Chính phủ quy định (như sản xuất hàng xuất khẩu dệt may, điện tử, chế biến thủy sản) thì được làm thêm giờ không quá 300 giờ trong 01 năm.",
    # Trang 14
    "Điều 112. NGHỈ LỄ, TẾT HƯỞNG NGUYÊN LƯƠNG (TỔNG CỘNG 11 NGÀY):\n"
    "Người lao động được nghỉ làm việc, hưởng nguyên lương trong những ngày lễ, tết sau đây:\n"
    "1. Tết Dương lịch: 01 ngày (ngày 01 tháng 01 dương lịch);\n"
    "2. Tết Âm lịch: 05 ngày;\n"
    "3. Ngày Chiến thắng: 01 ngày (ngày 30 tháng 4 dương lịch);\n"
    "4. Ngày Quốc tế lao động: 01 ngày (ngày 01 tháng 5 dương lịch);\n"
    "5. Quốc khánh: 02 ngày (ngày 02 tháng 9 dương lịch và 01 ngày liền kề trước hoặc sau);\n"
    "6. Ngày Giỗ Tổ Hùng Vương: 01 ngày (ngày 10 tháng 3 âm lịch).",
    # Trang 15
    "Điều 113. NGHỈ HẰNG NĂM (NGHỈ PHÉP NĂM):\n"
    "1. Người lao động làm việc đủ 12 tháng cho một người sử dụng lao động thì được nghỉ hằng năm, hưởng nguyên lương theo hợp đồng lao động như sau:\n"
    "a) 12 ngày làm việc đối với người làm công việc trong điều kiện bình thường;\n"
    "b) 14 ngày làm việc đối với người lao động chưa thành niên, lao động là người khuyết tật, người làm nghề, công việc nặng nhọc, độc hại, nguy hiểm;\n"
    "c) 16 ngày làm việc đối với người làm nghề, công việc đặc biệt nặng nhọc, độc hại, nguy hiểm.\n"
    "2. Người lao động làm việc chưa đủ 12 tháng thì số ngày nghỉ hằng năm theo tỷ lệ tương ứng với số tháng làm việc.",
    # Trang 16
    "Điều 114 và Điều 115. NGÀY NGHỈ HẰNG NĂM TĂNG THÊM THEO THÂM NIÊN VÀ NGHỈ VIỆC RIÊNG:\n"
    "1. Ngày nghỉ phép tăng thêm theo thâm niên (Điều 114): Cứ đủ 05 năm làm việc cho một người sử dụng lao động thì số ngày nghỉ hằng năm của người lao động được tăng thêm tương ứng 01 ngày.\n"
    "2. Nghỉ việc riêng mà vẫn hưởng nguyên lương (Điều 115):\n"
    "a) Kết hôn: nghỉ 03 ngày;\n"
    "b) Con đẻ, con nuôi kết hôn: nghỉ 01 ngày;\n"
    "c) Cha đẻ, mẹ đẻ, cha nuôi, mẹ nuôi; cha đẻ, mẹ đẻ của vợ hoặc chồng; vợ hoặc chồng; con đẻ, con nuôi chết: nghỉ 03 ngày.",
    # Trang 17
    "Chương VIII: KỶ LUẬT LAO ĐỘNG VÀ TRÁCH NHIỆM VẬT CHẤT\n"
    "Điều 122 và Điều 123. Nguyên tắc, trình tự, thủ tục và Thời hiệu xử lý kỷ luật lao động:\n"
    "1. Thời hiệu xử lý kỷ luật lao động là 06 tháng kể từ ngày xảy ra hành vi vi phạm; trường hợp hành vi vi phạm liên quan trực tiếp đến tài chính, tài sản, tiết lộ bí mật công nghệ, bí mật kinh doanh của người sử dụng lao động thì thời hiệu xử lý kỷ luật lao động là 12 tháng.\n"
    "2. Không được xử lý kỷ luật lao động đối với người lao động đang trong thời gian nghỉ ốm đau, điều dưỡng, đang mang thai hoặc nuôi con nhỏ dưới 12 tháng tuổi.",
    # Trang 18
    "Điều 124 và Điều 125. HÌNH THỨC XỬ LÝ KỶ LUẬT LAO ĐỘNG VÀ ÁP DỤNG SA THẢI:\n"
    "1. Có 04 hình thức xử lý kỷ luật lao động: Khiển trách; Kéo dài thời hạn nâng lương không quá 06 tháng; Cách chức; Sa thải.\n"
    "2. Hình thức kỷ luật sa thải được người sử dụng lao động áp dụng trong trường hợp:\n"
    "a) Người lao động có hành vi trộm cắp, tham ô, đánh bạc, cố ý gây thương tích, sử dụng ma túy tại nơi làm việc;\n"
    "b) Tiết lộ bí mật kinh doanh, bí mật công nghệ, xâm phạm quyền sở hữu trí tuệ;\n"
    "c) Tự ý bỏ việc 05 ngày cộng dồn trong thời hạn 30 ngày hoặc 20 ngày cộng dồn trong thời hạn 365 ngày tính từ ngày đầu tiên tự ý bỏ việc mà không có lý do chính đáng.",
    # Trang 19
    "Chương X: NHỮNG QUY ĐỊNH RIÊNG ĐỐI VỚI LAO ĐỘNG NỮ VÀ THAI SẢN\n"
    "Điều 137 và Điều 139. Bảo vệ thai sản và Nghỉ thai sản:\n"
    "1. Người sử dụng lao động không được sử dụng người lao động làm việc ban đêm, làm thêm giờ và đi công tác xa khi mang thai từ tháng thứ 07 (hoặc từ tháng thứ 06 nếu làm việc ở vùng cao, vùng sâu, vùng xa, biên giới, hải đảo) hoặc đang nuôi con dưới 12 tháng tuổi.\n"
    "2. Lao động nữ được nghỉ thai sản trước và sau khi sinh con là 06 tháng; thời gian nghỉ trước khi sinh không quá 02 tháng. Trường hợp lao động nữ sinh đôi trở lên thì tính từ con thứ 02 trở đi, cứ mỗi con người mẹ được nghỉ thêm 01 tháng.",
    # Trang 20
    "Chương XII: BẢO HIỂM XÃ HỘI, BẢO HIỂM Y TẾ, BẢO HIỂM THẤT NGHIỆP VÀ TUỔI NGHỈ HƯU\n"
    "Điều 168 và Điều 169. Tham gia bảo hiểm bắt buộc và Tuổi nghỉ hưu:\n"
    "1. Người sử dụng lao động và người lao động phải tham gia bảo hiểm xã hội bắt buộc, bảo hiểm y tế, bảo hiểm thất nghiệp.\n"
    "2. Tuổi nghỉ hưu của người lao động trong điều kiện lao động bình thường được điều chỉnh theo lộ trình cho đến khi đủ 62 tuổi đối với lao động nam vào năm 2028 và đủ 60 tuổi đối với lao động nữ vào năm 2035.\n"
    "3. Kể từ năm 2021, mỗi năm tăng thêm 03 tháng đối với lao động nam và 04 tháng đối với lao động nữ.",
]


DOC_02_FILENAME = "02_Quy_che_Dao_tao_Tin_chi_Dai_hoc.pdf"
DOC_02_PAGES: List[str] = [
    # Trang 1
    "QUY CHẾ ĐÀO TẠO ĐẠI HỌC THEO HỆ THỐNG TÍN CHỈ\n"
    "Chương I: QUY ĐỊNH CHUNG VỀ ĐÀO TẠO TÍN CHỈ\n"
    "Điều 1. Tín chỉ là đơn vị dùng để đo lường khối lượng học tập của sinh viên. Một tín chỉ được quy định bằng 15 tiết học lý thuyết hoặc 30 tiết thực hành, thí nghiệm, thảo luận trên lớp, và tối thiểu 30 giờ tự học chuẩn bị cá nhân.\n"
    "Điều 2. Một tiết học trên lớp được tính bằng 50 phút.",
    # Trang 2
    "Điều 3. KHỐI LƯỢNG CHƯƠNG TRÌNH ĐÀO TẠO VÀ THỜI GIAN ĐÀO TẠO CHUẨN:\n"
    "1. Chương trình đào tạo trình độ đại học hệ Cử nhân có tổng khối lượng tối thiểu là 120 tín chỉ (chưa tính học phần Giáo dục thể chất và Giáo dục quốc phòng - an ninh), thời gian đào tạo chuẩn là 4.0 năm (8 học kỳ chính).\n"
    "2. Chương trình đào tạo hệ Kỹ sư chuyên sâu đặc thù có tổng khối lượng tối thiểu là 150 tín chỉ, thời gian đào tạo chuẩn là 5.0 năm (10 học kỳ chính).\n"
    "3. Thời gian tối đa để sinh viên hoàn thành khóa học không được vượt quá 2 lần thời gian thiết kế chuẩn của chương trình (tức tối đa 8.0 năm đối với hệ Cử nhân và 10.0 năm đối với hệ Kỹ sư).",
    # Trang 3
    "Chương II: TỔ CHỨC ĐÀO TẠO VÀ ĐĂNG KÝ HỌC PHẦN\n"
    "Điều 5. Học kỳ và tổ chức năm học: Mỗi năm học có 02 học kỳ chính (Học kỳ I và Học kỳ II), mỗi học kỳ chính có ít nhất 15 tuần thực học và 03 tuần thi kết thúc học phần. Ngoài hai học kỳ chính, Nhà trường có thể tổ chức 01 học kỳ phụ (Học kỳ Hè) kéo dài ít nhất 05 tuần thực học và 01 tuần thi.",
    # Trang 4
    "Điều 6. KHỐI LƯỢNG ĐĂNG KÝ HỌC TẬP TRONG MỖI HỌC KỲ:\n"
    "1. Trong mỗi học kỳ chính (trừ học kỳ cuối khóa), sinh viên có học lực bình thường phải đăng ký tối thiểu 14 tín chỉ và tối đa 24 tín chỉ.\n"
    "2. Đối với sinh viên xếp loại học lực yếu hoặc đang trong diện cảnh báo học vụ, khối lượng đăng ký tối thiểu là 10 tín chỉ và tối đa không quá 14 tín chỉ trong một học kỳ chính để tập trung cải thiện điểm.\n"
    "3. Trong học kỳ Hè, sinh viên được đăng ký tối đa không quá 09 tín chỉ.",
    # Trang 5
    "Điều 7. RÚT BỚT HỌC PHẦN ĐÃ ĐĂNG KÝ:\n"
    "1. Sinh viên được phép tự điều chỉnh, thêm hoặc hủy học phần không mất học phí trong 02 tuần đầu tiên của học kỳ chính (hoặc 01 tuần đầu của học kỳ Hè).\n"
    "2. Sau thời hạn trên nhưng không muộn hơn tuần thứ 06 của học kỳ chính, sinh viên có thể làm đơn xin rút bớt học phần để nhận điểm W (Withdrawn), nhưng vẫn phải đóng 50% học phí của học phần đó và tổng số tín chỉ còn lại không được thấp hơn mức tối thiểu.",
    # Trang 6
    "Chương III: ĐÁNH GIÁ KẾT QUẢ HỌC TẬP VÀ CÁCH TÍNH ĐIỂM\n"
    "Điều 9. Thành phần điểm đánh giá học phần:\n"
    "1. Điểm đánh giá học phần bao gồm: Điểm chuyên cần (trọng số 10%), Điểm kiểm tra giữa kỳ hoặc bài tập lớn (trọng số 30%) và Điểm thi kết thúc học phần (trọng số 60%).\n"
    "2. Điểm thi kết thúc học phần là bắt buộc cho mọi học phần và có trọng số không được thấp hơn 50%.\n"
    "3. Sinh viên vắng mặt quá 20% tổng số tiết quy định của học phần sẽ bị cấm thi kết thúc học phần và nhận điểm 0 (điểm F).",
    # Trang 7
    "Điều 10. BẢNG QUY ĐỔI THANG ĐIỂM 10, THANG ĐIỂM CHỮ VÀ THANG ĐIỂM 4:\n"
    "- Từ 8.5 đến 10.0 điểm: Điểm chữ A  -> Quy đổi thang 4 là 4.0 (Đạt - Xuất sắc/Giỏi)\n"
    "- Từ 8.0 đến 8.4 điểm:  Điểm chữ B+ -> Quy đổi thang 4 là 3.5 (Đạt - Khá giỏi)\n"
    "- Từ 7.0 đến 7.9 điểm:  Điểm chữ B  -> Quy đổi thang 4 là 3.0 (Đạt - Khá)\n"
    "- Từ 6.5 đến 6.9 điểm:  Điểm chữ C+ -> Quy đổi thang 4 là 2.5 (Đạt - Trung bình khá)\n"
    "- Từ 5.5 đến 6.4 điểm:  Điểm chữ C  -> Quy đổi thang 4 là 2.0 (Đạt - Trung bình)\n"
    "- Từ 5.0 đến 5.4 điểm:  Điểm chữ D+ -> Quy đổi thang 4 là 1.5 (Đạt có điều kiện)\n"
    "- Từ 4.0 đến 4.9 điểm:  Điểm chữ D  -> Quy đổi thang 4 là 1.0 (Đạt mức tối thiểu)\n"
    "- Dưới 4.0 điểm:        Điểm chữ F  -> Quy đổi thang 4 là 0.0 (Không đạt - Phải học lại).",
    # Trang 8
    "Điều 11. HỌC LẠI VÀ HỌC CẢI THIỆN ĐIỂM:\n"
    "1. Sinh viên có học phần bắt buộc bị điểm F (dưới 4.0 theo thang điểm 10) phải đăng ký học lại chính học phần đó ở các học kỳ tiếp theo.\n"
    "2. Đối với các học phần đạt điểm D hoặc D+, sinh viên được phép đăng ký học lại để cải thiện điểm trung bình tích lũy (CPA).\n"
    "3. Khi học cải thiện điểm, kết quả cao nhất trong các lần học sẽ được chọn để tính vào điểm trung bình tích lũy toàn khóa.",
    # Trang 9
    "Điều 12. XẾP HẠNG HỌC LỰC THEO ĐIỂM TRUNG BÌNH TÍCH LŨY (THANG ĐIỂM 4):\n"
    "- Loại Xuất sắc: Điểm trung bình tích lũy từ 3.60 đến 4.00\n"
    "- Loại Giỏi:     Điểm trung bình tích lũy từ 3.20 đến 3.59\n"
    "- Loại Khá:      Điểm trung bình tích lũy từ 2.50 đến 3.19\n"
    "- Loại Trung bình: Điểm trung bình tích lũy từ 2.00 đến 2.49\n"
    "- Loại Yếu:      Điểm trung bình tích lũy từ 1.00 đến 1.99\n"
    "- Loại Kém:      Điểm trung bình tích lũy dưới 1.00.",
    # Trang 10
    "Điều 14. CẢNH BÁO HỌC VỤ VÀ BUỘC THÔI HỌC:\n"
    "1. Sinh viên bị Cảnh báo học vụ vào cuối mỗi học kỳ chính nếu rơi vào một trong các trường hợp:\n"
    "a) Điểm trung bình học kỳ (GPA) đạt dưới 0.80 đối với học kỳ đầu tiên của khóa học, hoặc dưới 1.00 đối với các học kỳ tiếp theo;\n"
    "b) Tổng số tín chỉ không đạt (điểm F) trong học kỳ vượt quá 50% khối lượng đã đăng ký trong học kỳ đó, hoặc tổng số tín chỉ nợ đọng từ đầu khóa vượt quá 24 tín chỉ.\n"
    "2. Sinh viên bị Buộc thôi học nếu đã bị cảnh báo học vụ 02 lần liên tiếp hoặc tổng số lần bị cảnh báo học vụ vượt quá 03 lần trong toàn khóa học.",
    # Trang 11
    "Chương IV: NGHỈ HỌC TẠM THỜI (BẢO LƯU) VÀ HỌC CÙNG LÚC HAI CHƯƠNG TRÌNH\n"
    "Điều 16. Nghỉ học tạm thời và bảo lưu kết quả học tập:\n"
    "1. Sinh viên được quyền viết đơn xin nghỉ học tạm thời và bảo lưu kết quả đã học trong trường hợp: đi nghĩa vụ quân sự, bị ốm đau tai nạn phải điều trị dài ngày, hoặc vì lý do cá nhân.\n"
    "2. Để xin nghỉ học tạm thời vì lý do cá nhân, sinh viên phải đã học ít nhất 01 học kỳ tại trường, không thuộc diện bị buộc thôi học và có điểm trung bình tích lũy đạt từ 2.00 trở lên. Thời gian nghỉ học tạm thời vì lý do cá nhân tối đa không quá 02 năm (04 học kỳ chính) và được tính vào thời gian học tối đa của khóa học.",
    # Trang 12
    "Điều 17. HỌC CÙNG LÚC HAI CHƯƠNG TRÌNH (SONG BẰNG):\n"
    "Sinh viên được đăng ký học thêm chương trình thứ hai (song bằng) khi đáp ứng đủ các điều kiện:\n"
    "1. Đã kết thúc học kỳ thứ hai của năm học đầu tiên ở chương trình thứ nhất;\n"
    "2. Không thuộc diện xếp hạng học lực yếu ở chương trình thứ nhất và có điểm trung bình tích lũy (CPA) đạt từ 2.50 trở lên;\n"
    "3. Trong quá trình học hai chương trình, nếu điểm trung bình tích lũy của chương trình thứ nhất tụt xuống dưới 2.00 thì sinh viên phải dừng học chương trình thứ hai.",
    # Trang 13
    "Chương V: ĐỒ ÁN, KHÓA LUẬN TỐT NGHIỆP VÀ CHUẨN ĐẦU RA NGOẠI NGỮ\n"
    "Điều 19. Điều kiện nhận Đồ án / Khóa luận tốt nghiệp:\n"
    "1. Khóa luận tốt nghiệp có khối lượng từ 06 đến 10 tín chỉ tùy theo ngành đào tạo.\n"
    "2. Sinh viên được giao làm Khóa luận tốt nghiệp khi đã tích lũy tối thiểu 85% tổng số tín chỉ của chương trình đào tạo, không nợ quá 06 tín chỉ của các học phần bắt buộc và có điểm trung bình tích lũy từ 2.30 trở lên.",
    # Trang 14
    "Điều 20. CHUẨN ĐẦU RA NGOẠI NGỮ VÀ CÔNG NGHỆ THÔNG TIN:\n"
    "1. Đối với các ngành không chuyên ngữ, sinh viên phải đạt chuẩn đầu ra tiếng Anh tối thiểu bậc 3/6 theo Khung năng lực ngoại ngữ 6 bậc dùng cho Việt Nam (tương đương IELTS 5.0, TOEIC 550 điểm kỹ năng Nghe-Đọc hoặc TOEFL iBT 45 điểm).\n"
    "2. Đối với chương trình Chất lượng cao và Tiên tiến giảng dạy bằng tiếng Anh, chuẩn đầu ra ngoại ngữ tối thiểu là IELTS 6.0 hoặc TOEIC 650.\n"
    "3. Sinh viên phải có chứng chỉ Ứng dụng Công nghệ thông tin cơ bản theo chuẩn của Bộ Thông tin và Truyền thông.",
    # Trang 15
    "Chương VI: XÉT CÔNG NHẬN TỐT NGHIỆP VÀ XẾP HẠNG BẰNG TỐT NGHIỆP\n"
    "Điều 22. Điều kiện xét tốt nghiệp:\n"
    "1. Tích lũy đủ số học phần và khối lượng tín chỉ quy định của chương trình đào tạo (tối thiểu 120 tín chỉ với hệ Cử nhân, 150 tín chỉ với hệ Kỹ sư);\n"
    "2. Điểm trung bình tích lũy toàn khóa (CPA) đạt từ 2.00 trở lên (theo thang điểm 4);\n"
    "3. Đạt chuẩn đầu ra Ngoại ngữ, Tin học và có chứng chỉ Giáo dục thể chất, Giáo dục quốc phòng - an ninh;\n"
    "4. Tại thời điểm xét tốt nghiệp không bị truy cứu trách nhiệm hình sự hoặc không đang trong thời gian bị kỷ luật từ mức đình chỉ học tập trở lên.",
    # Trang 16
    "Điều 23. HẠ BẬC XẾP LOẠI BẰNG TỐT NGHIỆP:\n"
    "Hạng tốt nghiệp của sinh viên có điểm trung bình tích lũy toàn khóa loại Xuất sắc (3.60 - 4.00) và loại Giỏi (3.20 - 3.59) sẽ bị giảm đi một mức (Xuất sắc xuống Giỏi; Giỏi xuống Khá) nếu thuộc một trong các trường hợp:\n"
    "1. Khối lượng của các học phần phải học lại (do bị điểm F) vượt quá 5% so với tổng số tín chỉ quy định cho toàn chương trình đào tạo;\n"
    "2. Sinh viên đã bị kỷ luật từ mức Cảnh cáo trở lên trong thời gian học tại trường.",
    # Trang 17
    "Điều 24. CÔNG NHẬN TƯƠNG ĐƯƠNG VÀ CHUYỂN ĐỔI TÍN CHỈ:\n"
    "1. Sinh viên chuyển trường hoặc tham gia chương trình trao đổi quốc tế được xem xét công nhận và chuyển đổi tín chỉ nếu nội dung học phần tương đương ít nhất 80% và đạt từ điểm C (5.5 theo thang điểm 10) trở lên.\n"
    "2. Tổng số tín chỉ được công nhận chuyển đổi không vượt quá 50% tổng khối lượng của chương trình đào tạo.",
    # Trang 18
    "Điều 25. XỬ LÝ VI PHẠM QUY CHẾ THI VÀ HỌC THUẬT:\n"
    "1. Sinh viên mang tài liệu hoặc thiết bị thu phát sóng trái phép vào phòng thi sẽ bị lập biên bản Đình chỉ thi và nhận điểm 0 (điểm F) cho bài thi đó.\n"
    "2. Sinh viên nhờ người thi hộ hoặc đi thi hộ người khác sẽ bị kỷ luật Đình chỉ học tập 01 năm ở lần vi phạm thứ nhất và Buộc thôi học ở lần vi phạm thứ hai.\n"
    "3. Khóa luận tốt nghiệp có tỷ lệ đạo văn (Turnitin similarity) vượt quá 20% sẽ không được phép bảo vệ trước Hội đồng.",
]


DOC_03_FILENAME = "03_Tai_lieu_Kien_truc_Ky_thuat_CNTT_RAG.pdf"
DOC_03_PAGES: List[str] = [
    # Trang 1
    "TÀI LIỆU ĐẶC TẢ KIẾN TRÚC KỸ THUẬT HỆ THỐNG CNTT & ĐÁM MÂY DOANH NGHIỆP\n"
    "Mục 1. TỔNG QUAN KIẾN TRÚC HỆ THỐNG:\n"
    "Hệ thống phần mềm lõi của doanh nghiệp được thiết kế theo mô hình Modular Monolith trên nền tảng container hóa Docker, cho phép mở rộng sang Microservices khi lưu lượng vượt ngưỡng 5000 requests/giây.\n"
    "Ngôn ngữ lập trình chính phía Backend là Python 3.13 kết hợp FastAPI 0.115+, phía Frontend sử dụng React 18 với TypeScript 5.x và Tailwind CSS.",
    # Trang 2
    "Mục 2. CAM KẾT MỨC ĐỘ DỊCH VỤ (SLA - SERVICE LEVEL AGREEMENT):\n"
    "1. Độ sẵn sàng cam kết (Uptime SLA) đối với môi trường Production là 99.95% tính theo chu kỳ hằng tháng.\n"
    "2. Thời gian ngừng hoạt động ngoài kế hoạch (Unplanned Downtime) tối đa cho phép không vượt quá 21 phút 54 giây trong một tháng.\n"
    "3. Thời gian bảo trì định kỳ (Scheduled Maintenance Window) được thực hiện vào khung giờ từ 01:00 đến 03:00 sáng Chủ nhật tuần thứ hai của mỗi tháng và phải thông báo trước ít nhất 48 giờ.",
    # Trang 3
    "Mục 3. CHỈ TIÊU HIỆU NĂNG PHẢN HỒI API (LATENCY BUDGET):\n"
    "1. Đối với các RESTful API nghiệp vụ thông thường (CRUD tài liệu, lịch sử hội thoại): Độ trễ phân vị thứ 95 (p95 Latency) không vượt quá 200ms và p99 Latency không vượt quá 450ms.\n"
    "2. Đối với luồng truy xuất ngữ nghĩa Vector (Semantic Retrieval trên ChromaDB với 10.000 Chunks): Thời gian tìm kiếm Top-5 vector phải nhỏ hơn 500ms.\n"
    "3. Đối với luồng tổng hợp câu trả lời RAG toàn trình (End-to-End RAG Chat): Thời gian phản hồi p95 dưới 8.0 giây.",
    # Trang 4
    "Mục 4. KIẾN TRÚC CƠ SỞ DỮ LIỆU QUAN HỆ (POSTGRESQL 16):\n"
    "1. Hệ thống sử dụng PostgreSQL 16.4 chạy theo mô hình Primary - Standby Replication (1 node Primary ghi/đọc và 1 node Read Replica đồng bộ).\n"
    "2. Bộ quản lý kết nối (Connection Pooling) sử dụng SQLAlchemy QueuePool kết hợp PgBouncer với thông số chuẩn: pool_size = 20 kết nối thường trực, max_overflow = 10 kết nối mở rộng và pool_recycle = 1800 giây.\n"
    "3. Mọi khóa chính của các bảng dữ liệu nghiệp vụ đều sử dụng kiểu UUID v4 nhằm tránh lộ số lượng bản ghi tuần tự.",
    # Trang 5
    "Mục 5. KIẾN TRÚC CƠ SỞ DỮ LIỆU VECTOR (CHROMADB & HNSW INDEX):\n"
    "1. Các đoạn văn bản (Chunks) sau khi đi qua mô hình BAAI/bge-m3 sẽ sinh ra vector dày đặc (Dense Vector) có kích thước cố định 1024 chiều (1024 dimensions), kiểu số thực dấu phẩy động float32.\n"
    "2. ChromaDB sử dụng thuật toán lập chỉ mục đồ thị HNSW (Hierarchical Navigable Small World) với hàm đo khoảng cách Cosine (hnsw:space = 'cosine').\n"
    "3. Các siêu tham số HNSW chuẩn trong hệ thống: M = 16 (số liên kết hai chiều mỗi nút), ef_construction = 200 khi xây dựng chỉ mục và ef_search = 100 khi truy vấn.",
    # Trang 6
    "Mục 6. TIÊU CHUẨN MÃ HÓA VÀ BẢO MẬT DỮ LIỆU (ENCRYPTION STANDARDS):\n"
    "1. Bảo mật dữ liệu trên đường truyền (Encryption in Transit): Bắt buộc sử dụng giao thức TLS 1.3 (tối thiểu TLS 1.2) với bộ mã hóa ECDHE-RSA-AES256-GCM-SHA384 cho toàn bộ kết nối HTTPS và kết nối nội bộ tới cơ sở dữ liệu.\n"
    "2. Bảo mật dữ liệu lưu trữ tĩnh (Encryption at Rest): Toàn bộ ổ đĩa lưu trữ tệp PDF/DOCX, phân vùng PostgreSQL và ChromaDB được mã hóa bằng chuẩn AES-256.\n"
    "3. Mật khẩu người dùng bắt buộc băm bằng thuật toán Argon2id hoặc bcrypt với hệ số chi phí (cost factor) tối thiểu là 12.",
    # Trang 7
    "Mục 7. XÁC THỰC VÀ PHÂN QUYỀN TRUY CẬP (AUTHENTICATION & RBAC):\n"
    "1. Hệ thống sử dụng cơ chế xác thực không trạng thái bằng JSON Web Token (JWT) ký bằng thuật toán bất đối xứng RS256 (RSA 2048-bit).\n"
    "2. Thời hạn hiệu lực của Access Token là 15 phút; thời hạn của Refresh Token là 07 ngày và được lưu trong HttpOnly, Secure, SameSite=Strict Cookie.\n"
    "3. Khi người dùng đăng xuất hoặc đổi mật khẩu, Refresh Token cũ bị thu hồi ngay lập tức thông qua danh sách đen (Token Blacklist) lưu trên Redis.",
    # Trang 8
    "Mục 8. GIỚI HẠN TẦN SUẤT GỌI API (RATE LIMITING & THROTTLING):\n"
    "Để chống tấn công từ chối dịch vụ (DoS) và lạm dụng tài nguyên LLM, cổng Nginx và Middleware áp dụng thuật toán Token Bucket theo địa chỉ IP và User ID:\n"
    "1. Nhóm API chung (GET /api/documents, GET /api/conversations): Tối đa 120 requests / phút / người dùng.\n"
    "2. Nhóm API tải tệp (POST /api/documents/upload): Tối đa 10 requests / phút / người dùng; dung lượng tệp tối đa 20MB.\n"
    "3. Nhóm API hỏi đáp AI (POST /api/chat): Tối đa 20 requests / phút / người dùng.",
    # Trang 9
    "Mục 9. CHÍNH SÁCH SAO LƯU VÀ PHỤC HỒI THẢM HỌA (BACKUP, RPO & RTO):\n"
    "1. Chỉ tiêu điểm phục hồi dữ liệu (RPO - Recovery Point Objective): Tối đa 15 phút (nhờ cơ chế lưu trữ liên tục Write-Ahead Logging WAL của PostgreSQL lên kho lưu trữ đối tượng S3).\n"
    "2. Chỉ tiêu thời gian phục hồi hệ thống (RTO - Recovery Time Objective): Tối đa 60 phút kể từ khi kích hoạt quy trình chuyển đổi dự phòng (Failover).\n"
    "3. Lịch sao lưu định kỳ: Sao lưu toàn phần (Full Backup) tự động lúc 02:00 sáng hằng ngày; bản sao lưu hằng ngày được lưu giữ trong 30 ngày và bản sao lưu hằng tháng được lưu giữ trong 12 tháng.",
    # Trang 10
    "Mục 10. QUản LÝ NHẬT KÝ HỆ THỐNG VÀ GIÁM SÁT (LOGGING & MONITORING):\n"
    "1. Toàn bộ nhật ký ứng dụng (Application Logs) được xuất theo định dạng chuẩn JSON (Structured JSON Logging) bao gồm: timestamp, level, trace_id, endpoint, latency_ms và status_code.\n"
    "2. Tuyệt đối không ghi (Masking/Redaction) các thông tin nhạy cảm như mật khẩu, API Key, JWT Token hoặc số căn cước công dân vào tệp nhật ký.\n"
    "3. Thời gian lưu trữ nhật ký trực tuyến (Hot Storage trên Elasticsearch/Loki) là 90 ngày và lưu trữ lạnh (Cold Archive) là 365 ngày.",
    # Trang 11
    "Mục 11. HỆ THỐNG CẢNH BÁO TỰ ĐỘNG (PROMETHEUS & GRAFANA ALERTING):\n"
    "Hệ thống thu thập chỉ số hạ tầng mỗi 15 giây qua Prometheus và phát cảnh báo tức thì qua Slack/PagerDuty khi vượt các ngưỡng sau:\n"
    "1. Mức sử dụng CPU hoặc RAM của bất kỳ container nào vượt quá 85% liên tục trong 05 phút.\n"
    "2. Dung lượng ổ đĩa lưu trữ (/app/storage) đạt mức 80% dung lượng tối đa.\n"
    "3. Tỷ lệ lỗi máy chủ (HTTP 5xx Error Rate) vượt quá 1.0% tổng số requests trong cửa sổ 05 phút.",
    # Trang 12
    "Mục 12. PHÂN LOẠI VÀ THỜI GIAN PHẢN ỨNG SỰ CỐ (INCIDENT RESPONSE SLA):\n"
    "- Mức P1 (Critical - Hệ thống ngừng hoạt động hoàn toàn hoặc rò rỉ dữ liệu): Thời gian phản hồi đầu tiên trong vòng 15 phút, cập nhật trạng thái mỗi 30 phút, mục tiêu khắc phục trong 02 giờ.\n"
    "- Mức P2 (High - Một phân hệ chính như Upload hoặc Chat LLM bị lỗi nặng): Thời gian phản hồi trong 30 phút, mục tiêu khắc phục trong 04 giờ.\n"
    "- Mức P3 (Medium - Lỗi chức năng phụ, có cách xử lý tạm thời): Thời gian phản hồi trong 04 giờ làm việc, khắc phục trong 24 giờ.\n"
    "- Mức P4 (Low - Lỗi hiển thị giao diện nhỏ): Phản hồi trong 24 giờ, xử lý ở bản phát hành Sprint kế tiếp.",
    # Trang 13
    "Mục 13. QUY TRÌNH KIỂM THỬ VÀ TÍCH HỢP LIÊN TỤC (CI/CD PIPELINE):\n"
    "Mọi Pull Request gửi vào nhánh main trên GitHub bắt buộc phải vượt qua tự động 04 cổng kiểm tra trên GitHub Actions:\n"
    "1. Kiểm tra định dạng và quy chuẩn mã nguồn (Ruff Linter cho Python, ESLint & TypeScript tsc --noEmit cho Frontend).\n"
    "2. Chạy toàn bộ bộ kiểm thử đơn vị và tích hợp (Pytest) với độ bao phủ mã nguồn (Code Coverage) của tầng dịch vụ lõi đạt tối thiểu 80%.\n"
    "3. Quét lỗ hổng bảo mật thư viện phụ thuộc (Trivy / pip-audit / npm audit) không có lỗ hổng mức Critical.\n"
    "4. Đóng gói thử nghiệm thành công Docker Image cho cả Backend và Frontend.",
    # Trang 14
    "Mục 14. PHÒNG CHỐNG TẤN CÔNG ĐẶC THÙ TRÊN ỨNG DỤNG LLM & RAG:\n"
    "1. Chống Indirect Prompt Injection: Toàn bộ văn bản trích xuất từ tài liệu của người dùng phải được đặt trong cặp thẻ phân tách <document_context>...</document_context> kèm chỉ thị rõ đây chỉ là dữ liệu thụ động.\n"
    "2. Chống Hallucination & Bịa nguồn trích dẫn: Hệ thống áp dụng cơ chế xác thực trích dẫn 2 lớp (Regex + đối chiếu bảng source_map tại Backend) và giữ tham số Temperature trong khoảng 0.1 - 0.2.\n"
    "3. Chống Path Traversal & Malicious File Upload: Kiểm tra chữ ký byte đầu tệp (Magic Bytes %PDF- cho PDF và PK\\x03\\x04 cho DOCX), đổi tên tệp lưu trữ sang UUID ngẫu nhiên.",
    # Trang 15
    "Mục 15. CẤU HÌNH TRIỂN KHAI CONTAINER (DOCKER COMPOSE RESOURCE LIMITS):\n"
    "Trong môi trường Production tiêu chuẩn, giới hạn tài nguyên cho 03 dịch vụ trong docker-compose.yml được quy định như sau:\n"
    "1. Dịch vụ db (postgres:16-alpine): Giới hạn 2 vCPU, 2GB RAM, gắn Named Volume postgres_data.\n"
    "2. Dịch vụ backend (Python 3.13 + FastAPI + BAAI/bge-m3): Giới hạn 4 vCPU, 6GB RAM, gắn Volume lưu trữ bền vững cho /app/storage/uploads và /app/storage/chroma_db.\n"
    "3. Dịch vụ frontend (Nginx 1.27-alpine phục vụ bản build React): Giới hạn 1 vCPU, 512MB RAM, mở cổng 80/443.",
    # Trang 16
    "Mục 16. QUY ĐỊNH QUẢN LÝ KHÓA BÍ MẬT VÀ VÒNG ĐỜI DỮ LIỆU (SECRET & DATA RETENTION):\n"
    "1. Tuyệt đối không lưu khóa LLM_API_KEY hoặc mật khẩu cơ sở dữ liệu trực tiếp trong mã nguồn Git; mọi khóa bí mật phải được truyền qua biến môi trường (.env hoặc Vault).\n"
    "2. Chu kỳ xoay vòng khóa bí mật (Secret Rotation): Khóa API và mật khẩu cơ sở dữ liệu Production phải được xoay vòng định kỳ mỗi 90 ngày một lần.\n"
    "3. Khi người dùng thực hiện lệnh DELETE /api/documents/{id}, hệ thống phải xóa đồng bộ ngay lập tức ở cả 3 nơi: vector trong ChromaDB, tệp vật lý trên ổ đĩa và bản ghi trong PostgreSQL.",
]


DOC_04_FILENAME = "04_So_tay_Chinh_sach_Nhan_su_va_ATTT.docx"
DOC_04_SECTIONS: List[Dict[str, Any]] = [
    {
        "heading": "Mục 1. Thời gian làm việc chuẩn và khung giờ linh hoạt tại Công ty",
        "paragraphs": [
            "Công ty áp dụng tuần làm việc 40 giờ từ thứ Hai đến thứ Sáu hằng tuần (nghỉ thứ Bảy và Chủ nhật). Thời gian làm việc tiêu chuẩn mỗi ngày là 08 giờ.",
            "Nhân viên được áp dụng cơ chế khung giờ linh hoạt (Flexible Hours): Giờ bắt đầu làm việc buổi sáng từ 08:00 đến 09:00 và kết thúc buổi chiều tương ứng từ 17:30 đến 18:30 (đã bao gồm 90 phút nghỉ trưa từ 12:00 đến 13:30).",
        ],
    },
    {
        "heading": "Mục 2. Chính sách làm việc từ xa (Hybrid Work / Remote Work)",
        "paragraphs": [
            "Nhân viên chính thức (đã hoàn thành thời gian thử việc) được phép đăng ký làm việc từ xa tối đa 02 ngày mỗi tuần (không áp dụng cho các ngày có cuộc họp toàn công ty bắt buộc).",
            "Yêu cầu đăng ký làm việc từ xa phải được gửi trên hệ thống HRM trước ít nhất 24 giờ và được Quản lý trực tiếp phê duyệt. Trong thời gian làm việc từ xa, nhân viên phải duy trì kết nối trực tuyến trên Microsoft Teams/Slack trong khung giờ lõi (Core Hours) từ 09:30 đến 16:30.",
        ],
    },
    {
        "heading": "Mục 3. Chính sách phụ cấp ăn trưa, đi lại và điện thoại",
        "paragraphs": [
            "Tất cả nhân viên toàn thời gian được hưởng phụ cấp ăn trưa cố định là 1.100.000 VNĐ/tháng và phụ cấp xăng xe đi lại là 500.000 VNĐ/tháng.",
            "Đối với các vị trí Chuyên viên Kinh doanh, Chăm sóc khách hàng và Kỹ sư trực hệ thống (On-call), Công ty hỗ trợ thêm phụ cấp điện thoại và cước viễn thông từ 400.000 VNĐ đến 800.000 VNĐ/tháng tùy cấp bậc.",
        ],
    },
    {
        "heading": "Mục 4. Ngân sách đào tạo, học tập và thưởng chứng chỉ quốc tế",
        "paragraphs": [
            "Mỗi nhân viên chính thức được cấp ngân sách học tập và phát triển kỹ năng (Learning & Development Budget) tối đa 15.000.000 VNĐ/năm để tham gia các khóa học chuyên môn hoặc mua tài liệu.",
            "Công ty tài trợ 100% lệ phí thi lần đầu và thưởng nóng 5.000.000 VNĐ khi nhân viên đạt được một trong các chứng chỉ quốc tế: AWS Certified Solutions Architect, Google Cloud Professional, PMP, CISSP hoặc IELTS từ 7.5 trở lên.",
        ],
    },
    {
        "heading": "Mục 5. Chế độ khám sức khỏe định kỳ và bảo hiểm sức khỏe PVI/Bảo Việt",
        "paragraphs": [
            "Công ty tổ chức khám sức khỏe tổng quát định kỳ 01 lần/năm vào Quý II hằng năm tại các bệnh viện đa khoa quốc tế cho toàn bộ nhân viên.",
            "Nhân viên có thâm niên làm việc từ đủ 01 năm trở lên được cấp thêm gói Bảo hiểm sức khỏe cao cấp mở rộng cho bản thân và ưu đãi giảm 50% phí mua bảo hiểm cho 02 người thân trong gia đình.",
        ],
    },
    {
        "heading": "Mục 6. Chính sách cấp phát thiết bị làm việc và bảo mật thiết bị đầu cuối",
        "paragraphs": [
            "Mỗi nhân viên khối Kỹ thuật và Sản phẩm được trang bị 01 máy tính xách tay (Laptop RAM tối thiểu 16GB, ổ cứng SSD 512GB) kèm 01 màn hình rời 24 inch.",
            "Thiết bị công ty cấp phát bắt buộc phải bật mã hóa ổ đĩa BitLocker (Windows) hoặc FileVault (macOS), cài đặt phần mềm phòng chống mã độc EDR và tự động khóa màn hình sau 05 phút không tương tác.",
        ],
    },
    {
        "heading": "Mục 7. Quy định mật khẩu tài khoản nội bộ và xác thực đa nhân tố (MFA)",
        "paragraphs": [
            "Mật khẩu tài khoản корпора (Email, VPN, Git, Cloud Console) phải có độ dài tối thiểu 12 ký tự, bao gồm chữ hoa, chữ thường, chữ số và ký tự đặc biệt; bắt buộc thay đổi mật khẩu định kỳ mỗi 90 ngày.",
            "Bắt buộc kích hoạt xác thực đa nhân tố (MFA / 2FA qua ứng dụng Authenticator hoặc khóa cứng FIDO2) đối với 100% tài khoản nhân viên trước khi truy cập hệ thống nội bộ.",
        ],
    },
    {
        "heading": "Mục 8. Phân loại mức độ bảo mật tài liệu nội bộ (Data Classification)",
        "paragraphs": [
            "Tài liệu trong Công ty được phân thành 04 cấp độ bảo mật: Công khai (Public), Nội bộ (Internal), Mật (Confidential) và Tuyệt mật (Strictly Confidential).",
            "Tài liệu mức Mật và Tuyệt mật (như mã nguồn lõi, hợp đồng khách hàng, bảng lương, khóa API) tuyệt đối không được tải lên các công cụ AI công cộng bên ngoài hoặc lưu trên dịch vụ đám mây cá nhân.",
        ],
    },
    {
        "heading": "Mục 9. Quy trình báo cáo sự cố mất thiết bị hoặc nghi ngờ lộ lọt thông tin",
        "paragraphs": [
            "Khi phát hiện mất máy tính xách tay, điện thoại công vụ hoặc nghi ngờ tài khoản bị xâm nhập, nhân viên phải thông báo ngay lập tức cho Bộ phận An toàn thông tin (SOC/IT Helpdesk) trong vòng tối đa 30 phút kể từ khi phát hiện.",
            "Bộ phận IT sẽ thực hiện lệnh khóa tài khoản từ xa (Remote Lock) và xóa dữ liệu doanh nghiệp từ xa (Remote Wipe) trong vòng 15 phút sau khi tiếp nhận báo cáo.",
        ],
    },
    {
        "heading": "Mục 10. Đánh giá hiệu suất làm việc (KPI/OKR) và xét thưởng cuối năm",
        "paragraphs": [
            "Công ty thực hiện đánh giá hiệu suất làm việc định kỳ 02 kỳ/năm (Kỳ giữa năm vào tháng 6 và Kỳ cuối năm vào tháng 12) dựa trên mức độ hoàn thành mục tiêu OKR và khung năng lực.",
            "Nhân viên đạt xếp loại A (Xuất sắc) trong cả 2 kỳ đánh giá sẽ được xét nâng lương trước hạn với mức tăng từ 12% đến 20% và hưởng thưởng hiệu suất từ 02 đến 04 tháng lương.",
        ],
    },
]

DOC_04_TABLE_ROWS: List[List[str]] = [
    ["Cấp bậc nhân sự", "Phụ cấp ăn trưa", "Phụ cấp đi lại", "Ngân sách đào tạo/năm", "Số ngày WFH tối đa/tuần"],
    ["Nhân viên thử việc", "1.100.000 VNĐ", "500.000 VNĐ", "Không áp dụng", "0 ngày (Làm tại văn phòng)"],
    ["Nhân viên chính thức (Level 1-2)", "1.100.000 VNĐ", "500.000 VNĐ", "15.000.000 VNĐ", "02 ngày/tuần"],
    ["Chuyên gia / Trưởng nhóm (Level 3)", "1.100.000 VNĐ", "800.000 VNĐ", "20.000.000 VNĐ", "02 ngày/tuần"],
    ["Quản lý cấp trung trở lên (Level 4+)", "1.500.000 VNĐ", "1.200.000 VNĐ", "30.000.000 VNĐ", "Linh hoạt theo công việc"],
]


# ==============================================================================
# 2. DANH SÁCH 75 CÂU HỎI GOLDEN DATASET ([SP6-01.2 & SP6-01.3])
#    - 40 câu hỏi tra cứu trực tiếp (direct_lookup: GD-001 -> GD-040)
#    - 20 câu hỏi tổng hợp nhiều đoạn (multi_chunk_synthesis: GD-041 -> GD-060)
#    - 15 câu hỏi ngoài phạm vi tài liệu (out_of_scope: GD-061 -> GD-075)
# ==============================================================================

def build_75_golden_questions() -> List[Dict[str, Any]]:
    questions: List[Dict[str, Any]] = [
        # ---------------- PHẦN A: 40 CÂU HỎI TRA CỨU TRỰC TIẾP (GD-001 -> GD-040) ----------------
        # Tài liệu 01: Bộ luật Lao động (12 câu trực tiếp)
        {
            "id": "GD-001",
            "category": "direct_lookup",
            "question": "Độ tuổi lao động tối thiểu của người lao động theo Bộ luật Lao động là bao nhiêu tuổi?",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [1],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 3 Bộ luật Lao động 2019, độ tuổi lao động tối thiểu của người lao động là đủ 15 tuổi, trừ các trường hợp quy định riêng.",
            "evidence_keywords": ["đủ 15 tuổi", "Điều 3"],
        },
        {
            "id": "GD-002",
            "category": "direct_lookup",
            "question": "Trong trường hợp nào hai bên được giao kết hợp đồng lao động bằng lời nói?",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [2],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 14, hai bên có thể giao kết hợp đồng lao động bằng lời nói đối với hợp đồng có thời hạn dưới 01 tháng, trừ các trường hợp công việc theo mùa vụ đặc biệt.",
            "evidence_keywords": ["bằng lời nói", "dưới 01 tháng"],
        },
        {
            "id": "GD-003",
            "category": "direct_lookup",
            "question": "Hợp đồng lao động xác định thời hạn có thời hạn tối đa không quá bao nhiêu tháng?",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [3],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 20, hợp đồng lao động xác định thời hạn có thời hạn không quá 36 tháng kể từ thời điểm có hiệu lực.",
            "evidence_keywords": ["36 tháng", "Điều 20"],
        },
        {
            "id": "GD-004",
            "category": "direct_lookup",
            "question": "Thời gian thử việc tối đa đối với công việc cần trình độ từ cao đẳng, đại học trở lên là bao nhiêu ngày?",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [4],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 25, thời gian thử việc không quá 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên.",
            "evidence_keywords": ["60 ngày", "cao đẳng trở lên"],
        },
        {
            "id": "GD-005",
            "category": "direct_lookup",
            "question": "Tiền lương của người lao động trong thời gian thử việc ít nhất phải bằng bao nhiêu phần trăm mức lương của công việc đó?",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [5],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 26, tiền lương của người lao động trong thời gian thử việc do hai bên thỏa thuận nhưng ít nhất phải bằng 85% mức tiền lương của công việc đó.",
            "evidence_keywords": ["85%", "thử việc"],
        },
        {
            "id": "GD-006",
            "category": "direct_lookup",
            "question": "Người lao động làm việc theo hợp đồng lao động không xác định thời hạn muốn đơn phương chấm dứt hợp đồng thì phải báo trước ít nhất bao nhiêu ngày?",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [7],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 35, người lao động làm việc theo hợp đồng lao động không xác định thời hạn phải báo trước ít nhất 45 ngày khi đơn phương chấm dứt hợp đồng.",
            "evidence_keywords": ["45 ngày", "không xác định thời hạn"],
        },
        {
            "id": "GD-007",
            "category": "direct_lookup",
            "question": "Người lao động làm thêm giờ vào ngày nghỉ lễ, tết được trả lương ít nhất bằng bao nhiêu phần trăm?",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [10],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 98, người lao động làm thêm giờ vào ngày nghỉ lễ, tết, ngày nghỉ có hưởng lương được trả lương ít nhất bằng 300% chưa kể tiền lương ngày lễ, tết đối với người hưởng lương ngày.",
            "evidence_keywords": ["300%", "ngày nghỉ lễ, tết"],
        },
        {
            "id": "GD-008",
            "category": "direct_lookup",
            "question": "Mức khấu trừ tiền lương hằng tháng để bồi thường thiệt hại tài sản tối đa không được vượt quá bao nhiêu phần trăm?",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [11],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 102, mức khấu trừ tiền lương hằng tháng không được quá 30% tiền lương thực trả hằng tháng của người lao động sau khi trích nộp các khoản bảo hiểm bắt buộc và thuế thu nhập cá nhân.",
            "evidence_keywords": ["30%", "khấu trừ tiền lương"],
        },
        {
            "id": "GD-009",
            "category": "direct_lookup",
            "question": "Giờ làm việc ban đêm được Bộ luật Lao động quy định tính từ mấy giờ đến mấy giờ?",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [12],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 106, giờ làm việc ban đêm được tính từ 22 giờ đến 06 giờ sáng ngày hôm sau.",
            "evidence_keywords": ["22 giờ", "06 giờ sáng"],
        },
        {
            "id": "GD-010",
            "category": "direct_lookup",
            "question": "Người lao động làm việc đủ 12 tháng trong điều kiện bình thường được nghỉ phép hằng năm bao nhiêu ngày?",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [15],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 113, người lao động làm việc đủ 12 tháng trong điều kiện bình thường được nghỉ hằng năm hưởng nguyên lương 12 ngày làm việc.",
            "evidence_keywords": ["12 ngày làm việc", "Điều 113"],
        },
        {
            "id": "GD-011",
            "category": "direct_lookup",
            "question": "Thời hiệu xử lý kỷ luật lao động đối với hành vi liên quan trực tiếp đến tài chính, tài sản và bí mật công nghệ là bao nhiêu tháng?",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [17],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 123, thời hiệu xử lý kỷ luật lao động thông thường là 06 tháng, nhưng đối với hành vi liên quan trực tiếp đến tài chính, tài sản, tiết lộ bí mật công nghệ, bí mật kinh doanh thì thời hiệu là 12 tháng.",
            "evidence_keywords": ["12 tháng", "tài chính, tài sản"],
        },
        {
            "id": "GD-012",
            "category": "direct_lookup",
            "question": "Lao động nữ sinh con được nghỉ thai sản trước và sau khi sinh tổng cộng bao nhiêu tháng?",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [19],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 139, lao động nữ được nghỉ thai sản trước và sau khi sinh con là 06 tháng (thời gian nghỉ trước khi sinh không quá 02 tháng); nếu sinh đôi trở lên thì từ con thứ 02 trở đi mỗi con được nghỉ thêm 01 tháng.",
            "evidence_keywords": ["06 tháng", "thai sản"],
        },

        # Tài liệu 02: Quy chế Đào tạo Tín chỉ Đại học (10 câu trực tiếp)
        {
            "id": "GD-013",
            "category": "direct_lookup",
            "question": "Một tín chỉ được quy định tương đương với bao nhiêu tiết học lý thuyết trên lớp?",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [1],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 1 Quy chế đào tạo, một tín chỉ được quy định bằng 15 tiết học lý thuyết hoặc 30 tiết thực hành, thí nghiệm, thảo luận trên lớp và tối thiểu 30 giờ tự học.",
            "evidence_keywords": ["15 tiết học lý thuyết", "30 tiết thực hành"],
        },
        {
            "id": "GD-014",
            "category": "direct_lookup",
            "question": "Chương trình đào tạo hệ Cử nhân và hệ Kỹ sư yêu cầu tích lũy tối thiểu bao nhiêu tín chỉ?",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [2],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 3, hệ Cử nhân có tổng khối lượng tối thiểu 120 tín chỉ (thời gian chuẩn 4.0 năm), còn hệ Kỹ sư chuyên sâu đặc thù có tổng khối lượng tối thiểu 150 tín chỉ (thời gian chuẩn 5.0 năm).",
            "evidence_keywords": ["120 tín chỉ", "150 tín chỉ"],
        },
        {
            "id": "GD-015",
            "category": "direct_lookup",
            "question": "Sinh viên có học lực bình thường phải đăng ký tối thiểu và tối đa bao nhiêu tín chỉ trong một học kỳ chính?",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [4],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 6, trong mỗi học kỳ chính (trừ học kỳ cuối khóa), sinh viên có học lực bình thường phải đăng ký tối thiểu 14 tín chỉ và tối đa 24 tín chỉ.",
            "evidence_keywords": ["14 tín chỉ", "24 tín chỉ"],
        },
        {
            "id": "GD-016",
            "category": "direct_lookup",
            "question": "Sinh viên vắng mặt quá bao nhiêu phần trăm số tiết của học phần sẽ bị cấm thi kết thúc học phần?",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [6],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 9, sinh viên vắng mặt quá 20% tổng số tiết quy định của học phần sẽ bị cấm thi kết thúc học phần và nhận điểm 0 (điểm F).",
            "evidence_keywords": ["quá 20%", "cấm thi"],
        },
        {
            "id": "GD-017",
            "category": "direct_lookup",
            "question": "Điểm học phần đạt từ 8.0 đến 8.4 theo thang điểm 10 sẽ quy đổi sang điểm chữ gì và bao nhiêu điểm ở thang điểm 4?",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [7],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 10, mức điểm từ 8.0 đến 8.4 theo thang 10 được quy đổi thành điểm chữ B+ và tương ứng với 3.5 điểm theo thang điểm 4.",
            "evidence_keywords": ["B+", "3.5"],
        },
        {
            "id": "GD-018",
            "category": "direct_lookup",
            "question": "Sinh viên bị cảnh báo học vụ liên tiếp bao nhiêu lần thì bị buộc thôi học?",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [10],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 14, sinh viên bị buộc thôi học nếu đã bị cảnh báo học vụ 02 lần liên tiếp hoặc tổng số lần bị cảnh báo học vụ vượt quá 03 lần trong toàn khóa học.",
            "evidence_keywords": ["02 lần liên tiếp", "quá 03 lần"],
        },
        {
            "id": "GD-019",
            "category": "direct_lookup",
            "question": "Điều kiện về điểm trung bình tích lũy (CPA) để sinh viên được đăng ký học cùng lúc hai chương trình (song bằng) là bao nhiêu?",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [12],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 17, sinh viên đăng ký học chương trình thứ hai (song bằng) phải đã kết thúc học kỳ thứ hai của năm đầu tiên và có điểm trung bình tích lũy (CPA) đạt từ 2.50 trở lên.",
            "evidence_keywords": ["2.50 trở lên", "song bằng"],
        },
        {
            "id": "GD-020",
            "category": "direct_lookup",
            "question": "Chuẩn đầu ra tiếng Anh tối thiểu đối với các ngành không chuyên ngữ tương đương bao nhiêu điểm IELTS hoặc TOEIC?",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [14],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 20, đối với các ngành không chuyên ngữ, sinh viên phải đạt chuẩn đầu ra tiếng Anh tối thiểu bậc 3/6 (tương đương IELTS 5.0, TOEIC 550 hoặc TOEFL iBT 45).",
            "evidence_keywords": ["IELTS 5.0", "TOEIC 550"],
        },
        {
            "id": "GD-021",
            "category": "direct_lookup",
            "question": "Khối lượng học phần phải học lại vượt quá bao nhiêu phần trăm tổng số tín chỉ toàn khóa thì sinh viên loại Xuất sắc, Giỏi bị hạ một bậc bằng tốt nghiệp?",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [16],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 23, hạng tốt nghiệp loại Xuất sắc và Giỏi sẽ bị giảm đi một mức nếu khối lượng các học phần phải học lại (do bị điểm F) vượt quá 5% tổng số tín chỉ quy định của toàn chương trình.",
            "evidence_keywords": ["vượt quá 5%", "giảm đi một mức"],
        },
        {
            "id": "GD-022",
            "category": "direct_lookup",
            "question": "Khóa luận tốt nghiệp có tỷ lệ đạo văn trên Turnitin vượt quá bao nhiêu phần trăm sẽ không được phép bảo vệ?",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [18],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 25, khóa luận tốt nghiệp có tỷ lệ đạo văn (Turnitin similarity) vượt quá 20% sẽ không được phép bảo vệ trước Hội đồng.",
            "evidence_keywords": ["vượt quá 20%", "Turnitin"],
        },

        # Tài liệu 03: Đặc tả Kiến trúc Kỹ thuật CNTT & RAG (10 câu trực tiếp)
        {
            "id": "GD-023",
            "category": "direct_lookup",
            "question": "Cam kết độ sẵn sàng (Uptime SLA) hằng tháng của môi trường Production là bao nhiêu phần trăm và thời gian ngừng hoạt động tối đa là bao lâu?",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [2],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 2, độ sẵn sàng cam kết (Uptime SLA) đối với môi trường Production là 99.95% mỗi tháng, tương ứng thời gian ngừng hoạt động ngoài kế hoạch tối đa không vượt quá 21 phút 54 giây/tháng.",
            "evidence_keywords": ["99.95%", "21 phút 54 giây"],
        },
        {
            "id": "GD-024",
            "category": "direct_lookup",
            "question": "Chỉ tiêu thời gian tìm kiếm Top-5 vector trên ChromaDB với 10.000 Chunks và thời gian phản hồi p95 của End-to-End RAG Chat là bao nhiêu?",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [3],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 3, thời gian tìm kiếm Top-5 vector trên ChromaDB với 10.000 Chunks phải nhỏ hơn 500ms, và thời gian phản hồi p95 của End-to-End RAG Chat phải dưới 8.0 giây.",
            "evidence_keywords": ["500ms", "8.0 giây"],
        },
        {
            "id": "GD-025",
            "category": "direct_lookup",
            "question": "Thông số cấu hình Connection Pooling chuẩn của PostgreSQL trên SQLAlchemy (pool_size, max_overflow, pool_recycle) là bao nhiêu?",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [4],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 4, bộ quản lý kết nối SQLAlchemy QueuePool cấu hình chuẩn với pool_size = 20 kết nối thường trực, max_overflow = 10 kết nối mở rộng và pool_recycle = 1800 giây.",
            "evidence_keywords": ["pool_size = 20", "max_overflow = 10", "1800 giây"],
        },
        {
            "id": "GD-026",
            "category": "direct_lookup",
            "question": "Mô hình BAAI/bge-m3 sinh ra vector có bao nhiêu chiều và ChromaDB sử dụng các siêu tham số HNSW (M, ef_construction, ef_search) như thế nào?",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [5],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 5, mô hình BAAI/bge-m3 sinh ra vector dày đặc 1024 chiều (float32). Chỉ mục HNSW trên ChromaDB dùng hàm khoảng cách Cosine với M = 16, ef_construction = 200 và ef_search = 100.",
            "evidence_keywords": ["1024 chiều", "M = 16", "ef_construction = 200", "ef_search = 100"],
        },
        {
            "id": "GD-027",
            "category": "direct_lookup",
            "question": "Thời hạn hiệu lực của Access Token và Refresh Token trong cơ chế xác thực JWT là bao lâu?",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [7],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 7, JWT được ký bằng thuật toán RS256; thời hạn hiệu lực của Access Token là 15 phút và thời hạn của Refresh Token là 07 ngày.",
            "evidence_keywords": ["15 phút", "07 ngày", "RS256"],
        },
        {
            "id": "GD-028",
            "category": "direct_lookup",
            "question": "Giới hạn tần suất gọi API (Rate Limiting) đối với endpoint POST /api/chat và POST /api/documents/upload là bao nhiêu requests mỗi phút?",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [8],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 8, giới hạn tần suất gọi API đối với POST /api/documents/upload là tối đa 10 requests/phút/người dùng, và đối với POST /api/chat là tối đa 20 requests/phút/người dùng.",
            "evidence_keywords": ["10 requests", "20 requests"],
        },
        {
            "id": "GD-029",
            "category": "direct_lookup",
            "question": "Chỉ tiêu RPO và RTO trong chính sách sao lưu phục hồi thảm họa của hệ thống là bao nhiêu phút?",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [9],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 9, chỉ tiêu điểm phục hồi dữ liệu RPO tối đa là 15 phút và chỉ tiêu thời gian phục hồi hệ thống RTO tối đa là 60 phút.",
            "evidence_keywords": ["15 phút", "60 phút", "RPO", "RTO"],
        },
        {
            "id": "GD-030",
            "category": "direct_lookup",
            "question": "Thời gian lưu trữ nhật ký hệ thống trực tuyến (Hot Storage) và lưu trữ lạnh (Cold Archive) được quy định là bao nhiêu ngày?",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [10],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 10, thời gian lưu trữ nhật ký trực tuyến (Hot Storage trên Elasticsearch/Loki) là 90 ngày và lưu trữ lạnh (Cold Archive) là 365 ngày.",
            "evidence_keywords": ["90 ngày", "365 ngày"],
        },
        {
            "id": "GD-031",
            "category": "direct_lookup",
            "question": "Hệ thống Prometheus phát cảnh báo tự động khi mức sử dụng CPU/RAM hoặc tỷ lệ lỗi HTTP 5xx vượt ngưỡng nào?",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [11],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 11, cảnh báo phát ra khi CPU/RAM vượt quá 85% liên tục trong 05 phút, ổ đĩa đạt 80%, hoặc tỷ lệ lỗi HTTP 5xx vượt quá 1.0% trong cửa sổ 05 phút.",
            "evidence_keywords": ["85%", "80%", "1.0%"],
        },
        {
            "id": "GD-032",
            "category": "direct_lookup",
            "question": "Khóa API và mật khẩu cơ sở dữ liệu Production phải được xoay vòng (Secret Rotation) định kỳ bao nhiêu ngày một lần?",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [16],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 16, khóa API và mật khẩu cơ sở dữ liệu Production phải được xoay vòng định kỳ mỗi 90 ngày một lần.",
            "evidence_keywords": ["90 ngày", "Secret Rotation"],
        },

        # Tài liệu 04: Sổ tay Chính sách Nhân sự và ATTT - DOCX (8 câu trực tiếp)
        {
            "id": "GD-033",
            "category": "direct_lookup",
            "question": "Khung giờ làm việc linh hoạt buổi sáng và khung giờ nghỉ trưa tại Công ty được quy định như thế nào?",
            "expected_documents": [DOC_04_FILENAME],
            "expected_pages": [1],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 1 Sổ tay Nhân sự, khung giờ linh hoạt bắt đầu buổi sáng từ 08:00 đến 09:00 và kết thúc buổi chiều từ 17:30 đến 18:30, bao gồm 90 phút nghỉ trưa từ 12:00 đến 13:30.",
            "evidence_keywords": ["08:00 đến 09:00", "12:00 đến 13:30"],
        },
        {
            "id": "GD-034",
            "category": "direct_lookup",
            "question": "Nhân viên chính thức được đăng ký làm việc từ xa (Hybrid Work) tối đa bao nhiêu ngày mỗi tuần và phải duy trì trực tuyến trong khung giờ lõi nào?",
            "expected_documents": [DOC_04_FILENAME],
            "expected_pages": [2],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 2, nhân viên chính thức được đăng ký làm việc từ xa tối đa 02 ngày/tuần (báo trước ít nhất 24 giờ) và phải duy trì trực tuyến trong khung giờ lõi (Core Hours) từ 09:30 đến 16:30.",
            "evidence_keywords": ["02 ngày", "09:30 đến 16:30"],
        },
        {
            "id": "GD-035",
            "category": "direct_lookup",
            "question": "Mức phụ cấp ăn trưa và phụ cấp xăng xe đi lại cố định hằng tháng của nhân viên toàn thời gian là bao nhiêu?",
            "expected_documents": [DOC_04_FILENAME],
            "expected_pages": [3],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 3, nhân viên toàn thời gian được hưởng phụ cấp ăn trưa cố định là 1.100.000 VNĐ/tháng và phụ cấp xăng xe đi lại là 500.000 VNĐ/tháng.",
            "evidence_keywords": ["1.100.000 VNĐ", "500.000 VNĐ"],
        },
        {
            "id": "GD-036",
            "category": "direct_lookup",
            "question": "Ngân sách đào tạo hằng năm của nhân viên chính thức là bao nhiêu và mức thưởng nóng khi đạt chứng chỉ AWS, GCP, PMP, CISSP là bao nhiêu?",
            "expected_documents": [DOC_04_FILENAME],
            "expected_pages": [4],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 4, nhân viên chính thức có ngân sách đào tạo tối đa 15.000.000 VNĐ/năm, được tài trợ 100% lệ phí thi lần đầu và thưởng nóng 5.000.000 VNĐ khi đạt chứng chỉ AWS, GCP, PMP, CISSP hoặc IELTS 7.5+.",
            "evidence_keywords": ["15.000.000 VNĐ", "5.000.000 VNĐ"],
        },
        {
            "id": "GD-037",
            "category": "direct_lookup",
            "question": "Máy tính xách tay công ty cấp phát phải tự động khóa màn hình sau bao nhiêu phút không tương tác?",
            "expected_documents": [DOC_04_FILENAME],
            "expected_pages": [6],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 6, máy tính công ty cấp phát phải bật mã hóa BitLocker/FileVault, cài đặt EDR và tự động khóa màn hình sau 05 phút không tương tác.",
            "evidence_keywords": ["05 phút", "BitLocker"],
        },
        {
            "id": "GD-038",
            "category": "direct_lookup",
            "question": "Độ dài tối thiểu của mật khẩu tài khoản nội bộ là bao nhiêu ký tự và bao lâu phải đổi mật khẩu một lần?",
            "expected_documents": [DOC_04_FILENAME],
            "expected_pages": [7],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 7, mật khẩu tài khoản nội bộ phải có độ dài tối thiểu 12 ký tự (gồm chữ hoa, chữ thường, chữ số, ký tự đặc biệt) và bắt buộc thay đổi định kỳ mỗi 90 ngày.",
            "evidence_keywords": ["12 ký tự", "90 ngày"],
        },
        {
            "id": "GD-039",
            "category": "direct_lookup",
            "question": "Khi phát hiện mất máy tính xách tay hoặc nghi ngờ lộ tài khoản, nhân viên phải báo cho bộ phận An toàn thông tin trong vòng bao nhiêu phút?",
            "expected_documents": [DOC_04_FILENAME],
            "expected_pages": [9],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 9, nhân viên phải thông báo ngay cho Bộ phận An toàn thông tin (SOC/IT Helpdesk) trong vòng tối đa 30 phút kể từ khi phát hiện; IT sẽ thực hiện Remote Lock và Remote Wipe trong vòng 15 phút sau đó.",
            "evidence_keywords": ["30 phút", "15 phút", "Remote Wipe"],
        },
        {
            "id": "GD-040",
            "category": "direct_lookup",
            "question": "Theo bảng tổng hợp chế độ đãi ngộ trong Sổ tay Nhân sự, Quản lý cấp trung trở lên (Level 4+) được hưởng phụ cấp ăn trưa, đi lại và ngân sách đào tạo mỗi năm là bao nhiêu?",
            "expected_documents": [DOC_04_FILENAME],
            "expected_pages": [10],
            "expected_refusal": False,
            "ground_truth_answer": "Theo bảng tổng hợp chế độ đãi ngộ, Quản lý cấp trung trở lên (Level 4+) được hưởng phụ cấp ăn trưa 1.500.000 VNĐ, phụ cấp đi lại 1.200.000 VNĐ và ngân sách đào tạo 30.000.000 VNĐ/năm.",
            "evidence_keywords": ["1.500.000 VNĐ", "1.200.000 VNĐ", "30.000.000 VNĐ"],
        },

        # ---------------- PHẦN B: 20 CÂU HỎI TỔNG HỢP TỪ NHIỀU ĐOẠN (GD-041 -> GD-060) ----------------
        {
            "id": "GD-041",
            "category": "multi_chunk_synthesis",
            "question": "Hãy tổng hợp đầy đủ các mốc thời gian thử việc tối đa theo từng cấp bậc công việc và quy định về mức tiền lương tối thiểu trong thời gian thử việc.",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [4, 5],
            "expected_refusal": False,
            "ground_truth_answer": "Thời gian thử việc tối đa gồm: 180 ngày với người quản lý doanh nghiệp; 60 ngày với trình độ từ cao đẳng trở lên; 30 ngày với trình độ trung cấp, công nhân kỹ thuật; 06 ngày làm việc với công việc khác (không thử việc với hợp đồng dưới 01 tháng). Tiền lương thử việc ít nhất phải bằng 85% mức lương chính thức của công việc đó.",
            "evidence_keywords": ["180 ngày", "60 ngày", "30 ngày", "85%"],
        },
        {
            "id": "GD-042",
            "category": "multi_chunk_synthesis",
            "question": "So sánh mức hưởng trợ cấp thôi việc (Điều 46) và trợ cấp mất việc làm (Điều 47) đối với người lao động đã làm việc đủ 12 tháng trở lên.",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [8],
            "expected_refusal": False,
            "ground_truth_answer": "Đối với người lao động đã làm việc thường xuyên từ đủ 12 tháng trở lên: Trợ cấp thôi việc (Điều 46) mỗi năm làm việc được hưởng một nửa tháng tiền lương (0.5 tháng lương/năm); trong khi Trợ cấp mất việc làm (Điều 47) mỗi năm làm việc được hưởng 01 tháng tiền lương nhưng ít nhất phải bằng 02 tháng tiền lương.",
            "evidence_keywords": ["một nửa tháng tiền lương", "01 tháng tiền lương", "02 tháng tiền lương"],
        },
        {
            "id": "GD-043",
            "category": "multi_chunk_synthesis",
            "question": "Tổng hợp giới hạn số giờ làm thêm tối đa theo ngày, tháng, năm và cách tính tiền lương làm thêm giờ vào ngày thường, ngày nghỉ tuần, ngày lễ tết.",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [10, 13],
            "expected_refusal": False,
            "ground_truth_answer": "Giới hạn làm thêm giờ: không quá 50% giờ bình thường/ngày (tổng không quá 12 giờ/ngày), không quá 40 giờ/tháng và không quá 200 giờ/năm (trường hợp đặc biệt không quá 300 giờ/năm). Tiền lương làm thêm giờ: ngày thường ít nhất 150%, ngày nghỉ hằng tuần ít nhất 200%, và ngày lễ tết ít nhất 300%.",
            "evidence_keywords": ["40 giờ", "200 giờ", "150%", "200%", "300%"],
        },
        {
            "id": "GD-044",
            "category": "multi_chunk_synthesis",
            "question": "Một nhân viên làm việc trong điều kiện bình thường đã gắn bó liên tục đủ 10 năm tại công ty thì tổng số ngày nghỉ phép năm hưởng nguyên lương là bao nhiêu ngày? Giải thích cách tính.",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [15, 16],
            "expected_refusal": False,
            "ground_truth_answer": "Tổng cộng là 14 ngày phép năm hưởng nguyên lương. Cụ thể: theo Điều 113, làm việc đủ 12 tháng trong điều kiện bình thường được 12 ngày phép chuẩn; theo Điều 114, cứ đủ 05 năm làm việc liên tục cho một người sử dụng lao động được cộng thêm 01 ngày phép, nên 10 năm được cộng thêm 02 ngày (12 + 2 = 14 ngày).",
            "evidence_keywords": ["12 ngày làm việc", "05 năm", "tăng thêm tương ứng 01 ngày"],
        },
        {
            "id": "GD-045",
            "category": "multi_chunk_synthesis",
            "question": "Tổng hợp các ngày nghỉ lễ, tết hưởng nguyên lương trong năm (Điều 112) và các trường hợp nghỉ việc riêng hưởng nguyên lương (Điều 115).",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [14, 16],
            "expected_refusal": False,
            "ground_truth_answer": "Nghỉ lễ, tết hưởng nguyên lương gồm 11 ngày (Tết Dương lịch 01 ngày, Tết Âm lịch 05 ngày, Ngày Chiến thắng 30/4 01 ngày, Quốc tế lao động 1/5 01 ngày, Quốc khánh 2/9 02 ngày, Giỗ Tổ Hùng Vương 01 ngày). Nghỉ việc riêng hưởng nguyên lương gồm: bản thân kết hôn nghỉ 03 ngày; con kết hôn nghỉ 01 ngày; cha mẹ hai bên, vợ/chồng hoặc con chết nghỉ 03 ngày.",
            "evidence_keywords": ["11 ngày", "Tết Âm lịch: 05 ngày", "Kết hôn: nghỉ 03 ngày"],
        },
        {
            "id": "GD-046",
            "category": "multi_chunk_synthesis",
            "question": "Trình bày thời hiệu xử lý kỷ luật lao động, các trường hợp không được xử lý kỷ luật và các hành vi dẫn đến hình thức kỷ luật sa thải.",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [17, 18],
            "expected_refusal": False,
            "ground_truth_answer": "Thời hiệu xử lý kỷ luật là 06 tháng (12 tháng nếu liên quan tài chính, tài sản, bí mật công nghệ); không xử lý kỷ luật khi đang nghỉ ốm, mang thai hoặc nuôi con dưới 12 tháng tuổi. Sa thải áp dụng khi trộm cắp, tham ô, đánh bạc, dùng ma túy, tiết lộ bí mật kinh doanh, hoặc tự ý bỏ việc 05 ngày cộng dồn trong 30 ngày (hoặc 20 ngày trong 365 ngày).",
            "evidence_keywords": ["06 tháng", "12 tháng", "05 ngày cộng dồn", "20 ngày cộng dồn"],
        },
        {
            "id": "GD-047",
            "category": "multi_chunk_synthesis",
            "question": "Tổng hợp các quyền lợi bảo vệ thai sản đối với lao động nữ mang thai từ tháng thứ 07, thời gian nghỉ thai sản và lộ trình tuổi nghỉ hưu của lao động nữ.",
            "expected_documents": [DOC_01_FILENAME],
            "expected_pages": [19, 20],
            "expected_refusal": False,
            "ground_truth_answer": "Lao động nữ mang thai từ tháng thứ 07 (hoặc tháng thứ 06 ở vùng cao, biên giới, hải đảo) hoặc nuôi con dưới 12 tháng tuổi không phải làm đêm, làm thêm giờ và đi công tác xa; được nghỉ thai sản 06 tháng (sinh đôi trở lên thêm 01 tháng/con từ con thứ 2). Tuổi nghỉ hưu của lao động nữ tăng thêm 04 tháng mỗi năm cho đến khi đạt đủ 60 tuổi vào năm 2035.",
            "evidence_keywords": ["tháng thứ 07", "06 tháng", "60 tuổi", "năm 2035"],
        },
        {
            "id": "GD-048",
            "category": "multi_chunk_synthesis",
            "question": "So sánh sự khác biệt giữa chương trình đào tạo hệ Cử nhân và hệ Kỹ sư về tổng số tín chỉ tối thiểu, thời gian đào tạo chuẩn và thời gian tối đa được phép học.",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [2],
            "expected_refusal": False,
            "ground_truth_answer": "Hệ Cử nhân yêu cầu tối thiểu 120 tín chỉ, thời gian đào tạo chuẩn 4.0 năm (8 học kỳ chính) và thời gian học tối đa là 8.0 năm. Hệ Kỹ sư yêu cầu tối thiểu 150 tín chỉ, thời gian đào tạo chuẩn 5.0 năm (10 học kỳ chính) và thời gian học tối đa là 10.0 năm.",
            "evidence_keywords": ["120 tín chỉ", "150 tín chỉ", "8.0 năm", "10.0 năm"],
        },
        {
            "id": "GD-049",
            "category": "multi_chunk_synthesis",
            "question": "Một sinh viên đang trong diện cảnh báo học vụ thì bị giới hạn số tín chỉ đăng ký mỗi học kỳ chính như thế nào và khi nào sẽ bị buộc thôi học?",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [4, 10],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 6, sinh viên diện cảnh báo học vụ chỉ được đăng ký tối thiểu 10 tín chỉ và tối đa 14 tín chỉ trong một học kỳ chính (thay vì 14-24 tín chỉ như bình thường). Theo Điều 14, nếu sinh viên bị cảnh báo học vụ 02 lần liên tiếp hoặc tổng cộng vượt quá 03 lần trong toàn khóa sẽ bị buộc thôi học.",
            "evidence_keywords": ["10 tín chỉ", "14 tín chỉ", "02 lần liên tiếp", "quá 03 lần"],
        },
        {
            "id": "GD-050",
            "category": "multi_chunk_synthesis",
            "question": "Trình bày quy định về trọng số điểm học phần, điều kiện dự thi kết thúc học phần và quy định học lại / học cải thiện điểm đối với điểm F, D, D+.",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [6, 7, 8],
            "expected_refusal": False,
            "ground_truth_answer": "Trọng số điểm gồm: chuyên cần 10%, giữa kỳ 30%, cuối kỳ 60% (vắng quá 20% số tiết bị cấm thi và nhận điểm F). Học phần bắt buộc bị điểm F (dưới 4.0) phải học lại; học phần đạt điểm D (4.0-4.9) hoặc D+ (5.0-5.4) được phép đăng ký học lại để cải thiện CPA và lấy điểm cao nhất.",
            "evidence_keywords": ["10%", "30%", "60%", "quá 20%", "điểm F", "điểm D"],
        },
        {
            "id": "GD-051",
            "category": "multi_chunk_synthesis",
            "question": "Tổng hợp tất cả các điều kiện để một sinh viên hệ Cử nhân được xét công nhận tốt nghiệp đúng hạn và đạt bằng tốt nghiệp loại Xuất sắc mà không bị hạ bậc.",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [9, 14, 15, 16],
            "expected_refusal": False,
            "ground_truth_answer": "Sinh viên cần: tích lũy đủ tối thiểu 120 tín chỉ; đạt CPA từ 3.60 đến 4.00; đạt chuẩn tiếng Anh tối thiểu IELTS 5.0 / TOEIC 550 (hoặc IELTS 6.0 với hệ CLC), chứng chỉ CNTT cơ bản, GDTC và GDQP-AN; tỷ lệ tín chỉ học lại do điểm F không vượt quá 5% tổng tín chỉ toàn khóa và không bị kỷ luật từ mức Cảnh cáo trở lên.",
            "evidence_keywords": ["120 tín chỉ", "3.60 đến 4.00", "IELTS 5.0", "vượt quá 5%"],
        },
        {
            "id": "GD-052",
            "category": "multi_chunk_synthesis",
            "question": "So sánh điều kiện về điểm trung bình tích lũy (CPA) tối thiểu khi: (1) Xin nghỉ học tạm thời vì lý do cá nhân, (2) Nhận làm Khóa luận tốt nghiệp, và (3) Đăng ký học song bằng.",
            "expected_documents": [DOC_02_FILENAME],
            "expected_pages": [11, 12, 13],
            "expected_refusal": False,
            "ground_truth_answer": "Điều kiện CPA tối thiểu cho 3 trường hợp là: (1) Xin nghỉ học tạm thời vì lý do cá nhân: CPA từ 2.00 trở lên (đã học ít nhất 01 học kỳ); (2) Nhận làm Khóa luận tốt nghiệp: CPA từ 2.30 trở lên (tích lũy >= 85% tín chỉ); (3) Đăng ký học song bằng: CPA từ 2.50 trở lên (sau học kỳ 2 năm nhất).",
            "evidence_keywords": ["2.00 trở lên", "2.30 trở lên", "2.50 trở lên"],
        },
        {
            "id": "GD-053",
            "category": "multi_chunk_synthesis",
            "question": "Tổng hợp kiến trúc lưu trữ dữ liệu của hệ thống RAG gồm PostgreSQL 16 và ChromaDB (kích thước vector, thuật toán chỉ mục và thông số kết nối).",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [4, 5],
            "expected_refusal": False,
            "ground_truth_answer": "Hệ thống dùng PostgreSQL 16.4 (Primary - Standby) với SQLAlchemy QueuePool + PgBouncer (pool_size=20, max_overflow=10, pool_recycle=1800s, khóa chính UUID v4). Dữ liệu vector lưu trên ChromaDB với vector BAAI/bge-m3 1024 chiều (float32), dùng chỉ mục HNSW khoảng cách Cosine (M=16, ef_construction=200, ef_search=100).",
            "evidence_keywords": ["PostgreSQL 16.4", "pool_size = 20", "1024 chiều", "HNSW", "M = 16"],
        },
        {
            "id": "GD-054",
            "category": "multi_chunk_synthesis",
            "question": "Trình bày toàn diện các lớp bảo mật dữ liệu, cơ chế xác thực JWT và giới hạn tần suất Rate Limiting trên hệ thống CNTT.",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [6, 7, 8],
            "expected_refusal": False,
            "ground_truth_answer": "Đường truyền dùng TLS 1.3, lưu trữ tĩnh mã hóa AES-256, mật khẩu băm Argon2id/bcrypt (cost >= 12). Xác thực dùng JWT RS256 (Access Token 15 phút, Refresh Token 07 ngày trong HttpOnly Cookie, thu hồi qua Redis Blacklist). Rate Limiting áp dụng Token Bucket: 120 req/phút cho API chung, 10 req/phút cho upload tệp (<= 20MB) và 20 req/phút cho API chat AI.",
            "evidence_keywords": ["TLS 1.3", "AES-256", "RS256", "15 phút", "10 requests", "20 requests"],
        },
        {
            "id": "GD-055",
            "category": "multi_chunk_synthesis",
            "question": "Tổng hợp chính sách sao lưu phục hồi thảm họa (RPO, RTO, lịch Backup) và thời gian phản ứng sự cố đối với mức P1 và P2.",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [9, 12],
            "expected_refusal": False,
            "ground_truth_answer": "Chính sách sao lưu đảm bảo RPO tối đa 15 phút (nhờ WAL S3), RTO tối đa 60 phút, Full Backup tự động lúc 02:00 sáng hằng ngày (lưu 30 ngày). Về ứng cứu sự cố: mức P1 (Critical) phản hồi trong 15 phút và khắc phục trong 02 giờ; mức P2 (High) phản hồi trong 30 phút và khắc phục trong 04 giờ.",
            "evidence_keywords": ["RPO", "15 phút", "RTO", "60 phút", "P1", "02 giờ", "P2", "04 giờ"],
        },
        {
            "id": "GD-056",
            "category": "multi_chunk_synthesis",
            "question": "Hệ thống triển khai những biện pháp kỹ thuật nào để chống Indirect Prompt Injection, chống ảo giác (Hallucination) và chống tải tệp độc hại?",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [14],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Mục 14: (1) Chống Indirect Prompt Injection bằng cách đóng khung văn bản trong thẻ <document_context> và chỉ thị rõ đây là dữ liệu thụ động; (2) Chống Hallucination bằng xác thực trích dẫn 2 lớp (Regex + đối chiếu source_map) và giữ Temperature 0.1 - 0.2; (3) Chống tệp độc hại bằng kiểm tra Magic Bytes (%PDF- và PK) và đổi tên tệp sang UUID.",
            "evidence_keywords": ["<document_context>", "source_map", "0.1 - 0.2", "Magic Bytes"],
        },
        {
            "id": "GD-057",
            "category": "multi_chunk_synthesis",
            "question": "Tổng hợp giới hạn tài nguyên phần cứng (vCPU, RAM) của 3 dịch vụ trong Docker Compose và 4 cổng kiểm tra bắt buộc trong quy trình CI/CD.",
            "expected_documents": [DOC_03_FILENAME],
            "expected_pages": [13, 15],
            "expected_refusal": False,
            "ground_truth_answer": "Cấu hình Docker Compose gồm: db (2 vCPU, 2GB RAM), backend (4 vCPU, 6GB RAM), frontend Nginx (1 vCPU, 512MB RAM). Quy trình CI/CD trên GitHub Actions bắt buộc vượt qua 4 cổng: (1) Linter Ruff/ESLint/tsc, (2) Pytest với Code Coverage >= 80%, (3) Quét bảo mật Trivy/audit không có lỗi Critical, và (4) Build thành công Docker Image.",
            "evidence_keywords": ["4 vCPU, 6GB RAM", "2 vCPU, 2GB RAM", "80%", "Docker Image"],
        },
        {
            "id": "GD-058",
            "category": "multi_chunk_synthesis",
            "question": "So sánh quyền lợi giữa Nhân viên thử việc và Nhân viên chính thức (Level 1-2) tại Công ty về phụ cấp ăn trưa, đi lại, ngân sách đào tạo và số ngày làm việc từ xa (WFH).",
            "expected_documents": [DOC_04_FILENAME],
            "expected_pages": [2, 3, 4, 10],
            "expected_refusal": False,
            "ground_truth_answer": "Cả nhân viên thử việc và nhân viên chính thức (Level 1-2) đều được hưởng phụ cấp ăn trưa 1.100.000 VNĐ/tháng và phụ cấp đi lại 500.000 VNĐ/tháng. Tuy nhiên, nhân viên thử việc chưa được cấp ngân sách đào tạo và không được WFH (0 ngày), trong khi nhân viên chính thức được cấp ngân sách đào tạo 15.000.000 VNĐ/năm và được WFH tối đa 02 ngày/tuần.",
            "evidence_keywords": ["1.100.000 VNĐ", "500.000 VNĐ", "15.000.000 VNĐ", "02 ngày/tuần"],
        },
        {
            "id": "GD-059",
            "category": "multi_chunk_synthesis",
            "question": "Tổng hợp các quy định về bảo mật thiết bị đầu cuối, mật khẩu tài khoản nội bộ và quy trình xử lý khi nhân viên bị mất laptop công vụ.",
            "expected_documents": [DOC_04_FILENAME],
            "expected_pages": [6, 7, 9],
            "expected_refusal": False,
            "ground_truth_answer": "Laptop công vụ phải bật mã hóa BitLocker/FileVault, cài EDR và tự khóa màn hình sau 05 phút; tài khoản phải có mật khẩu >= 12 ký tự, đổi mỗi 90 ngày và bật MFA 100%. Khi mất laptop, nhân viên phải báo cho SOC/IT Helpdesk trong tối đa 30 phút để IT thực hiện khóa và xóa dữ liệu từ xa (Remote Wipe) trong vòng 15 phút.",
            "evidence_keywords": ["BitLocker", "05 phút", "12 ký tự", "90 ngày", "30 phút", "15 phút"],
        },
        {
            "id": "GD-060",
            "category": "multi_chunk_synthesis",
            "question": "Đối chiếu quy định thời giờ làm việc bình thường trong Bộ luật Lao động (Tài liệu 01) và Thời gian làm việc chuẩn thực tế tại Công ty trong Sổ tay Nhân sự (Tài liệu 04).",
            "expected_documents": [DOC_01_FILENAME, DOC_04_FILENAME],
            "expected_pages": [12, 1],
            "expected_refusal": False,
            "ground_truth_answer": "Theo Điều 105 Bộ luật Lao động, thời giờ làm việc bình thường không quá 08 giờ/ngày và không quá 48 giờ/tuần, đồng thời Nhà nước khuyến khích thực hiện tuần làm việc 40 giờ. Thực hiện khuyến khích này, tại Mục 1 Sổ tay Nhân sự, Công ty áp dụng tuần làm việc 40 giờ (08 giờ/ngày từ thứ Hai đến thứ Sáu, nghỉ thứ Bảy và Chủ nhật).",
            "evidence_keywords": ["48 giờ", "40 giờ", "thứ Hai đến thứ Sáu"],
        },

        # ---------------- PHẦN C: 15 CÂU HỎI NGOÀI PHẠM VI TÀI LIỆU - CHỐNG ẢO GIÁC (GD-061 -> GD-075) ----------------
        {
            "id": "GD-061",
            "category": "out_of_scope",
            "question": "Dự báo thời tiết tại thủ đô Hà Nội và TP. Hồ Chí Minh vào cuối tuần này có mưa bão không?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
        {
            "id": "GD-062",
            "category": "out_of_scope",
            "question": "Giá vàng miếng SJC và tỷ giá đồng Bitcoin hôm nay trên thị trường quốc tế là bao nhiêu đô la?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
        {
            "id": "GD-063",
            "category": "out_of_scope",
            "question": "Hướng dẫn chi tiết công thức nấu món phở bò gia truyền Nam Định và cách hầm nước dùng trong ngọt?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
        {
            "id": "GD-064",
            "category": "out_of_scope",
            "question": "Đội tuyển bóng đá quốc gia nào đã giành chức vô địch World Cup 2022 và cầu thủ nào ghi nhiều bàn thắng nhất?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
        {
            "id": "GD-065",
            "category": "out_of_scope",
            "question": "Liều lượng sử dụng thuốc kháng sinh Amoxicillin 500mg để điều trị viêm họng cấp ở trẻ em 5 tuổi như thế nào?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
        {
            "id": "GD-066",
            "category": "out_of_scope",
            "question": "Khoảng cách trung bình từ Trái Đất đến Sao Hỏa là bao nhiêu triệu km và tàu vũ trụ bay mất bao lâu?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
        {
            "id": "GD-067",
            "category": "out_of_scope",
            "question": "Thủ tục xin cấp thị thực (Visa) du lịch Schengen sang Pháp và Thụy Sĩ cần chứng minh tài chính bao nhiêu tiền?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
        {
            "id": "GD-068",
            "category": "out_of_scope",
            "question": "Thuế suất thuế bất động sản liên bang tại bang California (Hoa Kỳ) năm 2026 được tính theo công thức nào?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
        {
            "id": "GD-069",
            "category": "out_of_scope",
            "question": "Cấu hình chi tiết của dòng xe điện VinFast VF8 và dung lượng pin di chuyển được tối đa bao nhiêu km một lần sạc?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
        {
            "id": "GD-070",
            "category": "out_of_scope",
            "question": "Cách chăm sóc cây hoa lan hồ điệp ra hoa đúng dịp Tết Nguyên Đán và tỷ lệ pha phân bón NPK?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
        {
            "id": "GD-071",
            "category": "out_of_scope",
            "question": "Lịch chiếu phim rạp CGV cuối tuần này có những bộ phim bom tấn Hollywood nào mới ra mắt?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
        {
            "id": "GD-072",
            "category": "out_of_scope",
            "question": "Quá trình quang hợp ở thực vật diễn ra tại bào quan nào và phương trình hóa học tổng quát là gì?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
        {
            "id": "GD-073",
            "category": "out_of_scope",
            "question": "Danh sách các hoàng đế triều đại nhà Nguyễn trong lịch sử phong kiến Việt Nam theo thứ tự niên đại?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
        {
            "id": "GD-074",
            "category": "out_of_scope",
            "question": "Giá vé máy bay khứ hồi hạng thương gia của Vietnam Airlines chặng Hà Nội đi Tokyo Nhật Bản hiện tại là bao nhiêu?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
        {
            "id": "GD-075",
            "category": "out_of_scope",
            "question": "Cách pha chế cà phê Espresso chuẩn Ý với áp suất máy pha bao nhiêu bar và nhiệt độ nước bao nhiêu độ C?",
            "expected_documents": [],
            "expected_pages": [],
            "expected_refusal": True,
            "ground_truth_answer": REFUSAL_STANDARD_ANSWER,
            "evidence_keywords": [],
        },
    ]
    return questions


# ==============================================================================
# 3. HÀM SINH TỆP PDF NHIỀU TRANG VÀ DOCX CHUẨN ([SP6-01.1])
# ==============================================================================

def _get_unicode_font_path() -> str | None:
    """Tìm font Unicode hỗ trợ đầy đủ tiếng Việt trên hệ thống (Arial / Segoe UI / DejaVuSans)."""
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/times.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def _create_unicode_pdf(file_path: Path, title: str, pages_content: List[str]) -> None:
    """Tạo tệp PDF nhiều trang hỗ trợ đầy đủ tiếng Việt Unicode bằng PyMuPDF (~360-420 tokens/trang)."""
    doc = fitz.open()
    font_file = _get_unicode_font_path()

    for page_idx, page_text in enumerate(pages_content, start=1):
        page = doc.new_page(width=595, height=842)  # Khổ A4 chuẩn
        supplementary_notes = (
            f"\n\nHướng dẫn thi hành và áp dụng thực tiễn tại Trang {page_idx}:\n"
            f"Các đơn vị phòng ban, bộ phận chuyên môn, cán bộ quản lý và cá nhân có liên quan chịu trách "
            f"nhiệm phổ biến, quán triệt và tổ chức thực hiện nghiêm túc các quy định nêu tại trang {page_idx} "
            f"của văn bản {title}. Trong quá trình triển khai thực tế tại doanh nghiệp và cơ sở đào tạo, "
            f"mọi hồ sơ, chứng từ, biên bản đối chiếu và dữ liệu lưu trữ điện tử phải được lập đầy đủ, "
            f"chính xác, minh bạch, tuân thủ đúng trình tự thủ tục, định mức kỹ thuật và thời hạn quy định. "
            f"Trường hợp phát sinh vướng mắc hoặc tình huống đặc thù chưa được liệt kê chi tiết tại điều khoản "
            f"này, bộ phận phụ trách phải lập báo cáo bằng văn bản trình cấp có thẩm quyền xem xét, phê duyệt "
            f"phương án xử lý trên nguyên tắc bảo đảm quyền lợi hợp pháp của các bên, an toàn thông tin hệ thống "
            f"và tuân thủ quy định hiện hành của pháp luật Việt Nam."
        )
        full_text = f"{title} - Trang {page_idx}/{len(pages_content)}\n\n{page_text}{supplementary_notes}"
        rect = fitz.Rect(45, 45, 550, 795)

        if font_file:
            page.insert_textbox(
                rect,
                full_text,
                fontsize=11,
                fontname="vi_font",
                fontfile=font_file,
            )
        else:
            page.insert_htmlbox(
                rect,
                f"<div style='font-family: sans-serif; font-size: 11pt;'>{full_text.replace(chr(10), '<br/>')}</div>",
            )

    file_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(file_path))
    doc.close()


def _create_policy_docx(file_path: Path) -> None:
    """Tạo tệp DOCX Sổ tay Chính sách Nhân sự và ATTT kèm bảng biểu chuẩn."""
    doc = DocxDocument()
    doc.add_heading(
        "SỔ TAY CHÍNH SÁCH NHÂN SỰ, PHÚC LỢI VÀ AN TOÀN THÔNG TIN NỘI BỘ",
        level=0,
    )

    for section in DOC_04_SECTIONS:
        doc.add_heading(section["heading"], level=1)
        for para in section["paragraphs"]:
            doc.add_paragraph(para)

    doc.add_heading("Mục 11. Bảng tổng hợp chế độ đãi ngộ theo cấp bậc nhân sự", level=1)
    table = doc.add_table(rows=len(DOC_04_TABLE_ROWS), cols=5)
    for r_idx, row_values in enumerate(DOC_04_TABLE_ROWS):
        for c_idx, cell_value in enumerate(row_values):
            table.cell(r_idx, c_idx).text = cell_value

    file_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(file_path))


# ==============================================================================
# 4. XUẤT TỆP JSON, CSV VÀ README ([SP6-01.4])
# ==============================================================================

def generate_all_golden_assets() -> Dict[str, Any]:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Tạo 3 tệp PDF (20 trang, 18 trang, 16 trang) và 1 tệp DOCX
    _create_unicode_pdf(
        DOCS_DIR / DOC_01_FILENAME,
        "BO LUAT LAO DONG 2019 (TRICH YEU)",
        DOC_01_PAGES,
    )
    _create_unicode_pdf(
        DOCS_DIR / DOC_02_FILENAME,
        "QUY CHE DAO TAO DAI HOC TIN CHI",
        DOC_02_PAGES,
    )
    _create_unicode_pdf(
        DOCS_DIR / DOC_03_FILENAME,
        "DAC TA KIEN TRUC KY THUAT CNTT & RAG",
        DOC_03_PAGES,
    )
    _create_policy_docx(DOCS_DIR / DOC_04_FILENAME)

    # 2. Khởi tạo bộ 75 câu hỏi Golden Dataset
    questions = build_75_golden_questions()
    direct_count = sum(1 for q in questions if q["category"] == "direct_lookup")
    synthesis_count = sum(1 for q in questions if q["category"] == "multi_chunk_synthesis")
    oos_count = sum(1 for q in questions if q["category"] == "out_of_scope")

    assert len(questions) == 75, f"Phải có đúng 75 câu hỏi, hiện tại: {len(questions)}"
    assert direct_count == 40, f"Phải có đúng 40 câu trực tiếp, hiện tại: {direct_count}"
    assert synthesis_count == 20, f"Phải có đúng 20 câu tổng hợp, hiện tại: {synthesis_count}"
    assert oos_count == 15, f"Phải có đúng 15 câu ngoài tài liệu, hiện tại: {oos_count}"

    dataset_payload: Dict[str, Any] = {
        "dataset_name": "Intelligent Document Chatbot - RAG Golden Dataset",
        "version": "1.0.0",
        "sprint": "SP6-01",
        "summary": {
            "total_questions": len(questions),
            "direct_lookup_count": direct_count,
            "multi_chunk_synthesis_count": synthesis_count,
            "out_of_scope_count": oos_count,
            "documents": [
                {
                    "filename": DOC_01_FILENAME,
                    "file_type": "pdf",
                    "page_count": len(DOC_01_PAGES),
                    "domain": "Pháp luật Lao động (Bộ luật Lao động 2019)",
                },
                {
                    "filename": DOC_02_FILENAME,
                    "file_type": "pdf",
                    "page_count": len(DOC_02_PAGES),
                    "domain": "Giáo dục Đại học (Quy chế Đào tạo Tín chỉ)",
                },
                {
                    "filename": DOC_03_FILENAME,
                    "file_type": "pdf",
                    "page_count": len(DOC_03_PAGES),
                    "domain": "Kỹ thuật CNTT, Bảo mật & Kiến trúc Hệ thống RAG",
                },
                {
                    "filename": DOC_04_FILENAME,
                    "file_type": "docx",
                    "section_count": len(DOC_04_SECTIONS) + 1,
                    "domain": "Chính sách Nhân sự, Phúc lợi & An toàn Thông tin Nội bộ",
                },
            ],
        },
        "questions": questions,
    }

    # Lưu JSON
    json_path = GOLDEN_DIR / "golden_dataset_75.json"
    json_path.write_text(
        json.dumps(dataset_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Lưu CSV (UTF-8-SIG có BOM để mở trực tiếp trên Excel không lỗi font tiếng Việt)
    csv_path = GOLDEN_DIR / "golden_dataset_75.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "id",
                "category",
                "question",
                "expected_documents",
                "expected_pages",
                "expected_refusal",
                "ground_truth_answer",
                "evidence_keywords",
            ]
        )
        for q in questions:
            writer.writerow(
                [
                    q["id"],
                    q["category"],
                    q["question"],
                    ";".join(q["expected_documents"]),
                    ";".join(str(p) for p in q["expected_pages"]),
                    str(q["expected_refusal"]),
                    q["ground_truth_answer"],
                    ";".join(q["evidence_keywords"]),
                ]
            )

    # Lưu README.md mô tả bộ dữ liệu
    readme_path = GOLDEN_DIR / "README.md"
    readme_content = f"""# Bộ Dữ Liệu Kiểm Thử Chuẩn RAG (Golden Dataset — SP6-01)

Bộ dữ liệu kiểm thử chuẩn (**Golden Dataset**) gồm **75 câu hỏi** kèm đáp án tham chiếu (`ground_truth_answer`), tên tệp nguồn (`expected_documents`), số trang tham chiếu (`expected_pages`) và từ khóa bằng chứng (`evidence_keywords`) dùng để đánh giá định lượng hệ thống **Intelligent Document Chatbot (LLM + RAG)**.

---

## 1. Danh mục 4 Tài liệu Kiểm thử Chuẩn (`docs/golden_dataset/documents/`)

| STT | Tên tệp tài liệu | Định dạng | Quy mô | Lĩnh vực nội dung |
| :-- | :--- | :---: | :---: | :--- |
| 1 | `{DOC_01_FILENAME}` | PDF | 20 trang | Bộ luật Lao động 2019 (Hợp đồng, Thử việc, Tiền lương, Làm thêm giờ, Nghỉ phép, Kỷ luật, Thai sản, BHXH) |
| 2 | `{DOC_02_FILENAME}` | PDF | 18 trang | Quy chế Đào tạo Đại học theo Hệ thống Tín chỉ (Khối lượng học tập, Thang điểm, Cảnh báo học vụ, Bảo lưu, Tốt nghiệp) |
| 3 | `{DOC_03_FILENAME}` | PDF | 16 trang | Đặc tả Kiến trúc Kỹ thuật CNTT & Hệ thống RAG (SLA 99.95%, PostgreSQL, ChromaDB HNSW, Bảo mật, RPO/RTO, CI/CD) |
| 4 | `{DOC_04_FILENAME}` | DOCX | 11 mục + Bảng | Sổ tay Chính sách Nhân sự, Hybrid Work, Phụ cấp, Đào tạo & An toàn Thông tin Nội bộ |

---

## 2. Phân bổ 75 Câu hỏi Kiểm thử (`golden_dataset_75.json` & `golden_dataset_75.csv`)

| Phân loại (`category`) | Mã câu hỏi | Số lượng | Mục đích đánh giá |
| :--- | :---: | :---: | :--- |
| **`direct_lookup`** (Tra cứu trực tiếp) | `GD-001` $\\rightarrow$ `GD-040` | **40 câu** | Đánh giá độ chính xác truy xuất (`Hit Rate@K`, `MRR`) và trích dẫn đúng số trang/đoạn trên thông tin đơn lẻ. |
| **`multi_chunk_synthesis`** (Tổng hợp nhiều đoạn) | `GD-041` $\\rightarrow$ `GD-060` | **20 câu** | Đánh giá khả năng kết hợp thông tin từ nhiều trang/đoạn khác nhau hoặc liên tài liệu (`Recall@K`, `Faithfulness`, `Answer Relevancy`). |
| **`out_of_scope`** (Ngoài phạm vi tài liệu) | `GD-061` $\\rightarrow$ `GD-075` | **15 câu** | Kiểm tra khả năng chống ảo giác (Hallucination): bắt buộc từ chối lịch sự và trả về mảng `sources = []`. |
| **TỔNG CỘNG** | `GD-001` $\\rightarrow$ `GD-075` | **75 câu** | Phục vụ chạy tự động kịch bản đánh giá RAG (`SP6-02`). |

---

## 3. Cách tạo lại hoặc cập nhật Golden Dataset

Chạy lệnh sau từ thư mục gốc của dự án:

```powershell
.\\backend\\venv\\Scripts\\python.exe scripts/generate_golden_dataset.py
```
"""
    readme_path.write_text(readme_content, encoding="utf-8")

    return {
        "json_path": str(json_path),
        "csv_path": str(csv_path),
        "docs_dir": str(DOCS_DIR),
        "total_questions": len(questions),
    }


if __name__ == "__main__":
    result = generate_all_golden_assets()
    print(
        f"[SP6-01] Đã khởi tạo thành công Golden Dataset ({result['total_questions']} câu hỏi) tại:\n"
        f"  - JSON: {result['json_path']}\n"
        f"  - CSV : {result['csv_path']}\n"
        f"  - Docs: {result['docs_dir']}"
    )
