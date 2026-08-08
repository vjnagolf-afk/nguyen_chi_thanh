"""
============================================================
XỬ LÝ DỮ LIỆU & LOGIC SINH ĐỀ KIỂM TRA (DATA LAYER)
Kết nối UI (xd_de_kt.py) với AI Engine (provider.py).
============================================================
"""

import streamlit as st
from loguru import logger
from utils.document_reader import extract_text_from_file

def build_system_prompt(config: dict, mode: str, text_context: str) -> str:
    """Xây dựng Prompt chi tiết dựa vào Mode và Cấu hình từ UI."""
    
    # Base Context - Các chỉ thị Tối cao
    prompt = f"""
[CHỈ THỊ TỐI CAO]
Bạn là Cỗ máy Sinh Đề Thi tự động. Bạn PHẢI tuân thủ 100% các yêu cầu dưới đây, không được sai lệch dù chỉ 1 câu hay 0.25 điểm.

1. THÔNG TIN CHUNG:
- Môn học: {config.get('mon_hoc', 'Không xác định')} | Khối: Lớp {config.get('lop', 'Không xác định')}
- Loại đề: {config.get('loai_de', 'Kiểm tra')}
- Thời lượng: BẮT BUỘC thiết kế nội dung đủ làm trong {config.get('thoi_gian', '45 phút')}.
- Chủ đề: {config.get('chu_de', 'Tổng hợp')}

2. QUY ĐỊNH KỸ THUẬT NGHIÊM NGẶT:
- BẮT BUỘC sử dụng LaTeX (bọc trong $$ hoặc $) cho TẤT CẢ công thức Toán, Lý, Hóa (VD: $x^2 + y^2 = z^2$).
- Không dùng HTML, không lồng bảng.
"""
    
    # Siết chặt Dữ liệu đầu vào
    if text_context:
        prompt += f"""
3. TÀI LIỆU NỀN TẢNG (QUAN TRỌNG NHẤT):
- BẠN BỊ CẤM sử dụng kiến thức bên ngoài. CHỈ ĐƯỢC PHÉP sử dụng thông tin từ tài liệu đính kèm dưới đây để đặt câu hỏi.
- NGUỒN TÀI LIỆU:\n{text_context[:10000]}...\n
"""
    else:
        prompt += "\n3. TÀI LIỆU NỀN TẢNG: Bám sát chuẩn kiến thức kỹ năng CT GDPT 2018.\n"

    # Xử lý riêng cho Tab 4 (Chỉ Sinh Ma Trận)
    if mode == "chi_ma_tran":
        prompt += """
[NHIỆM VỤ ĐẶC BIỆT]
Dựa vào nội dung Đề kiểm tra trong "TÀI LIỆU NỀN TẢNG", hãy XÂY DỰNG NGƯỢC LẠI:
# I. MA TRẬN ĐỀ KIỂM TRA (Trình bày dưới dạng Bảng Markdown)
# II. BẢN ĐẶC TẢ ĐỀ KIỂM TRA (Trình bày dưới dạng Bảng Markdown)
Tuyệt đối KHÔNG sinh lại đề, KHÔNG sinh đáp án. CHỈ trả về 2 bảng trên.
"""
        return prompt

    # Chi tiết điểm số cho Tab 1, 2, 3
    tn = config.get('tn', {})
    tl = config.get('tl', {})
    md = config.get('muc_do', {})
    
    prompt += f"""
4. CẤU TRÚC ĐIỂM SỐ (BẮT BUỘC KHỚP 100% TỔNG ĐIỂM = 10):
- TỶ LỆ MỨC ĐỘ: Nhận biết ({md.get('nb', 40)}%) - Thông hiểu ({md.get('th', 30)}%) - Vận dụng ({md.get('vd', 20)}%) - Vận dụng cao ({md.get('vdc', 10)}%).
- TRẮC NGHIỆM ({tn.get('total', 0)} điểm - Yêu cầu sinh chính xác số lượng câu):
   + Nhiều lựa chọn (4 đáp án A,B,C,D): PHẢI CÓ ĐÚNG {tn.get('n_nlc', 0)} câu (Mỗi câu {tn.get('p_nlc', 0)} điểm)
   + Đúng/Sai (Mỗi câu có 4 ý a,b,c,d): PHẢI CÓ ĐÚNG {tn.get('n_ds', 0)} câu (Mỗi câu {tn.get('p_ds', 0)} điểm)
   + Điền khuyết: PHẢI CÓ ĐÚNG {tn.get('n_dk', 0)} câu (Mỗi câu {tn.get('p_dk', 0)} điểm)
   + Trả lời ngắn: PHẢI CÓ ĐÚNG {tn.get('n_ngan', 0)} câu (Mỗi câu {tn.get('p_ngan', 0)} điểm)
- TỰ LUẬN ({tl.get('total', 0)} điểm): PHẢI CÓ ĐÚNG {tl.get('so_cau', 0)} câu, bao gồm:
"""
    for i, p in enumerate(tl.get('diem_chi_tiet', [])):
        prompt += f"   + Câu {i+1}: Trị giá đúng {p} điểm\n"

    # Định dạng Đầu ra
    if mode in ["cv7991", "tuy_chon_co_ma_tran"]:
        prompt += """
5. CẤU TRÚC TRẢ VỀ (MARKDOWN):
HÃY TRẢ VỀ ĐÚNG TRÌNH TỰ SAU, ĐÁNH DẤU CHÍNH XÁC CÁC TIÊU ĐỀ BẰNG MARKDOWN HEADER:
# I. MA TRẬN ĐỀ KIỂM TRA (Bảng Markdown chuẩn)
# II. BẢN ĐẶC TẢ (Bảng Markdown chuẩn)
# III. ĐỀ KIỂM TRA (Đánh số câu liên tục hoặc chia phần rõ ràng)
# IV. ĐÁP ÁN (Liệt kê rõ ràng)
# V. HƯỚNG DẪN CHẤM (Chi tiết barem điểm đến 0.25 cho từng ý tự luận)
"""
    elif mode == "tuy_chon_khong_ma_tran":
        prompt += """
5. CẤU TRÚC TRẢ VỀ (MARKDOWN):
BỎ QUA MA TRẬN VÀ BẢN ĐẶC TẢ. HÃY TRẢ VỀ ĐÚNG TRÌNH TỰ SAU:
# I. ĐỀ KIỂM TRA (Đánh số câu liên tục hoặc chia phần rõ ràng)
# II. ĐÁP ÁN (Liệt kê rõ ràng)
# III. HƯỚNG DẪN CHẤM (Chi tiết barem điểm đến 0.25 cho từng ý tự luận)
"""
    return prompt

def process_request(config: dict, mode: str, uploaded_file):
    """
    Hàm trung tâm (Controller) tiếp nhận yêu cầu từ UI và gọi tới AI Engine.
    """
    text_context = ""
    
    # 1. Đọc file đính kèm nếu có
    if uploaded_file is not None:
        with st.spinner("Đang đọc và phân tích tài liệu đính kèm..."):
            text_context = extract_text_from_file(uploaded_file)
            if "[LỖI" in text_context:
                st.error(text_context)
                logger.error(f"Lỗi đọc file: {text_context}")
                return
            st.success(f"✅ Đã đọc thành công tài liệu: {uploaded_file.name}")
            logger.info(f"Đã trích xuất {len(text_context)} ký tự từ {uploaded_file.name}")
    
    # 2. Xây dựng lệnh (Prompt)
    system_prompt = build_system_prompt(config, mode, text_context)
    
    # 3. Lấy Engine từ Session
    engine = st.session_state.get("ai_engine")
    if not engine or not engine.is_ready():
        st.error("⚠️ Lỗi Xác Thực AI: Vui lòng vào thanh cấu hình bên trái để cập nhật API Key hợp lệ.")
        logger.warning("Truy cập Module khi AI Engine chưa sẵn sàng.")
        return

    # 4. Giao tiếp với AI
    with st.spinner(f"Hệ thống AI ({engine.provider_type}) đang tổng hợp kiến thức và xây dựng đề kiểm tra. Vui lòng đợi trong giây lát..."):
        try:
            # SỬ DỤNG HÀM MỚI 'generate_text' ĐỂ TRẢ VỀ AIResponse
            response = engine.generate_text(
                prompt=system_prompt, 
                system_instruction="Bạn là Trợ lý AI tuân thủ mệnh lệnh tuyệt đối. Các thông số về số lượng, điểm số và tài liệu đính kèm là bắt buộc và không thể thương lượng."
            )
            
            # Hiển thị thông số từ AIResponse
            st.success(f"✅ Nhiệm vụ hoàn tất! (Thời gian xử lý: {response.latency:.2f}s | Đã dùng: {response.total_tokens} tokens)")
            
            # Lưu Text của phản hồi vào bộ nhớ để chuẩn bị Xuất Word
            st.session_state["latest_exam_md"] = response.text
            logger.info("Sinh đề kiểm tra thành công.")
            
            # 5. Hiển thị kết quả trên UI
            with st.expander("👀 XEM TRƯỚC KẾT QUẢ (DẠNG VĂN BẢN MARKDOWN)", expanded=True):
                st.markdown(response.text)
                
        except Exception as e:
            st.error(f"❌ Tiến trình bị gián đoạn: {str(e)}")
            logger.error(f"Lỗi khi sinh đề: {str(e)}")
            st.info("💡 MẸO TEST: Nếu bạn gặp lỗi hết tín dụng (Credits), hãy đảm bảo bạn đã lưu cấu hình để cập nhật giới hạn token mới.")
