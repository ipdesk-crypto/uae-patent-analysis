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

# --- DATA REFINEMENT ENGINE ---
def refine_data(df):
    df.columns = df.columns.str.strip()
    # Application Dates
    if 'Application Date' in df.columns:
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df = df.dropna(subset=['Application Date'])
        df['App_Year'] = df['Application Date'].dt.year.astype(int)
        df['App_Month'] = df['Application Date'].dt.month_name()
        df['App_Period_Sort'] = df['Application Date'].dt.to_period('M')
    # Priority Dates
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df = df.dropna(subset=['Earliest Priority Date'])
        df['Prio_Year'] = df['Earliest Priority Date'].dt.year.astype(int)
        df['Prio_Month'] = df['Earliest Priority Date'].dt.month_name()
        df['Prio_Period_Sort'] = df['Earliest Priority Date'].dt.to_period('M')
    # IPC (A-H only, removing T)
    if 'Classification' in df.columns:
        df['Primary_IPC'] = df['Classification'].astype(str).str.split(',').str[0].str.strip()
        df['IPC_Section'] = df['Primary_IPC'].str[0].str.upper()
        df = df[df['IPC_Section'].isin(['A','B','C','D','E','F','G','H'])]
    return df

def pad_months(df, date_col_prefix):
    if df.empty: return df
    sort_col = f'{date_col_prefix}_Period_Sort'
    min_d, max_d = df[sort_col].min().to_timestamp(), df[sort_col].max().to_timestamp()
    full_range = pd.date_range(start=min_d, end=max_d, freq='MS')
    template = pd.DataFrame({sort_col: full_range.to_period('M')})
    counts = df.groupby(sort_col).size().reset_index(name='Count')
    padded = pd.merge(template, counts, on=sort_col, how='left').fillna(0)
    padded['Date'] = padded[sort_col].dt.to_timestamp()
    return padded

# --- SIDEBAR & LOADING ---
with st.sidebar:
    try:
        st.image(Image.open("logo.jpeg"), use_container_width=True)
    except:
        st.title("🏛️ ARCHISTRATEGOS")
    st.markdown("---")
    menu = st.radio("Navigation:", ["Time-Series Growth", "Classification & Country Strength", "Global Priority & Comparisons", "Expert Search"])

try:
    df = refine_data(pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv"))
except:
    st.error("Data file missing.")
    st.stop()

# --- 1. TIME-SERIES GROWTH ---
if menu == "Time-Series Growth":
    st.header("📈 Growth Trends (App & Priority)")
    
    # Yearly Application Bar & Table
    c1, c2 = st.columns([2, 1])
    y_counts = df.groupby('App_Year').size().reset_index(name='Count')
    c1.plotly_chart(px.bar(y_counts, x='App_Year', y='Count', text='Count', color_discrete_sequence=['#3498db']), use_container_width=True)
    c2.dataframe(y_counts.sort_values('App_Year', ascending=False), hide_index=True)

    # Continuous Application Line
    st.subheader("📅 Monthly Application Sequence (Use Slider to Zoom)")
    app_p = pad_months(df, 'App')
    fig_app = px.line(app_p, x='Date', y='Count', markers=True, text='Count')
    fig_app.update_traces(line=dict(color='#00FFFF'), textposition='top center')
    fig_app.update_xaxes(dtick="M1", tickformat="%b %Y", tickangle=-45, rangeslider_visible=True)
    st.plotly_chart(fig_app, use_container_width=True)

    # Continuous Priority Line
    st.subheader("📅 Monthly Priority Sequence (Use Slider to Zoom)")
    prio_p = pad_months(df, 'Prio')
    fig_prio = px.line(prio_p, x='Date', y='Count', markers=True, text='Count')
    fig_prio.update_traces(line=dict(color='#FF00FF'), textposition='top center')
    fig_prio.update_xaxes(dtick="M1", tickformat="%b %Y", tickangle=-45, rangeslider_visible=True)
    st.plotly_chart(fig_prio, use_container_width=True)

    # RESTORED Focus Year
    st.markdown("---")
    focus_yr = st.selectbox("Detailed View for Year:", sorted(df['App_Year'].unique(), reverse=True))
    m_list = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    m_counts = df[df['App_Year'] == focus_yr].groupby('App_Month').size().reindex(m_list, fill_value=0).reset_index(name='Count')
    st.plotly_chart(px.line(m_counts, x='App_Month', y='Count', markers=True, text='Count', title=f"Trend for {focus_yr}"), use_container_width=True)

# --- 2. CLASSIFICATION & COUNTRY (RESTORED EVERYTHING) ---
elif menu == "Classification & Country Strength":
    st.header("🌍 IPC Strength & Country Leaderboard")
    
    # Histogram A-H
    sec_counts = df['IPC_Section'].value_counts().reset_index(name='Count').sort_values('IPC_Section')
    st.plotly_chart(px.bar(sec_counts, x='IPC_Section', y='Count', text='Count', color='IPC_Section'), use_container_width=True)
    
    st.markdown("---")
    # RESTORED Specific IPC Country Breakdown
    target_ipc = st.selectbox("Leaderboard for Specific IPC Code:", sorted(df['Primary_IPC'].unique()))
    lead_df = df[df['Primary_IPC'] == target_ipc].groupby('Country Name (Priority)').size().reset_index(name='Count').sort_values('Count', ascending=False)
    st.plotly_chart(px.bar(lead_df, x='Country Name (Priority)', y='Count', text='Count', color_discrete_sequence=['#e74c3c']), use_container_width=True)

# --- 3. GLOBAL PRIORITY & COMPARISONS ---
elif menu == "Global Priority & Comparisons":
    st.header("🏁 Global Comparison (Priority Date)")
    v_p = df['Prio_Year']
    p_rng = st.sidebar.slider("Year Range", int(v_p.min()), int(v_p.max()), (int(v_p.max()-5), int(v_p.max())))
    p_df = df[(df['Prio_Year'] >= p_rng[0]) & (df['Prio_Year'] <= p_rng[1])]
    
    c1, c2 = st.columns([2, 1])
    with c1:
        mo = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        act = p_df.groupby(['Prio_Year', 'Prio_Month']).size().reset_index(name='Count')
        st.plotly_chart(px.bar(act, x='Prio_Month', y='Count', color=act['Prio_Year'].astype(str), barmode='group', text='Count', category_orders={"Prio_Month": mo}), use_container_width=True)
    with c2:
        st.subheader("Summary Registry")
        st.dataframe(p_df.groupby('Prio_Year').size().reset_index(name='Count').sort_values('Prio_Year', ascending=False), hide_index=True)
        det_p = p_df.groupby(['Prio_Year', 'Prio_Month']).size().reset_index(name='Count')
        det_p['M_N'] = pd.to_datetime(det_p['Prio_Month'], format='%B').dt.month
        st.dataframe(det_p.sort_values(['Prio_Year', 'M_N'], ascending=[False, True])[['Prio_Year', 'Prio_Month', 'Count']], height=400, hide_index=True)

# --- 4. EXPERT SEARCH (RESTORED) ---
elif menu == "Expert Search":
    st.header("🔍 Registry Search")
    query = st.text_input("Enter Keyword (Title, Number, IPC, Country):")
    if query:
        mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False, na=False)).any(axis=1)
        st.dataframe(df[mask][['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date', 'Earliest Priority Date']], use_container_width=True, hide_index=True)
