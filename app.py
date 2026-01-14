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
    h1, h2, h3 { color: #002147; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- DATA REFINEMENT ENGINE ---
def refine_data(df):
    df.columns = df.columns.str.strip()
    if 'Application Date' in df.columns:
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df['App_Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
        df['App_Month'] = df['Application Date'].dt.month_name()
        # Formatting for X-Axis Labels: "Jan 2023"
        df['App_Period_Label'] = df['Application Date'].dt.strftime('%b %Y')
        df['App_Period_Sort'] = df['Application Date'].dt.to_period('M')
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df['Prio_Year'] = df['Earliest Priority Date'].dt.year.fillna(0).astype(int)
        df['Prio_Month'] = df['Earliest Priority Date'].dt.month_name()
        # Formatting for X-Axis Labels: "Jan 2023"
        df['Prio_Period_Label'] = df['Earliest Priority Date'].dt.strftime('%b %Y')
        df['Prio_Period_Sort'] = df['Earliest Priority Date'].dt.to_period('M')
    if 'Classification' in df.columns:
        df['Primary_IPC'] = df['Classification'].astype(str).str.split(',').str[0].str.strip()
        df['IPC_Section'] = df['Primary_IPC'].str[0].str.upper()
    return df

# --- SIDEBAR & LOADING ---
with st.sidebar:
    try:
        logo = Image.open("logo.jpeg")
        st.image(logo, use_container_width=True)
    except:
        st.title("🏛️ ARCHISTRATEGOS")
    st.markdown("---")
    data_source = st.sidebar.radio("Data Source:", ["Default UAE Dataset", "Upload Custom CSV"])

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

    if menu == "Time-Series Growth":
        st.header("📈 Growth Trends & Temporal Analysis")
        
        # BAR CHART (APPLICATION)
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Yearly Filing Volume (Application Date)")
            y_counts = filtered_df[filtered_df['App_Year'] >= 1990].groupby('App_Year').size().reset_index(name='Count')
            fig_bar = px.bar(y_counts, x='App_Year', y='Count', text='Count', color_discrete_sequence=['#3498db'])
            fig_bar.update_traces(textposition='outside', textfont=dict(family="Arial Black"))
            st.plotly_chart(fig_bar, use_container_width=True)
        with col2:
            st.subheader("Application Data Registry")
            st.dataframe(y_counts.sort_values('App_Year', ascending=False), use_container_width=True, hide_index=True)

        st.markdown("---")
        # APPLICATION TRENDS (ORANGE & CYAN)
        st.subheader("📉 Yearly Growth: Application Date (UAE Filing)")
        fig_app_y = px.line(y_counts, x='App_Year', y='Count', markers=True, text='Count')
        fig_app_y.update_traces(line=dict(color='#FF3300', width=4), textposition='top center', textfont=dict(family="Arial Black", color="white"))
        st.plotly_chart(fig_app_y, use_container_width=True)

        st.subheader("📅 Monthly Continuous: Application Date (UAE Filing)")
        # Grouping with labels and sorting period
        app_m = filtered_df[filtered_df['App_Year'] > 0].groupby(['App_Period_Sort', 'App_Period_Label']).size().reset_index(name='Count')
        app_m = app_m.sort_values('App_Period_Sort')
        fig_app_m = px.line(app_m, x='App_Period_Label', y='Count', markers=True, text='Count')
        fig_app_m.update_traces(line=dict(color='#00FFFF', width=3), textposition='top center', textfont=dict(size=10, color="white", family="Arial Black"))
        fig_app_m.update_xaxes(tickangle=45)
        st.plotly_chart(fig_app_m, use_container_width=True)

        st.markdown("---")
        # PRIORITY TRENDS (LIME & MAGENTA)
        st.subheader("🌍 Yearly Growth: Earliest Priority Date (Global Invention)")
        prio_y = filtered_df[filtered_df['Prio_Year'] >= 1990].groupby('Prio_Year').size().reset_index(name='Count')
        fig_prio_y = px.line(prio_y, x='Prio_Year', y='Count', markers=True, text='Count')
        fig_prio_y.update_traces(line=dict(color='#33FF00', width=4), textposition='top center', textfont=dict(family="Arial Black", color="white"))
        st.plotly_chart(fig_prio_y, use_container_width=True)

        st.subheader("📅 Monthly Continuous: Earliest Priority Date (Global Invention)")
        prio_m = filtered_df[filtered_df['Prio_Year'] > 0].groupby(['Prio_Period_Sort', 'Prio_Period_Label']).size().reset_index(name='Count')
        prio_m = prio_m.sort_values('Prio_Period_Sort')
        fig_prio_m = px.line(prio_m, x='Prio_Period_Label', y='Count', markers=True, text='Count')
        fig_prio_m.update_traces(line=dict(color='#FF00FF', width=3), textposition='top center', textfont=dict(size=10, color="white", family="Arial Black"))
        fig_prio_m.update_xaxes(tickangle=45)
        st.plotly_chart(fig_prio_m, use_container_width=True)

    # --- ALL OTHER MODULES (INTACT) ---
    elif menu == "Classification & Country Strength":
        st.header("🌍 IPC Strength & Sector Analysis")
        st.subheader("Histogram: High-Level IPC Sections (Earliest Priority Section)")
        ipc_counts = filtered_df['IPC_Section'].value_counts().reset_index(name='Count').sort_values('IPC_Section')
        fig_hist = px.bar(ipc_counts, x='IPC_Section', y='Count', text='Count', color='IPC_Section', color_discrete_sequence=px.colors.qualitative.Vivid)
        fig_hist.update_traces(textposition='outside', textfont=dict(family="Arial Black"))
        st.plotly_chart(fig_hist, use_container_width=True)
        
        st.markdown("---")
        target_ipc = st.selectbox("Select Specific IPC Code for Country Breakdown:", [x for x in sorted(filtered_df['Primary_IPC'].dropna().unique()) if len(str(x)) > 1])
        lead_df = filtered_df[filtered_df['Primary_IPC'] == target_ipc].groupby('Country Name (Priority)').size().reset_index(name='Count').sort_values('Count', ascending=False)
        st.plotly_chart(px.bar(lead_df, x='Country Name (Priority)', y='Count', text='Count', color_discrete_sequence=['#e74c3c']), use_container_width=True)

    elif menu == "Global Priority & Comparisons":
        st.header("🏁 Global Priority Analysis (Earliest Priority Date)")
        v_p = df[df['Prio_Year'] > 1900]['Prio_Year']
        p_rng = st.sidebar.slider("Priority Date Filter", int(v_p.min()), int(v_p.max()), (int(v_p.max()-5), int(v_p.max())))
        p_df = filtered_df[(filtered_df['Prio_Year'] >= p_rng[0]) & (filtered_df['Prio_Year'] <= p_rng[1])]
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Monthly filing volume by Priority Year")
            mo = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
            act = p_df.groupby(['Prio_Year', 'Prio_Month']).size().reset_index(name='Count')
            act['Prio_Year'] = act['Prio_Year'].astype(str)
            st.plotly_chart(px.bar(act, x='Prio_Month', y='Count', color='Prio_Year', barmode='group', text='Count', category_orders={"Prio_Month": mo}), use_container_width=True)
        with c2:
            st.subheader("📌 Yearly Totals (Priority)")
            st.dataframe(p_df.groupby('Prio_Year').size().reset_index(name='Total Count').sort_values('Prio_Year', ascending=False), use_container_width=True, hide_index=True)
            st.subheader("📅 Monthly Detailed Counts (Priority)")
            det_p = p_df.groupby(['Prio_Year', 'Prio_Month']).size().reset_index(name='Count')
            det_p['M_N'] = pd.to_datetime(det_p['Prio_Month'], format='%B').dt.month
            st.dataframe(det_p.sort_values(['Prio_Year', 'M_N'], ascending=[False, True])[['Prio_Year', 'Prio_Month', 'Count']], use_container_width=True, height=400, hide_index=True)

    elif menu == "Expert Search":
        st.header("🔍 Identify Experts")
        query = st.text_input("Search Registry:")
        if query:
            mask = filtered_df.astype(str).apply(lambda x: x.str.contains(query, case=False, na=False)).any(axis=1)
            st.dataframe(filtered_df[mask][['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date', 'Earliest Priority Date']], use_container_width=True, hide_index=True)
