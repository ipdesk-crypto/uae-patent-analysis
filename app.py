import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Analysis Pro", layout="wide", page_icon="🇦🇪")

# --- DATA REFINEMENT ENGINE ---
def refine_data(df):
    """STRICT EXTRACTION: Ensures YYYY-MM-DD is read correctly for 100% accuracy."""
    # Clean column names for whitespace
    df.columns = df.columns.str.strip()

    # 1. Date processing for Application Date (UAE Filing)
    if 'Application Date' in df.columns:
        # Force YYYY-MM-DD format and strip any hidden spaces
        df['Application Date'] = pd.to_datetime(
            df['Application Date'].astype(str).str.strip(), 
            format='%Y-%m-%d', 
            errors='coerce'
        )
        mask = df['Application Date'].notna()
        df.loc[mask, 'Year'] = df['Application Date'].dt.year
        df.loc[mask, 'Month'] = df['Application Date'].dt.month_name()
        df.loc[mask, 'YearMonth'] = df['Application Date'].dt.to_period('M').astype(str)
        df['Year'] = df['Year'].fillna(0).astype(int)
    
    # 2. Date processing for Earliest Priority Date (Global Priority)
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(
            df['Earliest Priority Date'].astype(str).str.strip(), 
            format='%Y-%m-%d', 
            errors='coerce'
        )
        mask_p = df['Earliest Priority Date'].notna()
        df.loc[mask_p, 'Priority_Year'] = df['Earliest Priority Date'].dt.year
        df.loc[mask_p, 'Priority_Month'] = df['Earliest Priority Date'].dt.month_name()
        df['Priority_Year'] = df['Priority_Year'].fillna(0).astype(int)
    
    # 3. IPC Cleaning
    if 'Classification' in df.columns:
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
    min_p, max_p = int(valid_p_years.min()), int(valid_p_years.max())
    st.sidebar.subheader("📅 Priority Year Filter")
    p_year_range = st.sidebar.slider("Select Range for Priority Charts", min_p, max_p, (max_p - 5, max_p))

# Dynamic Filters
all_countries = sorted(df['Country Name (Priority)'].dropna().unique()) if 'Country Name (Priority)' in df.columns else []
all_years = sorted(df['Year'].unique(), reverse=True) if 'Year' in df.columns else []
selected_country = st.sidebar.multiselect("Filter by Country", all_countries)
selected_year = st.sidebar.selectbox("Focus Year (for monthly view)", all_years)

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
        st.subheader("Applications per Year (UAE Filing Date)")
        yearly_counts = filtered_df[filtered_df['Year'] >= 1990].groupby('Year').size().reset_index(name='Total')
        fig_year = px.bar(yearly_counts, x='Year', y='Total', text_auto=True, color='Total', color_continuous_scale='Blues')
        fig_year.update_yaxes(nticks=15)
        st.plotly_chart(fig_year, use_container_width=True)
    with col2:
        st.subheader(f"Applications per Month in {selected_year}")
        year_focus_df = filtered_df[filtered_df['Year'] == selected_year]
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        monthly_counts = year_focus_df.groupby('Month').size().reindex(month_order, fill_value=0).reset_index(name='Total')
        fig_month = px.line(monthly_counts, x='Month', y='Total', markers=True, color_discrete_sequence=['#E74C3C'])
        st.plotly_chart(fig_month, use_container_width=True)

    st.subheader("12-Month Moving Average (Market Velocity)")
    growth_data = filtered_df.groupby('YearMonth').size().reset_index(name='Count')
    growth_data['YearMonth_DT'] = pd.to_datetime(growth_data['YearMonth'])
    growth_data = growth_data.sort_values('YearMonth_DT')
    growth_data['MA12'] = growth_data['Count'].rolling(window=12).mean()
    fig_ma = go.Figure()
    fig_ma.add_trace(go.Scatter(x=growth_data['YearMonth'], y=growth_data['Count'], name="Monthly Apps", opacity=0.3, line=dict(color='gray')))
    fig_ma.add_trace(go.Scatter(x=growth_data['YearMonth'], y=growth_data['MA12'], name="12-Month Trend", line=dict(color='red', width=3)))
    st.plotly_chart(fig_ma, use_container_width=True)

elif menu == "Classification & Country Strength":
    st.header("🌍 IPC Strength & Country Activity")
    heat_df = filtered_df.groupby(['Country Name (Priority)', 'Primary_IPC']).size().reset_index(name='Apps')
    top_ipcs = heat_df.groupby('Primary_IPC')['Apps'].sum().nlargest(20).index
    heat_df_top = heat_df[heat_df['Primary_IPC'].isin(top_ipcs)]
    fig_heat = px.density_heatmap(heat_df_top, x="Primary_IPC", y="Country Name (Priority)", z="Apps", color_continuous_scale="Viridis", text_auto=True)
    st.plotly_chart(fig_heat, use_container_width=True)
    st.dataframe(heat_df_top.sort_values(by=['Country Name (Priority)', 'Apps'], ascending=[True, False]), use_container_width=True)

# --- GLOBAL PRIORITY & COMPARISONS ---
elif menu == "Global Priority & Comparisons":
    st.header("🏁 Global Priority vs Country & Classification")
    p_filtered = filtered_df[(filtered_df['Priority_Year'] >= p_year_range[0]) & (filtered_df['Priority_Year'] <= p_year_range[1])]

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Invention Volume by Priority Year")
        p_counts = p_filtered.groupby('Priority_Year').size().reset_index(name='Count')
        fig_p_year = px.area(p_counts, x='Priority_Year', y='Count', color_discrete_sequence=['#27ae60'])
        fig_p_year.update_yaxes(nticks=20)
        st.plotly_chart(fig_p_year, use_container_width=True)

    with c2:
        st.subheader("Monthly Priority: Year-over-Year (All 12 Months)")
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        years_in_range = range(p_year_range[0], p_year_range[1] + 1)
        template = pd.MultiIndex.from_product([years_in_range, month_order], names=['Priority_Year', 'Priority_Month']).to_frame(index=False)
        actual_p = p_filtered.groupby(['Priority_Year', 'Priority_Month']).size().reset_index(name='Apps')
        p_month_counts = pd.merge(template, actual_p, on=['Priority_Year', 'Priority_Month'], how='left').fillna(0)
        p_month_counts['Priority_Year'] = p_month_counts['Priority_Year'].astype(str)
        fig_p_month = px.bar(p_month_counts, x='Priority_Month', y='Apps', color='Priority_Year', barmode='group', text_auto=True, category_orders={"Priority_Month": month_order}, color_discrete_sequence=px.colors.qualitative.Prism)
        st.plotly_chart(fig_p_month, use_container_width=True)

    st.subheader("Priority Distribution by Country")
    top_10 = p_filtered['Country Name (Priority)'].value_counts().nlargest(10).index
    fig_box = px.box(p_filtered[p_filtered['Country Name (Priority)'].isin(top_10)], x='Priority_Year', y='Country Name (Priority)', color='Country Name (Priority)')
    st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("Technology Evolution (Priority Year vs Classifications)")
    top_5_ipcs = p_filtered['Primary_IPC'].value_counts().nlargest(5).index
    ipc_trend = p_filtered[p_filtered['Primary_IPC'].isin(top_5_ipcs)].groupby(['Priority_Year', 'Primary_IPC']).size().reset_index(name='Count')
    fig_ipc_time = px.line(ipc_trend, x='Priority_Year', y='Count', color='Primary_IPC', markers=True)
    st.plotly_chart(fig_ipc_time, use_container_width=True)

elif menu == "Expert Search":
    st.header("🔍 Identify Experts and Patent Details")
    search = st.text_input("Search IPC, Title, or Applicant")
    if search:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        results = filtered_df[mask]
        st.write(f"Matches found: {len(results)}")
        st.dataframe(results[['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date', 'Priority_Year']], use_container_width=True)
