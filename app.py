import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hmac
from PIL import Image

# --- ARCHISTRATEGOS SECURITY ---
def check_password():
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], "LeoGiannotti2026!"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    # Branding for Login Screen
    st.markdown("<h1 style='text-align: center; color: #FF6600;'>🏛️ ARCHISTRATEGOS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-weight: bold;'>STRATEGIC INTELLIGENCE PORTAL</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.text_input("Access Key:", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("Invalid Key.")
    return False

if not check_password():
    st.stop()

# --- UI CONFIG & BRANDING ---
st.set_page_config(page_title="Archistrategos | UAE Patent Analysis", layout="wide", page_icon="🏛️")

BRAND_ORANGE = "#FF6600" 
BRAND_NAVY = "#002147"   
BG_LIGHT = "#F8F9FA"

st.markdown(f"""
    <style>
    .main {{ background-color: {BG_LIGHT}; }}
    [data-testid="stSidebar"] {{ background-color: {BRAND_NAVY}; color: white; }}
    h1, h2, h3 {{ color: {BRAND_NAVY}; border-bottom: 3px solid {BRAND_ORANGE}; padding-bottom: 8px; }}
    .stMetric {{ background-color: white; border-radius: 8px; border-left: 6px solid {BRAND_ORANGE}; padding: 10px; }}
    </style>
""", unsafe_allow_html=True)

# --- DATA REFINEMENT ENGINE (DO NOT CHANGE) ---
def refine_data(df):
    df.columns = df.columns.str.strip()
    if 'Application Date' in df.columns:
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df['Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
        df['Month'] = df['Application Date'].dt.month_name()
        df['Date_Display'] = df['Application Date'].dt.strftime('%Y-%m-%d')
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df['Priority_Year'] = df['Earliest Priority Date'].dt.year.fillna(0).astype(int)
        df['Priority_Month'] = df['Earliest Priority Date'].dt.month_name()
        df['Priority_Display'] = df['Earliest Priority Date'].dt.strftime('%Y-%m-%d')
    if 'Classification' in df.columns:
        df['Primary_IPC'] = df['Classification'].astype(str).str.split(',').str[0].str.strip().str[:4]
    return df

# --- DATABASE LOADING ---
try:
    raw_df = pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv")
    df = refine_data(raw_df)
except:
    df = None

# --- SIDEBAR: LOGO & NAVIGATION ---
with st.sidebar:
    # --- LOGO INTEGRATION ---
    try:
        logo = Image.open("logo.jpeg")
        st.image(logo, use_container_width=True)
    except FileNotFoundError:
        st.markdown(f"<h2 style='color:{BRAND_ORANGE}; text-align:center;'>ARCHISTRATEGOS</h2>", unsafe_allow_html=True)
    
    st.markdown("---")
    menu = st.radio("Intelligence Modules:", [
        "Time-Series Growth", 
        "Classification & Country Strength", 
        "Global Priority & Comparisons", 
        "Expert Search"
    ])

# --- DASHBOARD CONTENT ---
if df is not None:
    # Filter Logic
    all_countries = sorted(df['Country Name (Priority)'].dropna().unique())
    selected_country = st.sidebar.multiselect("Filter Jurisdiction", all_countries)
    filtered_df = df.copy()
    if selected_country:
        filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_country)]

    if menu == "Time-Series Growth":
        st.header("📈 UAE Patent Growth Analysis")
        col1, col2 = st.columns([2, 1])
        with col1:
            counts = filtered_df[filtered_df['Year'] >= 1990].groupby('Year').size().reset_index(name='Number of Applications')
            fig = px.bar(counts, x='Year', y='Number of Applications', text='Number of Applications', color_discrete_sequence=[BRAND_NAVY])
            fig.update_traces(textposition='outside', textfont=dict(family="Arial Black"))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.subheader("Data Registry")
            st.dataframe(counts.sort_values('Year', ascending=False), use_container_width=True, hide_index=True)

    elif menu == "Classification & Country Strength":
        st.header("🌍 Technology Matrix")
        all_ipcs = [x for x in sorted(filtered_df['Primary_IPC'].dropna().unique()) if x != "Ther"]
        target_ipc = st.selectbox("Select IPC Sector:", all_ipcs)
        leader_counts = filtered_df[filtered_df['Primary_IPC'] == target_ipc].groupby('Country Name (Priority)').size().reset_index(name='Number of Applications').sort_values('Number of Applications', ascending=False)
        fig = px.bar(leader_counts, x='Country Name (Priority)', y='Number of Applications', text='Number of Applications', color_discrete_sequence=[BRAND_ORANGE])
        fig.update_traces(textposition='outside', textfont=dict(family="Arial Black"))
        st.plotly_chart(fig, use_container_width=True)

    elif menu == "Global Priority & Comparisons":
        st.header("🏁 International Priority Analysis")
        valid_p = df[df['Priority_Year'] > 1900]['Priority_Year']
        p_range = st.sidebar.slider("Priority Range", int(valid_p.min()), int(valid_p.max()), (int(valid_p.max()-5), int(valid_p.max())))
        p_df = filtered_df[(filtered_df['Priority_Year'] >= p_range[0]) & (filtered_df['Priority_Year'] <= p_range[1])]
        actual = p_df.groupby(['Priority_Year', 'Priority_Month']).size().reset_index(name='Number of Applications')
        fig = px.bar(actual, x='Priority_Month', y='Number of Applications', color='Priority_Year', barmode='group', text='Number of Applications')
        fig.update_traces(textfont=dict(family="Arial Black"))
        st.plotly_chart(fig, use_container_width=True)

    elif menu == "Expert Search":
        st.header("🔍 Registry Intelligence Query")
        search = st.text_input("Search Registry:")
        if search:
            mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
            results = filtered_df[mask][['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Date_Display', 'Priority_Display']]
            results.columns = ['App Number', 'Title', 'IPC', 'Country', 'Filing Date (UAE)', 'Priority Date (Global)']
            st.dataframe(results, use_container_width=True, hide_index=True)
else:
    st.info("System Ready. Please connect to the Archistrategos Database.")
