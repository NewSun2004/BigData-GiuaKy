import streamlit as st
import vaex
import numpy as np

st.title("🚀 Vaex + Streamlit Compatibility Test")

st.write("Checking environment...")

# Display Versions
st.info(f"Vaex Version: {vaex.__version__}")
st.info(f"NumPy Version: {np.__version__}")

try:
    # 1. Create a dummy dataset in-memory
    # Vaex excels at handling millions of rows, but we'll use 10k for a quick test
    n_rows = 10000
    x = np.random.normal(size=n_rows)
    y = x * 0.5 + np.random.normal(size=n_rows)
    
    df = vaex.from_arrays(x=x, y=y)
    
    st.success("✅ Vaex DataFrame created successfully!")

    # 2. Perform a lazy virtual calculation
    df['z'] = df.x + df.y
    mean_z = df.z.mean()

    # 3. Display Results
    st.subheader("Statistical Summary")
    col1, col2 = st.columns(2)
    col1.metric("Row Count", f"{len(df):,}")
    col2.metric("Mean of Virtual Col (z)", f"{mean_z:.4f}")

    st.write("Preview of the Data (First 5 rows):")
    st.table(df.head(5).to_pandas_df())

except Exception as e:
    st.error(f"❌ An error occurred: {e}")
    st.warning("Hint: Check if your Python version is 3.10 or 3.11 in the Streamlit Cloud settings.")
