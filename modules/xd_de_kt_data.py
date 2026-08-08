"""
============================================================
XỬ LÝ DỮ LIỆU & LOGIC SINH ĐỀ KIỂM TRA (DATA LAYER)
Tác tử 1 sinh JSON cho Template - Tác tử 2,3 sinh Markdown
============================================================
"""

import re
import os
import json
import streamlit as st
from loguru import logger
from utils.document_reader import extract_text_from_file
from exports.word_export_engine import WordExportEngine

def calculate_absolute_points(config: dict) -> dict:
    md = config.get('muc_do', {})
    return {
        "nb": (md.get('nb', 0) / 100) * 10.0,
        "th": (md.get('th', 0) / 100) * 10.0,
        "vd": (md.get('vd', 0) / 100) * 10.0,
        "vdc": (md.get('vdc', 0) / 100) * 10.0
    }

def process_request(config: dict, mode: str, uploaded_files: list, template_path: str = None):
    text_context = ""
    if uploaded_files:
        with st.spinner("Đang tiền xử lý toàn bộ tài liệu đính kèm..."):
            for file in uploaded_files:
                extracted = extract_text_from_file(file)
                if "[LỖI" not in extracted:
                    text_context += f"\n--- TÀI LIỆU: {file.name} ---\n{extracted}\n"

    engine = st.session_state.get("ai_engine")
    if not engine or not engine.is_ready():
        st.error("⚠️ Chưa kết nối AI.")
        return

    pts = calculate_absolute_points(config)
    tn = config.get('tn', {})
    tl = config.get('tl', {})
    
    math_rules = f"""
- Nhận biết: {pts['nb']:.2f}đ | Thông hiểu: {pts['th']:.2f}đ | Vận dụng: {pts['vd']:.2f}đ | VDC: {pts['vdc']:.2f}đ.
- TN ({tn.get('total')}đ): {tn.get('n_nlc')} NLC, {tn.get('n_ds')} Đ/S, {tn.get('n_dk')} ĐK, {tn.get('n_ngan')} TL ngắn.
- TL ({tl.get('total')}đ): {tl.get('so_cau')} câu (Điểm: {', '.join(map(str, tl.get('diem_chi_tiet', [])))}).
"""

    try:
        with st.status("🚀 KHỞI ĐỘNG LUỒNG PIPELINE (JSON + MARKDOWN)...", expanded=True) as status:
            
            # --- TÁC TỬ 1: SINH JSON MA TRẬN & ĐẶC TẢ ---
            st.write("⚙️ Tác tử 1: Phân tích số liệu và xuất tệp JSON theo Template...")
            sys_1 = "Bạn là hệ thống tính toán. BẮT BUỘC TRẢ VỀ ĐÚNG ĐỊNH DẠNG JSON. KHÔNG DÙNG ```json. KHÔNG CÓ BẤT KỲ ĐOẠN VĂN NÀO KHÁC."
            
            prompt_1 = f"""
            Dựa vào TÀI LIỆU sau: {text_context[:10000]}
            Và CẤU TRÚC ĐIỂM: {math_rules}
            Hãy tạo 1 chuỗi JSON hợp lệ với cấu trúc sau:
            {{
              "MON_HOC": "{config.get('mon_hoc')}",
              "ma_tran_data": [
                 {{"chu_de": "Tên chủ đề", "noi_dung": "Nội dung", "nb": "2", "th": "1", "vd": "0", "vdc": "0", "tong_so_cau": "3", "tong_diem": "1.5"}}
              ],
              "dac_ta_data": [
                 {{"stt": "1", "chu_de": "Tên", "bai_hoc": "Bài", "yccd": "Yêu cầu", "tn_nb": "2", "tn_hieu": "0", "tn_vd": "0", "ds_nb": "0", "ds_hieu": "0", "ds_vd": "0", "tl_biet": "0", "tl_hieu": "0", "tl_vd": "1", "tong_diem": "1.5"}}
              ]
            }}
            Lưu ý: Bạn phải tự sinh nhiều object trong mảng ma_tran_data và dac_ta_data sao cho cộng lại đúng tổng điểm 10.0.
            """
            
            res_json = engine.generate_json(prompt=prompt_1, system_instruction=sys_1)
            raw_text = res_json.text.strip()
            
            if raw_text.startswith("```json"):
                raw_text = raw_text.strip("`").replace("json\n", "", 1).strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.strip("`").strip()
                
            try:
                matrix_json = json.loads(raw_text)
            except Exception as e:
                st.error(f"AI không xuất được định dạng JSON chuẩn. Nội dung thô: {raw_text[:200]}")
                return

            if mode == "chi_ma_tran":
                st.session_state["matrix_json"] = matrix_json
                st.session_state["latest_exam_md"] = ""
                st.session_state["key_md"] = ""
                status.update(label="✅ Hoàn tất trích xuất số liệu Ma trận!", state="complete")
            else:
                # --- TÁC TỬ 2: ĐỀ THI ---
                st.write("⚙️ Tác tử 2: Đang ra Đề Thi (Markdown)...")
                sys_2 = "Chuyên gia ra đề. Soạn chính xác số câu hỏi. Giữ công thức trong $...$ hoặc $$...$$."
                prompt_2 = f"Dựa vào BẢNG SỐ LIỆU SAU:\n{json.dumps(matrix_json)}\nTÀI LIỆU:\n{text_context}\n\nNHIỆM VỤ: Soạn nội dung ĐỀ THI (Các câu hỏi). TUYỆT ĐỐI KHÔNG LÀM ĐÁP ÁN."
                res_exam = engine.generate_text(prompt=prompt_2, system_instruction=sys_2)

                # --- TÁC TỬ 3: ĐÁP ÁN ---
                st.write("⚙️ Tác tử 3: Đang chấm thi (Markdown)...")
                sys_3 = "Chuyên gia làm đáp án. Đảm bảo điểm cộng lại đúng như cấu trúc."
                prompt_3 = f"ĐỀ THI TÔI VỪA SOẠN:\n{res_exam.text}\n\nNHIỆM VỤ: Lập ĐÁP ÁN và HƯỚNG DẪN CHẤM chi tiết."
                res_key = engine.generate_text(prompt=prompt_3, system_instruction=sys_3)

                st.session_state["matrix_json"] = matrix_json
                st.session_state["latest_exam_md"] = f"# ĐỀ KIỂM TRA\n\n{res_exam.text}"
                st.session_state["key_md"] = f"# ĐÁP ÁN & HDC\n\n{res_key.text}"
                status.update(label="✅ HOÀN TẤT LUỒNG PIPELINE!", state="complete")

    except Exception as e:
        st.error(f"❌ Lỗi Pipeline: {str(e)}")
        return

    # KẾT XUẤT VÀ TẢI XUỐNG
    if "matrix_json" in st.session_state:
        st.success("✅ Đã kết nối thành công dữ liệu JSON với Template.")
        
        # Gọi engine kết hợp với đường dẫn tĩnh trên máy chủ
        if template_path and os.path.exists(template_path):
            with st.spinner(f"Đang kết hợp JSON vào Mẫu '{os.path.basename(template_path)}'..."):
                docx_bytes = WordExportEngine.export_with_template(
                    template_path, 
                    st.session_state["matrix_json"], 
                    st.session_state.get("latest_exam_md", ""), 
                    st.session_state.get("key_md", "")
                )
            
            st.download_button(
                "📥 TẢI XUỐNG FILE WORD ĐÃ ĐIỀN MẪU", 
                data=docx_bytes, 
                file_name=f"De_Kiem_Tra_Chuan_Mau.docx", 
                type="primary", 
                use_container_width=True
            )
        else:
            st.warning("⚠️ Lỗi file mẫu. Hệ thống không thể đọc được file mẫu trên máy chủ.")
            with st.expander("👀 XEM TRƯỚC SỐ LIỆU JSON (Dành cho kiểm tra)", expanded=False):
                st.json(st.session_state["matrix_json"])
