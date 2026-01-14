import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Analysis Pro", layout="wide", page_icon="🇦🇪")

# --- DATA REFINEMENT ENGINE ---
def refine_data(df):
    """Cleans data and creates time-based features for analysis."""
    # 1. Date processing for Application Date
    if 'Application Date' in df.columns:
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df['Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
        df['Month'] = df['Application Date'].dt.month_name()
        df['YearMonth'] = df['Application Date'].dt.to_period('M').astype(str)
    
    # 2. Date processing for Earliest Priority Date
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df['Priority_Year'] = df['Earliest Priority Date'].dt.year.fillna(0).astype(int)
        df['Priority_Month'] = df['Earliest Priority Date'].dt.month_name()
    
    # 3. IPC Cleaning: Extraction of primary classification
    if 'Classification' in df.columns:
        df['Primary_IPC'] = df['Classification'].astype(str).str.split(',').str[0].str.strip().str[:4]
        df = df[df['Primary_IPC'] != "Ther"] 
        
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

# --- SIDEBAR: NAVIGATION & GLOBAL FILTERS ---
st.sidebar.markdown("---")
st.sidebar.title("🛠️ Analysis Tools")
menu = st.sidebar.radio("Go to:", ["Time-Series Growth", "Classification & Country Strength", "Global Priority & Comparisons", "Expert Search"])

# Sidebar Slider for Priority Year Range
if df is not None and 'Priority_Year' in df.columns:
    valid_years = df[df['Priority_Year'] > 1900]['Priority_Year']
    min_p_year = int(valid_years.min())
    max_p_year = int(valid_years.max())
    
    st.sidebar.subheader("📅 Priority Year Filter")
    p_year_range = st.sidebar.slider(
        "Select Range for Priority Analysis",
        min_value=min_p_year,
        max_value=max_p_year,
        value=(max_p_year - 5, max_p_year)
    )
    
    # Apply global filter
    filtered_df = df[(df['Priority_Year'] >= p_year_range[0]) & (df['Priority_Year'] <= p_year_range[1])]
else:
    filtered_df = df.copy() if df is not None else pd.DataFrame()

# --- MAIN DASHBOARD ---
st.title("🇦🇪 UAE Patent Analysis Engine")

if menu == "Time-Series Growth":
    st.header("📈 Growth Trends")
    c1, c2 = st.columns(2)
    with c1:
        yearly = filtered_df.groupby('Year').size().reset_index(name='Total')
        fig = px.bar(yearly, x='Year', y='Total', text_auto=True, title="UAE Filing Volume")
        # Ensure axis numbers are complete
        fig.update_yaxes(nticks=15, showgrid=True)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        growth_data = filtered_df.groupby('YearMonth').size().reset_index(name='Count')
        growth_data['MA12'] = growth_data['Count'].rolling(window=12).mean()
        fig_ma = px.line(growth_data, x='YearMonth', y='MA12', title="12-Month Market Velocity")
        st.plotly_chart(fig_ma, use_container_width=True)

elif menu == "Classification & Country Strength":
    st.header("🌍 IPC Strength & Country Activity")
    heat_df = filtered_df.groupby(['Country Name (Priority)', 'Primary_IPC']).size().reset_index(name='Apps')
    top_ipcs = heat_df.groupby('Primary_IPC')['Apps'].sum().nlargest(15).index
    heat_df_top = heat_df[heat_df['Primary_IPC'].isin(top_ipcs)]
    fig_heat = px.density_heatmap(heat_df_top, x="Primary_IPC", y="Country Name (Priority)", z="Apps", text_auto=True)
    st.plotly_chart(fig_heat, use_container_width=True)

elif menu == "Global Priority & Comparisons":
    st.header("🏁 Global Priority Analysis")
    st.info(f"Analysis Scope: Priority Years {p_year_range[0]} to {p_year_range[1]}")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Invention Volume by Priority Year")
        p_counts = filtered_df.groupby('Priority_Year').size().reset_index(name='Count')
        fig_p = px.area(p_counts, x='Priority_Year', y='Count', color_discrete_sequence=['#27ae60'])
        # Dense axis labels
        fig_p.update_yaxes(nticks=20, showgrid=True)
        st.plotly_chart(fig_p, use_container_width=True)

    with c2:
        st.subheader("Monthly Priority: Year-over-Year")
        
        p_month_df = filtered_df.copy()
        p_month_df['Priority_Year'] = p_month_df['Priority_Year'].astype(str)
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December']
        p_grouped = p_month_df.groupby(['Priority_Year', 'Priority_Month']).size().reset_index(name='Apps')
        
        fig_p_month = px.bar(
            p_grouped, x='Priority_Month', y='Apps', color='Priority_Year',
            barmode='group', text_auto=True, # text_auto shows the highest number clearly
            category_orders={"Priority_Month": month_order},
            labels={'Priority_Month': 'Month', 'Apps': 'Apps', 'Priority_Year': 'Year'},
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        # Fix: Force axis to be complete and detailed
        fig_p_month.update_yaxes(nticks=15, title="Total Applications")
        st.plotly_chart(fig_p_month, use_container_width=True)

    st.subheader("Top 10 Countries: Priority Trends")
    top_countries = filtered_df['Country Name (Priority)'].value_counts().nlargest(10).index
    box_df = filtered_df[filtered_df['Country Name (Priority)'].isin(top_countries)]
    fig_box = px.box(box_df, x='Priority_Year', y='Country Name (Priority)', color='Country Name (Priority)')
    fig_box.update_xaxes(nticks=25)
    st.plotly_chart(fig_box, use_container_width=True)

elif menu == "Expert Search":
    st.header("🔍 Expert Search")
    search = st.text_input("Search by IPC, Applicant, or Title...")
    if search:
        results = filtered_df[filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        st.write(f"Found {len(results)} matches.")
        st.dataframe(results[['Application Number', 'Title', 'Primary_IPC', 'Priority_Year']], use_container_width=True)
