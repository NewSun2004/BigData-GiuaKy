import streamlit as st
import pandas as pd
import vaex
import matplotlib.pyplot as plt
from pymongo import MongoClient
import joblib

# =========================
# 0) PAGE CONFIG
# =========================
st.set_page_config(page_title="Phân Tích Vé Máy Bay", layout="wide")
st.title("✈️ Phân Tích Dữ Liệu Hàng Không")

st.markdown("""
**Công nghệ sử dụng:**
- Dữ liệu: **MongoDB Atlas**
- Xử lý Big Data: **Vaex**
- Dashboard + Predict: **Streamlit**
""")

# =========================
# 1) LOAD DATA (Mongo -> Vaex)
# =========================
@st.cache_resource
def load_data_from_mongo():
    uri = "mongodb+srv://chuthihoainu2004_db_user:F8d6qLpOGhd3YLuQ@vpandas.z8hw3tg.mongodb.net/"
    try:
        client = MongoClient(uri)
        db = client["Vpandas"]
        collection = db["Fight_data"]

        data = list(collection.find({}))
        if not data:
            return None

        pdf = pd.DataFrame(data)
        if "_id" in pdf.columns:
            pdf.drop(columns=["_id"], inplace=True)

        return vaex.from_pandas(pdf)

    except Exception as e:
        st.error(f"Lỗi kết nối MongoDB: {e}")
        return None

# =========================
# 2) LOAD MODEL + MAPPING (Predict)
# =========================
@st.cache_resource
def load_model_and_mapping():
    model = joblib.load("lgbm_model.pkl")
    mapping = joblib.load("label_mapping.pkl")

    # ép mapping[col] về list
    for k, v in mapping.items():
        if not isinstance(v, list):
            mapping[k] = list(v)

    return model, mapping

def encode_with_mapping(mapping: dict, col: str, value: str) -> int:
    cats = mapping.get(col, [])
    if value not in cats:
        raise ValueError(f"'{value}' không có trong mapping của {col}.")
    return cats.index(value)

# model train với 4 feature: Column_0..3
MODEL_FEATURES = ["Column_0", "Column_1", "Column_2", "Column_3"]
INPUT_COLS = ["Airline", "Source", "Destination", "Total_Stops"]

# =========================
# 3) TABS
# =========================
tab_dash, tab_pred = st.tabs(["📊 Dashboard", "🔮 Dự đoán giá vé"])

# =========================
# TAB 1: DASHBOARD
# =========================
with tab_dash:
    st.subheader("📊 Dashboard Phân Tích Dữ Liệu")

    with st.spinner("Đang kết nối MongoDB và xử lý bằng Vaex..."):
        vdf = load_data_from_mongo()

    if vdf is None:
        st.warning("Không lấy được dữ liệu. Hãy kiểm tra lại IP Access List trên MongoDB Atlas!")
        st.stop()

    # Sidebar filter (chỉ dùng cho dashboard)
    st.sidebar.header("🔍 Bộ Lọc (Dashboard)")

    airline_list = vdf.unique("Airline")
    default_list = airline_list[:2] if len(airline_list) >= 2 else airline_list

    selected_airlines = st.sidebar.multiselect(
        "Chọn Hãng Hàng Không",
        options=airline_list,
        default=default_list
    )

    if selected_airlines:
        df_view = vdf[vdf.Airline.isin(selected_airlines)]
    else:
        df_view = vdf

    # KPI
    st.divider()
    col1, col2, col3 = st.columns(3)

    total_flights = len(df_view)
    avg_price = df_view.Price.mean() if "Price" in df_view.get_column_names() else None
    max_price = df_view.Price.max() if "Price" in df_view.get_column_names() else None

    col1.metric("Tổng chuyến bay", f"{total_flights:,}")
    col2.metric("Giá vé trung bình", f"{avg_price:,.0f} INR" if avg_price is not None else "N/A")
    col3.metric("Giá vé cao nhất", f"{max_price:,.0f} INR" if max_price is not None else "N/A")

    st.divider()

    # Charts
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📊 Giá trung bình theo Hãng")
        if "Price" in df_view.get_column_names():
            stats = df_view.groupby(by="Airline", agg={"Gia_TB": vaex.agg.mean("Price")})
            chart_data = stats.to_pandas_df().sort_values("Gia_TB")
            st.bar_chart(chart_data, x="Airline", y="Gia_TB")
        else:
            st.info("Dataset không có cột Price để tính giá trung bình.")

    with c2:
        st.subheader("📉 Phân phối Giá vé")
        if "Price" in df_view.get_column_names():
            prices = df_view.Price.tolist()
            fig, ax = plt.subplots()
            ax.hist(prices, bins=20, edgecolor="black")
            ax.set_title("Phổ giá vé")
            st.pyplot(fig)
        else:
            st.info("Dataset không có cột Price để vẽ histogram.")

    # Table
    with st.expander("Xem bảng dữ liệu chi tiết"):
        st.dataframe(df_view.head(50).to_pandas_df(), use_container_width=True)

# =========================
# TAB 2: PREDICT
# =========================
with tab_pred:
    st.subheader("🔮 Dự đoán giá vé (LightGBM)")

    st.info("Model hiện tại train với **4 features**: Airline, Source, Destination, Total_Stops.")

    try:
        model, mapping = load_model_and_mapping()
    except Exception as e:
        st.error(f"Không load được model/mapping: {e}")
        st.stop()

    # check mapping keys
    missing_keys = [k for k in INPUT_COLS if k not in mapping]
    if missing_keys:
        st.error(f"Thiếu mapping cho các cột: {missing_keys}. Kiểm tra label_mapping.pkl")
        st.stop()

    with st.form("predict_form"):
        a1, a2 = st.columns(2)

        with a1:
            airline = st.selectbox("Hãng bay (Airline)", options=mapping["Airline"])
            source = st.selectbox("Nơi đi (Source)", options=mapping["Source"])

        with a2:
            destination = st.selectbox("Nơi đến (Destination)", options=mapping["Destination"])
            total_stops = st.selectbox("Số điểm dừng (Total_Stops)", options=mapping["Total_Stops"])

        submit = st.form_submit_button("🚀 Dự đoán")

    if submit:
        try:
            x0 = encode_with_mapping(mapping, "Airline", airline)
            x1 = encode_with_mapping(mapping, "Source", source)
            x2 = encode_with_mapping(mapping, "Destination", destination)
            x3 = encode_with_mapping(mapping, "Total_Stops", total_stops)

            X = pd.DataFrame([[x0, x1, x2, x3]], columns=MODEL_FEATURES)
            pred = float(model.predict(X)[0])

            st.success(f"✅ Giá vé dự đoán: **{pred:,.0f} INR**")

            with st.expander("Xem input đã encode"):
                show_df = pd.DataFrame({
                    "Input": INPUT_COLS,
                    "Giá trị chọn": [airline, source, destination, total_stops],
                    "Mã số (encode)": [x0, x1, x2, x3],
                    "Tên cột model": MODEL_FEATURES
                })
                st.dataframe(show_df, use_container_width=True)

        except Exception as e:
            st.error(f"❌ Lỗi dự đoán: {e}")
