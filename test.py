import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import json

# Konfigurasi Halaman (Harus selalu di paling atas)
st.set_page_config(page_title="Dashboard Pengawasan Bawaslu", layout="wide")

# --- SISTEM LOGIN ---
def check_password():
    """Mengembalikan nilai True jika user sudah memasukkan password yang benar."""
    def password_entered():
        # Mengecek apakah username dan password cocok dengan yang ada di Secrets
        if (st.session_state["username"] == st.secrets["login"]["username"]
            and st.session_state["password"] == st.secrets["login"]["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Hapus password dari memori untuk keamanan
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Jika belum login, tampilkan form login
    if "password_correct" not in st.session_state:
        st.title("🔒 Halaman Login")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        return False
    
    # Jika login salah
    elif not st.session_state["password_correct"]:
        st.title("🔒 Halaman Login")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        st.error("Username atau password salah 😕")
        return False
    
    # Jika login benar
    return True

# --- JIKA LOGIN BERHASIL, TAMPILKAN APLIKASI ---
if check_password():
    
    st.title("📊 Dashboard Database Form A Pengawasan")
    st.success("Berhasil login!")

    # Fungsi untuk mengambil data dari Google Sheets
    @st.cache_data(ttl=60)
    def load_data():
        creds_json = st.secrets["google_credentials"]
        creds_dict = json.loads(creds_json)
        
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Link spreadsheet Anda
        sheet_url = "https://docs.google.com/spreadsheets/d/11qKowHN9IYt2pGteigPsYBFJxj4WNuPD9Z2bMI-PRoM"
        sheet = client.open_by_url(sheet_url).sheet1
        
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df = df.replace("", None)
        return df

    try:
        df = load_data()
    except Exception as e:
        st.error("Gagal terhubung ke Spreadsheet. Pastikan pengaturan Secrets sudah benar.")
        st.stop()

    # --- SIDEBAR: FILTER DATA ---
    st.sidebar.header("🔍 Filter Data")
    
    # Tombol Logout di Sidebar
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    tahapan_list = df['Tahapan yang diawasi'].dropna().unique().tolist()
    selected_tahapan = st.sidebar.multiselect("Pilih Tahapan yang Diawasi", tahapan_list, default=tahapan_list)

    pelaksana_list = df['Nama Pelaksana Tugas'].dropna().unique().tolist()
    selected_pelaksana = st.sidebar.multiselect("Pilih Nama Pelaksana", pelaksana_list, default=pelaksana_list)

    df_filtered = df[
        (df['Tahapan yang diawasi'].isin(selected_tahapan)) &
        (df['Nama Pelaksana Tugas'].isin(selected_pelaksana))
    ]

    # --- MAIN PAGE: INDIKATOR UTAMA ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Data Terinput", len(df_filtered))
    col2.metric("Jumlah Pelaksana Tugas", df_filtered['Nama Pelaksana Tugas'].nunique())
    col3.metric("Jumlah Tahapan Diawasi", df_filtered['Tahapan yang diawasi'].nunique())

    st.markdown("---")

    # --- GRAFIK (CHARTS) ---
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("📈 Jumlah Laporan per Tahapan")
        if not df_filtered.empty:
            tahapan_count = df_filtered['Tahapan yang diawasi'].value_counts().reset_index()
            tahapan_count.columns = ['Tahapan', 'Jumlah']
            fig1 = px.bar(tahapan_count, x='Tahapan', y='Jumlah', color='Tahapan', text='Jumlah')
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Tidak ada data.")

    with col_chart2:
        st.subheader("👥 Laporan Berdasarkan Pelaksana")
        if not df_filtered.empty:
            pelaksana_count = df_filtered['Nama Pelaksana Tugas'].value_counts().reset_index()
            pelaksana_count.columns = ['Nama Pelaksana', 'Jumlah']
            fig2 = px.pie(pelaksana_count, names='Nama Pelaksana', values='Jumlah', hole=0.3)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Tidak ada data.")

    st.markdown("---")

    # --- TABEL DATA ---
    st.subheader("📄 Detail Data (Tabel)")
    st.dataframe(df_filtered, use_container_width=True)
