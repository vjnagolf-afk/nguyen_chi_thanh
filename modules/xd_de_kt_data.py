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
[CHỈ THỊ TỐI CAO DÀNH CHO AI]
Bạn là Chuyên gia ra đề thi chuẩn Bộ GD&ĐT Việt Nam. BẠN PHẢI SINH ĐẦY ĐỦ NỘI DUNG TỪ ĐẦU ĐẾN CUỐI, TUYỆT ĐỐI KHÔNG ĐƯỢC DỪNG LẠI GIỮA CHỪNG.

1. THÔNG TIN CHUNG:
- Môn học: {config.get('mon_hoc', 'Không xác định')} | Lớp {config.get('lop', 'Không xác định')} | Thời lượng: {config.get('thoi_gian', '45 phút')}.

2. KỶ LUẬT ĐỊNH DẠNG (BẮT BUỘC):
- CHỐNG LỖI BẢNG (QUAN TRỌNG NHẤT): Bảng Markdown CHỈ ĐƯỢC PHÉP có DUY NHẤT 1 dòng kẻ ngang để phân cách tiêu đề (VD: `|---|---|`). NGHIÊM CẤM VIỆC TẠO RA CÁC DÒNG CHỈ CÓ DẤU GẠCH NGANG LIÊN TỤC. Bạn phải điền nội dung chữ thực tế vào bảng.
- TOÁN HỌC/VẬT LÝ: Dùng `$công thức$` cho các biểu thức toán học. Không dùng dấu $ cho văn bản thường.
- KHÔNG lặp lại nội dung. KHÔNG giải thích lảm nhảm.
"""
    
    if text_context:
        prompt += f"""
3. TÀI LIỆU NỀN TẢNG (CHẾ ĐỘ CÓ ĐỀ CƯƠNG):
- CHỈ ĐƯỢC PHÉP sử dụng kiến thức từ các văn bản sau. NGHIÊM CẤM bịa đặt kiến thức ngoài.
- NỘI DUNG ĐỀ CƯƠNG TỔNG HỢP:\n{text_context[:15000]}...\n
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
5. TRÌNH TỰ TRẢ VỀ (BẮT BUỘC PHẢI CÓ ĐỦ 5 PHẦN, ĐÁNH DẤU BẰNG HEADING MARKDOWN #):
# I. MA TRẬN ĐỀ KIỂM TRA
(Chèn Bảng Ma Trận vào đây)

# II. BẢN ĐẶC TẢ
(Chèn Bảng Đặc Tả vào đây)

# III. ĐỀ KIỂM TRA
(Chèn Đề thi gồm Trắc nghiệm và Tự luận vào đây)

# IV. ĐÁP ÁN
(Chèn Đáp án Trắc nghiệm vào đây)

# V. HƯỚNG DẪN CHẤM
(Chèn Hướng dẫn chấm Tự luận vào đây)
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

def process_request(config: dict, mode: str, uploaded_files: list):
    text_context = ""
    
    # HỖ TRỢ XỬ LÝ NHIỀU FILE CÙNG LÚC
    if uploaded_files:
        with st.spinner(f"Đang đọc và phân tích {len(uploaded_files)} tài liệu đính kèm..."):
            for file in uploaded_files:
                extracted = extract_text_from_file(file)
                if "[LỖI" in extracted:
                    st.error(f"Lỗi đọc file {file.name}: {extracted}")
                    return
                text_context += f"\n\n--- BẮT ĐẦU TÀI LIỆU: {file.name} ---\n{extracted}\n--- KẾT THÚC TÀI LIỆU ---\n"
            st.success(f"✅ Đã tổng hợp thành công {len(uploaded_files)} tài liệu!")
    
    system_prompt = build_system_prompt(config, mode, text_context)
    engine = st.session_state.get("ai_engine")
    
    if not engine or not engine.is_ready():
        st.error("⚠️ Lỗi Xác Thực AI: Vui lòng cấu hình API Key ở Sidebar.")
        return

    with st.spinner(f"Hệ thống AI ({engine.provider_type}) đang xây dựng 100% đề kiểm tra. Vui lòng đợi từ 30 - 60 giây..."):
        try:
            response = engine.generate_text(
                prompt=system_prompt, 
                system_instruction="Chỉ sinh nội dung. Không được tạo bảng rỗng, không được sinh ra dòng kẻ nét đứt liên tục. Đảm bảo sinh đề thi hoàn chỉnh."
            )
            st.session_state["latest_exam_md"] = response.text
            st.success(f"✅ Nhiệm vụ hoàn tất! (Thời gian xử lý: {response.latency:.2f}s | Đã dùng: {response.total_tokens} tokens)")
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
