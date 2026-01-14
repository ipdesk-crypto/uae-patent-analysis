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
    st.markdown("<h1 style='text-align: center; color: #FF6600;'>🏛️ ARCHISTRATEGOS</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.text_input("Access Key:", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("Invalid Key.")
    return False

if not check_password():
    st.stop()

st.set_page_config(page_title="UAE Patent Analysis Pro", layout="wide", page_icon="🏛️")

# --- DATA REFINEMENT ENGINE ---
def refine_data(df):
    df.columns = df.columns.str.strip()
    
    # Process Application Date
    if 'Application Date' in df.columns:
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df = df.dropna(subset=['Application Date'])
        df['App_Year'] = df['Application Date'].dt.year.astype(int)
        df['App_Month'] = df['Application Date'].dt.month_name()
        df['App_Period_Sort'] = df['Application Date'].dt.to_period('M')

    # Process Priority Date
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df = df.dropna(subset=['Earliest Priority Date'])
        df['Prio_Year'] = df['Earliest Priority Date'].dt.year.astype(int)
        df['Prio_Month'] = df['Earliest Priority Date'].dt.month_name()
        df['Prio_Period_Sort'] = df['Earliest Priority Date'].dt.to_period('M')

    if 'Classification' in df.columns:
        df['Primary_IPC'] = df['Classification'].astype(str).str.split(',').str[0].str.strip()
        df['IPC_Section'] = df['Primary_IPC'].str[0].str.upper()
        # STRICT FILTER: A-H ONLY (No T)
        df = df[df['IPC_Section'].isin(['A','B','C','D','E','F','G','H'])]
    return df

def pad_months(df, date_col_prefix):
    """Fills missing months with 0s for a continuous timeline."""
    if df.empty: return df
    sort_col = f'{date_col_prefix}_Period_Sort'
    min_date = df[sort_col].min().to_timestamp()
    max_date = df[sort_col].max().to_timestamp()
    full_range = pd.date_range(start=min_date, end=max_date, freq='MS')
    template = pd.DataFrame({sort_col: full_range.to_period('M')})
    counts = df.groupby(sort_col).size().reset_index(name='Count')
    padded = pd.merge(template, counts, on=sort_col, how='left').fillna(0)
    # Convert Period back to Timestamp for Plotly to use dtick properly
    padded['Date'] = padded[sort_col].dt.to_timestamp()
    return padded

# --- LOADING ---
try:
    df = refine_data(pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv"))
except:
    st.error("Data File Error.")
    st.stop()

if df is not None:
    menu = st.sidebar.radio("Go to:", ["Time-Series Growth", "Classification & Country Strength", "Global Priority & Comparisons", "Expert Search"])
    f_df = df.copy()

    if menu == "Time-Series Growth":
        st.header("📈 Growth Trends & Temporal Analysis")
        
        # YEARLY BAR
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Yearly Filing Volume (Application Date)")
            y_counts = f_df.groupby('App_Year').size().reset_index(name='Count')
            st.plotly_chart(px.bar(y_counts, x='App_Year', y='Count', text='Count', color_discrete_sequence=['#3498db']), use_container_width=True)
        with c2:
            st.subheader("Registry")
            st.dataframe(y_counts.sort_values('App_Year', ascending=False), use_container_width=True, hide_index=True)

        st.markdown("---")
        # CONTINUOUS APPLICATION (CYAN - ALL MONTHS LABELED)
        st.subheader("📅 Full Monthly Sequence: Application Date (Forced Labels)")
        app_padded = pad_months(f_df, 'App')
        fig_app_m = px.line(app_padded, x='Date', y='Count', markers=True, text='Count')
        fig_app_m.update_traces(line=dict(color='#00FFFF', width=3), textposition='top center', textfont=dict(color="white"))
        fig_app_m.update_xaxes(
            dtick="M1", # Force every single month
            tickformat="%b\n%Y", # Format: Jan 2023
            tickangle=0,
            showgrid=True
        )
        st.plotly_chart(fig_app_m, use_container_width=True)

        st.markdown("---")
        # CONTINUOUS PRIORITY (MAGENTA - ALL MONTHS LABELED)
        st.subheader("📅 Full Monthly Sequence: Earliest Priority Date (Forced Labels)")
        prio_padded = pad_months(f_df, 'Prio')
        fig_prio_m = px.line(prio_padded, x='Date', y='Count', markers=True, text='Count')
        fig_prio_m.update_traces(line=dict(color='#FF00FF', width=3), textposition='top center', textfont=dict(color="white"))
        fig_prio_m.update_xaxes(
            dtick="M1", 
            tickformat="%b\n%Y",
            tickangle=0,
            showgrid=True
        )
        st.plotly_chart(fig_prio_m, use_container_width=True)

        st.markdown("---")
        # YEAR SELECTOR DETAIL
        st.subheader("🔍 Monthly Detail Line Graph per Selected Year")
        focus_yr = st.selectbox("Choose Year:", sorted(f_df['App_Year'].unique(), reverse=True))
        if focus_yr:
            m_df = f_df[f_df['App_Year'] == focus_yr]
            mo_list = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
            m_counts = m_df.groupby('App_Month').size().reindex(mo_list, fill_value=0).reset_index(name='Count')
            st.plotly_chart(px.line(m_counts, x='App_Month', y='Count', markers=True, text='Count').update_traces(line=dict(color='#f1c40f', width=4)), use_container_width=True)

    elif menu == "Classification & Country Strength":
        st.header("🌍 IPC Sector Analysis (Standard A-H)")
        sec_counts = f_df['IPC_Section'].value_counts().reset_index(name='Count').sort_values('IPC_Section')
        st.plotly_chart(px.bar(sec_counts, x='IPC_Section', y='Count', text='Count', color='IPC_Section'), use_container_width=True)

    elif menu == "Global Priority & Comparisons":
        st.header("🏁 Global Priority Analysis")
        # [Priority Tables & Grouped Bars Intact]
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
