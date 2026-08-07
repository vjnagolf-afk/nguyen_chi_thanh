import streamlit as st

def render_ui():
    st.title("📝 Xây Dựng Đề Kiểm Tra & Ma Trận Đặc Tả")
    st.markdown("Hệ thống tự động sinh Ma trận, Bản đặc tả và Đề kiểm tra bám sát chương trình GDPT 2018.")

    # 1. THÔNG TIN CHUNG
    with st.expander("1. THÔNG TIN ĐỀ KIỂM TRA", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            mon_hoc = st.selectbox("Môn học", ["Toán", "Ngữ Văn", "Tiếng Anh", "Khoa học Tự nhiên", "Vật lí", "Hóa học", "Sinh học", "Lịch sử & Địa lí"])
        with col2:
            lop = st.selectbox("Lớp", ["6", "7", "8", "9", "10", "11", "12"])
        with col3:
            ten_de = st.text_input("Tên bài / Chủ đề kiểm tra", placeholder="VD: Khúc xạ ánh sáng")

    # 2. CẤU HÌNH CÂU HỎI & ĐIỂM SỐ
    with st.expander("2. CẤU HÌNH SỐ LƯỢNG & ĐIỂM SỐ", expanded=True):
        st.markdown("**Phần Trắc nghiệm (TN)**")
        t_col1, t_col2, t_col3, t_col4 = st.columns(4)
        with t_col1:
            n_nlc = st.number_input("Số câu Nhiều lựa chọn", min_value=0, value=12, step=1)
        with t_col2:
            n_ds = st.number_input("Số câu Đúng/Sai", min_value=0, value=4, step=1)
        with t_col3:
            n_dk = st.number_input("Số câu Điền khuyết", min_value=0, value=0, step=1)
        with t_col4:
            n_ngan = st.number_input("Số câu Trả lời ngắn", min_value=0, value=0, step=1)
        
        total_diem_tn = st.number_input("Tổng điểm Trắc nghiệm", min_value=0.0, max_value=10.0, value=7.0, step=0.5)
        
        st.divider()
        st.markdown("**Phần Tự luận (TL)**")
        tl_col1, tl_col2 = st.columns(2)
        with tl_col1:
            num_tl = st.number_input("Số câu Tự luận", min_value=0, value=2, step=1)
        with tl_col2:
            total_diem_tl = st.number_input("Tổng điểm Tự luận", min_value=0.0, max_value=10.0, value=3.0, step=0.5)

        tong_diem = total_diem_tn + total_diem_tl
        if tong_diem != 10.0:
            st.warning(f"⚠️ Tổng điểm hiện tại là {tong_diem}. Khuyến nghị tổng điểm nên là 10.0")

    # 3. CẤU HÌNH MỨC ĐỘ NHẬN THỨC
    with st.expander("3. MỨC ĐỘ NHẬN THỨC (%)", expanded=True):
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            nb = st.number_input("Nhận biết (%)", min_value=0, max_value=100, value=40, step=5)
        with m_col2:
            th = st.number_input("Thông hiểu (%)", min_value=0, max_value=100, value=30, step=5)
        with m_col3:
            vd = st.number_input("Vận dụng (%)", min_value=0, max_value=100, value=20, step=5)
        with m_col4:
            vdc = st.number_input("Vận dụng cao (%)", min_value=0, max_value=100, value=10, step=5)
        
        tong_muc_do = nb + th + vd + vdc
        if tong_muc_do != 100:
            st.error(f"❌ Tổng tỷ lệ mức độ đang là {tong_muc_do}%. Vui lòng điều chỉnh lại cho đúng 100%.")

    # 4. TÀI LIỆU ĐÍNH KÈM
    with st.expander("4. TÀI LIỆU THAM KHẢO (Tùy chọn)"):
        st.markdown("Hệ thống sẽ bám sát CT GDPT 2018. Nếu có tài liệu cụ thể, nội dung bài kiểm tra sẽ được giới hạn trong tài liệu này.")
        file_context = st.text_area("Dán nội dung tài liệu tham khảo vào đây:", height=150, placeholder="Dán nội dung văn bản, bài đọc, hoặc trích đoạn SGK...")

    st.divider()

    # NÚT KHỞI TẠO
    if st.button("🚀 Xây Dựng Đề Kiểm Tra", type="primary", use_container_width=True):
        if tong_muc_do == 100:
            st.success("Cấu hình hợp lệ! Đang chuẩn bị chuyển dữ liệu tới AI Engine...")
            
            # --- TÍCH HỢP PROMPT BÊN DƯỚI ---
            # Đây là nơi hệ thống sẽ format prompt của bạn với các biến vừa nhập
            system_prompt = f"""
            THÔNG TIN ĐỀ KIỂM TRA
            Môn học: {mon_hoc}
            Lớp: {lop}
            Tên bài: {ten_de}
            ========================
            CẤU HÌNH
            Trắc nghiệm
            - NLC: {n_nlc} câu
            - Đúng Sai: {n_ds} câu
            - Điền khuyết: {n_dk} câu
            - TL ngắn: {n_ngan} câu
            Tổng điểm TN: {total_diem_tn}
            ------------------------
            Tự luận
            Số câu: {num_tl}
            Tổng điểm: {total_diem_tl}
            ------------------------
            MỨC ĐỘ
            Nhận biết: {nb} %
            Thông hiểu: {th} %
            Vận dụng: {vd} %
            Vận dụng cao: {vdc} %
            ========================
            TÀI LIỆU
            {file_context if file_context else "Không có tài liệu, sử dụng CT GDPT 2018."}
            ========================
            HÃY TRẢ VỀ ĐÚNG CẤU TRÚC SAU
            # I. MA TRẬN ĐỀ KIỂM TRA
            (Bảng Markdown)
            # II. BẢN ĐẶC TẢ
            (Bảng Markdown)
            # III. ĐỀ KIỂM TRA
            Đầy đủ câu hỏi.
            # IV. ĐÁP ÁN
            # V. HƯỚNG DẪN CHẤM
            """
            
            with st.expander("🔍 Xem trước Prompt gửi tới AI (Dành cho Tester)"):
                st.code(system_prompt, language="markdown")
                
            st.info("Luồng tiếp theo: Gửi prompt này vào `st.session_state['ai_engine']`, nhận kết quả Markdown, và đẩy vào `WordExportEngine` để xuất file!")
        else:
            st.warning("Vui lòng đảm bảo Tổng mức độ nhận thức là 100% trước khi tạo đề.")

if __name__ == "__main__":
    render_ui()
