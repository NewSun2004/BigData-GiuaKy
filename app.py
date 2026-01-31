import streamlit as st
import pandas as pd
import vaex
import matplotlib.pyplot as plt
from pymongo import MongoClient

# --- 1. CẤU HÌNH GIAO DIỆN WEB ---
st.set_page_config(page_title="Phân Tích Vé Máy Bay", layout="wide")
st.title("✈️ Dashboard Phân Tích Dữ Liệu Hàng Không")
st.markdown("""
**Công nghệ sử dụng:**
- Dữ liệu: **MongoDB Atlas**
- Xử lý Big Data: **Vaex**
- Giao diện: **Streamlit**
""")

# --- 2. HÀM KẾT NỐI VÀ LẤY DỮ LIỆU ---
# Dùng @st.cache để dữ liệu chỉ tải 1 lần, giúp web chạy nhanh
@st.cache_resource
def load_data_from_mongo():
    # Chuỗi kết nối của bạn
    uri = "mongodb+srv://chuthihoainu2004_db_user:F8d6qLpOGhd3YLuQ@vpandas.z8hw3tg.mongodb.net/"

    try:
        client = MongoClient(uri)
        db = client["Vpandas"]
        collection = db["Fight_data"]

        # Lấy dữ liệu về
        data = list(collection.find({}))

        if not data:
            return None

        # Chuyển List -> Pandas -> Vaex
        pdf = pd.DataFrame(data)

        # Xóa cột _id của Mongo (vì Vaex không đọc được kiểu object này)
        if '_id' in pdf.columns:
            pdf.drop(columns=['_id'], inplace=True)

        # Chuyển sang Vaex DataFrame (Đây là yêu cầu cốt lõi của đề bài)
        vdf = vaex.from_pandas(pdf)
        return vdf

    except Exception as e:
        st.error(f"Lỗi kết nối: {e}")
        return None

# --- 3. XỬ LÝ CHÍNH ---
with st.spinner('Đang kết nối MongoDB và xử lý bằng Vaex...'):
    vdf = load_data_from_mongo()

if vdf is not None:
    # --- Sidebar: Bộ lọc dữ liệu ---
    st.sidebar.header("🔍 Bộ Lọc")

    # Lấy danh sách hãng bay (Vaex unique)
    airline_list = vdf.unique('Airline')
    selected_airlines = st.sidebar.multiselect(
        "Chọn Hãng Hàng Không",
        options=airline_list,
        default=airline_list[:2] # Mặc định chọn 2 hãng đầu
    )

    # Lọc dữ liệu bằng Vaex
    if selected_airlines:
        # Cú pháp lọc của Vaex
        df_view = vdf[vdf.Airline.isin(selected_airlines)]
    else:
        df_view = vdf

    # --- Hiển thị KPI (Chỉ số) ---
    st.divider()
    col1, col2, col3 = st.columns(3)

    # Tính toán thống kê bằng Vaex
    total_flights = len(df_view)
    avg_price = df_view.Price.mean()
    max_price = df_view.Price.max()

    col1.metric("Tổng chuyến bay", f"{total_flights:,}")
    col2.metric("Giá vé trung bình", f"{avg_price:,.0f} INR")
    col3.metric("Giá vé cao nhất", f"{max_price:,.0f} INR")

    st.divider()

    # --- Vẽ Biểu Đồ ---
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📊 Giá trung bình theo Hãng")
        # Sử dụng Vaex GroupBy (Yêu cầu đề bài phân tích)
        stats = df_view.groupby(by='Airline', agg={'Gia_TB': vaex.agg.mean('Price')})
        # Chuyển kết quả group nhỏ xíu này sang Pandas để vẽ chart
        chart_data = stats.to_pandas_df().sort_values('Gia_TB')
        st.bar_chart(chart_data, x='Airline', y='Gia_TB', color='#FF4B4B')

    with c2:
        st.subheader("📉 Phân phối Giá vé")
        # Lấy dữ liệu cột Price ra vẽ Histogram
        prices = df_view.Price.tolist()
        fig, ax = plt.subplots()
        ax.hist(prices, bins=20, color='skyblue', edgecolor='black')
        ax.set_title("Phổ giá vé")
        st.pyplot(fig)

    # --- Hiển thị dữ liệu chi tiết ---
    with st.expander("Xem bảng dữ liệu chi tiết"):
        # Hiển thị 50 dòng đầu tiên
        st.dataframe(df_view.head(50).to_pandas_df())

else:
    st.warning("Không lấy được dữ liệu. Hãy kiểm tra lại IP Access List trên MongoDB Atlas!")
