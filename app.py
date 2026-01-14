import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Analysis Pro", layout="wide", page_icon="🇦🇪")

# --- DATA REFINEMENT ENGINE ---
def refine_data(df):
    df.columns = df.columns.str.strip()

    # 1. Date processing for Application Date - Forced Accuracy
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
    
    # 3. IPC Extraction
    if 'Classification' in df.columns:
        df['Primary_IPC'] = df['Classification'].astype(str).str.split(',').str[0].str.strip().str[:4]
    
    return df

# --- DATA LOADING ---
data_source = st.sidebar.radio("Select Data Source:", ["Default UAE Dataset", "Upload Custom CSV"])
df = None
if data_source == "Upload Custom CSV":
    uploaded_file = st.sidebar.file_uploader("Upload CSV", type="csv")
    if uploaded_file: df = refine_data(pd.read_csv(uploaded_file))
else:
    try: df = refine_data(pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv"))
    except: st.stop()

# --- SIDEBAR NAVIGATION ---
menu = st.sidebar.radio("Go to:", ["Time-Series Growth", "Classification & Country Strength", "Global Priority & Comparisons", "Expert Search"])

# Filters
valid_years = sorted(df[df['Year'] > 0]['Year'].unique(), reverse=True)
selected_year = st.sidebar.selectbox("Focus Year (Monthly)", valid_years)
selected_country = st.sidebar.multiselect("Filter Country", sorted(df['Country Name (Priority)'].dropna().unique()))

filtered_df = df.copy()
if selected_country:
    filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_country)]

# --- TIME-SERIES GROWTH ---
if menu == "Time-Series Growth":
    st.header("📈 Growth Trends & Temporal Analysis")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Total Applications per Year (With Data Labels)")
        yearly_counts = filtered_df[filtered_df['Year'] >= 1990].groupby('Year').size().reset_index(name='Total')
        
        # text_auto=True forces the numbers to appear on the bars
        fig_year = px.bar(yearly_counts, x='Year', y='Total', text='Total',
                          labels={'Year': 'Filing Year', 'Total': 'Number of Applications'},
                          color_discrete_sequence=['#3498db'])
        
        fig_year.update_traces(textposition='outside') # Put numbers on top of bars
        fig_year.update_xaxes(type='category', tickangle=45)
        fig_year.update_yaxes(dtick=10, showgrid=True)
        st.plotly_chart(fig_year, use_container_width=True)

    with col2:
        st.subheader("Numerical Summary")
        st.write("Exact counts per year for verification:")
        st.dataframe(yearly_counts.sort_values('Year', ascending=False), height=400)

    st.markdown("---")
    st.subheader(f"Monthly Breakdown for {selected_year}")
    year_df = filtered_df[filtered_df['Year'] == selected_year]
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    monthly_counts = year_df.groupby('Month').size().reindex(month_order, fill_value=0).reset_index(name='Total')
    
    fig_month = px.line(monthly_counts, x='Month', y='Total', markers=True, text='Total', labels={'Total': 'Apps'})
    fig_month.update_traces(textposition='top center')
    st.plotly_chart(fig_month, use_container_width=True)

# --- CLASSIFICATION & COUNTRY ---
elif menu == "Classification & Country Strength":
    st.header("🌍 IPC Strength & Country Activity")
    heat_data = filtered_df.dropna(subset=['Primary_IPC', 'Country Name (Priority)'])
    heat_data = heat_data[heat_data['Primary_IPC'] != "Ther"]
    
    heat_grouped = heat_data.groupby(['Country Name (Priority)', 'Primary_IPC']).size().reset_index(name='Apps')
    top_ipcs = heat_grouped.groupby('Primary_IPC')['Apps'].sum().nlargest(20).index
    heat_df_top = heat_grouped[heat_grouped['Primary_IPC'].isin(top_ipcs)]
    
    fig_heat = px.density_heatmap(heat_df_top, x="Primary_IPC", y="Country Name (Priority)", z="Apps",
                                  color_continuous_scale="Viridis", text_auto=True)
    st.plotly_chart(fig_heat, use_container_width=True)

# --- GLOBAL PRIORITY ---
elif menu == "Global Priority & Comparisons":
    st.header("🏁 Global Priority Analysis")
    valid_p = df[df['Priority_Year'] > 1990]['Priority_Year']
    p_range = st.sidebar.slider("Priority Year Range", int(valid_p.min()), int(valid_p.max()), (int(valid_p.max())-5, int(valid_p.max())))
    p_df = filtered_df[(filtered_df['Priority_Year'] >= p_range[0]) & (filtered_df['Priority_Year'] <= p_range[1])]
    
    st.subheader("Monthly Priority Distribution (Grouped by Year)")
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    years = range(p_range[0], p_range[1] + 1)
    template = pd.MultiIndex.from_product([years, month_order], names=['Priority_Year', 'Priority_Month']).to_frame(index=False)
    actual = p_df.groupby(['Priority_Year', 'Priority_Month']).size().reset_index(name='Apps')
    merged = pd.merge(template, actual, on=['Priority_Year', 'Priority_Month'], how='left').fillna(0)
    merged['Priority_Year'] = merged['Priority_Year'].astype(str)
    
    fig_m = px.bar(merged, x='Priority_Month', y='Apps', color='Priority_Year', barmode='group', text='Apps',
                   category_orders={"Priority_Month": month_order}, color_discrete_sequence=px.colors.qualitative.Prism)
    fig_m.update_traces(textposition='outside')
    fig_m.update_yaxes(dtick=5)
    st.plotly_chart(fig_m, use_container_width=True)

# --- SEARCH ---
elif menu == "Expert Search":
    st.header("🔍 Identify Experts")
    search = st.text_input("Enter IPC, Title, or Applicant")
    if search:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        st.dataframe(filtered_df[mask][['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date', 'Priority_Year']], use_container_width=True)
