"""
============================================================
GIAO DIỆN XÂY DỰNG ĐỀ KIỂM TRA (UI LAYER)
============================================================
"""
import os
import math
import streamlit as st
from modules import xd_de_kt_data

def get_template_list():
    """Tự động quét và lấy danh sách file .docx từ thư mục templates/"""
    templates_dir = "templates"
    if os.path.exists(templates_dir):
        # Bỏ qua các file rác sinh ra khi đang mở Word (bắt đầu bằng ~)
        return [f for f in os.listdir(templates_dir) if f.endswith(".docx") and not f.startswith("~")]
    return []

def render_basic_info(tab_key: str) -> dict:
    st.markdown("### 1. Thông Tin Cơ Bản")
    col1, col2, col3, col4 = st.columns(4)
    with col1: mon = st.selectbox("Môn học", ["Khoa học Tự nhiên", "Toán", "Ngữ Văn", "Tiếng Anh", "Vật lí", "Hóa học", "Sinh học", "Lịch sử và Địa lí", "Tin học", "Giáo dục công dân", "Công nghệ"], key=f"{tab_key}_mon")
    with col2: lop = st.selectbox("Khối Lớp", ["6", "7", "8", "9", "10", "11", "12"], index=1, key=f"{tab_key}_lop")
    with col3: thoi_gian = st.selectbox("Thời gian làm bài", ["45 phút", "60 phút", "90 phút", "120 phút"], key=f"{tab_key}_time")
    with col4: loai_de = st.selectbox("Loại đề", ["Kiểm tra đánh giá giữa kì I", "Kiểm tra đánh giá cuối kì I", "Kiểm tra đánh giá giữa kì II", "Kiểm tra đánh giá cuối kì II", "Kiểm tra thường xuyên"], key=f"{tab_key}_loai")
    chu_de = st.text_input("Nhập Chủ đề / Nội dung:", key=f"{tab_key}_chude")
    return {"mon_hoc": mon, "lop": lop, "thoi_gian": thoi_gian, "loai_de": loai_de, "chu_de": chu_de}

def render_exam_tab(tab_key: str, mode: str):
    basic_info = render_basic_info(tab_key)
    templates = get_template_list()

    if mode == "chi_ma_tran":
        st.markdown("### 2. Chọn Mẫu & Tải Lên Đề Kiểm Tra")
        col_a, col_b = st.columns(2)
        with col_a:
            selected_tpl = st.selectbox("1. Chọn File MẪU (.docx) từ hệ thống:", templates, key=f"{tab_key}_tpl")
            template_path = os.path.join("templates", selected_tpl) if selected_tpl else None
        with col_b:
            uploaded_files = st.file_uploader("2. Tải file Đề (Word, PDF, TXT):", accept_multiple_files=True, key=f"{tab_key}_file")
            
        if st.button("🚀 PHÂN TÍCH & SINH MA TRẬN", type="primary", key=f"{tab_key}_btn"):
            if not uploaded_files: st.error("❌ BẮT BUỘC PHẢI TẢI LÊN ĐỀ KIỂM TRA!")
            elif not template_path: st.error("❌ CHƯA CÓ FILE MẪU TRONG THƯ MỤC TEMPLATES!")
            else: xd_de_kt_data.process_request(basic_info, mode, uploaded_files, template_path)
        return

    st.markdown("### 2. Cấu Hình Phần Trắc Nghiệm (TN)")
    t_col1, t_col2, t_col3, t_col4 = st.columns(4)
    with t_col1:
        n_nlc = st.number_input("Số câu NLC", min_value=0, value=12, key=f"{tab_key}_n_nlc")
        p_nlc = st.number_input("Điểm/câu NLC", min_value=0.0, value=0.25, step=0.25, key=f"{tab_key}_p_nlc")
    with t_col2:
        n_ds = st.number_input("Số câu Đ/S", min_value=0, value=4, key=f"{tab_key}_n_ds")
        p_ds = st.number_input("Điểm/câu Đ/S", min_value=0.0, value=0.25, step=0.25, key=f"{tab_key}_p_ds")
    with t_col3:
        n_dk = st.number_input("Số câu Điền khuyết", min_value=0, value=0, key=f"{tab_key}_n_dk")
        p_dk = st.number_input("Điểm/câu ĐK", min_value=0.0, value=0.25, step=0.25, key=f"{tab_key}_p_dk")
    with t_col4:
        n_ngan = st.number_input("Số câu TL Ngắn", min_value=0, value=0, key=f"{tab_key}_n_ngan")
        p_ngan = st.number_input("Điểm/câu TLN", min_value=0.0, value=0.25, step=0.25, key=f"{tab_key}_p_ngan")

    total_tn = (n_nlc * p_nlc) + (n_ds * p_ds) + (n_dk * p_dk) + (n_ngan * p_ngan)
    st.success(f"**Tổng điểm Trắc nghiệm hiện tại:** {total_tn:.2f} điểm")

    if total_tn > 10.0:
        st.error("❌ ĐIỂM LỖI: Điểm Trắc nghiệm vượt quá 10. Hãy giảm số câu/điểm.")
        return

    st.markdown("### 3. Cấu Hình Phần Tự Luận (TL)")
    total_tl_expected = 10.0 - total_tn
    n_tl = st.number_input("Số câu Tự luận:", min_value=0, max_value=10, value=2 if total_tl_expected > 0 else 0, key=f"{tab_key}_n_tl")
    tl_points = []
    if n_tl > 0:
        tl_cols = st.columns(n_tl)
        for i in range(n_tl):
            with tl_cols[i]:
                p = st.number_input(f"Điểm Câu {i+1}", min_value=0.0, value=float(max(0.0, total_tl_expected/n_tl)), step=0.25, key=f"{tab_key}_tl_p_{i}")
                tl_points.append(p)
    sum_tl = sum(tl_points)

    st.markdown("### 4. Tỷ Lệ Mức Độ Nhận Thức (%)")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1: nb = st.number_input("Nhận biết", min_value=0, value=40, key=f"{tab_key}_nb")
    with m_col2: th = st.number_input("Thông hiểu", min_value=0, value=30, key=f"{tab_key}_th")
    with m_col3: vd = st.number_input("Vận dụng", min_value=0, value=20, key=f"{tab_key}_vd")
    with m_col4: vdc = st.number_input("Vận dụng cao", min_value=0, value=10, key=f"{tab_key}_vdc")

    st.markdown("### 5. Chọn Mẫu & Tải Lên Đề Cương")
    col_a, col_b = st.columns(2)
    with col_a:
        # Logic ưu tiên file "ma_tran_de_kt.docx"
        default_idx = 0
        for i, t in enumerate(templates):
            if "ma_tran" in t.lower():
                default_idx = i
                break
        selected_tpl = st.selectbox("1. Chọn File MẪU (.docx) từ hệ thống:", templates, index=default_idx if templates else 0, key=f"{tab_key}_tpl")
        template_path = os.path.join("templates", selected_tpl) if selected_tpl else None
        st.caption("Danh sách này tự động tải từ thư mục `templates/`")
        
    with col_b:
        uploaded_files = st.file_uploader("2. Tải lên Đề Cương / SGK:", accept_multiple_files=True, key=f"{tab_key}_file_ref")

    st.divider()
    if st.button("🚀 TIẾN HÀNH XÂY DỰNG ĐỀ", type="primary", use_container_width=True, key=f"{tab_key}_btn_submit"):
        if mode in ["cv7991", "tuy_chon_co_ma_tran"] and not uploaded_files:
            st.error("❌ BẮT BUỘC TẢI LÊN ĐỀ CƯƠNG HOẶC TÀI LIỆU NỀN TẢNG!")
            return
        if not template_path:
            st.error("❌ LỖI HỆ THỐNG: KHÔNG TÌM THẤY FILE MẪU NÀO TRONG THƯ MỤC 'templates/'!")
            return
        if not math.isclose(sum_tl, total_tl_expected, abs_tol=0.001):
            st.error("❌ Điểm Tự luận bị sai so với tổng Trắc nghiệm!")
            return

        config = {
            **basic_info,
            "tn": {"n_nlc": n_nlc, "p_nlc": p_nlc, "n_ds": n_ds, "p_ds": p_ds, "n_dk": n_dk, "p_dk": p_dk, "n_ngan": n_ngan, "p_ngan": p_ngan, "total": total_tn},
            "tl": {"so_cau": n_tl, "diem_chi_tiet": tl_points, "total": sum_tl},
            "muc_do": {"nb": nb, "th": th, "vd": vd, "vdc": vdc}
        }
        xd_de_kt_data.process_request(config, mode, uploaded_files, template_path)

def render_ui():
    st.title("📝 HỆ THỐNG XÂY DỰNG ĐỀ KIỂM TRA CHUYÊN SÂU")
    tab1, tab2, tab3, tab4 = st.tabs(["📖 Đề CV 7991 (Có Ma trận)", "🛠️ Đề Tự do (Có Ma trận)", "⚡ Đề Tự do (Chỉ ra đề)", "🔍 Đọc Đề -> Sinh Ma trận"])
    with tab1: render_exam_tab("tab1", "cv7991")
    with tab2: render_exam_tab("tab2", "tuy_chon_co_ma_tran")
    with tab3: render_exam_tab("tab3", "tuy_chon_khong_ma_tran")
    with tab4: render_exam_tab("tab4", "chi_ma_tran")
