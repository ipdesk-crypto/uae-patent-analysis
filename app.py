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
    
    # 2. Date processing for Earliest Priority Date
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df['Priority_Year'] = df['Earliest Priority Date'].dt.year.fillna(0).astype(int)
        df['Priority_Month'] = df['Earliest Priority Date'].dt.month_name()
    
    # 3. IPC Cleaning: Extraction of primary classification
    if 'Classification' in df.columns:
        # Extract the subclass (first 4 characters, e.g., G06F)
        df['Primary_IPC'] = df['Classification'].astype(str).str.split(',').str[0].str.strip().str[:4]
        df = df[df['Primary_IPC'] != "Ther"] 
    
    # 4. Priority Lag Calculation
    if 'Earliest Priority Date' in df.columns and 'Application Date' in df.columns:
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
    try:
        raw_df = pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv")
        df = refine_data(raw_df)
    except FileNotFoundError:
        st.error("Default dataset not found. Please upload a CSV instead.")
        st.stop()

# --- SIDEBAR: NAVIGATION & FILTERS ---
st.sidebar.markdown("---")
st.sidebar.title("🛠️ Analysis Tools")
menu = st.sidebar.radio("Go to:", [
    "Time-Series Growth", 
    "Classification & Country Strength", 
    "Global Priority & Comparisons", 
    "Expert Search"
])

# Global Date Filter for Priority Analysis (Slider)
if 'Priority_Year' in df.columns:
    valid_p_years = df[df['Priority_Year'] > 1900]['Priority_Year']
    min_p = int(valid_p_years.min())
    max_p = int(valid_p_years.max())
    
    st.sidebar.subheader("📅 Priority Year Filter")
    p_year_range = st.sidebar.slider(
        "Select Range for Priority Charts",
        min_value=min_p,
        max_value=max_p,
        value=(max_p - 5, max_p)
    )

# Dynamic Filter Logic for Countries
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
        st.subheader("Applications per Year (UAE Filing Date)")
        yearly_counts = filtered_df[filtered_df['Year'] > 1999].groupby('Year').size().reset_index(name='Total')
        fig_year = px.bar(yearly_counts, x='Year', y='Total', text_auto=True, 
                          color='Total', color_continuous_scale='Blues',
                          labels={'Year': 'UAE Filing Year', 'Total': 'Number of Applications'})
        fig_year.update_yaxes(nticks=15) # Ensure complete axis labels
        st.plotly_chart(fig_year, use_container_width=True)
        
    with col2:
        st.subheader(f"Applications per Month in {selected_year}")
        year_focus_df = filtered_df[filtered_df['Year'] == selected_year]
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        monthly_counts = year_focus_df.groupby('Month').size().reindex(month_order, fill_value=0).reset_index(name='Total')
        fig_month = px.line(monthly_counts, x='Month', y='Total', markers=True, 
                           color_discrete_sequence=['#E74C3C'],
                           labels={'Month': 'Month', 'Total': 'Applications'})
        fig_month.update_yaxes(nticks=10)
        st.plotly_chart(fig_month, use_container_width=True)

    st.subheader("12-Month Moving Average (Market Velocity)")
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
    st.subheader("Interactive Heatmap: IPC vs Country")
    heat_df = filtered_df.groupby(['Country Name (Priority)', 'Primary_IPC']).size().reset_index(name='Apps')
    top_ipcs = heat_df.groupby('Primary_IPC')['Apps'].sum().nlargest(20).index
    heat_df_top = heat_df[heat_df['Primary_IPC'].isin(top_ipcs)]
    
    fig_heat = px.density_heatmap(
        heat_df_top, x="Primary_IPC", y="Country Name (Priority)", z="Apps",
        color_continuous_scale="Viridis", text_auto=True,
        labels={'Apps': 'Count', 'Primary_IPC': 'IPC Code', 'Country Name (Priority)': 'Country'},
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# --- UPDATED SECTION: GLOBAL PRIORITY & COMPARISONS ---
elif menu == "Global Priority & Comparisons":
    st.header("🏁 Global Priority vs Country & Classification")
    
    # Apply the Slider Filter to this section specifically
    p_filtered = filtered_df[(filtered_df['Priority_Year'] >= p_year_range[0]) & 
                             (filtered_df['Priority_Year'] <= p_year_range[1])]

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Invention Volume by Priority Year")
        p_counts = p_filtered.groupby('Priority_Year').size().reset_index(name='Count')
        fig_p_year = px.area(p_counts, x='Priority_Year', y='Count', 
                            labels={'Priority_Year': 'Global Priority Year', 'Count': 'No. of Inventions'},
                            color_discrete_sequence=['#27ae60'])
        fig_p_year.update_yaxes(nticks=20) # Ensure axis numbers are complete
        st.plotly_chart(fig_p_year, use_container_width=True)

    with c2:
        # --- NEW: MONTHLY PRIORITY SEPARATED BY YEAR ---
        st.subheader("Monthly Priority: Year-over-Year Comparison")
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December']
        
        # Ensure year is a string for distinct legend colors
        p_grouped_df = p_filtered.copy()
        p_grouped_df['Priority_Year'] = p_grouped_df['Priority_Year'].astype(str)
        p_month_counts = p_grouped_df.groupby(['Priority_Year', 'Priority_Month']).size().reset_index(name='Apps')
        
        fig_p_month = px.bar(
            p_month_counts, x='Priority_Month', y='Apps', color='Priority_Year',
            barmode='group', text_auto=True, # text_auto shows the highest number on top
            category_orders={"Priority_Month": month_order},
            labels={'Priority_Month': 'Month', 'Apps': 'No. of Applications', 'Priority_Year': 'Year'},
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_p_month.update_yaxes(nticks=15) # Complete axis labeling
        st.plotly_chart(fig_p_month, use_container_width=True)

    st.subheader("Priority Distribution by Country")
    top_10_countries = p_filtered['Country Name (Priority)'].value_counts().nlargest(10).index
    dist_df = p_filtered[p_filtered['Country Name (Priority)'].isin(top_10_countries)]
    
    fig_box = px.box(dist_df, x='Priority_Year', y='Country Name (Priority)', 
                     color='Country Name (Priority)',
                     labels={'Priority_Year': 'Global Priority Year', 'Country Name (Priority)': 'Country'},
                     title="When did these countries start filing their patents?")
    fig_box.update_xaxes(nticks=20)
    fig_box.update_layout(showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

    # Technology Evolution
    st.subheader("Technology Evolution (Priority Year vs Classifications)")
    top_5_ipcs = p_filtered['Primary_IPC'].value_counts().nlargest(5).index
    ipc_time_df = p_filtered[p_filtered['Primary_IPC'].isin(top_5_ipcs)]
    ipc_trend = ipc_time_df.groupby(['Priority_Year', 'Primary_IPC']).size().reset_index(name='Count')
    
    fig_ipc_time = px.line(ipc_trend, x='Priority_Year', y='Count', color='Primary_IPC', 
                           markers=True, line_shape='spline',
                           labels={'Priority_Year': 'Global Priority Year', 'Count': 'Invention Count'})
    st.plotly_chart(fig_ipc_time, use_container_width=True)

elif menu == "Expert Search":
    st.header("🔍 Identify Experts and Patent Details")
    search = st.text_input("Enter IPC (e.g., G06F), Title keyword, or Applicant Name")
    if search:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        results = filtered_df[mask]
        st.write(f"Matches found: {len(results)}")
        display_cols = ['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date', 'Priority_Year']
        existing_display = [c for c in display_cols if c in results.columns]
        st.dataframe(results[existing_display] if existing_display else results, use_container_width=True)
