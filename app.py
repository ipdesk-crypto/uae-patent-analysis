import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hmac

# --- ARCHISTRATEGOS BRANDING & SECURITY ---
def check_password():
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], "LeoGiannotti2026!"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.markdown("<h1 style='text-align: center; color: #1B263B; font-family: \"Garamond\", serif;'>🏛️ ARCHISTRATEGOS</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #C5A059;'>Strategic Intelligence Portal</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.text_input("Enter Access Key:", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("Access Denied. Incorrect Credentials.")
    return False

if not check_password():
    st.stop()

# --- STYLING ---
st.set_page_config(page_title="Archistrategos | UAE Patent Analytics", layout="wide", page_icon="🏛️")
A_NAVY = "#1B263B"
A_GOLD = "#C5A059"
A_GRAY = "#E0E1DD"

# --- DATA REFINEMENT ENGINE (FORCED YYYY-MM-DD) ---
def refine_data(df):
    df.columns = df.columns.str.strip()
    
    # Process Application Date
    if 'Application Date' in df.columns:
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df['Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
        df['Month'] = df['Application Date'].dt.month_name()
        # Create a string version for clean display
        df['Display_App_Date'] = df['Application Date'].dt.strftime('%Y-%m-%d')
    
    # Process Earliest Priority Date (STRICT YYYY-MM-DD)
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df['Priority_Year'] = df['Earliest Priority Date'].dt.year.fillna(0).astype(int)
        df['Priority_Month'] = df['Earliest Priority Date'].dt.month_name()
        # Forced Format for display
        df['Display_Priority_Date'] = df['Earliest Priority Date'].dt.strftime('%Y-%m-%d')
    
    if 'Classification' in df.columns:
        df['Primary_IPC'] = df['Classification'].astype(str).str.split(',').str[0].str.strip().str[:4]
    
    return df

# --- LOAD DATA ---
try:
    raw_df = pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv")
    df = refine_data(raw_df)
except:
    st.error("Database file missing.")
    st.stop()

# --- SIDEBAR ---
st.sidebar.markdown(f"<h2 style='color:{A_GOLD}; text-align:center;'>🏛️ ARCHISTRATEGOS</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")
menu = st.sidebar.radio("Module:", ["Time-Series Growth", "Classification & Country Strength", "Global Priority & Comparisons", "Expert Search"])

all_countries = sorted(df['Country Name (Priority)'].dropna().unique())
selected_country = st.sidebar.multiselect("Jurisdictions:", all_countries)

filtered_df = df.copy()
if selected_country:
    filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_country)]

# --- MODULES ---
if menu == "Time-Series Growth":
    st.header("📈 UAE Patent Growth Analysis")
    col1, col2 = st.columns([2, 1])
    with col1:
        yearly_counts = filtered_df[filtered_df['Year'] >= 1990].groupby('Year').size().reset_index(name='Number of Applications')
        fig = px.bar(yearly_counts, x='Year', y='Number of Applications', text='Number of Applications', color_discrete_sequence=[A_NAVY])
        fig.update_traces(textposition='outside', textfont=dict(size=14, family="Arial Black"))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Registry Summary")
        st.dataframe(yearly_counts.sort_values('Year', ascending=False), use_container_width=True, hide_index=True)

elif menu == "Classification & Country Strength":
    st.header("🌍 Technology Matrix")
    all_ipcs = [x for x in sorted(filtered_df['Primary_IPC'].dropna().unique()) if x != "Ther"]
    target_ipc = st.selectbox("IPC Sector:", all_ipcs)
    leader_counts = filtered_df[filtered_df['Primary_IPC'] == target_ipc].groupby('Country Name (Priority)').size().reset_index(name='Number of Applications').sort_values('Number of Applications', ascending=False)
    fig = px.bar(leader_counts, x='Country Name (Priority)', y='Number of Applications', text='Number of Applications', color='Number of Applications', color_continuous_scale=[A_GRAY, A_NAVY])
    fig.update_traces(textposition='outside', textfont=dict(family="Arial Black"))
    st.plotly_chart(fig, use_container_width=True)

elif menu == "Global Priority & Comparisons":
    st.header("🏁 International Priority Registry")
    valid_p = df[df['Priority_Year'] > 1900]['Priority_Year']
    p_range = st.sidebar.slider("Priority Range", int(valid_p.min()), int(valid_p.max()), (int(valid_p.max()-5), int(valid_p.max())))
    p_df = filtered_df[(filtered_df['Priority_Year'] >= p_range[0]) & (filtered_df['Priority_Year'] <= p_range[1])]
    
    col_chart, col_table = st.columns([2, 1])
    with col_chart:
        actual = p_df.groupby(['Priority_Year', 'Priority_Month']).size().reset_index(name='Number of Applications')
        fig = px.bar(actual, x='Priority_Month', y='Number of Applications', color='Priority_Year', barmode='group', text='Number of Applications', labels={'Number of Applications': 'Number of Applications'})
        fig.update_traces(textposition='outside', textfont=dict(family="Arial Black"))
        st.plotly_chart(fig, use_container_width=True)
    with col_table:
        st.subheader("Summary Table")
        summary = p_df.groupby('Priority_Year').size().reset_index(name='Number of Applications')
        st.dataframe(summary.sort_values('Priority_Year', ascending=False), use_container_width=True, hide_index=True)

elif menu == "Expert Search":
    st.header("🔍 Intelligence Query")
    search = st.text_input("Query Registry:")
    if search:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        # Using the Display Date columns for strict YYYY-MM-DD visibility
        results = filtered_df[mask][['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Display_App_Date', 'Display_Priority_Date']]
        results.columns = ['Application Number', 'Title', 'IPC', 'Country', 'Filing Date', 'Priority Date']
        st.dataframe(results, use_container_width=True, hide_index=True)
