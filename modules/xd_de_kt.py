"""
============================================================
GIAO DIỆN XÂY DỰNG ĐỀ KIỂM TRA (UI LAYER)
============================================================
"""
import streamlit as st
from modules import xd_de_kt_data

def render_exam_config(tab_key: str, mode: str):
    st.markdown("### 1. Thông Tin Cơ Bản")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        mon_hoc = st.selectbox("Môn học", ["Khoa học Tự nhiên", "Toán", "Ngữ Văn", "Tiếng Anh", "Vật lí", "Hóa học", "Sinh học", "Lịch sử và Địa lí", "Tin học", "Giáo dục công dân", "Công nghệ"], key=f"{tab_key}_mon")
    with col2:
        lop = st.selectbox("Khối Lớp", ["6", "7", "8", "9", "10", "11", "12"], index=1, key=f"{tab_key}_lop")
    with col3:
        thoi_gian = st.selectbox("Thời gian làm bài", ["45 phút", "60 phút", "90 phút", "120 phút"], key=f"{tab_key}_time")
    with col4:
        loai_de = st.selectbox("Loại đề", ["Kiểm tra đánh giá giữa kì I", "Kiểm tra đánh giá cuối kì I", "Kiểm tra đánh giá giữa kì II", "Kiểm tra đánh giá cuối kì II", "Kiểm tra khác"], key=f"{tab_key}_loai")

    chu_de = st.text_input("Nhập tên Chủ đề / Nội dung bài kiểm tra:", placeholder="VD: Quang hợp ở thực vật, Lực và Chuyển động...", key=f"{tab_key}_chude")

    if mode == "chi_ma_tran":
        st.markdown("### 2. Tải Lên Đề Kiểm Tra Có Sẵn (BẮT BUỘC)")
        file_upload = st.file_uploader("Tải file Đề kiểm tra (Word, PDF, TXT):", key=f"{tab_key}_file")
        
        if st.button("🚀 PHÂN TÍCH & SINH MA TRẬN", type="primary", key=f"{tab_key}_btn"):
            if not file_upload:
                st.error("❌ BẮT BUỘC PHẢI TẢI LÊN ĐỀ KIỂM TRA trước khi thực hiện!")
            else:
                config = {"mon_hoc": mon_hoc, "lop": lop, "thoi_gian": thoi_gian, "loai_de": loai_de, "chu_de": chu_de}
                xd_de_kt_data.process_request(config, mode, file_upload)
        return

    st.markdown("### 2. Cấu Hình Phần Trắc Nghiệm (TN)")
    t_col1, t_col2, t_col3, t_col4 = st.columns(4)
    
    with t_col1:
        n_nlc = st.number_input("Số câu Nhiều lựa chọn", min_value=0, value=12, step=1, key=f"{tab_key}_n_nlc")
        p_nlc = st.number_input("Điểm / 1 câu NLC", min_value=0.0, value=0.25, step=0.25, key=f"{tab_key}_p_nlc")
    with t_col2:
        n_ds = st.number_input("Số câu Đúng/Sai", min_value=0, value=4, step=1, key=f"{tab_key}_n_ds")
        p_ds = st.number_input("Điểm / 1 câu Đ/S", min_value=0.0, value=0.25, step=0.25, key=f"{tab_key}_p_ds")
    with t_col3:
        n_dk = st.number_input("Số câu Điền khuyết", min_value=0, value=0, step=1, key=f"{tab_key}_n_dk")
        p_dk = st.number_input("Điểm / 1 câu ĐK", min_value=0.0, value=0.25, step=0.25, key=f"{tab_key}_p_dk")
    with t_col4:
        n_ngan = st.number_input("Số câu Trả lời ngắn", min_value=0, value=0, step=1, key=f"{tab_key}_n_ngan")
        p_ngan = st.number_input("Điểm / 1 câu TLN", min_value=0.0, value=0.25, step=0.25, key=f"{tab_key}_p_ngan")

    total_tn = (n_nlc * p_nlc) + (n_ds * p_ds) + (n_dk * p_dk) + (n_ngan * p_ngan)
    st.success(f"**Tổng điểm Trắc nghiệm hiện tại:** {total_tn} điểm")

    st.markdown("### 3. Cấu Hình Phần Tự Luận (TL)")
    total_tl_expected = 10.0 - total_tn
    st.info(f"Hệ thống tự tính: Tổng điểm Tự luận cần đạt là **{total_tl_expected} điểm** (Để tổng đề = 10)")
    
    n_tl = st.number_input("Nhập số câu Tự luận:", min_value=1, max_value=10, value=2, step=1, key=f"{tab_key}_n_tl")
    
    tl_points = []
    tl_cols = st.columns(n_tl)
    for i in range(n_tl):
        with tl_cols[i]:
            default_p = total_tl_expected / n_tl
            p = st.number_input(f"Điểm Câu {i+1}", min_value=0.0, value=float(default_p), step=0.25, key=f"{tab_key}_tl_p_{i}")
            tl_points.append(p)
            
    sum_tl = sum(tl_points)
    if sum_tl != total_tl_expected:
        st.error(f"❌ Tổng điểm các câu tự luận đang là {sum_tl}. Cần điều chỉnh để bằng {total_tl_expected}!")

    st.markdown("### 4. Tỷ Lệ Mức Độ Nhận Thức (%)")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1: nb = st.number_input("Nhận biết (%)", min_value=0, value=40, step=5, key=f"{tab_key}_nb")
    with m_col2: th = st.number_input("Thông hiểu (%)", min_value=0, value=30, step=5, key=f"{tab_key}_th")
    with m_col3: vd = st.number_input("Vận dụng (%)", min_value=0, value=20, step=5, key=f"{tab_key}_vd")
    with m_col4: vdc = st.number_input("Vận dụng cao (%)", min_value=0, value=10, step=5, key=f"{tab_key}_vdc")
    
    sum_muc_do = nb + th + vd + vdc
    if sum_muc_do != 100:
        st.error(f"❌ Tổng tỷ lệ đang là {sum_muc_do}%. Vui lòng điều chỉnh lại cho đúng 100%.")

    # BẮT BUỘC TẢI ĐỀ CƯƠNG CHO TAB 1 & 2
    if mode in ["cv7991", "tuy_chon_co_ma_tran"]:
        st.markdown("### 5. Đính Kèm Đề Cương / Nội Dung (BẮT BUỘC)")
        file_upload = st.file_uploader("Tải file tài liệu để AI bám sát (Word, PDF, Text):", key=f"{tab_key}_file_ref")
    else:
        st.markdown("### 5. Đính Kèm Đề Cương / Sách Giáo Khoa (Tùy chọn)")
        file_upload = st.file_uploader("Tải file tài liệu (Tùy chọn):", key=f"{tab_key}_file_ref")

    st.divider()
    if st.button("🚀 TIẾN HÀNH XÂY DỰNG ĐỀ", type="primary", use_container_width=True, key=f"{tab_key}_btn_submit"):
        # CHỐT CHẶN BẮT BUỘC TẢI ĐỀ CƯƠNG
        if mode in ["cv7991", "tuy_chon_co_ma_tran"] and not file_upload:
            st.error("❌ CHỨC NĂNG NÀY BẮT BUỘC PHẢI TẢI LÊN ĐỀ CƯƠNG HOẶC TÀI LIỆU ÔN TẬP!")
        elif sum_tl != total_tl_expected:
            st.warning("Vui lòng sửa lại điểm các câu Tự luận cho khớp tổng điểm!")
        elif sum_muc_do != 100:
            st.warning("Vui lòng sửa lại Tỷ lệ mức độ cho đủ 100%!")
        else:
            config = {
                "mon_hoc": mon_hoc, "lop": lop, "thoi_gian": thoi_gian, "loai_de": loai_de, "chu_de": chu_de,
                "tn": {"n_nlc": n_nlc, "p_nlc": p_nlc, "n_ds": n_ds, "p_ds": p_ds, "n_dk": n_dk, "p_dk": p_dk, "n_ngan": n_ngan, "p_ngan": p_ngan, "total": total_tn},
                "tl": {"so_cau": n_tl, "diem_chi_tiet": tl_points, "total": sum_tl},
                "muc_do": {"nb": nb, "th": th, "vd": vd, "vdc": vdc}
            }
            xd_de_kt_data.process_request(config, mode, file_upload)

def render_ui():
    st.title("📝 HỆ THỐNG XÂY DỰNG ĐỀ KIỂM TRA CHUYÊN SÂU")
    tab1, tab2, tab3, tab4 = st.tabs(["📖 Đề CV 7991 (Có Ma trận)", "🛠️ Đề Tự do (Có Ma trận)", "⚡ Đề Tự do (Chỉ ra đề)", "🔍 Đọc Đề -> Sinh Ma trận"])
    with tab1: render_exam_config("tab1", "cv7991")
    with tab2: render_exam_config("tab2", "tuy_chon_co_ma_tran")
    with tab3: render_exam_config("tab3", "tuy_chon_khong_ma_tran")
    with tab4: render_exam_config("tab4", "chi_ma_tran")
