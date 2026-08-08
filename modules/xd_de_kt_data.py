"""
============================================================
XỬ LÝ DỮ LIỆU & LOGIC SINH ĐỀ KIỂM TRA (DATA LAYER)
Agentic Workflow & Python Validation Loop
============================================================
"""

import re
import math
import streamlit as st
from loguru import logger
from utils.document_reader import extract_text_from_file
from exports.word_export_engine import WordExportEngine

# --- PYTHON VALIDATORS ---
def validate_matrix(matrix_text: str, config: dict) -> tuple[bool, str]:
    """Kiểm định Ma Trận bằng Python."""
    if "|" not in matrix_text: return False, "Không tìm thấy cấu trúc bảng Markdown."
    # Có thể bổ sung đếm regex cột, hàng tại đây trong tương lai.
    return True, ""

def validate_exam(exam_text: str, config: dict) -> tuple[bool, str]:
    """Kiểm định Đề Thi bằng Python."""
    # Đếm số lượng chữ "Câu X:"
    cau_matches = re.findall(r'(?i)\*\*Câu\s+\d+[:\.\*\*]|\nCâu\s+\d+[:\.]', exam_text)
    total_found = len(cau_matches)
    
    tn = config.get('tn', {})
    tl = config.get('tl', {})
    expected_total = tn.get('n_nlc', 0) + tn.get('n_ds', 0) + tn.get('n_dk', 0) + tn.get('n_ngan', 0) + tl.get('so_cau', 0)
    
    if total_found != expected_total:
        return False, f"Tôi đếm được {total_found} câu hỏi, nhưng cấu hình yêu cầu chính xác {expected_total} câu. Hãy rà soát và sinh lại cho đúng số lượng."
    return True, ""

def generate_with_repair(engine, prompt: str, sys_inst: str, validator_func, config: dict, max_retries=2):
    """Vòng lặp AI tự sửa lỗi dựa trên phản hồi của Python."""
    current_prompt = prompt
    for attempt in range(max_retries):
        res = engine.generate_text(prompt=current_prompt, system_instruction=sys_inst)
        is_valid, error_msg = validator_func(res.text, config)
        if is_valid:
            return res
        
        logger.warning(f"Lần {attempt+1} AI sinh lỗi: {error_msg}. Đang yêu cầu sửa...")
        current_prompt = prompt + f"\n\n[HỆ THỐNG KIỂM ĐỊNH PYTHON PHÁT HIỆN LỖI TRONG CÂU TRẢ LỜI VỪA RỒI CỦA BẠN]:\n{error_msg}\nHÃY SỬA LẠI NGAY LẬP TỨC VÀ ĐẢM BẢO CHÍNH XÁC TOÁN HỌC."
    
    # Nếu hết lượt vẫn sai, trả về cái cuối cùng và báo cảnh báo
    st.toast("⚠️ AI không thể đạt độ chính xác 100% về số lượng sau nhiều lần sửa. Vui lòng rà soát lại thủ công.", icon="⚠️")
    return res

def calculate_absolute_points(config: dict) -> dict:
    md = config.get('muc_do', {})
    return {
        "nb": (md.get('nb', 0) / 100) * 10.0, "th": (md.get('th', 0) / 100) * 10.0,
        "vd": (md.get('vd', 0) / 100) * 10.0, "vdc": (md.get('vdc', 0) / 100) * 10.0
    }

def process_request(config: dict, mode: str, uploaded_files: list):
    text_context = ""
    # Truyền TẤT CẢ văn bản, không giới hạn [:15000] nữa. OpenRouter/Gemini 2.5 flash xử lý tốt 1 triệu token.
    if uploaded_files:
        with st.spinner("Đang đọc toàn bộ tài liệu..."):
            for file in uploaded_files:
                text_context += f"\n--- {file.name} ---\n{extract_text_from_file(file)}\n"

    engine = st.session_state.get("ai_engine")
    if not engine or not engine.is_ready():
        st.error("⚠️ Chưa kết nối AI.")
        return

    pts = calculate_absolute_points(config)
    tn = config.get('tn', {})
    tl = config.get('tl', {})
    
    math_rules = f"""
- Nhận biết: {pts['nb']:.2f} điểm | Thông hiểu: {pts['th']:.2f} điểm | Vận dụng: {pts['vd']:.2f} điểm | VDC: {pts['vdc']:.2f} điểm.
- TN: NLC ({tn.get('n_nlc')} câu), Đ/S ({tn.get('n_ds')} câu), Điền khuyết ({tn.get('n_dk')} câu), TL ngắn ({tn.get('n_ngan')} câu).
- TL: {tl.get('so_cau')} câu (Điểm: {', '.join(map(str, tl.get('diem_chi_tiet', [])))}).
"""

    try:
        with st.status("🚀 KHỞI ĐỘNG LUỒNG KIỂM ĐỊNH (AGENTIC PIPELINE)...", expanded=True) as status:
            
            # BƯỚC 1: MA TRẬN & ĐẶC TẢ
            st.write("⚙️ Tác tử 1: Đang thiết kế Ma Trận & Đặc Tả (Validate = Bảng)...")
            sys_1 = "Chuyên gia làm Ma trận & Đặc tả. TRẢ VỀ BẢNG MARKDOWN. Không lảm nhảm."
            prompt_1 = f"Dựa vào cấu hình sau:\n{math_rules}\nVà tài liệu:\n{text_context}\nHãy lập BẢNG MA TRẬN và BẢN ĐẶC TẢ."
            res_matrix = generate_with_repair(engine, prompt_1, sys_1, validate_matrix, config)
            
            if mode == "chi_ma_tran":
                st.session_state["latest_exam_md"] = f"# I. MA TRẬN & ĐẶC TẢ\n\n{res_matrix.text}"
                status.update(label="✅ Hoàn tất!", state="complete")
                return

            # BƯỚC 2: ĐỀ THI
            st.write("⚙️ Tác tử 2: Đang ra Đề Thi (Validate = Số lượng câu)...")
            sys_2 = "Chuyên gia ra đề. Soạn chính xác số câu hỏi. Giữ công thức trong $...$ hoặc $$...$$."
            prompt_2 = f"Dựa vào MA TRẬN SAU:\n{res_matrix.text}\nVà TÀI LIỆU:\n{text_context}\nSoạn nội dung ĐỀ THI. Bắt đầu bằng 'Câu X:'."
            res_exam = generate_with_repair(engine, prompt_2, sys_2, validate_exam, config)

            # BƯỚC 3: ĐÁP ÁN
            st.write("⚙️ Tác tử 3: Đang chấm thi (Cross-check)...")
            sys_3 = "Chuyên gia làm đáp án. Đảm bảo điểm cộng lại đúng như cấu trúc."
            prompt_3 = f"Dựa vào ĐỀ THI VỪA SOẠN:\n{res_exam.text}\nHãy làm BẢNG ĐÁP ÁN và HƯỚNG DẪN CHẤM chi tiết."
            res_key = engine.generate_text(prompt=prompt_3, system_instruction=sys_3)

            # ĐÓNG GÓI
            if mode == "tuy_chon_khong_ma_tran":
                final_md = f"# I. ĐỀ KIỂM TRA\n\n{res_exam.text}\n\n# II. ĐÁP ÁN & HDC\n\n{res_key.text}"
            else:
                final_md = f"# I. MA TRẬN & ĐẶC TẢ\n\n{res_matrix.text}\n\n# II. ĐỀ KIỂM TRA\n\n{res_exam.text}\n\n# III. ĐÁP ÁN & HDC\n\n{res_key.text}"

            st.session_state["latest_exam_md"] = final_md
            status.update(label="✅ HOÀN TẤT LUỒNG PIPELINE!", state="complete")

    except Exception as e:
        st.error(f"❌ Lỗi Pipeline: {str(e)}")
        return

    # HIỂN THỊ
    if "latest_exam_md" in st.session_state:
        md_text = st.session_state["latest_exam_md"]
        with st.expander("👀 XEM TRƯỚC BẢN THẢO KIỂM ĐỊNH", expanded=True):
            st.markdown(md_text, unsafe_allow_html=True)
        st.divider()
        with st.spinner("Đang kết xuất Word..."):
            docx_bytes = WordExportEngine.convert_markdown_to_docx_bytes(md_text)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 TẢI XUỐNG FILE WORD", data=docx_bytes, file_name="De_Kiem_Tra_Edu_AI.docx", type="primary", use_container_width=True)
        with col2:
            st.button("🗑️ TẠO LẠI", on_click=lambda: st.session_state.pop("latest_exam_md", None), type="secondary", use_container_width=True)
