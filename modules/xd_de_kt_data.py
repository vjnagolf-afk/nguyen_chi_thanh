"""
============================================================
XỬ LÝ DỮ LIỆU & LOGIC SINH ĐỀ KIỂM TRA (DATA LAYER)
Kiến trúc: Agentic Workflow & Strict Python Validation
============================================================
"""

import re
import streamlit as st
from loguru import logger
from utils.document_reader import extract_text_from_file
from exports.word_export_engine import WordExportEngine

class ExamValidator:
    @staticmethod
    def validate_matrix(matrix_text: str, config: dict) -> tuple[bool, str]:
        if "|" not in matrix_text:
            return False, "Không tìm thấy cấu trúc bảng Markdown."
        if "10" not in matrix_text and "10.0" not in matrix_text and "10," not in matrix_text:
            logger.warning("Không tìm thấy số 10 trong ma trận, nhưng có thể do định dạng. Cho qua với cảnh báo.")
        return True, ""

    @staticmethod
    def validate_exam(exam_text: str, config: dict) -> tuple[bool, str]:
        # Đếm số lượng 'Câu X' ở đầu dòng hoặc in đậm
        cau_matches = re.findall(r'(?m)^(?:\*\*Câu|Câu)\s*\d+[:\.\*\*]', exam_text)
        total_found = len(cau_matches)
        
        tn = config.get('tn', {})
        tl = config.get('tl', {})
        expected_total = tn.get('n_nlc', 0) + tn.get('n_ds', 0) + tn.get('n_dk', 0) + tn.get('n_ngan', 0) + tl.get('so_cau', 0)
        
        if total_found != expected_total:
            return False, f"LỖI TOÁN HỌC: Cấu hình yêu cầu chính xác {expected_total} câu hỏi, nhưng bạn lại sinh ra {total_found} câu. BẮT BUỘC PHẢI SINH ĐÚNG SỐ LƯỢNG!"
        return True, ""

def generate_with_repair(engine, prompt: str, sys_inst: str, validator_func, config: dict, max_retries=2):
    current_prompt = prompt
    for attempt in range(max_retries):
        res = engine.generate_text(prompt=current_prompt, system_instruction=sys_inst)
        is_valid, error_msg = validator_func(res.text, config)
        if is_valid:
            return res
        logger.warning(f"AI sinh lỗi lần {attempt+1}: {error_msg}")
        current_prompt = prompt + f"\n\n[HỆ THỐNG KIỂM ĐỊNH PHÁT HIỆN LỖI]:\n{error_msg}\nBẠN PHẢI TÍNH TOÁN VÀ SỬA LẠI NGAY LẬP TỨC."
    
    st.toast("⚠️ AI gặp khó khăn trong việc đáp ứng chính xác số lượng. Vui lòng rà soát lại kết quả.", icon="⚠️")
    return res

def calculate_absolute_points(config: dict) -> dict:
    md = config.get('muc_do', {})
    return {
        "nb": (md.get('nb', 0) / 100) * 10.0,
        "th": (md.get('th', 0) / 100) * 10.0,
        "vd": (md.get('vd', 0) / 100) * 10.0,
        "vdc": (md.get('vdc', 0) / 100) * 10.0
    }

def process_request(config: dict, mode: str, uploaded_files: list):
    text_context = ""
    if uploaded_files:
        with st.spinner("Đang tiền xử lý toàn bộ tài liệu đính kèm..."):
            for file in uploaded_files:
                extracted = extract_text_from_file(file)
                if "[LỖI" in extracted:
                    st.error(f"Lỗi đọc file {file.name}: {extracted}")
                    return
                text_context += f"\n--- TÀI LIỆU: {file.name} ---\n{extracted}\n"
    else:
        text_context = "Sử dụng kiến thức chuẩn CT GDPT 2018."

    engine = st.session_state.get("ai_engine")
    if not engine or not engine.is_ready():
        st.error("⚠️ Chưa kết nối AI.")
        return

    pts = calculate_absolute_points(config)
    tn = config.get('tn', {})
    tl = config.get('tl', {})
    
    math_rules = f"""
[CẤU TRÚC ĐIỂM SỐ - TOÁN HỌC KHOÁ CHẶT TỔNG 10.0 ĐIỂM]
- Nhận biết: {pts['nb']:.2f}đ | Thông hiểu: {pts['th']:.2f}đ | Vận dụng: {pts['vd']:.2f}đ | Vận dụng cao: {pts['vdc']:.2f}đ.
- Phần Trắc Nghiệm ({tn.get('total')}đ): {tn.get('n_nlc')} câu NLC ({tn.get('p_nlc')}đ/câu), {tn.get('n_ds')} câu Đ/S ({tn.get('p_ds')}đ/câu), {tn.get('n_dk')} câu Điền khuyết ({tn.get('p_dk')}đ/câu), {tn.get('n_ngan')} câu TL ngắn ({tn.get('p_ngan')}đ/câu).
- Phần Tự Luận ({tl.get('total')}đ): {tl.get('so_cau')} câu (Các thang điểm chi tiết: {', '.join(map(str, tl.get('diem_chi_tiet', [])))}).
"""

    try:
        with st.status("🚀 KHỞI ĐỘNG LUỒNG KIỂM ĐỊNH (AGENTIC PIPELINE)...", expanded=True) as status:
            
            # --- TÁC TỬ 1: MA TRẬN ---
            matrix_text = ""
            if mode != "tuy_chon_khong_ma_tran":
                st.write("⚙️ Tác tử 1: Đang thiết kế Ma Trận & Đặc Tả (Validate=Bảng)...")
                sys_1 = "Chuyên gia làm Ma trận & Đặc tả. TRẢ VỀ BẢNG MARKDOWN. Tổng điểm phải đúng 10."
                
                if mode == "chi_ma_tran":
                    prompt_1 = f"ĐỀ KIỂM TRA:\n{text_context}\n\nNHIỆM VỤ: Lập BẢNG MA TRẬN và BẢN ĐẶC TẢ."
                else:
                    prompt_1 = f"CHỦ ĐỀ: {config['chu_de']}\n{math_rules}\nTÀI LIỆU:\n{text_context}\n\nNHIỆM VỤ: Lập BẢNG MA TRẬN và BẢN ĐẶC TẢ. KHÔNG SINH ĐỀ."
                
                res_matrix = generate_with_repair(engine, prompt_1, sys_1, ExamValidator.validate_matrix, config)
                matrix_text = res_matrix.text
                
                if mode == "chi_ma_tran":
                    st.session_state["latest_exam_md"] = f"# I. MA TRẬN & ĐẶC TẢ\n\n{matrix_text}"
                    status.update(label="✅ Hoàn tất luồng Ma trận!", state="complete")
                    return

            # --- TÁC TỬ 2: ĐỀ THI ---
            st.write("⚙️ Tác tử 2: Đang ra Đề Thi (Validate=Số câu, Toán học)...")
            sys_2 = "Chuyên gia ra đề. Soạn chính xác số câu hỏi. Giữ công thức trong $...$ hoặc $$...$$."
            prompt_2 = f"MA TRẬN:\n{matrix_text if matrix_text else math_rules}\nTÀI LIỆU:\n{text_context}\n\nNHIỆM VỤ: Soạn nội dung ĐỀ THI (Các câu hỏi). Bắt đầu mỗi câu bằng 'Câu X:'. TUYỆT ĐỐI KHÔNG LÀM ĐÁP ÁN."
            res_exam = generate_with_repair(engine, prompt_2, sys_2, ExamValidator.validate_exam, config)

            # --- TÁC TỬ 3: ĐÁP ÁN ---
            st.write("⚙️ Tác tử 3: Đang chấm thi (Cross-check)...")
            sys_3 = "Chuyên gia làm đáp án. Đảm bảo điểm cộng lại đúng như cấu trúc."
            prompt_3 = f"ĐỀ THI TÔI VỪA SOẠN:\n{res_exam.text}\n\nNHIỆM VỤ: Lập ĐÁP ÁN và HƯỚNG DẪN CHẤM chi tiết."
            res_key = engine.generate_text(prompt=prompt_3, system_instruction=sys_3)

            # --- ĐÓNG GÓI ---
            if mode == "tuy_chon_khong_ma_tran":
                final_md = f"# I. ĐỀ KIỂM TRA\n\n{res_exam.text}\n\n# II. ĐÁP ÁN & HDC\n\n{res_key.text}"
            else:
                final_md = f"# I. MA TRẬN & ĐẶC TẢ\n\n{matrix_text}\n\n# II. ĐỀ KIỂM TRA\n\n{res_exam.text}\n\n# III. ĐÁP ÁN & HDC\n\n{res_key.text}"

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
            st.button("🗑️ XÓA KẾT QUẢ ĐỂ TẠO LẠI", on_click=lambda: st.session_state.pop("latest_exam_md", None), type="secondary", use_container_width=True)
