import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Analysis Pro", layout="wide")

# --- DATA LOADING & REFINED CLEANING ---
@st.cache_data
def load_and_refine_data():
    # Loading the specific Type 5 CSV
    df = pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv")
    
    # Date processing
    df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
    df['Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
    df['Month'] = df['Application Date'].dt.month_name()
    df['YearMonth'] = df['Application Date'].dt.to_period('M').astype(str)
    
    # IPC Cleaning: Extracting the first primary class
    df['Primary_IPC'] = df['Classification'].str.split(',').str[0].str.strip()
    df = df[df['Primary_IPC'] != "There are no classifications"]
    
    return df

df = load_and_refine_data()

# --- SIDEBAR: NAVIGATION & GLOBAL FILTERS ---
st.sidebar.title("🛠️ Analysis Tools")
menu = st.sidebar.radio("Go to:", ["Time-Series Growth", "Classification & Country Strength", "Expert Search"])

# Filters
all_countries = sorted(df['Country Name (Priority)'].dropna().unique())
all_years = sorted(df['Year'].unique(), reverse=True)

selected_country = st.sidebar.multiselect("Select Country", all_countries)
selected_year = st.sidebar.selectbox("Focus Year (for monthly view)", all_years)

# Filtering logic
filtered_df = df.copy()
if selected_country:
    filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_country)]

# --- MAIN DASHBOARD SECTIONS ---
st.title("🇦🇪 UAE Patent Analysis Engine (Type 5)")

if menu == "Time-Series Growth":
    st.header("📈 Growth Trends & Temporal Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Applications per Year")
        yearly_counts = filtered_df.groupby('Year').size().reset_index(name='Total')
        yearly_counts = yearly_counts[yearly_counts['Year'] > 0] # Remove null years
        fig_year = px.bar(yearly_counts, x='Year', y='Total', text_auto=True, color_discrete_sequence=['#2C3E50'])
        st.plotly_chart(fig_year, use_container_width=True)
        
    with col2:
        st.subheader(f"Applications per Month in {selected_year}")
        year_focus_df = filtered_df[filtered_df['Year'] == selected_year]
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        monthly_counts = year_focus_df.groupby('Month').size().reindex(month_order, fill_value=0).reset_index(name='Total')
        fig_month = px.line(monthly_counts, x='Month', y='Total', markers=True, color_discrete_sequence=['#E74C3C'])
        st.plotly_chart(fig_month, use_container_width=True)

    st.subheader("12-Month Moving Average (Growth over Time)")
    growth_data = filtered_df.groupby('YearMonth').size().reset_index(name='Count')
    growth_data['YearMonth_DT'] = pd.to_datetime(growth_data['YearMonth'])
    growth_data = growth_data.sort_values('YearMonth_DT')
    growth_data['MA12'] = growth_data['Count'].rolling(window=12).mean()
    
    fig_ma = go.Figure()
    fig_ma.add_trace(go.Scatter(x=growth_data['YearMonth'], y=growth_data['Count'], name="Monthly Apps", opacity=0.4))
    fig_ma.add_trace(go.Scatter(x=growth_data['YearMonth'], y=growth_data['MA12'], name="12-Month Trend", line=dict(color='red', width=3)))
    st.plotly_chart(fig_ma, use_container_width=True)

elif menu == "Classification & Country Strength":
    st.header("🌍 IPC Strength & Country Activity")
    
    st.subheader("Interactive Heatmap: IPC vs Country")
    # Improved Heatmap logic
    heat_df = filtered_df.groupby(['Country Name (Priority)', 'Primary_IPC']).size().reset_index(name='Apps')
    top_ipcs = heat_df.groupby('Primary_IPC')['Apps'].sum().nlargest(20).index
    heat_df_top = heat_df[heat_df['Primary_IPC'].isin(top_ipcs)]
    
    fig_heat = px.density_heatmap(
        heat_df_top, x="Primary_IPC", y="Country Name (Priority)", z="Apps",
        color_continuous_scale="Viridis", text_auto=True,
        labels={'Apps': 'No. of Apps'},
        aspect="auto"
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    st.subheader("Country IPC Concentration (Same IPC in a Country)")
    # This specifically addresses seeing how many applications share an IPC within a nation
    concentration_df = heat_df_top.sort_values(by=['Country Name (Priority)', 'Apps'], ascending=[True, False])
    st.dataframe(concentration_df, use_container_width=True)

elif menu == "Expert Search":
    st.header("🔍 Identify Experts and Patent Details")
    search = st.text_input("Enter IPC (e.g., G06F), Title keyword, or Applicant Name")
    
    if search:
        results = filtered_df[
            filtered_df['Title'].str.contains(search, case=False, na=False) |
            filtered_df['Primary_IPC'].str.contains(search, case=False, na=False)
        ]
        st.write(f"Matches found: {len(results)}")
        st.dataframe(results[['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date']])
