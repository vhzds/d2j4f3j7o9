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
        
        # --- FUNGSI ANTI-KEMBAR (DEDUPLIKASI NAMA KOLOM) ---
        def anti_kembar(kolom_list):
            clean = []
            seen = {}
            for k in kolom_list:
                k_str = str(k).strip()
                if k_str in seen:
                    seen[k_str] += 1
                    clean.append(f"{k_str} ({seen[k_str]})")
                else:
                    seen[k_str] = 1
                    clean.append(k_str)
            return clean

        raw_columns = anti_kembar(raw_data[0])
        df = pd.DataFrame(raw_data[1:], columns=raw_columns) 
        df = df.replace("", None)
        
        # --- PERUBAHAN NAMA KOLOM SERENTAK ---
        df = df.rename(columns={
            'Peserta': 'Tempat Kejadian Sengketa',
            'Tempat Sengketa': 'Peserta Pemilu',
            'Tempat KejadianSengketa': 'Peserta Pemilu',
            'PesertaPemilu': 'Tempat Kejadian Sengketa',
            'Informasi Sengketa Pemilu': 'Peserta Pemilu'
        })
        
        df.columns = anti_kembar(df.columns)
        
        # 1. Ekstraksi Tanggal dari 'Waktu dan Tempat'
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
        
        # 2. Ekstraksi Nama Utama (Sebelum Koma)
        def ekstrak_pelaksana_utama(teks):
            if isinstance(teks, str) and teks.strip():
                return teks.split(',')[0].strip()
            return teks

        # 3. Ekstraksi Tanggal dari kolom Timestamps (Untuk filter kalender)
        col_ts = None
        for col_name in ['Timestamps', 'Timestamp', 'Waktu Input']:
            if col_name in df.columns:
                col_ts = col_name
                break
                
        def ekstrak_tanggal_ts(val):
            if not val or not str(val).strip():
                return pd.NaT
            try:
                return pd.to_datetime(str(val).strip(), dayfirst=True).date()
            except:
                return pd.NaT

        df['Tanggal_Sistem'] = df['Waktu dan Tempat'].apply(ekstrak_tanggal_indo)
        df['Pelaksana_Sistem'] = df['Nama Pelaksana Tugas'].apply(ekstrak_pelaksana_utama)
        
        if col_ts:
            df['TS_Tanggal_Sistem'] = df[col_ts].apply(ekstrak_tanggal_ts)
        else:
            df['TS_Tanggal_Sistem'] = pd.Series([pd.NaT] * len(df))
        
        return df

    try:
        with st.spinner("Menarik data terbaru dari server..."):
            df = load_data()
    except Exception as e:
        st.error(f"Gagal mengambil data. Detail: {e}")
        st.stop()


    # --- SIDEBAR: CROSS-FILTERING MULTI-ARAH ---
    with st.sidebar:
        st.markdown("### 🎛️ Panel Filter")
        
        # --- TOMBOL RESET FILTER ---
        if st.button("🔄 Reset Semua Filter"):
            for key in ['sel_tahapan', 'sel_pelaksana', 'sel_sasaran', 'sel_bentuk', 'sel_lhp', 'sel_ts', 'sel_waktu']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun() 
            
        st.info("Pilihan akan otomatis menyusut mengikuti opsi yang Anda klik.")
        st.markdown("---")
        
        # 1. FILTER RENTANG WAKTU KEJADIAN
        st.markdown("#### 📅 Waktu Kejadian")
        tanggal_valid = df['Tanggal_Sistem'].dropna()
        if not tanggal_valid.empty:
            min_date = tanggal_valid.min()
            max_date = tanggal_valid.max()
        else:
            min_date = datetime.date(2023, 1, 1)
            max_date = datetime.date.today()
            
        rentang_tanggal = st.date_input(
            "Pilih Rentang Waktu Kejadian:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="sel_waktu"
        )
        
        if len(rentang_tanggal) == 2:
            start_date, end
