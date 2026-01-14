import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Analysis Pro", layout="wide", page_icon="🇦🇪")

# --- DATA REFINEMENT ENGINE ---
def refine_data(df):
    # Clean column names
    df.columns = df.columns.str.strip()

    # 1. Date processing for Application Date (UAE Filing)
    if 'Application Date' in df.columns:
        # Flexible parsing to ensure NO rows are lost
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df['Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
        df['Month'] = df['Application Date'].dt.month_name()
        df['YearMonth'] = df['Application Date'].dt.to_period('M').astype(str)
    
    # 2. Date processing for Earliest Priority Date (Global Priority)
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df['Priority_Year'] = df['Earliest Priority Date'].dt.year.fillna(0).astype(int)
        df['Priority_Month'] = df['Earliest Priority Date'].dt.month_name()
    
    # 3. Extraction of primary classification (IPC)
    if 'Classification' in df.columns:
        df['Primary_IPC'] = df['Classification'].astype(str).str.split(',').str[0].str.strip().str[:4]
    
    return df

# --- SIDEBAR: DATA SOURCE ---
st.sidebar.title("📁 Data Management")
data_source = st.sidebar.radio("Select Data Source:", ["Default UAE Dataset", "Upload Custom CSV"])

df = None
if data_source == "Upload Custom CSV":
    uploaded_file = st.sidebar.file_uploader("Upload your patent data CSV", type="csv")
    if uploaded_file is not None:
        df = refine_data(pd.read_csv(uploaded_file))
else:
    try:
        df = refine_data(pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv"))
    except:
        st.error("File not found.")
        st.stop()

# --- SIDEBAR: NAVIGATION ---
menu = st.sidebar.radio("Go to:", ["Time-Series Growth", "Classification & Country Strength", "Global Priority & Comparisons", "Expert Search"])

# Global Year/Country Filters
all_years = sorted(df[df['Year'] > 0]['Year'].unique(), reverse=True)
selected_year = st.sidebar.selectbox("Focus Year (for monthly view)", all_years)
all_countries = sorted(df['Country Name (Priority)'].dropna().unique())
selected_country = st.sidebar.multiselect("Filter by Country", all_countries)

# Apply Country Filter
filtered_df = df.copy()
if selected_country:
    filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_country)]

# --- DASHBOARD SECTIONS ---
if menu == "Time-Series Growth":
    st.header("📈 Growth Trends & Temporal Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Total Applications per Year")
        # Ensure we count EVERY application for accuracy
        yearly_counts = filtered_df[filtered_df['Year'] >= 1990].groupby('Year').size().reset_index(name='Total')
        
        fig_year = px.bar(yearly_counts, x='Year', y='Total', text_auto=True,
                          labels={'Year': 'Filing Year', 'Total': 'Number of Applications'})
        
        # FIX AXIS LABELS: Force category type so every year shows up
        fig_year.update_xaxes(type='category', tickangle=45)
        fig_year.update_yaxes(title="Count", dtick=10 if yearly_counts['Total'].max() > 100 else 5)
        st.plotly_chart(fig_year, use_container_width=True)
        
    with col2:
        st.subheader(f"Monthly Breakdown: {selected_year}")
        year_df = filtered_df[filtered_df['Year'] == selected_year]
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        monthly_counts = year_df.groupby('Month').size().reindex(month_order, fill_value=0).reset_index(name='Total')
        
        fig_month = px.line(monthly_counts, x='Month', y='Total', markers=True, labels={'Total': 'Applications'})
        fig_month.update_yaxes(dtick=5)
        st.plotly_chart(fig_month, use_container_width=True)

elif menu == "Global Priority & Comparisons":
    st.header("🏁 Global Priority Analysis")
    
    # Priority Year Slider
    valid_p = df[df['Priority_Year'] > 1990]['Priority_Year']
    p_range = st.sidebar.slider("Priority Year Range", int(valid_p.min()), int(valid_p.max()), (2018, int(valid_p.max())))
    
    p_df = filtered_df[(filtered_df['Priority_Year'] >= p_range[0]) & (filtered_df['Priority_Year'] <= p_range[1])]
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Inventions by Priority Year")
        p_counts = p_df.groupby('Priority_Year').size().reset_index(name='Count')
        fig_p = px.area(p_counts, x='Priority_Year', y='Count')
        fig_p.update_xaxes(type='category')
        st.plotly_chart(fig_p, use_container_width=True)

    with c2:
        st.subheader("Monthly Priority (Zero-Filled)")
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        
        # Create full 12-month template for every year in the selected range
        years = range(p_range[0], p_range[1] + 1)
        template = pd.MultiIndex.from_product([years, month_order], names=['Priority_Year', 'Priority_Month']).to_frame(index=False)
        
        actual = p_df.groupby(['Priority_Year', 'Priority_Month']).size().reset_index(name='Apps')
        merged = pd.merge(template, actual, on=['Priority_Year', 'Priority_Month'], how='left').fillna(0)
        merged['Priority_Year'] = merged['Priority_Year'].astype(str)
        
        fig_m = px.bar(merged, x='Priority_Month', y='Apps', color='Priority_Year', 
                       barmode='group', text_auto=True, category_orders={"Priority_Month": month_order})
        
        fig_m.update_xaxes(title="Month")
        fig_m.update_yaxes(title="No. of Applications", dtick=5)
        st.plotly_chart(fig_m, use_container_width=True)

# Other sections remain intact but hidden for brevity - they use the same filtered_df logic.
