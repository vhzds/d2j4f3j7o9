import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import json
import re
import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Dashboard Form A Pengawasan",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CUSTOM CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 2px 4px 12px rgba(0,0,0,0.08);
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 2px 8px 16px rgba(0,0,0,0.12);
    }
    
    div.stButton > button:first-child {
        background-color: #004aad;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        width: 100%;
        padding: 10px;
    }
    div.stButton > button:hover {
        background-color: #003073;
        color: white;
        border-color: #003073;
    }
</style>
""", unsafe_allow_html=True)


# --- 3. SISTEM LOGIN ---
def check_password():
    def password_entered():
        if (st.session_state["username"] == st.secrets["login"]["username"]
            and st.session_state["password"] == st.secrets["login"]["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        col_space1, col_login, col_space2 = st.columns([1, 1, 1])
        with col_login:
            st.markdown("<h2 style='text-align: center; color: #004aad;'>Portal Pengawasan</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray;'>Silakan masuk untuk mengakses dasbor</p>", unsafe_allow_html=True)
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.button("Masuk", on_click=password_entered)
        return False
    
    elif not st.session_state["password_correct"]:
        col_space1, col_login, col_space2 = st.columns([1, 1, 1])
        with col_login:
            st.markdown("<h2 style='text-align: center; color: #004aad;'>Portal Pengawasan</h2>", unsafe_allow_html=True)
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.button("Masuk", on_click=password_entered)
            st.error("Kredensial tidak valid. Silakan coba lagi.")
        return False
    
    return True


# --- 4. APLIKASI UTAMA ---
if check_password():
    
    # Header Dasbor
    col_header, col_logout = st.columns([8, 1])
    with col_header:
        st.markdown("<h1 style='color: #2c3e50;'>🛡️ Dasbor Form A Pengawasan</h1>", unsafe_allow_html=True)
    with col_logout:
        st.write("") 
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

    # Fungsi Ambil Data
    @st.cache_data(ttl=60)
    def load_data():
        creds_secret = st.secrets["google_credentials"]
        if isinstance(creds_secret, str):
            creds_dict = json.loads(creds_secret)
        else:
            creds_dict = dict(creds_secret)
            
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        sheet_url = "https://docs.google.com/spreadsheets/d/11qKowHN9IYt2pGteigPsYBFJxj4WNuPD9Z2bMI-PRoM/edit"
        sheet = client.open_by_url(sheet_url).sheet1
        
        raw_data = sheet.get_all_values()
        df = pd.DataFrame(raw_data[1:], columns=raw_data[0]) 
        df = df.replace("", None)
        
        # Ekstraksi Tanggal
        def ekstrak_tanggal_indo(teks):
            if not isinstance(teks, str):
                return pd.NaT
            
            daftar_bulan = {
                'januari': 1, 'februari': 2, 'maret': 3, 'april': 4,
                'mei': 5, 'juni': 6, 'juli': 7, 'agustus': 8,
                'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
            }
            
            pencarian = re.search(r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})', teks.lower())
            if pencarian:
                hari = int(pencarian.group(1))
                bulan_teks = pencarian.group(2)
                tahun = int(pencarian.group(3))
                
                if bulan_teks in daftar_bulan:
                    try:
                        return datetime.date(tahun, daftar_bulan[bulan_teks], hari)
                    except ValueError:
                        return pd.NaT
            return pd.NaT
        
        # Ekstraksi Nama Pertama
        def ekstrak_pelaksana_utama(teks):
            if isinstance(teks, str) and teks.strip():
                return teks.split(',')[0].strip()
            return teks

        df['Tanggal_Sistem'] = df['Waktu dan Tempat'].apply(ekstrak_tanggal_indo)
        df['Pelaksana_Sistem'] = df['Nama Pelaksana Tugas'].apply(ekstrak_pelaksana_utama)
        
        return df

    try:
        with st.spinner("Menarik data terbaru dari server..."):
            df = load_data()
    except Exception as e:
        st.error(f"Gagal mengambil data. Detail: {e}")
        st.stop()

    # --- SIDEBAR: FILTER CANGGIH ---
    with st.sidebar:
        st.markdown("### 🎛️ Panel Filter")
        st.info("Biarkan kosong untuk menampilkan semua data.")
        
        # 1. Filter Rentang Waktu
        st.markdown("#### 📅 Waktu Kejadian")
        tanggal_valid = df['Tanggal_Sistem'].dropna()
        if not tanggal_valid.empty:
            min_date = tanggal_valid.min()
            max_date = tanggal_valid.max()
        else:
            min_date = datetime.date(2023, 1, 1)
            max_date = datetime.date.today()
            
        rentang_tanggal = st.date_input(
            "Pilih Rentang Tanggal:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        st.markdown("---")
        
        # 2. Filter Tahapan (Default dikosongkan)
        tahapan_list = [x for x in df['Tahapan yang diawasi'].dropna().unique() if x]
        selected_tahapan = st.multiselect("Tahapan Pengawasan", tahapan_list, placeholder="Pilih Tahapan...")

        # 3. Filter Pelaksana (Default dikosongkan)
        pelaksana_list = [x for x in df['Pelaksana_Sistem'].dropna().unique() if x]
        selected_pelaksana = st.multiselect("Pelaksana Tugas Utama", pelaksana_list, placeholder="Pilih Pelaksana...")

    # --- PENERAPAN LOGIKA FILTER (SUDAH DIPERBAIKI) ---
    
    # Logika Tahapan: Jika list kosong, anggap semua benar (True). Jika ada isi, saring data.
    if not selected_tahapan:
        mask_tahapan = pd.Series(True, index=df.index)
    else:
        mask_tahapan = df['Tahapan yang diawasi'].isin(selected_tahapan)

    # Logika Pelaksana: Jika list kosong, anggap semua benar (True). Jika ada isi, saring data.
    if not selected_pelaksana:
        mask_pelaksana = pd.Series(True, index=df.index)
    else:
        mask_pelaksana = df['Pelaksana_Sistem'].isin(selected_pelaksana)
    
    # Logika Waktu: Agar data yang tanggalnya keliru/kosong tetap tampil jika filter tanggal tidak diubah
    if len(rentang_tanggal) == 2:
        start_date, end_date = rentang_tanggal
        # Jika rentang masih bawaan (min sampai max), tampilkan SEMUA data termasuk yang tanggalnya kosong (NaT)
        if start_date == min_date and end_date == max_date:
            mask_waktu = pd.Series(True, index=df.index)
        else:
            mask_waktu = df['Tanggal_Sistem'].between(start_date, end_date)
    elif len(rentang_tanggal) == 1:
        mask_waktu = df['Tanggal_Sistem'] == rentang_tanggal[0]
    else:
        mask_waktu = pd.Series(True, index=df.index)

    # Gabungkan semua filter
    df_filtered = df[mask_tahapan & mask_pelaksana & mask_waktu]
    
    df_tampil = df_filtered.drop(columns=['Tanggal_Sistem', 'Pelaksana_Sistem'], errors='ignore')

    # --- METRIK INDIKATOR UTAMA ---
    st.markdown("<br>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("📂 Total Laporan Terinput", f"{len(df_filtered)} Laporan")
    m2.metric("👥 Pelaksana Tugas Aktif", f"{df_filtered['Pelaksana_Sistem'].nunique()} Orang")
    m3.metric("📊 Tahapan Diawasi", f"{df_filtered['Tahapan yang diawasi'].nunique()} Kategori")
    st.markdown("<br>", unsafe_allow_html=True)

    # --- TAB MENU NAVIGASI ---
    tab1, tab2 = st.tabs(["📈 Analisis Visual", "📑 Detail Tabel Data"])

    # TAB 1: GRAFIK VISUAL
    with tab1:
        st.markdown("#### Ringkasan Grafik Pengawasan")
        c1, c2 = st.columns(2)
        
        with c1:
            if not df_filtered.empty:
                tahapan_count = df_filtered['Tahapan yang diawasi'].value_counts().reset_index()
                tahapan_count.columns = ['Tahapan', 'Jumlah']
                fig1 = px.bar(tahapan_count, x='Jumlah', y='Tahapan', orientation='h', 
                              color='Tahapan', text='Jumlah', 
                              title="Distribusi Laporan per Tahapan",
                              template="plotly_white")
                fig1.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("Tidak ada data laporan yang sesuai dengan filter.")

        with c2:
            if not df_filtered.empty:
                pelaksana_count = df_filtered['Pelaksana_Sistem'].value_counts().reset_index()
                pelaksana_count.columns = ['Nama Pelaksana Utama', 'Jumlah']
                fig2 = px.pie(pelaksana_count, names='Nama Pelaksana Utama', values='Jumlah', hole=0.4,
                              title="Kontribusi Pelaksana Tugas (Nama Utama)",
                              template="plotly_white")
                fig2.update_traces(textposition='inside', textinfo='percent+label')
                fig2.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Tidak ada data pelaksana yang sesuai dengan filter.")

    # TAB 2: TABEL DATA
    with tab2:
        st.markdown("#### Pangkalan Data Form A")
        st.markdown("Data disinkronkan secara *real-time*. Kolom 'Nama Pelaksana Tugas' tetap menampilkan data utuh sesuai input.")
        st.dataframe(
            df_tampil, 
            use_container_width=True, 
            height=500,
            hide_index=True 
        )
