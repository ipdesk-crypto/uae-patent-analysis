import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Analysis Engine", layout="wide", page_icon="🇦🇪")

# --- 1. DATA LOADING & CLEANING ---
@st.cache_data
def load_and_refine_data():
    # Load the specific Type 5 CSV
    df = pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv")
    
    # Precise Date conversion
    df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
    df['Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
    df['Month'] = df['Application Date'].dt.month_name()
    df['YearMonth'] = df['Application Date'].dt.to_period('M').astype(str)
    
    # IPC Cleaning: Extracting the first primary subclass (e.g., A61K)
    # We remove "There are no classifications" for cleaner metrics
    df['Primary_IPC'] = df['Classification'].str.split(',').str[0].str.strip().str[:4]
    df = df[df['Primary_IPC'] != "Ther"] 
    
    # Calculate Priority Lag if Priority Date exists
    df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
    df['Priority_Lag_Days'] = (df['Application Date'] - df['Earliest Priority Date']).dt.days
    
    return df

df = load_and_refine_data()

# --- 2. SIDEBAR: NAVIGATION & FILTERS ---
st.sidebar.title("🛠️ Analysis Tools")
menu = st.sidebar.radio("Go to:", ["Time-Series Growth", "Classification & Country Strength", "Expert Search"])

# Filters
all_countries = sorted(df['Country Name (Priority)'].dropna().unique())
all_years = sorted(df['Year'].unique(), reverse=True)

st.sidebar.markdown("---")
selected_country = st.sidebar.multiselect("Filter by Country", all_countries)
selected_year = st.sidebar.selectbox("Focus Year (for monthly drill-down)", all_years)

# Apply Filters
filtered_df = df.copy()
if selected_country:
    filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_country)]

# --- 3. MAIN DASHBOARD ---
st.title("🇦🇪 UAE Patent Analysis Engine (Type 5)")
st.markdown(f"**Current Dataset Scope:** {len(filtered_df)} Applications Analyzed")

if menu == "Time-Series Growth":
    st.header("📈 Growth Trends & Temporal Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Applications per Year")
        yearly_counts = filtered_df.groupby('Year').size().reset_index(name='Total Applications')
        yearly_counts = yearly_counts[yearly_counts['Year'] > 1999] # Filter for modern data
        
        fig_year = px.bar(yearly_counts, x='Year', y='Total Applications', 
                          text_auto=True, color='Total Applications',
                          color_continuous_scale='Blues',
                          labels={'Year': 'Calendar Year', 'Total Applications': 'Number of Filings'})
        fig_year.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_year, use_container_width=True)
        
    with col2:
        st.subheader(f"Monthly Distribution in {selected_year}")
        year_focus_df = filtered_df[filtered_df['Year'] == selected_year]
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        monthly_counts = year_focus_df.groupby('Month').size().reindex(month_order, fill_value=0).reset_index(name='Total Applications')
        
        fig_month = px.line(monthly_counts, x='Month', y='Total Applications', 
                           markers=True, color_discrete_sequence=['#E74C3C'],
                           labels={'Month': 'Month of Filing', 'Total Applications': 'Applications Count'})
        st.plotly_chart(fig_month, use_container_width=True)

    st.subheader("12-Month Moving Average (Trend Over Time)")
    st.info("The red line represents the smoothed average, helping to identify long-term growth by removing monthly spikes.")
    growth_data = filtered_df.groupby('YearMonth').size().reset_index(name='Count')
    growth_data['YearMonth_DT'] = pd.to_datetime(growth_data['YearMonth'])
    growth_data = growth_data.sort_values('YearMonth_DT')
    growth_data['MA12'] = growth_data['Count'].rolling(window=12).mean()
    
    fig_ma = go.Figure()
    fig_ma.add_trace(go.Scatter(x=growth_data['YearMonth'], y=growth_data['Count'], 
                                name="Monthly Actuals", opacity=0.3, line=dict(color='gray')))
    fig_ma.add_trace(go.Scatter(x=growth_data['YearMonth'], y=growth_data['MA12'], 
                                name="12-Month Moving Average", line=dict(color='red', width=3)))
    fig_ma.update_layout(xaxis_title="Timeline (Year-Month)", yaxis_title="Number of Applications")
    st.plotly_chart(fig_ma, use_container_width=True)

elif menu == "Classification & Country Strength":
    st.header("🌍 IPC Strength & Country Expertise")
    
    # 1. Expertise Heatmap
    st.subheader("Heatmap: Technology Concentration per Country")
    heat_df = filtered_df.groupby(['Country Name (Priority)', 'Primary_IPC']).size().reset_index(name='Apps')
    # Filter for top 20 most frequent IPCs for visual clarity
    top_ipcs = heat_df.groupby('Primary_IPC')['Apps'].sum().nlargest(20).index
    heat_df_top = heat_df[heat_df['Primary_IPC'].isin(top_ipcs)]
    
    fig_heat = px.density_heatmap(
        heat_df_top, x="Primary_IPC", y="Country Name (Priority)", z="Apps",
        color_continuous_scale="Viridis", text_auto=True,
        labels={'Apps': 'Total Filings', 'Primary_IPC': 'IPC Classification (Subclass)', 'Country Name (Priority)': 'Country of Origin'},
        title="Identifying Global Experts: Who leads in which classification?"
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # 2. Detailed Concentration Table
    st.subheader("Country IPC Concentration Details")
    concentration_df = heat_df_top.sort_values(by=['Country Name (Priority)', 'Apps'], ascending=[True, False])
    st.dataframe(concentration_df.rename(columns={'Apps': 'Count of Same IPC'}), use_container_width=True)

elif menu == "Expert Search":
    st.header("🔍 Expert Identification & Patent Explorer")
    search = st.text_input("Search by Technical keyword, Applicant name, or IPC Code (e.g., G06F)")
    
    if search:
        results = filtered_df[
            filtered_df['Title'].str.contains(search, case=False, na=False) |
            filtered_df['Primary_IPC'].str.contains(search, case=False, na=False) |
            filtered_df['Application Number'].str.contains(search, case=False, na=False)
        ]
        st.success(f"🔍 Found {len(results)} matching records")
        
        # Display results with proper formatting
        st.dataframe(results[['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date', 'Priority_Lag_Days']], 
                     use_container_width=True)
        
        # Download results
        csv = results.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Search Results as CSV", data=csv, file_name="UAE_Patent_Expert_Search.csv", mime="text/csv")
    else:
        st.info("Enter a keyword above to find specific technology experts and application details.")
