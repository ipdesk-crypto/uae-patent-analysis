import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Analysis Pro", layout="wide", page_icon="🇦🇪")

# --- DATA REFINEMENT ENGINE ---
def refine_data(df):
    """Preserves existing cleaning logic for all data sources."""
    # Date processing
    if 'Application Date' in df.columns:
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df['Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
        df['Month'] = df['Application Date'].dt.month_name()
        df['YearMonth'] = df['Application Date'].dt.to_period('M').astype(str)
    
    # IPC Cleaning: Extraction of primary classification 
    if 'Classification' in df.columns:
        df['Primary_IPC'] = df['Classification'].str.split(',').str[0].str.strip().str[:4]
        df = df[df['Primary_IPC'] != "Ther"] # Removes 'There are no classifications' 
    
    # Calculate Lag if relevant columns exist 
    if 'Earliest Priority Date' in df.columns and 'Application Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df['Priority_Lag_Days'] = (df['Application Date'] - df['Earliest Priority Date']).dt.days
        
    return df

# --- SIDEBAR: DATA SOURCE SELECTOR ---
st.sidebar.title("📁 Data Management")
data_source = st.sidebar.radio("Select Data Source:", ["Default UAE Dataset", "Upload Custom CSV"])

df = None

if data_source == "Upload Custom CSV":
    uploaded_file = st.sidebar.file_uploader("Upload your patent data CSV", type="csv")
    if uploaded_file is not None:
        try:
            raw_upload = pd.read_csv(uploaded_file)
            df = refine_data(raw_upload)
            st.sidebar.success("✅ Custom data loaded!")
        except Exception as e:
            st.sidebar.error(f"Error loading file: {e}")
            st.stop()
    else:
        st.info("👋 Please upload a CSV file to begin.")
        st.stop()
else:
    # Loading the specific Type 5 CSV by default 
    try:
        raw_df = pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv")
        df = refine_data(raw_df)
    except FileNotFoundError:
        st.error("Default dataset not found. Please upload a CSV instead.")
        st.stop()

# --- SIDEBAR: NAVIGATION & FILTERS ---
st.sidebar.markdown("---")
st.sidebar.title("🛠️ Analysis Tools")
menu = st.sidebar.radio("Go to:", ["Time-Series Growth", "Classification & Country Strength", "Expert Search"])

# Dynamic Filter Logic
all_countries = sorted(df['Country Name (Priority)'].dropna().unique()) if 'Country Name (Priority)' in df.columns else []
all_years = sorted(df['Year'].unique(), reverse=True) if 'Year' in df.columns else []

selected_country = st.sidebar.multiselect("Filter by Country", all_countries)
selected_year = st.sidebar.selectbox("Focus Year (for monthly view)", all_years)

# Filtering logic
filtered_df = df.copy()
if selected_country and 'Country Name (Priority)' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_country)]

# --- MAIN DASHBOARD ---
st.title("🇦🇪 UAE Patent Analysis Engine (Type 5)")
st.markdown(f"**Current Scope:** {len(filtered_df)} Applications Analyzed")

if menu == "Time-Series Growth":
    st.header("📈 Growth Trends & Temporal Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Applications per Year")
        if 'Year' in filtered_df.columns:
            yearly_counts = filtered_df.groupby('Year').size().reset_index(name='Total')
            yearly_counts = yearly_counts[yearly_counts['Year'] > 1999] # Filter for modern era 
            fig_year = px.bar(yearly_counts, x='Year', y='Total', text_auto=True, 
                              color='Total', color_continuous_scale='Blues',
                              labels={'Year': 'Calendar Year', 'Total': 'Total Applications'})
            st.plotly_chart(fig_year, use_container_width=True)
        
    with col2:
        st.subheader(f"Applications per Month in {selected_year}")
        if 'Month' in filtered_df.columns:
            year_focus_df = filtered_df[filtered_df['Year'] == selected_year]
            month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
            monthly_counts = year_focus_df.groupby('Month').size().reindex(month_order, fill_value=0).reset_index(name='Total')
            fig_month = px.line(monthly_counts, x='Month', y='Total', markers=True, 
                               color_discrete_sequence=['#E74C3C'],
                               labels={'Month': 'Month of Application', 'Total': 'Count'})
            st.plotly_chart(fig_month, use_container_width=True)

    st.subheader("12-Month Moving Average (Growth Trend)")
    if 'YearMonth' in filtered_df.columns:
        growth_data = filtered_df.groupby('YearMonth').size().reset_index(name='Count')
        growth_data['YearMonth_DT'] = pd.to_datetime(growth_data['YearMonth'])
        growth_data = growth_data.sort_values('YearMonth_DT')
        growth_data['MA12'] = growth_data['Count'].rolling(window=12).mean()
        
        fig_ma = go.Figure()
        fig_ma.add_trace(go.Scatter(x=growth_data['YearMonth'], y=growth_data['Count'], name="Monthly Apps", opacity=0.3, line=dict(color='gray')))
        fig_ma.add_trace(go.Scatter(x=growth_data['YearMonth'], y=growth_data['MA12'], name="12-Month Trend", line=dict(color='red', width=3)))
        fig_ma.update_layout(xaxis_title="Timeline", yaxis_title="Number of Filings")
        st.plotly_chart(fig_ma, use_container_width=True)

elif menu == "Classification & Country Strength":
    st.header("🌍 IPC Strength & Country Activity")
    
    if 'Primary_IPC' in filtered_df.columns and 'Country Name (Priority)' in filtered_df.columns:
        st.subheader("Interactive Heatmap: IPC vs Country")
        heat_df = filtered_df.groupby(['Country Name (Priority)', 'Primary_IPC']).size().reset_index(name='Apps')
        top_ipcs = heat_df.groupby('Primary_IPC')['Apps'].sum().nlargest(20).index
        heat_df_top = heat_df[heat_df['Primary_IPC'].isin(top_ipcs)]
        
        fig_heat = px.density_heatmap(
            heat_df_top, x="Primary_IPC", y="Country Name (Priority)", z="Apps",
            color_continuous_scale="Viridis", text_auto=True,
            labels={'Apps': 'No. of Apps', 'Primary_IPC': 'IPC Classification', 'Country Name (Priority)': 'Country'},
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        st.subheader("Country IPC Concentration Details")
        concentration_df = heat_df_top.sort_values(by=['Country Name (Priority)', 'Apps'], ascending=[True, False])
        st.dataframe(concentration_df, use_container_width=True)
    else:
        st.warning("Ensure your CSV contains 'Classification' and 'Country Name (Priority)' for this view.")

elif menu == "Expert Search":
    st.header("🔍 Identify Experts and Patent Details")
    search = st.text_input("Enter IPC (e.g., G06F), Title keyword, or Applicant Name")
    
    if search:
        # Search across all columns for maximum flexibility with uploaded data
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        results = filtered_df[mask]
        
        st.write(f"Matches found: {len(results)}")
        # Show specific columns if they exist, otherwise show all
        display_cols = ['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date']
        existing_display = [c for c in display_cols if c in results.columns]
        st.dataframe(results[existing_display] if existing_display else results, use_container_width=True)
