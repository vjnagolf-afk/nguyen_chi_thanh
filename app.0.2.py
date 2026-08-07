import streamlit as st
import os

# Thiết lập cấu hình trang
st.set_page_config(
    page_title="AI - THCS Nguyễn Chí Thanh",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # Thanh điều hướng (Sidebar)
    st.sidebar.title("🏫 Hệ thống AI")
    st.sidebar.markdown("**THCS Nguyễn Chí Thanh**")
    
    menu = ["Tổng quan", "Xây dựng Đề kiểm tra", "Xây dựng KHBD", "Xuất bản tài liệu"]
    choice = st.sidebar.selectbox("Danh mục chức năng", menu)

    # Xử lý hiển thị theo menu
    if choice == "Tổng quan":
        show_home()
    elif choice == "Xây dựng Đề kiểm tra":
        st.title("📝 Hệ thống Prompt: Xây dựng Đề kiểm tra")
        st.info("Module sinh đề kiểm tra sẽ được tích hợp tại đây (gọi từ thư mục modules/).")
    elif choice == "Xây dựng KHBD":
        st.title("📚 Hệ thống Prompt: Xây dựng KHBD")
        st.info("Module sinh Kế hoạch bài dạy sẽ được tích hợp tại đây (gọi từ thư mục modules/).")
    elif choice == "Xuất bản tài liệu":
        st.title("🖨️ Quy chuẩn xuất bản Word")
        st.info("Module xử lý python-docx xuất file vào thư mục exports/ sẽ được tích hợp tại đây.")

def show_home():
    st.title("Trang chủ quản lý dự án")
    st.write("Chào mừng bạn đến với hệ thống tự động hóa nghiệp vụ giáo dục của trường THCS Nguyễn Chí Thanh.")
    
    st.subheader("Trạng thái hệ thống thư mục")
    
    # Kiểm tra tự động các thư mục
    directories = ["docs", "modules", "utils", "templates", "exports", "data"]
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Cấu trúc yêu cầu:**")
        for directory in directories:
            st.write(f"- `/{directory}/`")
            
    with col2:
        st.write("**Trạng thái thực tế:**")
        for directory in directories:
            if os.path.exists(directory):
                st.success(f"✅ Đã tìm thấy `/{directory}/`")
            else:
                st.error(f"❌ Thiếu `/{directory}/` - Vui lòng tạo thư mục này.")

if __name__ == '__main__':
    # Đảm bảo tạo thư mục tự động nếu chạy cục bộ
    for folder in ["docs", "modules", "utils", "templates", "exports", "data"]:
        os.makedirs(folder, exist_ok=True)
    main()
