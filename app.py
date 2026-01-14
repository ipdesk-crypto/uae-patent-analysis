import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Analysis Pro", layout="wide", page_icon="🇦🇪")

# --- DATA REFINEMENT ENGINE ---
def refine_data(df):
    """Accurate date extraction and cleaning logic."""
    df.columns = df.columns.str.strip()

    # 1. Date processing for Application Date - UAE Filing (YYYY-MM-DD format)
    if 'Application Date' in df.columns:
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df['Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
        df['Month'] = df['Application Date'].dt.month_name()
        df['YearMonth'] = df['Application Date'].dt.to_period('M').astype(str)
    
    # 2. Date processing for Earliest Priority Date - Global Priority
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df['Priority_Year'] = df['Earliest Priority Date'].dt.year.fillna(0).astype(int)
        df['Priority_Month'] = df['Earliest Priority Date'].dt.month_name()
    
    # 3. IPC Extraction
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
        try:
            raw_upload = pd.read_csv(uploaded_file)
            df = refine_data(raw_upload)
            st.sidebar.success("✅ Custom data loaded!")
        except Exception as e:
            st.sidebar.error(f"Error loading file: {e}")
            st.stop()
else:
    try:
        raw_df = pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv")
        df = refine_data(raw_df)
    except FileNotFoundError:
        st.error("Default dataset not found. Please upload a CSV instead.")
        st.stop()

# --- SIDEBAR: NAVIGATION & FILTERS ---
if df is not None:
    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Go to:", [
        "Time-Series Growth", 
        "Classification & Country Strength", 
        "Global Priority & Comparisons", 
        "Expert Search"
    ])

    valid_years = sorted(df[df['Year'] > 0]['Year'].unique(), reverse=True) if 'Year' in df.columns else []
    all_countries = sorted(df['Country Name (Priority)'].dropna().unique()) if 'Country Name (Priority)' in df.columns else []

    selected_year = st.sidebar.selectbox("Focus Year (for monthly view)", valid_years) if valid_years else None
    selected_country = st.sidebar.multiselect("Filter by Country", all_countries)

    filtered_df = df.copy()
    if selected_country:
        filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_country)]

    # --- TIME-SERIES GROWTH ---
    if menu == "Time-Series Growth":
        st.header("📈 Growth Trends & Temporal Analysis")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Total Applications per Year")
            yearly_counts = filtered_df[filtered_df['Year'] >= 1990].groupby('Year').size().reset_index(name='Number of Applications')
            fig_year = px.bar(yearly_counts, x='Year', y='Number of Applications', text='Number of Applications', 
                              labels={'Number of Applications': 'Number of Applications', 'Year': 'Filing Year'}, 
                              color_discrete_sequence=['#3498db'])
            fig_year.update_traces(textposition='outside', textfont=dict(size=14, family="Arial Black"))
            fig_year.update_xaxes(type='category', tickangle=45)
            fig_year.update_yaxes(title="Number of Applications", dtick=10, showgrid=True)
            st.plotly_chart(fig_year, use_container_width=True)
        with col2:
            st.subheader("Data Table Verification")
            # Hide index removed the "random numbers" column
            st.dataframe(yearly_counts.sort_values('Year', ascending=False), use_container_width=True, height=450, hide_index=True)

        st.markdown("---")
        st.subheader(f"Monthly Distribution for {selected_year}")
        if selected_year:
            year_df = filtered_df[filtered_df['Year'] == selected_year]
            month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
            monthly_counts = year_df.groupby('Month').size().reindex(month_order, fill_value=0).reset_index(name='Number of Applications')
            
            fig_month = px.line(monthly_counts, x='Month', y='Number of Applications', markers=True, text='Number of Applications',
                                labels={'Number of Applications': 'Number of Applications'})
            fig_month.update_traces(textposition='top center', textfont=dict(family="Arial Black"))
            fig_month.update_yaxes(dtick=5, title="Number of Applications")
            st.plotly_chart(fig_month, use_container_width=True)

    # --- IPC LEADERSHIP ANALYSIS ---
    elif menu == "Classification & Country Strength":
        st.header("🌍 IPC Strength & Country Activity")
        st.subheader("🚀 Technology Leadership by Country")
        all_ipcs = sorted(filtered_df['Primary_IPC'].dropna().unique())
        all_ipcs = [x for x in all_ipcs if x != "Ther"]
        target_ipc = st.selectbox("Select an IPC Classification to see leading countries:", all_ipcs)
        
        ipc_leader_df = filtered_df[filtered_df['Primary_IPC'] == target_ipc]
        leader_counts = ipc_leader_df.groupby('Country Name (Priority)').size().reset_index(name='Number of Applications').sort_values('Number of Applications', ascending=False)
        
        fig_leader = px.bar(leader_counts, x='Country Name (Priority)', y='Number of Applications', 
                            text='Number of Applications', title=f"Top Countries for {target_ipc}", 
                            labels={'Number of Applications': 'Number of Applications'},
                            color='Number of Applications', color_continuous_scale='Reds')
        fig_leader.update_traces(textposition='outside', textfont=dict(family="Arial Black"))
        fig_leader.update_yaxes(dtick=5, title="Number of Applications")
        st.plotly_chart(fig_leader, use_container_width=True)

        st.markdown("---")
        st.subheader("Global Classification Heatmap")
        heat_data = filtered_df.dropna(subset=['Primary_IPC', 'Country Name (Priority)'])
        heat_data = heat_data[heat_data['Primary_IPC'] != "Ther"]
        if not heat_data.empty:
            heat_grouped = heat_data.groupby(['Country Name (Priority)', 'Primary_IPC']).size().reset_index(name='Number of Applications')
            top_ipcs = heat_grouped.groupby('Primary_IPC')['Number of Applications'].sum().nlargest(20).index
            heat_df_top = heat_grouped[heat_grouped['Primary_IPC'].isin(top_ipcs)]
            fig_heat = px.density_heatmap(heat_df_top, x="Primary_IPC", y="Country Name (Priority)", z="Number of Applications", 
                                          labels={'Number of Applications': 'Number of Applications'},
                                          color_continuous_scale="Viridis", text_auto=True)
            st.plotly_chart(fig_heat, use_container_width=True)

    # --- GLOBAL PRIORITY ---
    elif menu == "Global Priority & Comparisons":
        st.header("🏁 Global Priority Analysis")
        valid_p = df[df['Priority_Year'] > 1900]['Priority_Year']
        p_min, p_max = int(valid_p.min()), int(valid_p.max())
        p_range = st.sidebar.slider("Priority Year Range", p_min, p_max, (p_max-5, p_max))
        p_df = filtered_df[(filtered_df['Priority_Year'] >= p_range[0]) & (filtered_df['Priority_Year'] <= p_range[1])]
        
        col_chart, col_table = st.columns([2, 1])
        
        with col_chart:
            st.subheader("Monthly Priority Distribution (Grouped by Year)")
            month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
            years = range(p_range[0], p_range[1] + 1)
            template = pd.MultiIndex.from_product([years, month_order], names=['Priority_Year', 'Priority_Month']).to_frame(index=False)
            actual = p_df.groupby(['Priority_Year', 'Priority_Month']).size().reset_index(name='Number of Applications')
            merged = pd.merge(template, actual, on=['Priority_Year', 'Priority_Month'], how='left').fillna(0)
            merged['Priority_Year'] = merged['Priority_Year'].astype(str)
            
            fig_m = px.bar(merged, x='Priority_Month', y='Number of Applications', color='Priority_Year', barmode='group', text='Number of Applications',
                           labels={'Number of Applications': 'Number of Applications'},
                           category_orders={"Priority_Month": month_order}, color_discrete_sequence=px.colors.qualitative.Prism)
            fig_m.update_traces(textposition='outside', textfont=dict(family="Arial Black"))
            fig_m.update_yaxes(dtick=5, title="Number of Applications")
            st.plotly_chart(fig_m, use_container_width=True)

        with col_table:
            st.subheader("📌 Priority Summary Table")
            st.write(f"Data for: {p_range[0]} - {p_range[1]}")
            # Summary Table with consistent labeling and hidden index
            summary_p = p_df.groupby('Priority_Year').size().reset_index(name='Number of Applications')
            st.dataframe(summary_p.sort_values('Priority_Year', ascending=False), use_container_width=True, hide_index=True)
            
            st.write("Full Monthly Detail")
            detail_p = p_df.groupby(['Priority_Year', 'Priority_Month']).size().reset_index(name='Number of Applications')
            st.dataframe(detail_p.sort_values(['Priority_Year', 'Number of Applications'], ascending=[False, False]), 
                         use_container_width=True, height=300, hide_index=True)

    # --- EXPERT SEARCH ---
    elif menu == "Expert Search":
        st.header("🔍 Identify Experts")
        search = st.text_input("Enter IPC, Title, or Applicant")
        if search:
            mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
            # Displaying raw data table with hidden index
            st.dataframe(filtered_df[mask][['Application Number', 'Title', 'Primary_IPC', 'Country Name (Priority)', 'Application Date', 'Priority_Year']], 
                         use_container_width=True, hide_index=True)

else:
    st.info("Please upload a CSV file or ensure the default dataset is available.")
