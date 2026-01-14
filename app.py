import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Analysis Pro", layout="wide", page_icon="🇦🇪")

# --- DATA REFINEMENT ENGINE ---
def refine_data(df):
    """Preserves existing cleaning logic and adds priority-based time features."""
    # 1. Date processing for Application Date
    if 'Application Date' in df.columns:
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df['Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
        df['Month'] = df['Application Date'].dt.month_name()
        df['YearMonth'] = df['Application Date'].dt.to_period('M').astype(str)
    
    # 2. Date processing for Earliest Priority Date (THE BASE FOR GLOBAL PRIORITY)
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df['Priority_Year'] = df['Earliest Priority Date'].dt.year.fillna(0).astype(int)
        df['Priority_Month'] = df['Earliest Priority Date'].dt.month_name()
    
    # 3. IPC Cleaning
    if 'Classification' in df.columns:
        df['Primary_IPC'] = df['Classification'].astype(str).str.split(',').str[0].str.strip().str[:4]
        df = df[df['Primary_IPC'] != "Ther"] 
    
    # 4. Priority Lag Calculation
    if 'Earliest Priority Date' in df.columns and 'Application Date' in df.columns:
        df['Priority_Lag_Days'] = (df['Application Date'] - df['Earliest Priority Date']).dt.days
        
    return df

# --- SIDEBAR: DATA SOURCE ---
st.sidebar.title("📁 Data Management")
data_source = st.sidebar.radio("Select Data Source:", ["Default UAE Dataset", "Upload Custom CSV"])

df = None
if data_source == "Upload Custom CSV":
    uploaded_file = st.sidebar.file_uploader("Upload your patent data CSV", type="csv")
    if uploaded_file:
        df = refine_data(pd.read_csv(uploaded_file))
else:
    try:
        df = refine_data(pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv"))
    except FileNotFoundError:
        st.error("Default dataset not found. Please upload a CSV.")
        st.stop()

# --- SIDEBAR: NAVIGATION & FILTERS ---
st.sidebar.markdown("---")
st.sidebar.title("🛠️ Analysis Tools")
menu = st.sidebar.radio("Go to:", ["Time-Series Growth", "Classification & Country Strength", "Global Priority & Comparisons", "Expert Search"])

# Global Date Filter for Priority Analysis (Slider)
if df is not None and 'Priority_Year' in df.columns:
    valid_p_years = df[df['Priority_Year'] > 1900]['Priority_Year']
    min_p, max_p = int(valid_p_years.min()), int(valid_p_years.max())
    st.sidebar.subheader("📅 Priority Year Filter")
    p_year_range = st.sidebar.slider("Select Range for Priority Charts", min_p, max_p, (max_p - 5, max_p))

# Dynamic Country Filter
all_countries = sorted(df['Country Name (Priority)'].dropna().unique()) if 'Country Name (Priority)' in df.columns else []
selected_country = st.sidebar.multiselect("Filter by Country", all_countries)

# Applying Filter
filtered_df = df.copy()
if selected_country:
    filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_country)]

# --- MAIN DASHBOARD ---
st.title("🇦🇪 UAE Patent Analysis Engine (Type 5)")

if menu == "Time-Series Growth":
    st.header("📈 Growth Trends")
    c1, c2 = st.columns(2)
    with c1:
        yearly = filtered_df[filtered_df['Year'] > 1999].groupby('Year').size().reset_index(name='Total')
        fig = px.bar(yearly, x='Year', y='Total', text_auto=True, title="UAE Filing Volume", color_discrete_sequence=['#3498db'])
        fig.update_yaxes(nticks=15)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        growth_data = filtered_df.groupby('YearMonth').size().reset_index(name='Count')
        growth_data['MA12'] = growth_data['Count'].rolling(window=12).mean()
        fig_ma = px.line(growth_data, x='YearMonth', y='MA12', title="12-Month Market Velocity")
        st.plotly_chart(fig_ma, use_container_width=True)

elif menu == "Classification & Country Strength":
    st.header("🌍 IPC Strength & Country Activity")
    heat_df = filtered_df.groupby(['Country Name (Priority)', 'Primary_IPC']).size().reset_index(name='Apps')
    top_ipcs = heat_df.groupby('Primary_IPC')['Apps'].sum().nlargest(20).index
    heat_df_top = heat_df[heat_df['Primary_IPC'].isin(top_ipcs)]
    st.plotly_chart(px.density_heatmap(heat_df_top, x="Primary_IPC", y="Country Name (Priority)", z="Apps", text_auto=True, color_continuous_scale="Viridis"), use_container_width=True)

elif menu == "Global Priority & Comparisons":
    st.header("🏁 Global Priority vs Country & Classification")
    st.info(f"Analysis Scope: Priority Years {p_year_range[0]} to {p_year_range[1]}")

    # Slider Filter Application
    p_filtered = filtered_df[(filtered_df['Priority_Year'] >= p_year_range[0]) & (filtered_df['Priority_Year'] <= p_year_range[1])]

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Invention Volume by Priority Year")
        p_counts = p_filtered.groupby('Priority_Year').size().reset_index(name='Count')
        fig_p = px.area(p_counts, x='Priority_Year', y='Count', color_discrete_sequence=['#27ae60'])
        fig_p.update_yaxes(nticks=20)
        st.plotly_chart(fig_p, use_container_width=True)

    with c2:
        st.subheader("Monthly Priority: All 12 Months Comparison")
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        
        # LOGIC TO ENSURE ALL 12 MONTHS APPEAR
        years_in_range = range(p_year_range[0], p_year_range[1] + 1)
        template = pd.MultiIndex.from_product([years_in_range, month_order], names=['Priority_Year', 'Priority_Month']).to_frame(index=False)
        
        actual_counts = p_filtered.groupby(['Priority_Year', 'Priority_Month']).size().reset_index(name='Apps')
        p_month_counts = pd.merge(template, actual_counts, on=['Priority_Year', 'Priority_Month'], how='left').fillna(0)
        p_month_counts['Priority_Year'] = p_month_counts['Priority_Year'].astype(str) # For discrete colors
        
        fig_p_month = px.bar(
            p_month_counts, x='Priority_Month', y='Apps', color='Priority_Year',
            barmode='group', text_auto=True,
            category_orders={"Priority_Month": month_order},
            labels={'Apps': 'No. of Applications', 'Priority_Month': 'Month'},
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_p_month.update_yaxes(nticks=15)
        st.plotly_chart(fig_p_month, use_container_width=True)

    st.subheader("Priority Distribution by Country")
    top_10 = p_filtered['Country Name (Priority)'].value_counts().nlargest(10).index
    fig_box = px.box(p_filtered[p_filtered['Country Name (Priority)'].isin(top_10)], x='Priority_Year', y='Country Name (Priority)', color='Country Name (Priority)')
    fig_box.update_xaxes(nticks=20)
    st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("Technology Evolution (Based on Priority)")
    top_5_ipcs = p_filtered['Primary_IPC'].value_counts().nlargest(5).index
    ipc_trend = p_filtered[p_filtered['Primary_IPC'].isin(top_5_ipcs)].groupby(['Priority_Year', 'Primary_IPC']).size().reset_index(name='Count')
    st.plotly_chart(px.line(ipc_trend, x='Priority_Year', y='Count', color='Primary_IPC', markers=True), use_container_width=True)

elif menu == "Expert Search":
    st.header("🔍 Expert Search")
    search = st.text_input("Search IPC, Applicant, or Keywords...")
    if search:
        results = filtered_df[filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        st.dataframe(results[['Application Number', 'Title', 'Primary_IPC', 'Priority_Year']], use_container_width=True)
