import streamlit as st
import pandas as pd
from PIL import Image

# Konfigurasi Halaman
st.set_page_config(page_title="Cattle Feed Optimizer", layout="wide")

st.title("🐄 LALITA-Feed: Smart Cattle Nutrition Web App")
st.markdown("---")

# --- SIDEBAR: INPUT DATA ---
st.sidebar.header("Input Data Sapi")
uploaded_file = st.sidebar.file_uploader("Unggah Foto Sapi", type=['jpg', 'png', 'jpeg'])
breed = st.sidebar.selectbox("Jenis Sapi", ["Sapi Bali", "Brahman Cross (BX)", "Limousin", "Simental", "PO (Peranakan Ongole)"])
weight = st.sidebar.number_input("Berat Sapi (kg)", min_value=50.0, max_value=1200.0, value=300.0)
age = st.sidebar.number_input("Usia Sapi (Tahun)", min_value=0.1, max_value=20.0, value=2.0)

# --- LOGIKA PREDIKSI NUTRISI ---
def calculate_requirements(bw, breed_type):
    # Konstanta dasar (Asumsi NRC disesuaikan)
    dmi = bw * 0.03  # 3% dari Berat Badan
    
    # Penyesuaian berdasarkan ras
    multiplier = 1.1 if breed_type in ["Limousin", "Simental"] else 1.0
    
    cp_req = dmi * 0.12 * multiplier # Target Protein 12%
    tdn_req = dmi * 0.65 * multiplier # Target TDN 65%
    
    return {
        "DMI (kg/hari)": round(dmi, 2),
        "Protein Kasar (kg/hari)": round(cp_req, 2),
        "TDN/Energi (kg/hari)": round(tdn_req, 2)
    }

# --- DATABASE BAHAN PAKAN LOKAL ---
feed_db = {
    "Rumput Gajah": {"CP": 8.4, "TDN": 52.0, "Price": 500},
    "Dedak Padi": {"CP": 12.0, "TDN": 65.0, "Price": 3500},
    "Bungkil Sawit": {"CP": 16.0, "TDN": 70.0, "Price": 2500},
    "Jagung Giling": {"CP": 9.0, "TDN": 80.0, "Price": 5000},
    "Daun Lamtoro": {"CP": 22.0, "TDN": 60.0, "Price": 800}
}

# --- LAYOUT UTAMA ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Preview Visual")
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption=f"Sapi {breed} - Terdeteksi", use_column_width=True)
    else:
        st.info("Silakan unggah foto sapi pada sidebar.")

with col2:
    st.subheader("Hasil Prediksi Kebutuhan Nutrisi")
    results = calculate_requirements(weight, breed)
    
    for key, value in results.items():
        st.metric(label=key, value=value)

st.markdown("---")
st.subheader("Saran Komposisi Bahan Mentah (Formulasi)")

# Contoh Formulasi Sederhana (Heuristic)
# Rasio 60% Hijauan, 40% Konsentrat
hijauan_kg = results["DMI (kg/hari)"] * 0.6
konsentrat_kg = results["DMI (kg/hari)"] * 0.4

formula_df = pd.DataFrame({
    "Bahan Baku": ["Rumput Gajah (Hijauan)", "Campuran Konsentrat (Dedak/Sawit/Jagung)"],
    "Jumlah (kg Berat Kering)": [round(hijauan_kg, 2), round(konsentrat_kg, 2)],
    "Fungsi": ["Serat & Maintenance", "Pertumbuhan & Energi"]
})

st.table(formula_df)

st.success("Analisis selesai. Formulasi ini mengutamakan ketersediaan bahan lokal di Indonesia.")
