import streamlit as st
import json
import os

# Giả lập import các engine (bạn sẽ tạo các file này sau)
# from modules.exam_engine.matrix_builder import generate_matrix
# from modules.exam_engine.blueprint_builder import generate_blueprint

def load_curriculum():
    # Tạm thời trả về dữ liệu mẫu, sau này sẽ đọc từ database/curriculum.json
    return {
        "Khoa học Tự nhiên 7": ["Chủ đề 1: Nguyên tử - Nguyên tố hóa học", "Chủ đề 2: Phân tử - Liên kết hóa học"],
        "Toán 7": ["Chương 1: Số hữu tỉ", "Chương 2: Số thực"]
    }

def render_exam_builder_ui():
    st.header("🛠️ Xây Dựng Đề Kiểm Tra & Ma Trận Đặc Tả")
    st.markdown("Cấu hình các thông số để hệ thống tự động sinh ma trận, bản đặc tả và đề kiểm tra.")

    # Phần 1: Cấu hình chung
    with st.expander("1. Cấu hình cơ bản", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            subject = st.selectbox("Chọn môn học", ["Khoa học Tự nhiên 7", "Toán 7"])
        with col2:
            time_limit = st.number_input("Thời gian làm bài (phút)", min_value=15, max_value=120, value=45, step=15)
            
        curriculum_data = load_curriculum()
        topics = st.multiselect("Chọn các chủ đề/chương đưa vào đề kiểm tra:", curriculum_data[subject])

    # Phần 2: Cấu hình Ma trận (Tỷ lệ nhận thức)
    with st.expander("2. Cấu hình Ma trận (Tỷ lệ %)", expanded=True):
        st.info("Tổng tỷ lệ phải đúng bằng 100%")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            nb = st.number_input("Nhận biết (%)", min_value=0, max_value=100, value=40, step=5)
        with c2:
            th = st.number_input("Thông hiểu (%)", min_value=0, max_value=100, value=30, step=5)
        with c3:
            vd = st.number_input("Vận dụng (%)", min_value=0, max_value=100, value=20, step=5)
        with c4:
            vdc = st.number_input("Vận dụng cao (%)", min_value=0, max_value=100, value=10, step=5)
            
        total_percent = nb + th + vd + vdc
        if total_percent != 100:
            st.error(f"Tổng tỷ lệ hiện tại là {total_percent}%. Vui lòng điều chỉnh lại cho đủ 100%.")

    # Phần 3: Tạo Đề
    st.divider()
    if st.button("🚀 Khởi tạo Ma trận & Đề kiểm tra", type="primary", use_container_width=True):
        if total_percent == 100 and len(topics) > 0:
            with st.spinner("Hệ thống đang phân tích chương trình và sinh cấu trúc..."):
                # Nơi gọi các hàm từ exam_engine
                # matrix = generate_matrix(subject, topics, nb, th, vd, vdc)
                # blueprint = generate_blueprint(matrix)
                
                st.success("Tạo thành công! Dưới đây là kết quả mô phỏng:")
                st.write("**Các tệp chuẩn bị được tạo:** `MA_TRAN_DE_KT.docx`, `DAC_TA_DE_KT.docx`, `DE_KIEM_TRA.docx`")
        else:
            st.warning("Vui lòng kiểm tra lại cấu hình Chủ đề và Tỷ lệ ma trận.")

# Để test trực tiếp file này trên Streamlit:
if __name__ == "__main__":
    render_exam_builder_ui()
