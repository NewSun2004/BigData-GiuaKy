import pandas as pd
from pymongo import MongoClient
import streamlit as st
import vaex
import matplotlib.pyplot as plt

# 1. Connect
connection_string = "mongodb+srv://chuthihoainu2004_db_user:F8d6qLpOGhd3YLuQ@vpandas.z8hw3tg.mongodb.net/"

try:
    # 2. Kết nối
    client = MongoClient(connection_string)

    # 3. Trỏ đúng vào Database và Collection
    db = client["Vpandas"]
    collection = db["Fight_data"]

    # 4. Lấy toàn bộ dữ liệu về (hàm .find({}))
    # Ta chuyển kết quả thành một danh sách (list)
    data_from_atlas = list(collection.find({}))

    # 5. Chuyển thành DataFrame để xem và xử lý
    if len(data_from_atlas) > 0:
        df_new = pd.DataFrame(data_from_atlas)

        if '_id' in df_new.columns:
            df_new = df_new.drop(columns=['_id'])

        print(f"✅ Đã lấy thành công {len(df_new)} dòng dữ liệu từ Atlas về!")
        print("--- 5 dòng đầu tiên của dữ liệu ---")
        print(df_new.head())
    else:
        print("⚠️ Collection 'Fight_data' hiện đang trống, hãy kiểm tra lại bước đẩy data.")

except Exception as e:
    print(f"❌ Có lỗi xảy ra khi lấy dữ liệu: {e}")

# Giả sử bạn đã có df_new từ bước lấy dữ liệu trước đó
# Chuyển đổi từ Pandas sang Vaex DataFrame
vdf = vaex.from_pandas(df_new)

print("--- PHÂN TÍCH VÉ MÁY BAY VỚI VAEX ---")

# 1. Thống kê nhanh các cột số (như Price)
# Vaex tính toán các giá trị thống kê cực nhanh
print(vdf.describe())

# 2. Tạo cột ảo: Giả sử bạn muốn xem giá vé sau thuế (ví dụ 10%)
# Cột ảo này không tốn RAM, chỉ tính khi cần hiển thị
vdf['Price_with_Tax'] = vdf.Price * 1.1
print("\n✅ Đã tạo cột ảo 'Price_with_Tax'")

# 3. Phân tích giá vé trung bình theo từng hãng hàng không (Airline)
# Đây là thao tác GroupBy mạnh mẽ của Vaex
alpine_stats = vdf.groupby(by='Airline', agg={'Average_Price': vaex.agg.mean('Price')})
alpine_stats = alpine_stats.sort('Average_Price', ascending=False)
print("\n--- Giá vé trung bình theo hãng hàng không ---")
print(alpine_stats)

# 4. Tìm các chuyến bay có thời gian bay (Duration) lâu nhất
# Lưu ý: Vaex hỗ trợ lọc (filter) mà không tạo bản sao dữ liệu
long_flights = vdf[vdf.Duration.str.contains('h')] # Lọc các chuyến có tiếng (hours)
print(f"\nSố lượng chuyến bay dài: {len(long_flights)}")

# 5. Vẽ biểu đồ phân phối giá vé
plt.figure(figsize=(12, 6))
vdf.viz.histogram(vdf.Price, xlabel='Giá (Rupee)', color='skyblue')
plt.title('Phân phối giá vé máy bay') # Đặt tiêu đề riêng biệt
plt.show()

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
