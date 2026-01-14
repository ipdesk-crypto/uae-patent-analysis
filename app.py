import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Analysis Pro", layout="wide", page_icon="🇦🇪")

# --- DATA REFINEMENT ENGINE ---
def refine_data(df):
    """Refines patent data for both UAE-specific and Global Priority analysis."""
    # 1. Date processing for Application Date (UAE filing)
    if 'Application Date' in df.columns:
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df['Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
        df['Month'] = df['Application Date'].dt.month_name()
        df['YearMonth'] = df['Application Date'].dt.to_period('M').astype(str)
    
    # 2. Date processing for Earliest Priority Date (Global birth of invention)
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df['Priority_Year'] = df['Earliest Priority Date'].dt.year.fillna(0).astype(int)
        df['Priority_Month'] = df['Earliest Priority Date'].dt.month_name()
    
    # 3. IPC Cleaning: Extraction of primary subclass
    if 'Classification' in df.columns:
        # Extract the subclass (e.g., G06F)
        df['Primary_IPC'] = df['Classification'].str.split(',').str[0].str.strip().str[:4]
        df = df[df['Primary_IPC'] != "Ther"] # Removes 'There are no classifications'
    
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
    try:
        raw_df = pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv")
        df = refine_data(raw_df)
    except FileNotFoundError:
        st.error("Default dataset not found. Please upload a CSV instead.")
        st.stop()

# --- PRE-CALCULATE SHARED VARIABLES (Fixes NameError) ---
# We calculate these once so they are available across all menu tabs
top_10_countries = df['Country Name (Priority)'].value_counts().nlargest(10).index
global_heat_df = df.groupby(['Country Name (Priority)', 'Primary_IPC']).size().reset_index(name='Apps')
top_ipcs_list = global_heat_df.groupby('Primary_IPC')['Apps'].sum().nlargest(20).index

# --- SIDEBAR: NAVIGATION & FILTERS ---
st.sidebar.markdown("---")
st.sidebar.title("🛠️ Analysis Tools")
menu = st.sidebar.radio("Go to:", [
    "Time-Series Growth", 
    "Classification & Country Strength", 
    "Global Priority & Comparisons", 
    "Expert Search"
])

# Dynamic Filters
all_countries = sorted(df['Country Name (Priority)'].dropna().unique())
all_years = sorted(df['Year'].unique(), reverse=True)

selected_country = st.sidebar.multiselect("Filter by Country", all_countries)
selected_year = st.sidebar.selectbox("Focus Year (for monthly view)", all_years)

# Apply Global Filters to working DF
filtered_df = df.copy()
if selected_country:
    filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_country)]

# --- MAIN DASHBOARD ---
st.title("🇦🇪 UAE Patent Analysis Engine (Type 5)")
st.markdown(f"**Current Scope:** {len(filtered_df)} Applications Analyzed")

if menu == "Time-Series Growth":
    st.header("📈 Growth Trends & Temporal Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Applications per Year (UAE Filing)")
        yearly_counts = filtered_df[filtered_df['Year'] > 1999].groupby('Year').size().reset_index(name='Total')
        fig_year = px.bar(yearly_counts, x='Year', y='Total', text_auto=True, 
                          color='Total', color_continuous_scale='Blues',
                          labels={'Year': 'UAE Filing Year', 'Total': 'Count'})
        st.plotly_chart(fig_year, use_container_width=True)
        
    with col2:
        st.subheader(f"Applications per Month in {selected_year}")
        year_focus_df = filtered_df[filtered_df['Year'] == selected_year]
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        monthly_counts = year_focus_df.groupby('Month').size().reindex(month_order, fill_value=0).reset_index(name='Total')
        fig_month = px.line(monthly_counts, x='Month', y='Total', markers=True, 
                           color_discrete_sequence=['#E74C3C'],
                           labels={'Month': 'Month', 'Total': 'Applications'})
        st.plotly_chart(fig_month, use_container_width=True)

    st.subheader("12-Month Moving Average (Market Velocity)")
    growth_data = filtered_df.groupby('YearMonth').size().reset_index(name='Count')
    growth_data['YearMonth_DT'] = pd.to_datetime(growth_data['YearMonth'])
    growth_data = growth_data.sort_values('YearMonth_DT')
    growth_data['MA12'] = growth_data['Count'].rolling(window=12).mean()
    fig_ma = go.Figure()
    fig_ma.add_trace(go.Scatter(x=growth_data['YearMonth'], y=growth_data['Count'], name="Monthly Apps", opacity=0.3, line=dict(color='gray')))
    fig_ma.add_trace(go.Scatter(x=growth_data['YearMonth'], y=growth_data['MA12'], name="12-Month Trend", line=dict(color='red', width=3)))
    fig_ma.update_layout(xaxis_title="Timeline", yaxis_title="No. of Filings")
    st.plotly_chart(fig_ma, use_container_width=True)

elif menu == "Classification & Country Strength":
    st.header("🌍 IPC Strength & Country Activity")
    st.subheader("Interactive Heatmap: IPC vs Country")
    heat_df_top = global_heat_df[global_heat_df['Primary_IPC'].isin(top_ipcs_list)]
    
    fig_heat = px.density_heatmap(
        heat_df_top, x="Primary_IPC", y="Country Name (Priority)", z="Apps",
        color_continuous_scale="Viridis", text_auto=True,
        labels={'Apps': 'Count', 'Primary_IPC': 'IPC Code', 'Country Name (Priority)': 'Country'},
    )
    st.plotly_chart(fig_heat, use_container_width=True)
    st.dataframe(heat_df_top.sort_values(by=['Country Name (Priority)', 'Apps'], ascending=[True, False]), use_container_width=True)

elif menu == "Global Priority & Comparisons":
    st.header("🏁 Global Priority & Seasonal Analysis")
    
    # 1. NEW GRAPH: Priority Month vs No. of Applications (Colored by Year)
    st.subheader("📅 Global Filing Seasonality (Month vs. Applications)")
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    
    # Prepare seasonal data
    seasonal_df = filtered_df[filtered_df['Priority_Year'] > 1999].copy()
    seasonal_counts = seasonal_df.groupby(['Priority_Year', 'Priority_Month']).size().reset_index(name='Count')
    
    fig_seasonal = px.line(
        seasonal_counts, x='Priority_Month', y='Count', color='Priority_Year',
        category_orders={"Priority_Month": month_order},
        markers=True,
        labels={'Priority_Month': 'Earliest Priority Month', 'Count': 'No. of Applications', 'Priority_Year': 'Year'},
        title="Comparison: Global Invention Month Across Years"
    )
    fig_seasonal.update_layout(xaxis_title="Priority Month", yaxis_title="Number of Applications")
    st.plotly_chart(fig_seasonal, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Invention Volume by Priority Year")
        p_counts = filtered_df[filtered_df['Priority_Year'] > 1999].groupby('Priority_Year').size().reset_index(name='Count')
        fig_p_year = px.area(p_counts, x='Priority_Year', y='Count', 
                            labels={'Priority_Year': 'Global Priority Year', 'Count': 'Inventions'},
                            color_discrete_sequence=['#27ae60'])
        st.plotly_chart(fig_p_year, use_container_width=True)

    with c2:
        st.subheader("Priority Distribution by Country")
        dist_df = filtered_df[filtered_df['Country Name (Priority)'].isin(top_10_countries) & (filtered_df['Priority_Year'] > 1999)]
        fig_box = px.box(dist_df, x='Priority_Year', y='Country Name (Priority)', color='Country Name (Priority)',
                         labels={'Priority_Year': 'Priority Year', 'Country Name (Priority)': 'Country'})
        fig_box.update_layout(showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("Country Specialization (Top Countries vs IPC)")
    spec_df = filtered_df[filtered_df['Country Name (Priority)'].isin(top_10_countries) & filtered_df['Primary_IPC'].isin(top_ipcs_list)]
    spec_counts = spec_df.groupby(['Country Name (Priority)', 'Primary_IPC']).size().reset_index(name='Total')
    fig_spec = px.bar(spec_counts, x='Country Name (Priority)', y='Total', color='Primary_IPC',
                      labels={'Total': 'Patents', 'Primary_IPC': 'IPC Sector'}, barmode='stack')
    st.plotly_chart(fig_spec, use_container_width=True)

elif menu == "Expert Search":
    st.header("🔍 Identify Experts and Patent Details")
    search = st.text_input("Enter IPC, Keyword, or Applicant Name")
    if search:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        results = filtered_df[mask]
        st.write(f"Matches found: {len(results)}")
        display_cols = ['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date', 'Priority_Year']
        existing_display = [c for c in display_cols if c in results.columns]
        st.dataframe(results[existing_display] if existing_display else results, use_container_width=True)

