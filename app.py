import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Intelligence Pro", layout="wide", page_icon="🇦🇪")

# --- DATA LOADING & REFINED CLEANING ---
@st.cache_data
def load_and_refine_data():
    df = pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv")
    
    # 1. Date Conversions
    df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
    df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
    
    # 2. Time Features
    df['Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
    df['Month'] = df['Application Date'].dt.month_name()
    df['YearMonth'] = df['Application Date'].dt.to_period('M').astype(str)
    
    # 3. IPC Cleaning
    # Separate "No Class" from real data
    df['Has_IPC'] = df['Classification'].apply(lambda x: False if "no classifications" in str(x).lower() else True)
    
    # Extract IPC Main (e.g., A61K) and IPC Section (e.g., A)
    def extract_ipc(val):
        if "no classifications" in str(val).lower() or pd.isna(val):
            return "Unclassified"
        # Split by comma for multiple IPCs, take the first one, then take the first 4 chars
        first_ipc = str(val).split(',')[0].strip()
        return first_ipc[:4]

    df['Primary_IPC'] = df['Classification'].apply(extract_ipc)
    df['IPC_Section'] = df['Primary_IPC'].str[0]
    
    # 4. Priority Lag (Time between Priority and UAE filing)
    df['Priority_Lag_Days'] = (df['Application Date'] - df['Earliest Priority Date']).dt.days
    
    return df

df = load_and_refine_data()

# --- SIDEBAR: GLOBAL FILTERS ---
st.sidebar.title("🔍 Global Filters")
st.sidebar.info("Filters applied here affect all tabs.")

# Multi-select filters
countries = sorted(df['Country Name (Priority)'].dropna().unique())
selected_countries = st.sidebar.multiselect("Select Countries", countries)

# Date Range Slider
min_year, max_year = int(df['Year'].min()), int(df['Year'].max())
year_range = st.sidebar.slider("Select Year Range", min_year, max_year, (min_year, max_year))

# Filter the dataframe
filtered_df = df.copy()
if selected_countries:
    filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_countries)]
filtered_df = filtered_df[(filtered_df['Year'] >= year_range[0]) & (filtered_df['Year'] <= year_range[1])]

# --- MAIN DASHBOARD ---
st.title("🇦🇪 UAE Patent Analysis Engine")
st.markdown("---")

# 1. EXECUTIVE SUMMARY (KPIs)
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("Total Applications", len(filtered_df))
with kpi2:
    top_country = filtered_df['Country Name (Priority)'].mode()[0] if not filtered_df['Country Name (Priority)'].empty else "N/A"
    st.metric("Top Country", top_country)
with kpi3:
    ipc_mode = filtered_df[filtered_df['Has_IPC']]['Primary_IPC'].mode()
    top_ipc = ipc_mode[0] if not ipc_mode.empty else "N/A"
    st.metric("Top Classification", top_ipc)
with kpi4:
    avg_lag = filtered_df['Priority_Lag_Days'].mean()
    st.metric("Avg Priority Lag", f"{int(avg_lag) if not pd.isna(avg_lag) else 0} Days")

# 2. TABS FOR DETAILED ANALYSIS
tab1, tab2, tab3, tab4 = st.tabs(["📈 Growth & Trends", "🌍 Classification Strength", "🕒 Priority Analysis", "🔬 Expert Explorer"])

with tab1:
    st.header("Temporal Growth Analysis")
    
    col_a, col_b = st.columns(2)
    with col_a:
        yearly_counts = filtered_df.groupby('Year').size().reset_index(name='Total')
        yearly_counts = yearly_counts[yearly_counts['Year'] > 0]
        fig_year = px.bar(yearly_counts, x='Year', y='Total', title="Filing Volume by Year", 
                          color='Total', color_continuous_scale='Blues')
        st.plotly_chart(fig_year, use_container_width=True)
        
    with col_b:
        selected_year = st.selectbox("Monthly Drill-down Year", sorted(filtered_df['Year'].unique(), reverse=True))
        y_df = filtered_df[filtered_df['Year'] == selected_year]
        m_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        m_counts = y_df.groupby('Month').size().reindex(m_order, fill_value=0).reset_index(name='Total')
        fig_month = px.line(m_counts, x='Month', y='Total', title=f"Filing Seasonality in {selected_year}", markers=True)
        st.plotly_chart(fig_month, use_container_width=True)

    st.subheader("12-Month Moving Average & Trend Line")
    growth_data = filtered_df.groupby('YearMonth').size().reset_index(name='Count')
    growth_data['YearMonth_DT'] = pd.to_datetime(growth_data['YearMonth'])
    growth_data = growth_data.sort_values('YearMonth_DT')
    growth_data['MA12'] = growth_data['Count'].rolling(window=12).mean()
    
    fig_ma = go.Figure()
    fig_ma.add_trace(go.Scatter(x=growth_data['YearMonth'], y=growth_data['Count'], name="Monthly Vol", opacity=0.3))
    fig_ma.add_trace(go.Scatter(x=growth_data['YearMonth'], y=growth_data['MA12'], name="12-Month Trend", line=dict(color='red', width=3)))
    fig_ma.update_layout(title="Growth Trajectory")
    st.plotly_chart(fig_ma, use_container_width=True)

with tab2:
    st.header("Technology Concentration")
    
    c1, c2 = st.columns([2, 1])
    with c1:
        # Improved Heatmap
        heat_df = filtered_df[filtered_df['Has_IPC']].groupby(['Country Name (Priority)', 'Primary_IPC']).size().reset_index(name='Apps')
        top_20_ipcs = heat_df.groupby('Primary_IPC')['Apps'].sum().nlargest(20).index
        heat_df = heat_df[heat_df['Primary_IPC'].isin(top_20_ipcs)]
        
        fig_heat = px.density_heatmap(
            heat_df, x="Primary_IPC", y="Country Name (Priority)", z="Apps",
            color_continuous_scale="Viridis", text_auto=True, title="Technology vs. Country Strength"
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    with c2:
        st.subheader("Top IPC Sections")
        section_counts = filtered_df[filtered_df['Has_IPC']]['IPC_Section'].value_counts()
        fig_pie = px.pie(values=section_counts.values, names=section_counts.index, title="IPC Sector Share")
        st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("Full IPC-Country Concentration Data")
    st.dataframe(heat_df.sort_values('Apps', ascending=False), use_container_width=True)

with tab3:
    st.header("Priority & Lag Analysis")
    st.info("Priority Lag is the delay between filing in the home country and filing in the UAE.")
    
    lag_df = filtered_df[filtered_df['Priority_Lag_Days'].notna()]
    # Filter out extreme outliers for better visualization
    lag_df = lag_df[lag_df['Priority_Lag_Days'].between(0, 365*5)]
    
    fig_hist = px.histogram(lag_df, x="Priority_Lag_Days", nbins=50, title="Distribution of Filing Lag (Days)",
                            color_discrete_sequence=['#2ecc71'])
    st.plotly_chart(fig_hist, use_container_width=True)
    
    fig_scatter = px.scatter(filtered_df, x="Earliest Priority Date", y="Application Date", color="Primary_IPC",
                             hover_data=['Title'], title="Filing Timeline: Home vs UAE")
    st.plotly_chart(fig_scatter, use_container_width=True)

with tab4:
    st.header("Expert & Search Interface")
    search = st.text_input("🔍 Search Experts, Titles, or Classifications (e.g., 'Munther' or 'G06F')")
    
    results = filtered_df.copy()
    if search:
        results = results[
            results['Title'].str.contains(search, case=False, na=False) |
            results['Classification'].str.contains(search, case=False, na=False) |
            results['Application Number'].str.contains(search, case=False, na=False)
        ]
    
    st.write(f"Showing {len(results)} matching records")
    st.dataframe(results[['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date', 'Priority_Lag_Days']], use_container_width=True)
    
    # Download Button
    csv = results.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Results to CSV", data=csv, file_name="patent_search_results.csv", mime="text/csv")
