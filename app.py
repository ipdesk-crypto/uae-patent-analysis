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

# --- DATA REFINEMENT & 12-MONTH PADDING ENGINE ---
def refine_data(df):
    df.columns = df.columns.str.strip()
    
    # 1. APPLICATION DATE LOGIC
    if 'Application Date' in df.columns:
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df = df.dropna(subset=['Application Date'])
        df['App_Year'] = df['Application Date'].dt.year.astype(int)
        df['App_Month'] = df['Application Date'].dt.month_name()
        df['App_Period_Sort'] = df['Application Date'].dt.to_period('M')

    # 2. PRIORITY DATE LOGIC
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df = df.dropna(subset=['Earliest Priority Date'])
        df['Prio_Year'] = df['Earliest Priority Date'].dt.year.astype(int)
        df['Prio_Month'] = df['Earliest Priority Date'].dt.month_name()
        df['Prio_Period_Sort'] = df['Earliest Priority Date'].dt.to_period('M')

    if 'Classification' in df.columns:
        df['Primary_IPC'] = df['Classification'].astype(str).str.split(',').str[0].str.strip()
        df['IPC_Section'] = df['Primary_IPC'].str[0].str.upper()
    return df

def pad_months(df, date_col_prefix):
    """Ensures all months exist in the range, filling missing with 0."""
    if df.empty: return df
    year_col = f'{date_col_prefix}_Year'
    sort_col = f'{date_col_prefix}_Period_Sort'
    
    min_date = df[sort_col].min().to_timestamp()
    max_date = df[sort_col].max().to_timestamp()
    full_range = pd.date_range(start=min_date, end=max_date, freq='MS')
    
    template = pd.DataFrame({sort_col: full_range.to_period('M')})
    counts = df.groupby(sort_col).size().reset_index(name='Count')
    
    padded = pd.merge(template, counts, on=sort_col, how='left').fillna(0)
    padded['Label'] = padded[sort_col].dt.strftime('%b %Y')
    return padded

# --- LOADING ---
with st.sidebar:
    try:
        logo = Image.open("logo.jpeg")
        st.image(logo, use_container_width=True)
    except:
        st.title("🏛️ ARCHISTRATEGOS")
    data_source = st.radio("Source:", ["Default UAE Dataset", "Upload Custom CSV"])

try:
    if data_source == "Upload Custom CSV":
        uploaded_file = st.sidebar.file_uploader("Upload CSV", type="csv")
        df = refine_data(pd.read_csv(uploaded_file)) if uploaded_file else None
    else:
        df = refine_data(pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv"))
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

if df is not None:
    menu = st.sidebar.radio("Go to:", ["Time-Series Growth", "Classification & Country Strength", "Global Priority & Comparisons", "Expert Search"])
    selected_country = st.sidebar.multiselect("Filter by Country", sorted(df['Country Name (Priority)'].dropna().unique()))
    f_df = df.copy()
    if selected_country:
        f_df = f_df[f_df['Country Name (Priority)'].isin(selected_country)]

    # --- 1. TIME-SERIES GROWTH ---
    if menu == "Time-Series Growth":
        st.header("📈 Growth Trends & Temporal Analysis")
        
        # BAR CHART
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Yearly Filing Volume (Application Date)")
            y_counts = f_df.groupby('App_Year').size().reset_index(name='Count')
            fig_bar = px.bar(y_counts, x='App_Year', y='Count', text='Count', color_discrete_sequence=['#3498db'])
            fig_bar.update_traces(textposition='outside', textfont=dict(family="Arial Black"))
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            st.subheader("Registry")
            st.dataframe(y_counts.sort_values('App_Year', ascending=False), use_container_width=True, hide_index=True)

        st.markdown("---")
        # APPLICATION TRENDS (CYAN/ORANGE)
        st.subheader("📉 Yearly Growth: Application Date")
        fig_app_y = px.line(y_counts, x='App_Year', y='Count', markers=True, text='Count')
        fig_app_y.update_traces(line=dict(color='#FF3300', width=4), textfont=dict(color="white"))
        st.plotly_chart(fig_app_y, use_container_width=True)

        st.subheader("📅 Monthly Continuous (Application Date) - 12 Months Included")
        app_padded = pad_months(f_df, 'App')
        fig_app_m = px.line(app_padded, x='Label', y='Count', markers=True, text='Count')
        fig_app_m.update_traces(line=dict(color='#00FFFF', width=3), textfont=dict(size=9, color="white"))
        fig_app_m.update_xaxes(tickangle=45)
        st.plotly_chart(fig_app_m, use_container_width=True)

        st.markdown("---")
        # PRIORITY TRENDS (LIME/MAGENTA)
        st.subheader("🌍 Yearly Growth: Earliest Priority Date")
        prio_y_counts = f_df.groupby('Prio_Year').size().reset_index(name='Count')
        fig_prio_y = px.line(prio_y_counts, x='Prio_Year', y='Count', markers=True, text='Count')
        fig_prio_y.update_traces(line=dict(color='#33FF00', width=4), textfont=dict(color="white"))
        st.plotly_chart(fig_prio_y, use_container_width=True)

        st.subheader("📅 Monthly Continuous (Earliest Priority Date) - 12 Months Included")
        prio_padded = pad_months(f_df, 'Prio')
        fig_prio_m = px.line(prio_padded, x='Label', y='Count', markers=True, text='Count')
        fig_prio_m.update_traces(line=dict(color='#FF00FF', width=3), textfont=dict(size=9, color="white"))
        fig_prio_m.update_xaxes(tickangle=45)
        st.plotly_chart(fig_prio_m, use_container_width=True)

        st.markdown("---")
        # RESTORED: SELECTABLE YEARLY DETAIL
        st.subheader("🔍 Monthly Detail Line Graph per Selected Year")
        focus_yr = st.selectbox("Choose Year to Analyze:", sorted(f_df['App_Year'].unique(), reverse=True))
        if focus_yr:
            m_df = f_df[f_df['App_Year'] == focus_yr]
            mo_list = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
            m_counts = m_df.groupby('App_Month').size().reindex(mo_list, fill_value=0).reset_index(name='Count')
            fig_focus = px.line(m_counts, x='App_Month', y='Count', markers=True, text='Count', title=f"Application Distribution for {focus_yr}")
            fig_focus.update_traces(line=dict(color='#f1c40f', width=4), textposition='top center', textfont=dict(color="white"))
            st.plotly_chart(fig_focus, use_container_width=True)

    # --- 2. CLASSIFICATION ---
    elif menu == "Classification & Country Strength":
        st.header("🌍 IPC Strength & Sector Analysis")
        st.subheader("Histogram: High-Level IPC Sections (A-H)")
        sec_counts = f_df['IPC_Section'].value_counts().reset_index(name='Count').sort_values('IPC_Section')
        st.plotly_chart(px.bar(sec_counts, x='IPC_Section', y='Count', text='Count', color='IPC_Section'), use_container_width=True)
        st.markdown("---")
        target_ipc = st.selectbox("Select IPC Code:", sorted(f_df['Primary_IPC'].unique()))
        lead_df = f_df[f_df['Primary_IPC'] == target_ipc].groupby('Country Name (Priority)').size().reset_index(name='Count').sort_values('Count', ascending=False)
        st.plotly_chart(px.bar(lead_df, x='Country Name (Priority)', y='Count', text='Count', color_discrete_sequence=['#e74c3c']), use_container_width=True)

    # --- 3. GLOBAL PRIORITY & COMPARISONS ---
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
            act['Prio_Year'] = act['Prio_Year'].astype(str)
            st.plotly_chart(px.bar(act, x='Prio_Month', y='Count', color='Prio_Year', barmode='group', text='Count', category_orders={"Prio_Month": mo}), use_container_width=True)
        with c2:
            st.subheader("📌 Yearly Summary")
            st.dataframe(p_df.groupby('Prio_Year').size().reset_index(name='Count').sort_values('Prio_Year', ascending=False), use_container_width=True, hide_index=True)
            st.subheader("📅 Monthly Breakdown")
            det_p = p_df.groupby(['Prio_Year', 'Prio_Month']).size().reset_index(name='Count')
            det_p['M_N'] = pd.to_datetime(det_p['Prio_Month'], format='%B').dt.month
            st.dataframe(det_p.sort_values(['Prio_Year', 'M_N'], ascending=[False, True])[['Prio_Year', 'Prio_Month', 'Count']], use_container_width=True, height=400, hide_index=True)

    elif menu == "Expert Search":
        st.header("🔍 Identify Experts")
        query = st.text_input("Search Registry:")
        if query:
            mask = f_df.astype(str).apply(lambda x: x.str.contains(query, case=False, na=False)).any(axis=1)
            st.dataframe(f_df[mask][['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date', 'Earliest Priority Date']], use_container_width=True, hide_index=True)
