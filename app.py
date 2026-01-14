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

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #002147; color: white; }
    h1, h2, h3 { color: #002147; }
    </style>
""", unsafe_allow_html=True)

# --- DATA REFINEMENT ENGINE ---
def refine_data(df):
    df.columns = df.columns.str.strip()
    if 'Application Date' in df.columns:
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df['Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
        df['Month'] = df['Application Date'].dt.month_name()
        # IMPROVED LABELS: Changed format to YYYY-Mon (e.g., 2024-Jan)
        df['Period'] = df['Application Date'].dt.strftime('%Y-%b')
        
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df['Priority_Year'] = df['Earliest Priority Date'].dt.year.fillna(0).astype(int)
        df['Priority_Month'] = df['Earliest Priority Date'].dt.month_name()
        # IMPROVED LABELS: Changed format to YYYY-Mon (e.g., 2024-Jan)
        df['Priority_Period'] = df['Earliest Priority Date'].dt.strftime('%Y-%b')
        
    if 'Classification' in df.columns:
        df['Primary_IPC'] = df['Classification'].astype(str).str.split(',').str[0].str.strip()
        # Extract Section (A, B, C, etc.)
        df['IPC_Section'] = df['Primary_IPC'].str[0].str.upper()
        df['Primary_IPC_Short'] = df['Primary_IPC'].str[:4]
        
    return df

# --- SIDEBAR & LOADING ---
with st.sidebar:
    try:
        logo = Image.open("logo.jpeg")
        st.image(logo, use_container_width=True)
    except:
        st.title("🏛️ ARCHISTRATEGOS")
    st.markdown("---")
    data_source = st.radio("Select Data Source:", ["Default UAE Dataset", "Upload Custom CSV"])

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
    selected_country = st.sidebar.multiselect("Filter by Country", sorted(df['Country Name (Priority)'].dropna().unique()))
    filtered_df = df.copy()
    if selected_country:
        filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_country)]

    # --- MODULE 1: TIME-SERIES GROWTH ---
    if menu == "Time-Series Growth":
        st.header("📈 Growth Trends & Temporal Analysis")
        
        # 1. BAR GRAPH (APP DATE)
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Total Applications per Year (Application Date)")
            yearly_counts = filtered_df[filtered_df['Year'] >= 1990].groupby('Year').size().reset_index(name='Count')
            fig_bar = px.bar(yearly_counts, x='Year', y='Count', text='Count', color_discrete_sequence=['#3498db'])
            fig_bar.update_traces(textposition='outside', textfont=dict(family="Arial Black"))
            st.plotly_chart(fig_bar, use_container_width=True)
        with col2:
            st.subheader("Yearly Registry")
            st.dataframe(yearly_counts.sort_values('Year', ascending=False), use_container_width=True, hide_index=True)

        st.markdown("---")

        # 2. YEARLY TREND (APP DATE - ORANGE)
        st.subheader("📉 Yearly Application Trend (Line View)")
        fig_app_line = px.line(yearly_counts, x='Year', y='Count', markers=True, text='Count')
        fig_app_line.update_traces(line=dict(color='#FF3300', width=4), textposition='top center', textfont=dict(family="Arial Black", color="white"))
        st.plotly_chart(fig_app_line, use_container_width=True)

        # 3. CONTINUOUS MONTHLY (APP DATE - CYAN)
        st.subheader("📅 Full Historical Monthly Trend (Application Date)")
        app_monthly = filtered_df[filtered_df['Year'] > 0].sort_values('Application Date').groupby('Period', sort=False).size().reset_index(name='Count')
        fig_app_monthly = px.line(app_monthly, x='Period', y='Count', markers=True, text='Count')
        fig_app_monthly.update_traces(line=dict(color='#00FFFF', width=3), textposition='top center', textfont=dict(size=10, color="white", family="Arial Black"))
        # Rotate x-axis labels for readability
        fig_app_monthly.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_app_monthly, use_container_width=True)

        st.markdown("---")

        # 4. YEARLY TREND (PRIORITY DATE - LIME)
        st.subheader("🌍 Yearly Global Priority Trend (Invention Date)")
        priority_yearly = filtered_df[filtered_df['Priority_Year'] >= 1990].groupby('Priority_Year').size().reset_index(name='Count')
        fig_prio_line = px.line(priority_yearly, x='Priority_Year', y='Count', markers=True, text='Count')
        fig_prio_line.update_traces(line=dict(color='#33FF00', width=4), textposition='top center', textfont=dict(family="Arial Black", color="white"))
        st.plotly_chart(fig_prio_line, use_container_width=True)

        # 5. CONTINUOUS MONTHLY (PRIORITY DATE - MAGENTA)
        st.subheader("📅 Full Historical Monthly Trend (Earliest Priority Date)")
        prio_monthly = filtered_df[filtered_df['Priority_Year'] > 0].sort_values('Earliest Priority Date').groupby('Priority_Period', sort=False).size().reset_index(name='Count')
        fig_prio_monthly = px.line(prio_monthly, x='Priority_Period', y='Count', markers=True, text='Count')
        fig_prio_monthly.update_traces(line=dict(color='#FF00FF', width=3), textposition='top center', textfont=dict(size=10, color="white", family="Arial Black"))
        fig_prio_monthly.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_prio_monthly, use_container_width=True)

        st.markdown("---")

        # 6. MONTHLY FOCUS
        selected_year = st.sidebar.selectbox("Focus Year Detail", sorted(df[df['Year'] > 0]['Year'].unique(), reverse=True))
        if selected_year:
            st.subheader(f"Monthly Distribution for {selected_year}")
            year_df = filtered_df[filtered_df['Year'] == selected_year]
            month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
            m_counts = year_df.groupby('Month').size().reindex(month_order, fill_value=0).reset_index(name='Count')
            fig_m = px.line(m_counts, x='Month', y='Count', markers=True, text='Count')
            fig_m.update_traces(textposition='top center', textfont=dict(family="Arial Black", color="white"))
            st.plotly_chart(fig_m, use_container_width=True)

    # --- MODULE 3: GLOBAL PRIORITY & COMPARISONS ---
    elif menu == "Global Priority & Comparisons":
        st.header("🏁 Global Priority Analysis")
        valid_p = df[df['Priority_Year'] > 1900]['Priority_Year']
        p_range = st.sidebar.slider("Select Priority Year Range", int(valid_p.min()), int(valid_p.max()), (int(valid_p.max()-5), int(valid_p.max())))
        p_df = filtered_df[(filtered_df['Priority_Year'] >= p_range[0]) & (filtered_df['Priority_Year'] <= p_range[1])]
        
        col_chart, col_table = st.columns([2, 1])
        with col_chart:
            st.subheader("Monthly Filing Volume (Grouped by Year)")
            month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
            actual = p_df.groupby(['Priority_Year', 'Priority_Month']).size().reset_index(name='Number of Applications')
            actual['Priority_Year'] = actual['Priority_Year'].astype(str)
            fig_prio_bar = px.bar(actual, x='Priority_Month', y='Number of Applications', color='Priority_Year', barmode='group', text='Number of Applications', category_orders={"Priority_Month": month_order})
            st.plotly_chart(fig_prio_bar, use_container_width=True)
            
        with col_table:
            st.subheader("📌 Yearly Summary")
            summary_p = p_df.groupby('Priority_Year').size().reset_index(name='Number of Applications')
            st.dataframe(summary_p.sort_values('Priority_Year', ascending=False), use_container_width=True, hide_index=True)
            
            st.subheader("📅 Monthly Breakdown")
            detail_p = p_df.groupby(['Priority_Year', 'Priority_Month']).size().reset_index(name='Number of Applications')
            detail_p['Month_Num'] = pd.to_datetime(detail_p['Priority_Month'], format='%B').dt.month
            st.dataframe(detail_p.sort_values(['Priority_Year', 'Month_Num'], ascending=[False, True])[['Priority_Year', 'Priority_Month', 'Number of Applications']], use_container_width=True, height=400, hide_index=True)

    # --- CLASSIFICATION & EXPERT SEARCH ---
    elif menu == "Classification & Country Strength":
        st.header("🌍 IPC Strength & Country Activity")
        
        # NEW: IPC SECTION HISTOGRAM (A-H)
        st.subheader("📊 Distribution of IPC Sections (A to H)")
        ipc_sections = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        section_counts = filtered_df[filtered_df['IPC_Section'].isin(ipc_sections)].groupby('IPC_Section').size().reindex(ipc_sections, fill_value=0).reset_index(name='Count')
        
        fig_ipc_hist = px.bar(section_counts, x='IPC_Section', y='Count', text='Count', color='IPC_Section', color_discrete_sequence=px.colors.qualitative.Prism)
        fig_ipc_hist.update_layout(showlegend=False, xaxis_title="IPC Section", yaxis_title="Number of Patents")
        fig_ipc_hist.update_traces(textposition='outside', textfont=dict(family="Arial Black"))
        st.plotly_chart(fig_ipc_hist, use_container_width=True)
        
        st.markdown("---")
        
        all_ipcs = [x for x in sorted(filtered_df['Primary_IPC_Short'].dropna().unique()) if x != "Ther"]
        target_ipc = st.selectbox("Detailed IPC Sector:", all_ipcs)
        leader_counts = filtered_df[filtered_df['Primary_IPC_Short'] == target_ipc].groupby('Country Name (Priority)').size().reset_index(name='Count').sort_values('Count', ascending=False)
        fig_leader = px.bar(leader_counts, x='Country Name (Priority)', y='Count', text='Count', color_discrete_sequence=['#e74c3c'])
        st.plotly_chart(fig_leader, use_container_width=True)

    elif menu == "Expert Search":
        st.header("🔍 Identify Experts")
        search = st.text_input("Search Registry:")
        if search:
            mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
            st.dataframe(filtered_df[mask][['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date', 'Priority_Year']], use_container_width=True, hide_index=True)
