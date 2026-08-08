"""
============================================================
XỬ LÝ DỮ LIỆU & LOGIC SINH ĐỀ KIỂM TRA (DATA LAYER)
============================================================
"""

import streamlit as st
from loguru import logger
from utils.document_reader import extract_text_from_file
from exports.word_export_engine import WordExportEngine

def build_system_prompt(config: dict, mode: str, text_context: str) -> str:
    prompt = f"""
[CHỈ THỊ TỐI CAO]
Bạn là Cỗ máy Sinh Đề Thi tự động chuẩn Bộ GD&ĐT Việt Nam. BẠN PHẢI TUÂN THỦ 100% CÁC LỆNH SAU:

1. THÔNG TIN CHUNG:
- Môn học: {config.get('mon_hoc', 'Không xác định')} | Lớp {config.get('lop', 'Không xác định')} | Thời lượng: {config.get('thoi_gian', '45 phút')}.

2. KỶ LUẬT ĐỊNH DẠNG (BẮT BUỘC):
- TOÁN HỌC VÀ VẬT LÝ: Ưu tiên dùng Unicode thường (VD: s = v × t, 60 km/h, CO2). NGHIÊM CẤM dùng dấu $ cho các đơn vị đo lường đơn giản. CHỈ SỬ DỤNG LaTeX ($...$) cho công thức quá phức tạp (phân số, căn).
- BẢNG BIỂU: Phải điền đầy đủ dữ liệu, TUYỆT ĐỐI KHÔNG sinh ra bảng trống.
- KHÔNG in ra lời giải thích thừa thãi như "Đây là đề thi...". CHỈ in nội dung.
"""
    
    if text_context:
        prompt += f"""
3. TÀI LIỆU NỀN TẢNG (CHẾ ĐỘ CÓ ĐỀ CƯƠNG):
- CHỈ ĐƯỢC PHÉP sử dụng kiến thức từ văn bản sau. NGHIÊM CẤM bịa đặt kiến thức ngoài.
- VĂN BẢN ĐỀ CƯƠNG:\n{text_context[:10000]}...\n
"""
    else:
        prompt += "\n3. TÀI LIỆU NỀN TẢNG: Bám sát CT GDPT 2018.\n"

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
4. CẤU TRÚC ĐIỂM SỐ (TỔNG 10.0):
- Mức độ: Nhận biết ({md.get('nb', 40)}%) - Thông hiểu ({md.get('th', 30)}%) - Vận dụng ({md.get('vd', 20)}%) - Vận dụng cao ({md.get('vdc', 10)}%).
- TRẮC NGHIỆM ({tn.get('total', 0)} điểm): {tn.get('n_nlc', 0)} câu NLC, {tn.get('n_ds', 0)} câu Đ/S, {tn.get('n_dk', 0)} câu Điền khuyết, {tn.get('n_ngan', 0)} câu TL ngắn.
- TỰ LUẬN ({tl.get('total', 0)} điểm - Gồm {tl.get('so_cau', 0)} câu):
"""
    for i, p in enumerate(tl.get('diem_chi_tiet', [])):
        prompt += f"   + Câu {i+1}: {p} điểm\n"

    if mode in ["cv7991", "tuy_chon_co_ma_tran"]:
        prompt += """
5. TRÌNH TỰ TRẢ VỀ:
# I. MA TRẬN ĐỀ KIỂM TRA
# II. BẢN ĐẶC TẢ
# III. ĐỀ KIỂM TRA
# IV. ĐÁP ÁN
# V. HƯỚNG DẪN CHẤM
"""
    elif mode == "tuy_chon_khong_ma_tran":
        prompt += """
5. TRÌNH TỰ TRẢ VỀ (BỎ QUA MA TRẬN VÀ ĐẶC TẢ):
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
                system_instruction="Tuân thủ nghiêm ngặt định dạng Markdown. Trả lời dứt khoát, không giải thích."
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
            st.download_button(
                label="📥 TẢI XUỐNG FILE WORD (.DOCX)", data=docx_bytes,
                file_name=f"De_Kiem_Tra_{config.get('mon_hoc', 'Mon')}.docx".replace(" ", "_"),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary", use_container_width=True
            )
        with col2:
            st.button("🗑️ XÓA KẾT QUẢ ĐỂ TẠO ĐỀ MỚI", on_click=reset_output, type="secondary", use_container_width=True)
