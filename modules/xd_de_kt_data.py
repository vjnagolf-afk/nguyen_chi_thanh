"""
============================================================
XỬ LÝ DỮ LIỆU & LOGIC SINH ĐỀ KIỂM TRA (DATA LAYER)
Kiến trúc AI Đa Tác Tử (Agentic Pipeline / Sequential Generation)
============================================================
"""

import streamlit as st
from loguru import logger
from utils.document_reader import extract_text_from_file
from exports.word_export_engine import WordExportEngine

def calculate_cognitive_points(md: dict) -> dict:
    """Chuyển đổi % mức độ nhận thức thành Điểm thực tế trên thang 10."""
    return {
        "nb_pt": (md.get('nb', 40) / 100) * 10,
        "th_pt": (md.get('th', 30) / 100) * 10,
        "vd_pt": (md.get('vd', 20) / 100) * 10,
        "vdc_pt": (md.get('vdc', 10) / 100) * 10
    }

def process_request(config: dict, mode: str, uploaded_files: list):
    """
    Luồng tiền xử lý và điều phối các tác vụ AI (Agentic Workflow).
    """
    # 1. ĐỌC TÀI LIỆU (TÀNG KINH CÁC)
    text_context = ""
    if uploaded_files:
        with st.spinner(f"Đang tổng hợp {len(uploaded_files)} tài liệu đính kèm..."):
            for file in uploaded_files:
                extracted = extract_text_from_file(file)
                if "[LỖI" in extracted:
                    st.error(f"Lỗi đọc file {file.name}: {extracted}")
                    return
                text_context += f"\n\n--- TÀI LIỆU: {file.name} ---\n{extracted}\n"
    else:
        text_context = "Bám sát CT GDPT 2018."

    # 2. KIỂM TRA ENGINE
    engine = st.session_state.get("ai_engine")
    if not engine or not engine.is_ready():
        st.error("⚠️ Lỗi Xác Thực AI: Vui lòng cấu hình API Key ở Sidebar.")
        return

    # 3. QUY ĐỔI TOÁN HỌC CHO AI
    if mode != "chi_ma_tran":
        tn = config.get('tn', {})
        tl = config.get('tl', {})
        pts = calculate_cognitive_points(config.get('muc_do', {}))
        
        # Bảng chỉ thị Toán học ép AI không được tự tính sai
        math_prompt = f"""
CẤU TRÚC ĐỀ (TỔNG 10.0 ĐIỂM):
- Phân bổ điểm yêu cầu: Nhận biết ({pts['nb_pt']} đ), Thông hiểu ({pts['th_pt']} đ), Vận dụng ({pts['vd_pt']} đ), Vận dụng cao ({pts['vdc_pt']} đ).
- Trắc nghiệm ({tn.get('total')} đ): NLC ({tn.get('n_nlc')} câu x {tn.get('p_nlc')}đ), Đ/S ({tn.get('n_ds')} câu x {tn.get('p_ds')}đ), Điền khuyết ({tn.get('n_dk')} câu x {tn.get('p_dk')}đ), TL ngắn ({tn.get('n_ngan')} câu x {tn.get('p_ngan')}đ).
- Tự luận ({tl.get('total')} đ): {tl.get('so_cau')} câu (Các điểm: {', '.join(map(str, tl.get('diem_chi_tiet', [])))}).
"""
    
    # ==========================================
    # KHỞI CHẠY LUỒNG ĐA TÁC TỬ (MULTI-STEP GENERATION)
    # ==========================================
    final_md_output = ""
    total_latency = 0.0
    total_tokens_used = 0

    try:
        with st.status("🚀 BỘ NÃO AI ĐANG HOẠT ĐỘNG (LUỒNG ĐA BƯỚC)...", expanded=True) as status:
            
            # --- LUỒNG 4: CHỈ ĐỌC ĐỀ SINH MA TRẬN (SINGLE SHOT) ---
            if mode == "chi_ma_tran":
                st.write("Đang phân tích Đề và sinh Bảng Ma trận...")
                sys_inst = "Bạn là chuyên gia thẩm định đề. Trả về Markdown Bảng Ma Trận và Bảng Đặc Tả, không kèm lời giải thích."
                prompt_matrix = f"Dựa vào Đề kiểm tra sau, hãy lập Bảng Ma trận và Bảng Đặc tả:\n{text_context}"
                res = engine.generate_text(prompt=prompt_matrix, system_instruction=sys_inst)
                final_md_output = f"# I. MA TRẬN ĐỀ KIỂM TRA\n\n{res.text}"
                total_latency, total_tokens_used = res.latency, res.total_tokens

            # --- LUỒNG 3: CHỈ SINH ĐỀ & ĐÁP ÁN (2 BƯỚC) ---
            elif mode == "tuy_chon_khong_ma_tran":
                st.write("⏳ Bước 1/2: Đang sinh Đề kiểm tra...")
                sys_inst = "Chuyên gia ra đề. Không sinh đáp án ở bước này. Trả về Markdown."
                prompt_exam = f"Chủ đề: {config['chu_de']}\n{math_prompt}\nDữ liệu: {text_context}\nHãy soạn DUY NHẤT phần nội dung ĐỀ KIỂM TRA."
                res1 = engine.generate_text(prompt=prompt_exam, system_instruction=sys_inst)
                exam_text = res1.text
                
                st.write("⏳ Bước 2/2: Đang sinh Đáp án và Hướng dẫn chấm...")
                sys_inst = "Chuyên gia chấm thi. Không giải thích lảm nhảm. Trả về Markdown."
                prompt_key = f"Dựa vào ĐỀ KIỂM TRA TÔI VỪA SOẠN DƯỚI ĐÂY, hãy lập BẢNG ĐÁP ÁN (Trắc nghiệm) và HƯỚNG DẪN CHẤM (Tự luận chi tiết 0.25đ):\n\n{exam_text}"
                res2 = engine.generate_text(prompt=prompt_key, system_instruction=sys_inst)
                
                final_md_output = f"# I. ĐỀ KIỂM TRA\n\n{exam_text}\n\n# II. ĐÁP ÁN & HƯỚNG DẪN CHẤM\n\n{res2.text}"
                total_latency = res1.latency + res2.latency
                total_tokens_used = res1.total_tokens + res2.total_tokens

            # --- LUỒNG 1 & 2: FULL MA TRẬN + ĐỀ + ĐÁP ÁN (3 BƯỚC) ---
            else:
                st.write("⏳ Bước 1/3: Thiết kế Bảng Ma trận & Bản đặc tả...")
                sys_inst = "Chuyên gia giáo dục. CHỈ SINH BẢNG MARKDOWN Ma trận và Đặc tả. Phân bổ câu hỏi khớp 100% với cấu trúc điểm yêu cầu."
                prompt_matrix = f"Chủ đề: {config['chu_de']}\n{math_prompt}\nDữ liệu: {text_context}\nHãy lập BẢNG MA TRẬN ĐỀ KIỂM TRA và BẢNG ĐẶC TẢ."
                res1 = engine.generate_text(prompt=prompt_matrix, system_instruction=sys_inst)
                matrix_text = res1.text
                
                st.write("⏳ Bước 2/3: Biên soạn Đề kiểm tra bám sát Ma trận...")
                sys_inst = "Chuyên gia ra đề. TUYỆT ĐỐI BÁM SÁT MA TRẬN ĐỂ RA ĐỀ. Không sinh đáp án."
                prompt_exam = f"Sử dụng Tài liệu: {text_context[:5000]}...\nDựa vào MA TRẬN BẠN VỪA LẬP DƯỚI ĐÂY, hãy soạn DUY NHẤT phần ĐỀ KIỂM TRA (Gồm TN và TL):\n\n{matrix_text}"
                res2 = engine.generate_text(prompt=prompt_exam, system_instruction=sys_inst)
                exam_text = res2.text
                
                st.write("⏳ Bước 3/3: Soạn Đáp án & Hướng dẫn chấm...")
                sys_inst = "Chuyên gia chấm thi. Không giải thích lảm nhảm."
                prompt_key = f"Dựa vào ĐỀ KIỂM TRA DƯỚI ĐÂY, hãy lập BẢNG ĐÁP ÁN (Trắc nghiệm) và HƯỚNG DẪN CHẤM (Tự luận chi tiết):\n\n{exam_text}"
                res3 = engine.generate_text(prompt=prompt_key, system_instruction=sys_inst)
                
                final_md_output = f"# I. MA TRẬN VÀ BẢN ĐẶC TẢ\n\n{matrix_text}\n\n# II. ĐỀ KIỂM TRA\n\n{exam_text}\n\n# III. ĐÁP ÁN & HƯỚNG DẪN CHẤM\n\n{res3.text}"
                total_latency = res1.latency + res2.latency + res3.latency
                total_tokens_used = res1.total_tokens + res2.total_tokens + res3.total_tokens

            status.update(label=f"✅ HOÀN TẤT LUỒNG XỬ LÝ (Tổng thời gian: {total_latency:.2f}s | Đã dùng: {total_tokens_used} tokens)", state="complete")
            st.session_state["latest_exam_md"] = final_md_output

    except Exception as e:
        st.error(f"❌ Tiến trình bị đứt gãy: {str(e)}")
        logger.error(f"Lỗi luồng sinh đề: {str(e)}")
        return

    # HIỂN THỊ KẾT QUẢ VÀ NÚT TẢI
    if "latest_exam_md" in st.session_state:
        md_text = st.session_state["latest_exam_md"]
        
        with st.expander("👀 XEM TRƯỚC BẢN THẢO MARKDOWN", expanded=True):
            st.markdown(md_text, unsafe_allow_html=True)
        
        st.divider()
        with st.spinner("Đang render Engine Bảng và Công thức Word..."):
            docx_bytes = WordExportEngine.convert_markdown_to_docx_bytes(md_text)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 TẢI XUỐNG BẢN CHÍNH THỨC FILE WORD (.DOCX)", data=docx_bytes,
                file_name=f"De_Kiem_Tra_Edu_AI.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary", use_container_width=True
            )
        with col2:
            st.button("🗑️ HỦY KẾT QUẢ / TẠO LẠI", on_click=lambda: st.session_state.pop("latest_exam_md", None), type="secondary", use_container_width=True)
