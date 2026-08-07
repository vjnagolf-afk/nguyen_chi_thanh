import streamlit as st
import json
import os
from utils.document_reader import extract_text_from_file

def build_system_prompt(config: dict, mode: str, text_context: str) -> str:
    """Xây dựng Prompt chi tiết dựa vào Mode và Cấu hình"""
    
    # Base Context
    prompt = f"""
Bạn là Chuyên gia Giáo dục cấp cao. Nhiệm vụ của bạn là xây dựng đề kiểm tra môn {config['mon_hoc']} lớp {config['lop']}.
Loại đề: {config['loai_de']}. Thời gian: {config['thoi_gian']}.
Chủ đề / Nội dung: {config.get('chu_de', 'Bám sát CT GDPT 2018')}

YÊU CẦU NGHIÊM NGẶT:
- KHÔNG sử dụng ký tự đặc biệt gây lỗi.
- BẮT BUỘC sử dụng LaTeX (bọc trong $$ hoặc $) cho mọi công thức Toán học, Vật lí, Hóa học.
"""
    if text_context:
        prompt += f"\nCHỈ SỬ DỤNG DỮ LIỆU TỪ TÀI LIỆU SAU ĐÂY ĐỂ RA ĐỀ:\n{text_context[:5000]}...\n\n"

    # Xử lý theo từng Mode
    if mode == "chi_ma_tran":
        prompt += """
Dựa vào nội dung Đề kiểm tra ở trên, hãy XÂY DỰNG NGƯỢC LẠI:
# I. MA TRẬN ĐỀ KIỂM TRA (Trình bày dưới dạng Bảng Markdown)
# II. BẢN ĐẶC TẢ ĐỀ KIỂM TRA (Trình bày dưới dạng Bảng Markdown)
Tuyệt đối không sinh lại đề hay đáp án.
"""
        return prompt

    # Chi tiết điểm số cho Tab 1, 2, 3
    tn = config['tn']
    tl = config['tl']
    md = config['muc_do']
    
    prompt += f"""
CẤU HÌNH ĐIỂM VÀ CẤU TRÚC ĐỀ (TỔNG 10 ĐIỂM):
1. TỶ LỆ MỨC ĐỘ: Nhận biết ({md['nb']}%) - Thông hiểu ({md['th']}%) - Vận dụng ({md['vd']}%) - Vận dụng cao ({md['vdc']}%).
2. TRẮC NGHIỆM ({tn['total']} điểm):
   - Nhiều lựa chọn (A,B,C,D): {tn['n_nlc']} câu (Mỗi câu {tn['p_nlc']} điểm)
   - Đúng/Sai: {tn['n_ds']} câu (Mỗi câu {tn['p_ds']} điểm)
   - Điền khuyết: {tn['n_dk']} câu (Mỗi câu {tn['p_dk']} điểm)
   - Trả lời ngắn: {tn['n_ngan']} câu (Mỗi câu {tn['p_ngan']} điểm)
3. TỰ LUẬN ({tl['total']} điểm - Gồm {tl['so_cau']} câu):
"""
    for i, p in enumerate(tl['diem_chi_tiet']):
        prompt += f"   - Câu {i+1}: {p} điểm\n"

    # Yêu cầu xuất ra (Khác nhau giữa có và không có ma trận)
    if mode in ["cv7991", "tuy_chon_co_ma_tran"]:
        if mode == "cv7991":
            prompt += "\nLƯU Ý: Phải tuân thủ chuẩn form Công văn 7991 của Bộ GD&ĐT.\n"
            
        prompt += """
HÃY TRẢ VỀ ĐÚNG CẤU TRÚC SAU:
# I. MA TRẬN ĐỀ KIỂM TRA (Bảng Markdown)
# II. BẢN ĐẶC TẢ (Bảng Markdown)
# III. ĐỀ KIỂM TRA (Trình bày rõ ràng từng phần, phân chia TN và TL)
# IV. ĐÁP ÁN (Chi tiết)
# V. HƯỚNG DẪN CHẤM (Ghi rõ điểm thành phần cho từng ý tự luận)
"""
    elif mode == "tuy_chon_khong_ma_tran":
        prompt += """
HÃY TRẢ VỀ ĐÚNG CẤU TRÚC SAU (BỎ QUA MA TRẬN VÀ ĐẶC TẢ):
# I. ĐỀ KIỂM TRA (Trình bày rõ ràng từng phần, phân chia TN và TL)
# II. ĐÁP ÁN (Chi tiết)
# III. HƯỚNG DẪN CHẤM (Ghi rõ điểm thành phần cho từng ý tự luận)
"""
    return prompt

def process_request(config: dict, mode: str, uploaded_file):
    """Hàm trung tâm xử lý Logic sau khi người dùng bấm nút"""
    
    # 1. Trích xuất file đính kèm
    text_context = ""
    if uploaded_file is not None:
        with st.spinner("Đang đọc tài liệu đính kèm..."):
            text_context = extract_text_from_file(uploaded_file)
            if "[LỖI" in text_context:
                st.error(text_context)
                return
    
    # 2. Sinh Prompt
    system_prompt = build_system_prompt(config, mode, text_context)
    
    # 3. Kết nối AI Engine
    engine = st.session_state.get("ai_engine")
    if not engine or not engine.is_ready():
        st.error("⚠️ Hệ thống AI chưa kết nối! Vui lòng vào thanh bên (Sidebar) cấu hình và lưu API Key.")
        return

    with st.spinner("Bộ não AI đang tính toán và xây dựng đề... Thời gian dự kiến: 15-30 giây."):
        try:
            # Gửi Prompt. Vì đây là tác vụ lõi, ta đưa prompt vào cả 2 tham số để AI hiểu ngữ cảnh rõ nhất.
            response = engine.generate(prompt=system_prompt, system_instruction="Bạn là Chuyên gia làm đề thi chuẩn GDPT 2018.")
            
            # 4. Hiển thị kết quả & Đưa vào bộ nhớ để xuất Word (Bước sau)
            st.success("✅ Đã xây dựng xong!")
            st.session_state["latest_exam_md"] = response
            
            with st.expander("👀 XEM TRƯỚC NỘI DUNG (MARKDOWN)", expanded=True):
                st.markdown(response)
                
            st.info("Nội dung đã được tạo. Chức năng Xuất file Word (Export) đang được tích hợp ở bước tiếp theo!")
            
        except Exception as e:
            st.error(f"❌ Xảy ra lỗi trong quá trình sinh đề: {str(e)}")
