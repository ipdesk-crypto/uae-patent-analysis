import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hmac
from PIL import Image

# --- ARCHISTRATEGOS SECURITY (PASSWORD) ---
def check_password():
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], "LeoGiannotti2026!"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if st.session_state.get("password_correct", False):
        return True
    
    # Branding on Password Page
    st.markdown("<h1 style='text-align: center; color: #FF6600;'>🏛️ ARCHISTRATEGOS</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.text_input("Access Key:", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("Invalid Key.")
    return False

if not check_password():
    st.stop()

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Analysis Pro", layout="wide", page_icon="🏛️")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #002147; color: white; }
    h1, h2, h3 { color: #002147; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- DATA REFINEMENT ENGINE ---
def refine_data(df):
    df.columns = df.columns.str.strip()
    
    # 1. Application Date Logic
    if 'Application Date' in df.columns:
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df = df.dropna(subset=['Application Date'])
        df['App_Year'] = df['Application Date'].dt.year.astype(int)
        df['App_Month'] = df['Application Date'].dt.month_name()
        df['App_Period_Sort'] = df['Application Date'].dt.to_period('M')

    # 2. Priority Date Logic
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df = df.dropna(subset=['Earliest Priority Date'])
        df['Prio_Year'] = df['Earliest Priority Date'].dt.year.astype(int)
        df['Prio_Month'] = df['Earliest Priority Date'].dt.month_name()
        df['Prio_Period_Sort'] = df['Earliest Priority Date'].dt.to_period('M')

    # 3. IPC Classification Logic (Strict A-H)
    if 'Classification' in df.columns:
        df['Primary_IPC'] = df['Classification'].astype(str).str.split(',').str[0].str.strip()
        df['IPC_Section'] = df['Primary_IPC'].str[0].str.upper()
        df = df[df['IPC_Section'].isin(['A','B','C','D','E','F','G','H'])]
    return df

def pad_months(df, date_col_prefix):
    if df.empty: return df
    sort_col = f'{date_col_prefix}_Period_Sort'
    min_date = df[sort_col].min().to_timestamp()
    max_date = df[sort_col].max().to_timestamp()
    full_range = pd.date_range(start=min_date, end=max_date, freq='MS')
    template = pd.DataFrame({sort_col: full_range.to_period('M')})
    counts = df.groupby(sort_col).size().reset_index(name='Count')
    padded = pd.merge(template, counts, on=sort_col, how='left').fillna(0)
    padded['Date'] = padded[sort_col].dt.to_timestamp()
    return padded

# --- SIDEBAR & LOGO ---
with st.sidebar:
    try:
        logo = Image.open("logo.jpeg")
        st.image(logo, use_container_width=True)
    except:
        st.title("🏛️ ARCHISTRATEGOS")
    st.markdown("---")
    data_source = st.radio("Select Source:", ["Default UAE Dataset", "Upload Custom CSV"])

# --- DATA LOADING ---
try:
    if data_source == "Upload Custom CSV":
        uploaded_file = st.sidebar.file_uploader("Upload CSV", type="csv")
        df = refine_data(pd.read_csv(uploaded_file)) if uploaded_file else None
    else:
        df = refine_data(pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv"))
except:
    st.error("Data Source Error.")
    st.stop()

if df is not None:
    menu = st.sidebar.radio("Go to:", ["Time-Series Growth", "Classification & Country Strength", "Global Priority & Comparisons", "Expert Search"])
    f_df = df.copy()

    # --- MODULE 1: TIME-SERIES GROWTH ---
    if menu == "Time-Series Growth":
        st.header("📈 Growth Trends & Temporal Analysis")
        
        # Yearly Bar Chart
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Yearly Filing Volume (Application Date)")
            y_counts = f_df.groupby('App_Year').size().reset_index(name='Count')
            st.plotly_chart(px.bar(y_counts, x='App_Year', y='Count', text='Count', color_discrete_sequence=['#3498db']), use_container_width=True)
        with c2:
            st.subheader("Registry Table")
            st.dataframe(y_counts.sort_values('App_Year', ascending=False), use_container_width=True, hide_index=True)

        st.markdown("---")
        # Continuous Application Line (Forced Labels + Counts)
        st.subheader("📅 Full Monthly Sequence: Application Date (Forced Monthly Labels)")
        app_p = pad_months(f_df, 'App')
        fig_app = px.line(app_p, x='Date', y='Count', markers=True, text='Count')
        fig_app.update_traces(line=dict(color='#00FFFF', width=3), textposition='top center', textfont=dict(color="white"))
        fig_app.update_xaxes(dtick="M1", tickformat="%b\n%Y", tickangle=90, showgrid=True)
        st.plotly_chart(fig_app, use_container_width=True)

        st.markdown("---")
        # Continuous Priority Line (Forced Labels + Counts)
        st.subheader("📅 Full Monthly Sequence: Earliest Priority Date (Forced Monthly Labels)")
        prio_p = pad_months(f_df, 'Prio')
        fig_prio = px.line(prio_p, x='Date', y='Count', markers=True, text='Count')
        fig_prio.update_traces(line=dict(color='#FF00FF', width=3), textposition='top center', textfont=dict(color="white"))
        fig_prio.update_xaxes(dtick="M1", tickformat="%b\n%Y", tickangle=90, showgrid=True)
        st.plotly_chart(fig_prio, use_container_width=True)

        st.markdown("---")
        # Restored Focus Year Selector
        st.subheader("🔍 Monthly Detail Line Graph per Selected Year")
        focus_yr = st.selectbox("Choose Year to Analyze:", sorted(f_df['App_Year'].unique(), reverse=True))
        if focus_yr:
            m_df = f_df[f_df['App_Year'] == focus_yr]
            mo_list = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
            m_counts = m_df.groupby('App_Month').size().reindex(mo_list, fill_value=0).reset_index(name='Count')
            fig_f = px.line(m_counts, x='App_Month', y='Count', markers=True, text='Count')
            fig_f.update_traces(line=dict(color='#f1c40f', width=4), textfont=dict(color="white"))
            st.plotly_chart(fig_f, use_container_width=True)

    # --- MODULE 2: CLASSIFICATION ---
    elif menu == "Classification & Country Strength":
        st.header("🌍 IPC Sector Analysis (Standard A-H)")
        sec_counts = f_df['IPC_Section'].value_counts().reset_index(name='Count').sort_values('IPC_Section')
        st.plotly_chart(px.bar(sec_counts, x='IPC_Section', y='Count', text='Count', color='IPC_Section'), use_container_width=True)

    # --- MODULE 3: GLOBAL PRIORITY (ALL TABLES INTACT) ---
    elif menu == "Global Priority & Comparisons":
        st.header("🏁 Global Priority Analysis")
        v_p = f_df['Prio_Year']
        p_rng = st.sidebar.slider("Range", int(v_p.min()), int(v_p.max()), (int(v_p.max()-5), int(v_p.max())))
        p_df = f_df[(f_df['Prio_Year'] >= p_rng[0]) & (f_df['Prio_Year'] <= p_rng[1])]
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Monthly filing volume by Priority Year")
            mo = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
            act = p_df.groupby(['Prio_Year', 'Prio_Month']).size().reset_index(name='Count')
            st.plotly_chart(px.bar(act, x='Prio_Month', y='Count', color=act['Prio_Year'].astype(str), barmode='group', text='Count', category_orders={"Prio_Month": mo}), use_container_width=True)
        with c2:
            st.subheader("📌 Yearly Summary")
            st.dataframe(p_df.groupby('Prio_Year').size().reset_index(name='Count').sort_values('Prio_Year', ascending=False), use_container_width=True, hide_index=True)
            st.subheader("📅 Monthly Breakdown")
            det_p = p_df.groupby(['Prio_Year', 'Prio_Month']).size().reset_index(name='Count')
            det_p['M_N'] = pd.to_datetime(det_p['Prio_Month'], format='%B').dt.month
            st.dataframe(det_p.sort_values(['Prio_Year', 'M_N'], ascending=[False, True])[['Prio_Year', 'Prio_Month', 'Count']], use_container_width=True, height=400, hide_index=True)

    # --- MODULE 4: SEARCH ---
    elif menu == "Expert Search":
        st.header("🔍 Identify Experts")
        query = st.text_input("Search Registry:")
        if query:
            mask = f_df.astype(str).apply(lambda x: x.str.contains(query, case=False, na=False)).any(axis=1)
            st.dataframe(f_df[mask][['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date', 'Earliest Priority Date']], use_container_width=True, hide_index=True)
