import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
from scipy.optimize import linprog

# Konfigurasi Halaman
st.set_page_config(page_title="Cattle Feed Optimizer", layout="wide")

st.title("🐄 MOO-Feed: Smart Cattle Nutrition Web App")
st.markdown("---")

# --- SIDEBAR: INPUT DATA SAPI ---
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
    
    cp_req = dmi * 0.12 * multiplier # Target Protein minimal 12%
    tdn_req = dmi * 0.65 * multiplier # Target TDN minimal 65%
    
    return dmi, cp_req, tdn_req

dmi_target, cp_target, tdn_target = calculate_requirements(weight, breed)

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
    st.metric(label="Dry Matter Intake (DMI / Kapasitas Makan)", value=f"{dmi_target:.2f} kg/hari")
    st.metric(label="Kebutuhan Protein Kasar (CP)", value=f"{cp_target:.2f} kg/hari")
    st.metric(label="Kebutuhan Energi (TDN)", value=f"{tdn_target:.2f} kg/hari")

st.markdown("---")

# --- FITUR INTERAKTIF FORMULASI PAKAN ---
st.subheader("🧪 Optimizer Formulasi Pakan (Least Cost Ration)")

# 1. Pilihan Bahan Interaktif
selected_feeds = st.multiselect(
    "Pilih bahan baku yang tersedia di lokasi Anda:",
    options=list(feed_db.keys()),
    default=["Rumput Gajah", "Bungkil Sawit", "Dedak Padi"]
)

if st.button("Hitung Formulasi Otomatis"):
    if len(selected_feeds) < 2:
        st.warning("Pilih minimal 2 bahan baku agar sistem bisa mencampur formula dengan baik!")
    else:
        # Menyiapkan data untuk Linear Programming (SciPy)
        # Objektif: Meminimalkan Harga (Cost)
        c = [feed_db[feed]["Price"] for feed in selected_feeds]
        
        # Constraints: 
        # 1. Persamaan DMI: Total bobot bahan harus sama dengan DMI target
        A_eq = [[1] * len(selected_feeds)]
        b_eq = [dmi_target]
        
        # 2. Pertidaksamaan Nutrisi (SciPy menggunakan format <= , jadi kita kalikan negatif agar jadi >= target)
        # - Protein Kasar (CP)
        cp_fractions = [- (feed_db[feed]["CP"] / 100.0) for feed in selected_feeds]
        # - Energi (TDN)
        tdn_fractions = [- (feed_db[feed]["TDN"] / 100.0) for feed in selected_feeds]
        
        A_ub = [cp_fractions, tdn_fractions]
        b_ub = [-cp_target, -tdn_target]
        
        # Batasan (Bounds): Semua bahan mentah tidak boleh bernilai negatif
        bounds = [(0, None) for _ in selected_feeds]
        
        # Proses Optimasi
        result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
        
        if result.success:
            st.success("✅ Formulasi Optimal Ditemukan!")
            
            # Ekstrak Hasil
            amounts = result.x
            total_price = result.fun
            
            # Tampilkan ke dalam Tabel
            df_result = pd.DataFrame({
                "Bahan Baku": selected_feeds,
                "Kebutuhan (kg/hari)": np.round(amounts, 2),
                "Estimasi Biaya (Rp)": np.round(amounts * np.array(c), 0)
            })
            
            # Buang bahan yang hasilnya 0 kg
            df_result = df_result[df_result["Kebutuhan (kg/hari)"] > 0].reset_index(drop=True)
            
            st.table(df_result)
            st.info(f"**Total Biaya Pakan per Hari: Rp {total_price:,.0f}**")
            
            # Cek ulang capaian nutrisi dari hasil
            achieved_cp = sum((feed_db[f]["CP"] / 100.0) * a for f, a in zip(selected_feeds, amounts))
            achieved_tdn = sum((feed_db[f]["TDN"] / 100.0) * a for f, a in zip(selected_feeds, amounts))
            
            st.write(f"*Capaian Nutrisi Formula: Protein Kasar = {achieved_cp:.2f} kg | TDN = {achieved_tdn:.2f} kg*")
            
        else:
            st.error("❌ Formulasi Gagal: Bahan yang Anda pilih tidak bisa memenuhi target nutrisi (Protein/TDN) untuk batas makan sapi ini. Coba tambahkan bahan yang berprotein/berenergi tinggi seperti Bungkil Sawit atau Jagung.")
