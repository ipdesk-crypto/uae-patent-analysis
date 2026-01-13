import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Data Analysis Engine", layout="wide", page_icon="🇦🇪")

# --- DATA LOADING ---
@st.cache_data
def load_and_refine_data():
    df = pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv")
    
    # Date Cleaning
    df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
    df['Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
    df['Month'] = df['Application Date'].dt.month_name()
    df['YearMonth'] = df['Application Date'].dt.to_period('M').astype(str)
    
    # IPC Refinement: Extract 4-character subclass (e.g., G06F)
    df['Primary_IPC'] = df['Classification'].str.split(',').str[0].str.strip().str[:4]
    
    # Filter out entries with no real data
    df = df[df['Primary_IPC'] != "Ther"] # Removes "There are no classifications"
    df = df.dropna(subset=['Application Date', 'Country Name (Priority)'])
    
    return df

df = load_and_refine_data()

# --- SIDEBAR & FILTERS ---
st.sidebar.title("🛠️ Analysis Controls")
st.sidebar.markdown("Use these filters to drill down into specific data segments.")

all_countries = sorted(df['Country Name (Priority)'].unique())
selected_countries = st.sidebar.multiselect("Filter by Country", all_countries, help="Leave empty to see all")
selected_ipc = st.sidebar.multiselect("Filter by Classification (IPC)", sorted(df['Primary_IPC'].unique()))

# Filtering Logic
filtered_df = df.copy()
if selected_countries:
    filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_countries)]
if selected_ipc:
    filtered_df = filtered_df[filtered_df['Primary_IPC'].isin(selected_ipc)]

# --- MAIN DASHBOARD ---
st.title("🇦🇪 UAE Data Analysis Engine")
st.markdown("---")

# 1. EXECUTIVE METRICS (KPIs)
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("Total Applications", len(filtered_df))
with kpi2:
    st.metric("Active Countries", filtered_df['Country Name (Priority)'].nunique())
with kpi3:
    st.metric("Primary IPC", filtered_df['Primary_IPC'].mode()[0] if not filtered_df.empty else "N/A")
with kpi4:
    growth_pct = "Analysis Active"
    st.metric("Status", "Type 5 Data")

# 2. ANALYSIS TABS
tab1, tab2, tab3 = st.tabs(["📈 Growth Analysis", "🌍 Expertise & Specialization", "🔍 Expert Search"])

with tab1:
    st.header("Temporal Growth Trends")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Volume Growth Over the Years")
        yearly = filtered_df.groupby('Year').size().reset_index(name='Total')
        yearly = yearly[yearly['Year'] > 2000] # Filter for modern era
        fig_year = px.area(yearly, x='Year', y='Total', title="Annual Application Growth",
                           color_discrete_sequence=['#1f77b4'])
        st.plotly_chart(fig_year, use_container_width=True)
        
    with col2:
        st.subheader("Seasonal Trends (Monthly)")
        focus_year = st.selectbox("Select Year for Monthly View", sorted(df['Year'].unique(), reverse=True))
        year_df = filtered_df[filtered_df['Year'] == focus_year]
        m_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        m_counts = year_df.groupby('Month').size().reindex(m_order, fill_value=0).reset_index(name='Total')
        fig_month = px.bar(m_counts, x='Month', y='Total', color='Total', color_continuous_scale='Reds')
        st.plotly_chart(fig_month, use_container_width=True)

    st.subheader("12-Month Moving Average (Market Velocity)")
    st.markdown("The red line shows the smoothed trend, ignoring monthly spikes to show true market growth.")
    ma_df = filtered_df.groupby('YearMonth').size().reset_index(name='Count')
    ma_df['YearMonth_DT'] = pd.to_datetime(ma_df['YearMonth'])
    ma_df = ma_df.sort_values('YearMonth_DT')
    ma_df['MA12'] = ma_df['Count'].rolling(window=12).mean()
    
    fig_ma = go.Figure()
    fig_ma.add_trace(go.Scatter(x=ma_df['YearMonth'], y=ma_df['Count'], name="Monthly Apps", opacity=0.3))
    fig_ma.add_trace(go.Scatter(x=ma_df['YearMonth'], y=ma_df['MA12'], name="12-Month Trend", line=dict(color='red', width=4)))
    st.plotly_chart(fig_ma, use_container_width=True)

with tab2:
    st.header("Country Expertise & Classification Strength")
    
    st.subheader("Interactive Heatmap: IPC Concentration per Country")
    heat_df = filtered_df.groupby(['Country Name (Priority)', 'Primary_IPC']).size().reset_index(name='Frequency')
    # Filter for significant data
    top_ipcs = heat_df.groupby('Primary_IPC')['Frequency'].sum().nlargest(15).index
    heat_plot = heat_df[heat_df['Primary_IPC'].isin(top_ipcs)]
    
    fig_heat = px.density_heatmap(
        heat_plot, x="Primary_IPC", y="Country Name (Priority)", z="Frequency",
        color_continuous_scale="Viridis", text_auto=True,
        labels={'Frequency': 'Expertise Count'},
        title="Who is the Expert? (Number of Classifications per Country)"
    )
    st.plotly_chart(fig_heat, use_container_width=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Top 10 Global Experts (By Count)")
        top_countries = filtered_df['Country Name (Priority)'].value_counts().head(10)
        st.bar_chart(top_countries)
        
    with col_b:
        st.subheader("Classification Concentration")
        top_classes = filtered_df['Primary_IPC'].value_counts().head(10)
        fig_pie = px.pie(values=top_classes.values, names=top_classes.index, hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

with tab3:
    st.header("Expert Explorer & Search")
    query = st.text_input("Search by Patent Title, Applicant, or IPC Code...")
    
    if query:
        search_results = filtered_df[
            filtered_df['Title'].str.contains(query, case=False, na=False) |
            filtered_df['Primary_IPC'].str.contains(query, case=False, na=False)
        ]
    else:
        search_results = filtered_df.head(100)
        
    st.write(f"Showing {len(search_results)} matching records")
    st.dataframe(search_results[['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date']], use_container_width=True)

    # Export Feature
    csv = search_results.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download This Analysis as CSV", data=csv, file_name="UAE_Patent_Analysis.csv", mime="text/csv")
