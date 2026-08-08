"""
============================================================
XỬ LÝ DỮ LIỆU & LOGIC SINH ĐỀ KIỂM TRA (DATA LAYER)
Kiến trúc: Agentic Workflow & Strict Python Validation
============================================================
"""

import re
import math
import streamlit as st
from loguru import logger
from utils.document_reader import extract_text_from_file
from exports.word_export_engine import WordExportEngine

# ==========================================
# 1. BỘ CÔNG CỤ TIỀN XỬ LÝ (PRE-PROCESSING)
# ==========================================
def calculate_absolute_points(config: dict) -> dict:
    """Chuyển đổi % mức độ nhận thức thành điểm số tuyệt đối, tránh để AI tự làm toán."""
    md = config.get('muc_do', {})
    return {
        "nb": (md.get('nb', 40) / 100) * 10.0,
        "th": (md.get('th', 30) / 100) * 10.0,
        "vd": (md.get('vd', 20) / 100) * 10.0,
        "vdc": (md.get('vdc', 10) / 100) * 10.0
    }

def build_matrix_rules(config: dict, pts: dict) -> str:
    """Đặc tả thuật toán xây dựng ma trận vô cùng chặt chẽ."""
    tn = config.get('tn', {})
    tl = config.get('tl', {})
    
    rules = f"""
[LUẬT XÂY DỰNG MA TRẬN & BẢN ĐẶC TẢ]
1. CẤU TRÚC CỘT MA TRẬN BẮT BUỘC: 
   | Chủ đề/Nội dung | Nhận biết | Thông hiểu | Vận dụng | Vận dụng cao | Tổng số câu | Tổng điểm |
   (Lưu ý: Các cột mức độ phải chia rõ TN và TL nếu có).

2. RÀNG BUỘC ĐIỂM SỐ TỔNG (TOÁN HỌC TUYỆT ĐỐI):
   - Mức độ Nhận biết: BẮT BUỘC ĐÚNG {pts['nb']:.2f} điểm.
   - Mức độ Thông hiểu: BẮT BUỘC ĐÚNG {pts['th']:.2f} điểm.
   - Mức độ Vận dụng: BẮT BUỘC ĐÚNG {pts['vd']:.2f} điểm.
   - Mức độ Vận dụng cao: BẮT BUỘC ĐÚNG {pts['vdc']:.2f} điểm.
   - TỔNG ĐIỂM TOÀN BÀI: PHẢI CHÍNH XÁC 10.0 ĐIỂM.

3. RÀNG BUỘC SỐ LƯỢNG CÂU HỎI TỔNG:
   - Trắc nghiệm Nhiều lựa chọn ({tn.get('p_nlc')}đ/câu): BẮT BUỘC {tn.get('n_nlc')} câu.
   - Trắc nghiệm Đúng/Sai ({tn.get('p_ds')}đ/câu): BẮT BUỘC {tn.get('n_ds')} câu.
   - Trắc nghiệm Trả lời ngắn ({tn.get('p_ngan')}đ/câu): BẮT BUỘC {tn.get('n_ngan')} câu.
   - Tự luận: BẮT BUỘC {tl.get('so_cau')} câu (Gồm các thang điểm: {', '.join(map(str, tl.get('diem_chi_tiet', [])))}).

4. QUY TẮC ĐỐI CHIẾU: Bản Đặc tả phải ánh xạ 1-1 với Ma trận. Số lượng câu trong Đặc tả không được lệch dù chỉ 1 câu so với Ma trận.
"""
    return rules

# ==========================================
# 2. BỘ KIỂM ĐỊNH (PYTHON VALIDATORS)
# ==========================================
class ExamValidator:
    @staticmethod
    def validate_exam_questions_count(exam_text: str, config: dict) -> tuple[bool, list]:
        """Dùng Regex để đếm số câu hỏi thực tế AI sinh ra so với cấu hình."""
        errors = []
        
        # Đếm câu Trắc nghiệm Nhiều lựa chọn (Tìm các mẫu "Câu 1:", "Câu 2." trong phần trắc nghiệm)
        # Giả định câu hỏi bắt đầu bằng "Câu X"
        câu_matches = re.findall(r'(?i)\*\*Câu\s+\d+[:\.\*\*]', exam_text)
        total_questions_generated = len(câu_matches)
        
        tn = config.get('tn', {})
        tl = config.get('tl', {})
        expected_total = tn.get('n_nlc', 0) + tn.get('n_ds', 0) + tn.get('n_ngan', 0) + tn.get('n_dk', 0) + tl.get('so_cau', 0)
        
        # Regex đếm số lượng đáp án A, B, C, D để ước lượng
        options_a = len(re.findall(r'(?i)[A-D]\.', exam_text))
        
        if total_questions_generated < (expected_total * 0.8): # Dung sai 20% do AI định dạng "Câu" khác nhau
            errors.append(f"Cảnh báo: Đếm được {total_questions_generated} mỏ neo 'Câu X', nhưng cấu hình yêu cầu {expected_total} câu.")
            
        return len(errors) == 0, errors

# ==========================================
# 3. TRÌNH ĐIỀU PHỐI ĐA TÁC TỬ (PIPELINE)
# ==========================================
def reset_output():
    if "latest_exam_md" in st.session_state:
        del st.session_state["latest_exam_md"]

def process_request(config: dict, mode: str, uploaded_files: list):
    """Luồng Pipeline sinh Đề có kiểm định."""
    
    text_context = ""
    if uploaded_files:
        with st.spinner(f"Đang phân tích {len(uploaded_files)} tài liệu nền tảng..."):
            for file in uploaded_files:
                extracted = extract_text_from_file(file)
                if "[LỖI" in extracted:
                    st.error(f"Lỗi đọc file {file.name}: {extracted}")
                    return
                text_context += f"\n\n--- TÀI LIỆU: {file.name} ---\n{extracted}\n"
    else:
        text_context = "Sử dụng kiến thức chuẩn CT GDPT 2018."

    engine = st.session_state.get("ai_engine")
    if not engine or not engine.is_ready():
        st.error("⚠️ Lỗi Xác Thực AI: Vui lòng cấu hình API Key ở Sidebar.")
        return

    pts = calculate_absolute_points(config)
    matrix_rules = build_matrix_rules(config, pts)

    final_md_output = ""
    total_latency = 0.0
    total_tokens_used = 0

    try:
        with st.status("🚀 KHỞI ĐỘNG LUỒNG KIỂM ĐỊNH ĐA TÁC TỬ...", expanded=True) as status:
            
            # ---------------------------------------------------------
            # BƯỚC 1: SINH MA TRẬN & ĐẶC TẢ (NẾU CẦN)
            # ---------------------------------------------------------
            matrix_text = ""
            if mode != "tuy_chon_khong_ma_tran":
                st.write("⚙️ Tác tử 1: Đang thiết kế và toán học hóa Ma trận...")
                sys_inst_1 = "Bạn là Chuyên gia thiết kế Ma trận. CHỈ TRẢ VỀ Bảng Markdown. TUYỆT ĐỐI KHÔNG giải thích. Bảng phải có cột Tổng điểm."
                
                if mode == "chi_ma_tran":
                    prompt_1 = f"ĐỀ KIỂM TRA:\n{text_context}\n\nNHIỆM VỤ: Lập BẢNG MA TRẬN và BẢN ĐẶC TẢ cho đề trên."
                else:
                    prompt_1 = f"CHỦ ĐỀ: {config['chu_de']}\n{matrix_rules}\nTÀI LIỆU: {text_context[:10000]}...\n\nNHIỆM VỤ: Lập BẢNG MA TRẬN và BẢN ĐẶC TẢ."
                
                res1 = engine.generate_text(prompt=prompt_1, system_instruction=sys_inst_1)
                matrix_text = res1.text
                total_latency += res1.latency
                total_tokens_used += res1.total_tokens
                
                # Validator: Kiểm tra cơ bản Ma trận có chứa "10" không
                if "10" not in matrix_text and "10.0" not in matrix_text:
                    st.toast("⚠️ Cảnh báo: Ma trận sinh ra dường như không cộng đủ 10 điểm. Vui lòng kiểm tra lại thủ công.", icon="⚠️")

                if mode == "chi_ma_tran":
                    final_md_output = f"# I. MA TRẬN VÀ BẢN ĐẶC TẢ\n\n{matrix_text}"
                    status.update(label=f"✅ Hoàn tất (Thời gian: {total_latency:.2f}s | {total_tokens_used} tokens)", state="complete")
                    st.session_state["latest_exam_md"] = final_md_output
                    return # Kết thúc sớm cho luồng 4

            # ---------------------------------------------------------
            # BƯỚC 2: SINH ĐỀ THI DỰA TRÊN MA TRẬN ĐÃ SINH
            # ---------------------------------------------------------
            st.write("⚙️ Tác tử 2: Đang biên soạn Đề thi bám sát Ma trận...")
            sys_inst_2 = "Bạn là Chuyên gia ra đề. TUYỆT ĐỐI TUÂN THỦ số câu hỏi được giao. Sử dụng Unicode cho đơn vị, và bọc dấu $ cho công thức phức tạp."
            
            prompt_2 = f"""
1. TÀI LIỆU NỀN TẢNG:\n{text_context[:8000]}...
2. MA TRẬN YÊU CẦU ĐÁP ỨNG:\n{matrix_text if matrix_text else matrix_rules}
3. CẤU TRÚC ĐIỂM SỐ: Trắc nghiệm ({config['tn'].get('total')}đ) - Tự luận ({config['tl'].get('total')}đ).

NHIỆM VỤ: Soạn DUY NHẤT phần nội dung ĐỀ KIỂM TRA (Các câu hỏi). Bắt đầu mỗi câu bằng chữ "Câu X:". TUYỆT ĐỐI KHÔNG sinh đáp án ở bước này.
"""
            res2 = engine.generate_text(prompt=prompt_2, system_instruction=sys_inst_2)
            exam_text = res2.text
            total_latency += res2.latency
            total_tokens_used += res2.total_tokens

            # Python Validator đếm số câu hỏi
            is_valid, errors = ExamValidator.validate_exam_questions_count(exam_text, config)
            if not is_valid:
                for err in errors:
                    st.toast(err, icon="⚠️")

            # ---------------------------------------------------------
            # BƯỚC 3: SINH ĐÁP ÁN & HƯỚNG DẪN CHẤM
            # ---------------------------------------------------------
            st.write("⚙️ Tác tử 3: Đang xây dựng Đáp án & Hướng dẫn chấm (Kiểm định đối chiếu)...")
            sys_inst_3 = "Chuyên gia chấm thi. Nhiệm vụ: Đọc kỹ Đề thi và lập Bảng đáp án, Hướng dẫn chấm chi tiết đến 0.25đ. Không giải thích lề mề."
            
            prompt_3 = f"Dựa vào ĐỀ KIỂM TRA TÔI VỪA SOẠN DƯỚI ĐÂY, hãy lập ĐÁP ÁN VÀ HƯỚNG DẪN CHẤM. Đảm bảo tổng điểm chấm tự luận bằng {config['tl'].get('total')} điểm.\n\nĐỀ KIỂM TRA:\n{exam_text}"
            res3 = engine.generate_text(prompt=prompt_3, system_instruction=sys_inst_3)
            total_latency += res3.latency
            total_tokens_used += res3.total_tokens
            
            # ==========================================
            # 4. ĐÓNG GÓI CHUNG (ASSEMBLY)
            # ==========================================
            if matrix_text:
                final_md_output = f"# I. MA TRẬN VÀ BẢN ĐẶC TẢ\n\n{matrix_text}\n\n# II. ĐỀ KIỂM TRA\n\n{exam_text}\n\n# III. ĐÁP ÁN & HƯỚNG DẪN CHẤM\n\n{res3.text}"
            else:
                final_md_output = f"# I. ĐỀ KIỂM TRA\n\n{exam_text}\n\n# II. ĐÁP ÁN & HƯỚNG DẪN CHẤM\n\n{res3.text}"

            status.update(label=f"✅ HOÀN TẤT LUỒNG ĐA TÁC TỬ (Tổng thời gian: {total_latency:.2f}s | Đã dùng: {total_tokens_used} tokens)", state="complete")
            st.session_state["latest_exam_md"] = final_md_output

    except Exception as e:
        st.error(f"❌ Tiến trình bị đứt gãy tại Pipeline: {str(e)}")
        logger.error(f"Lỗi luồng sinh đề: {str(e)}")
        return

    # HIỂN THỊ VÀ TẢI XUỐNG
    if "latest_exam_md" in st.session_state:
        md_text = st.session_state["latest_exam_md"]
        
        with st.expander("👀 XEM TRƯỚC BẢN THẢO KIỂM ĐỊNH", expanded=True):
            st.markdown(md_text, unsafe_allow_html=True)
        
        st.divider()
        with st.spinner("Đang kết xuất tệp Word (Render Bảng & Công thức)..."):
            docx_bytes = WordExportEngine.convert_markdown_to_docx_bytes(md_text)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 TẢI XUỐNG BẢN CHÍNH THỨC (.DOCX)", data=docx_bytes,
                file_name=f"De_Kiem_Tra_Edu_AI.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary", use_container_width=True
            )
        with col2:
            st.button("🗑️ HỦY KẾT QUẢ / TẠO LẠI", on_click=reset_output, type="secondary", use_container_width=True)
