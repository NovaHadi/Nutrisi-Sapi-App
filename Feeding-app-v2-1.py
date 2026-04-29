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
        c = [feed_db[feed]["Price"] for feed in selected_feeds]
        A_eq = [[1] * len(selected_feeds)]
        b_eq = [dmi_target]
        
        cp_fractions = [- (feed_db[feed]["CP"] / 100.0) for feed in selected_feeds]
        tdn_fractions = [- (feed_db[feed]["TDN"] / 100.0) for feed in selected_feeds]
        
        A_ub = [cp_fractions, tdn_fractions]
        b_ub = [-cp_target, -tdn_target]
        
        bounds = [(0, None) for _ in selected_feeds]
        
        # Proses Optimasi
        result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
        
        if result.success:
            st.success("✅ Formulasi Optimal Ditemukan!")
            amounts = result.x
            total_price = result.fun
            
            active_feeds = [(f, a) for f, a in zip(selected_feeds, amounts) if a >= 0.01]
            final_feeds = [item[0] for item in active_feeds]
            final_amounts = [item[1] for item in active_feeds]
            final_costs = [amt * feed_db[feed]["Price"] for feed, amt in zip(final_feeds, final_amounts)]
            
            df_result = pd.DataFrame({
                "Bahan Baku": final_feeds,
                "Kebutuhan (kg/hari)": final_amounts,
                "Estimasi Biaya (Rp)": final_costs
            })
            
            st.table(
                df_result.style.format({
                    "Kebutuhan (kg/hari)": "{:.2f}",
                    "Estimasi Biaya (Rp)": "{:.2f}"
                })
            )
            st.info(f"**Total Biaya Pakan per Hari: Rp {total_price:,.2f}**")
            
            achieved_cp = sum((feed_db[f]["CP"] / 100.0) * a for f, a in zip(selected_feeds, amounts))
            achieved_tdn = sum((feed_db[f]["TDN"] / 100.0) * a for f, a in zip(selected_feeds, amounts))
            
            st.write(f"*Capaian Nutrisi Formula: Protein Kasar = {achieved_cp:.2f} kg | TDN = {achieved_tdn:.2f} kg*")
            
        else:
            # --- BLOK DIAGNOSTIK ERROR BARU ---
            st.error("❌ **Formulasi Gagal!** Sapi tidak bisa memenuhi kebutuhan nutrisinya (Batas Kapasitas Perut/DMI Penuh).")
            
            # Hitung persentase nutrisi tertinggi dari bahan yang dipilih user
            max_cp_percent = max([feed_db[f]["CP"] for f in selected_feeds])
            max_tdn_percent = max([feed_db[f]["TDN"] for f in selected_feeds])
            
            # Hitung perolehan maksimal jika sapi makan full bahan tersebut
            max_possible_cp = (max_cp_percent / 100.0) * dmi_target
            max_possible_tdn = (max_tdn_percent / 100.0) * dmi_target
            
            error_msgs = []
            
            if max_possible_cp < cp_target:
                deficit_cp = cp_target - max_possible_cp
                error_msgs.append(f"- **Kekurangan Protein (CP)**: Jika sapi makan penuh dengan bahan pilihan Anda, Protein maksimal yang didapat hanya {max_possible_cp:.2f} kg (Kurang **{deficit_cp:.2f} kg** dari target). \n  👉 *Saran: Tambahkan bahan berprotein tinggi (misal: Daun Lamtoro atau Bungkil Sawit).*")
                
            if max_possible_tdn < tdn_target:
                deficit_tdn = tdn_target - max_possible_tdn
                error_msgs.append(f"- **Kekurangan Energi (TDN)**: Jika sapi makan penuh dengan bahan pilihan Anda, Energi maksimal yang didapat hanya {max_possible_tdn:.2f} kg (Kurang **{deficit_tdn:.2f} kg** dari target). \n  👉 *Saran: Tambahkan bahan berenergi tinggi (misal: Jagung Giling atau Dedak Padi).*")
            
            # Menampilkan hasil diagnosis
            if error_msgs:
                st.warning("🔍 **Analisis Penyebab:**\n\n" + "\n\n".join(error_msgs))
            else:
                st.warning("🔍 **Analisis Penyebab:** Kombinasi bahan mentah yang dipilih saling bertolak belakang sehingga tidak bisa menyeimbangkan kebutuhan Protein dan Energi *sekaligus* tanpa melewati batas DMI. \n👉 *Saran: Tambahkan variasi bahan mentah lainnya.*")
