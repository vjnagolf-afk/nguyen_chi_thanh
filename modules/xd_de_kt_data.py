"""
============================================================
XỬ LÝ DỮ LIỆU & LOGIC SINH ĐỀ KIỂM TRA (DATA LAYER)
Tích hợp Streamlit UI, AI Engine và Word Export Engine.
============================================================
"""

import streamlit as st
from loguru import logger
from utils.document_reader import extract_text_from_file
from exports.word_export_engine import WordExportEngine

def build_system_prompt(config: dict, mode: str, text_context: str) -> str:
    """Xây dựng Prompt chi tiết dựa vào Mode và Cấu hình từ UI."""
    
    prompt = f"""
[CHỈ THỊ TỐI CAO DÀNH CHO AI]
Bạn là Cỗ máy Sinh Đề Thi tự động chuẩn Bộ GD&ĐT Việt Nam. BẠN PHẢI TUÂN THỦ TUYỆT ĐỐI 100% CÁC LỆNH SAU MÀ KHÔNG ĐƯỢC PHẢN BÁC:

1. THÔNG TIN CHUNG:
- Môn học: {config.get('mon_hoc', 'Không xác định')} | Khối: Lớp {config.get('lop', 'Không xác định')}
- Loại đề: {config.get('loai_de', 'Kiểm tra')} | Thời lượng: {config.get('thoi_gian', '45 phút')}.
- Chủ đề: {config.get('chu_de', 'Tổng hợp')}

2. KỶ LUẬT ĐẦU RA (CHỐNG LỖI LẶP LẠI VÀ LẢM NHẢM):
- TUYỆT ĐỐI KHÔNG lặp lại Ma trận hoặc Đề thi 2 lần. Chỉ sinh ra 1 lần duy nhất!
- TUYỆT ĐỐI KHÔNG in ra các lời giải thích thừa thãi, ví dụ như "Lưu ý: Tôi đã điều chỉnh...", "Dưới đây là đề thi...". CHỈ IN RA TIÊU ĐỀ VÀ NỘI DUNG.
- ĐỐI VỚI BẢNG MA TRẬN: Bắt buộc dùng cú pháp Bảng Markdown chuẩn (Các cột cách nhau bởi dấu `|`). 
- CÔNG THỨC TOÁN/LÝ/HÓA: BẮT BUỘC bọc trong dấu `$` (VD: $s = v \\times t$).
"""
    
    # Kỷ luật bám sát đề cương
    if text_context:
        prompt += f"""
3. TÀI LIỆU NỀN TẢNG (CHẾ ĐỘ CÓ ĐỀ CƯƠNG):
- CHỈ ĐƯỢC PHÉP sử dụng kiến thức, số liệu và ngữ liệu từ đoạn văn bản dưới đây.
- NGHIÊM CẤM TỰ BỊA ĐẶT HOẶC SỬ DỤNG KIẾN THỨC BÊN NGOÀI ĐỂ RA ĐỀ.
- VĂN BẢN ĐỀ CƯƠNG:\n{text_context[:12000]}...\n
"""
    else:
        prompt += """
3. TÀI LIỆU NỀN TẢNG (CHẾ ĐỘ KHÔNG CÓ ĐỀ CƯƠNG):
- Người dùng KHÔNG tải lên đề cương. Bạn phải tự sử dụng dữ liệu từ Chương trình Giáo dục Phổ thông 2018 (SGK hiện hành) để thiết kế câu hỏi bám sát chủ đề đã cho.
"""

    if mode == "chi_ma_tran":
        prompt += """
[NHIỆM VỤ ĐẶC BIỆT]
Dựa vào Đề kiểm tra ở trên, XÂY DỰNG NGƯỢC LẠI:
# I. MA TRẬN ĐỀ KIỂM TRA (Bảng Markdown)
# II. BẢN ĐẶC TẢ ĐỀ KIỂM TRA (Bảng Markdown)
TUYỆT ĐỐI KHÔNG SINH LẠI ĐỀ HAY ĐÁP ÁN.
"""
        return prompt

    tn = config.get('tn', {})
    tl = config.get('tl', {})
    md = config.get('muc_do', {})
    
    prompt += f"""
4. CẤU TRÚC ĐIỂM SỐ (BẮT BUỘC TỔNG ĐIỂM ĐÚNG 10.0):
- Mức độ: Nhận biết ({md.get('nb', 40)}%) - Thông hiểu ({md.get('th', 30)}%) - Vận dụng ({md.get('vd', 20)}%) - Vận dụng cao ({md.get('vdc', 10)}%).
- TRẮC NGHIỆM ({tn.get('total', 0)} điểm):
   + Nhiều lựa chọn (4 đáp án): {tn.get('n_nlc', 0)} câu (Mỗi câu {tn.get('p_nlc', 0)} điểm)
   + Đúng/Sai: {tn.get('n_ds', 0)} câu (Mỗi câu {tn.get('p_ds', 0)} điểm)
   + Điền khuyết: {tn.get('n_dk', 0)} câu (Mỗi câu {tn.get('p_dk', 0)} điểm)
   + Trả lời ngắn: {tn.get('n_ngan', 0)} câu (Mỗi câu {tn.get('p_ngan', 0)} điểm)
- TỰ LUẬN ({tl.get('total', 0)} điểm - Gồm {tl.get('so_cau', 0)} câu):
"""
    for i, p in enumerate(tl.get('diem_chi_tiet', [])):
        prompt += f"   + Câu {i+1}: {p} điểm\n"

    if mode in ["cv7991", "tuy_chon_co_ma_tran"]:
        prompt += """
5. CẤU TRÚC TRẢ VỀ (MARKDOWN - THEO ĐÚNG THỨ TỰ NÀY):
# I. MA TRẬN ĐỀ KIỂM TRA
# II. BẢN ĐẶC TẢ
# III. ĐỀ KIỂM TRA
# IV. ĐÁP ÁN
# V. HƯỚNG DẪN CHẤM
"""
    elif mode == "tuy_chon_khong_ma_tran":
        prompt += """
5. CẤU TRÚC TRẢ VỀ (MARKDOWN - THEO ĐÚNG THỨ TỰ NÀY, BỎ QUA MA TRẬN VÀ ĐẶC TẢ):
# I. ĐỀ KIỂM TRA
# II. ĐÁP ÁN
# III. HƯỚNG DẪN CHẤM
"""
    return prompt

def reset_output():
    if "latest_exam_md" in st.session_state:
        del st.session_state["latest_exam_md"]

def process_request(config: dict, mode: str, uploaded_file):
    text_context = ""
    
    if uploaded_file is not None:
        with st.spinner("Đang đọc và phân tích tài liệu đính kèm..."):
            text_context = extract_text_from_file(uploaded_file)
            if "[LỖI" in text_context:
                st.error(text_context)
                logger.error(f"Lỗi đọc file: {text_context}")
                return
            st.success(f"✅ Đã đọc thành công tài liệu: {uploaded_file.name}")
    
    system_prompt = build_system_prompt(config, mode, text_context)
    engine = st.session_state.get("ai_engine")
    
    if not engine or not engine.is_ready():
        st.error("⚠️ Lỗi Xác Thực AI: Vui lòng cấu hình API Key ở Sidebar.")
        return

    with st.spinner(f"Hệ thống AI ({engine.provider_type}) đang xây dựng đề kiểm tra. Thời gian dự kiến: 20 - 45 giây..."):
        try:
            response = engine.generate_text(
                prompt=system_prompt, 
                system_instruction="Bạn là AI phục tùng mệnh lệnh tuyệt đối. Chỉ trả về Markdown, không giao tiếp thêm."
            )
            st.session_state["latest_exam_md"] = response.text
            st.success(f"✅ Nhiệm vụ hoàn tất! (Thời gian xử lý: {response.latency:.2f}s | {response.total_tokens} tokens)")
        except Exception as e:
            st.error(f"❌ Tiến trình bị gián đoạn: {str(e)}")
            return

    if "latest_exam_md" in st.session_state:
        md_text = st.session_state["latest_exam_md"]
        
        with st.expander("👀 XEM TRƯỚC KẾT QUẢ", expanded=True):
            st.markdown(md_text, unsafe_allow_html=True)
        
        st.divider()
        
        with st.spinner("Đang đóng gói file Word (.docx)..."):
            docx_bytes = WordExportEngine.convert_markdown_to_docx_bytes(md_text)
        
        col1, col2 = st.columns(2)
        with col1:
            file_name_export = f"De_Kiem_Tra_{config.get('mon_hoc', 'Mon')}.docx".replace(" ", "_")
            st.download_button(
                label="📥 TẢI XUỐNG FILE WORD (.DOCX)",
                data=docx_bytes,
                file_name=file_name_export,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
                use_container_width=True
            )
        with col2:
            st.button(
                label="🗑️ XÓA KẾT QUẢ ĐỂ TẠO ĐỀ MỚI", 
                on_click=reset_output, 
                type="secondary",
                use_container_width=True
            )
