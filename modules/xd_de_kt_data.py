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
[CHỈ THỊ TỐI CAO]
Bạn là Cỗ máy Sinh Đề Thi tự động chuẩn Bộ GD&ĐT Việt Nam. Bạn PHẢI tuân thủ 100% các yêu cầu dưới đây.

1. THÔNG TIN CHUNG:
- Môn học: {config.get('mon_hoc', 'Không xác định')} | Khối: Lớp {config.get('lop', 'Không xác định')}
- Loại đề: {config.get('loai_de', 'Kiểm tra')}
- Thời lượng: {config.get('thoi_gian', '45 phút')}.
- Chủ đề: {config.get('chu_de', 'Tổng hợp')}

2. KỶ LUẬT CÔNG THỨC TOÁN/LÝ/HÓA (QUAN TRỌNG NHẤT):
- BẮT BUỘC sử dụng LaTeX bọc trong dấu `$` (cho inline) hoặc `$$` (cho block) đối với MỌI công thức, số đo, ký hiệu khoa học.
- VÍ DỤ ĐÚNG: $s = v \\times t$, $h = s/2$, $6000 m$, $CO_2$.
- VÍ DỤ SAI BỊ CẤM: (s = v x t), s = v*t. Không được dùng ngoặc đơn (...) để bọc công thức.
- Không dùng HTML, không lồng bảng phức tạp.
"""
    
    if text_context:
        prompt += f"""
3. TÀI LIỆU NỀN TẢNG:
- CHỈ ĐƯỢC PHÉP sử dụng thông tin từ tài liệu đính kèm dưới đây để đặt câu hỏi:
- NGUỒN TÀI LIỆU:\n{text_context[:10000]}...\n
"""
    else:
        prompt += "\n3. TÀI LIỆU NỀN TẢNG: Bám sát CT GDPT 2018.\n"

    if mode == "chi_ma_tran":
        prompt += """
[NHIỆM VỤ ĐẶC BIỆT]
Dựa vào Đề kiểm tra ở trên, hãy XÂY DỰNG NGƯỢC LẠI:
# I. MA TRẬN ĐỀ KIỂM TRA (Bảng Markdown)
# II. BẢN ĐẶC TẢ ĐỀ KIỂM TRA (Bảng Markdown)
KHÔNG sinh lại đề, KHÔNG sinh đáp án.
"""
        return prompt

    tn = config.get('tn', {})
    tl = config.get('tl', {})
    md = config.get('muc_do', {})
    
    prompt += f"""
4. CẤU TRÚC ĐIỂM SỐ (BẮT BUỘC TỔNG ĐIỂM = 10):
- TỶ LỆ MỨC ĐỘ: Nhận biết ({md.get('nb', 40)}%) - Thông hiểu ({md.get('th', 30)}%) - Vận dụng ({md.get('vd', 20)}%) - Vận dụng cao ({md.get('vdc', 10)}%).
- TRẮC NGHIỆM ({tn.get('total', 0)} điểm):
   + Nhiều lựa chọn: {tn.get('n_nlc', 0)} câu (Mỗi câu {tn.get('p_nlc', 0)} điểm)
   + Đúng/Sai: {tn.get('n_ds', 0)} câu (Mỗi câu {tn.get('p_ds', 0)} điểm)
   + Điền khuyết: {tn.get('n_dk', 0)} câu (Mỗi câu {tn.get('p_dk', 0)} điểm)
   + Trả lời ngắn: {tn.get('n_ngan', 0)} câu (Mỗi câu {tn.get('p_ngan', 0)} điểm)
- TỰ LUẬN ({tl.get('total', 0)} điểm - Gồm {tl.get('so_cau', 0)} câu):
"""
    for i, p in enumerate(tl.get('diem_chi_tiet', [])):
        prompt += f"   + Câu {i+1}: {p} điểm\n"

    if mode in ["cv7991", "tuy_chon_co_ma_tran"]:
        prompt += """
5. CẤU TRÚC TRẢ VỀ (MARKDOWN):
# I. MA TRẬN ĐỀ KIỂM TRA
# II. BẢN ĐẶC TẢ
# III. ĐỀ KIỂM TRA
# IV. ĐÁP ÁN
# V. HƯỚNG DẪN CHẤM
"""
    elif mode == "tuy_chon_khong_ma_tran":
        prompt += """
5. CẤU TRÚC TRẢ VỀ (MARKDOWN):
BỎ QUA MA TRẬN VÀ BẢN ĐẶC TẢ.
# I. ĐỀ KIỂM TRA
# II. ĐÁP ÁN
# III. HƯỚNG DẪN CHẤM
"""
    return prompt

def reset_output():
    """Hàm xóa bộ nhớ đệm kết quả."""
    if "latest_exam_md" in st.session_state:
        del st.session_state["latest_exam_md"]

def process_request(config: dict, mode: str, uploaded_file):
    """Controller tiếp nhận yêu cầu từ UI, gọi AI Engine và hiển thị File Export."""
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
        st.error("⚠️ Lỗi Xác Thực AI: Vui lòng cấu hình API Key.")
        return

    # Sinh nội dung AI
    with st.spinner(f"Hệ thống AI ({engine.provider_type}) đang xây dựng đề kiểm tra. Vui lòng đợi..."):
        try:
            response = engine.generate_text(
                prompt=system_prompt, 
                system_instruction="Tuân thủ nghiêm ngặt định dạng Markdown và dấu $ cho công thức Toán/Lý/Hóa."
            )
            st.session_state["latest_exam_md"] = response.text
            st.success(f"✅ Nhiệm vụ hoàn tất! (Thời gian xử lý: {response.latency:.2f}s | {response.total_tokens} tokens)")
        except Exception as e:
            st.error(f"❌ Tiến trình bị gián đoạn: {str(e)}")
            return

    # Hiển thị UI Output (Sau khi sinh xong)
    if "latest_exam_md" in st.session_state:
        md_text = st.session_state["latest_exam_md"]
        
        # 1. Khung xem trước (Có render KaTeX của Streamlit)
        with st.expander("👀 XEM TRƯỚC KẾT QUẢ", expanded=True):
            st.markdown(md_text, unsafe_allow_html=True)
        
        st.divider()
        
        # 2. Xử lý xuất file Word
        with st.spinner("Đang đóng gói file Word (.docx)..."):
            docx_bytes = WordExportEngine.convert_markdown_to_docx_bytes(md_text)
        
        col1, col2 = st.columns(2)
        with col1:
            # Nút Tải Word
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
            # Nút Xóa Kết Quả (Để tạo đề mới)
            st.button(
                label="🗑️ XÓA KẾT QUẢ NÀY", 
                on_click=reset_output, 
                type="secondary",
                use_container_width=True
            )
