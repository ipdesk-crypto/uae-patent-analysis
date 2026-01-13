import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Set Page Config
st.set_page_config(page_title="UAE Patent Analysis Engine", layout="wide")

# --- DATA LOADING ---
@st.cache_data
def load_and_clean_data():
    # Load the CSV
    df = pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - Type 5.csv")
    
    # Date Conversions
    df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
    df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
    
    # Clean Classifications (Handle "There are no classifications")
    df['Classification'] = df['Classification'].replace("There are no classifications", "Unclassified")
    
    # Extract IPC Main Class (First 4 characters, e.g., 'A61K')
    df['IPC_Main'] = df['Classification'].str.split(',').str[0].str.strip().str[:4]
    
    # Create Month-Year column for time-series analysis
    df['Month_Year'] = df['Application Date'].dt.to_period('M').astype(str)
    
    return df

df = load_and_clean_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Navigation & Filters")
analysis_mode = st.sidebar.selectbox("Choose Analysis", ["Growth & Trends", "Country Specialization", "Expert Search"])

# Global Filters
selected_countries = st.sidebar.multiselect("Filter by Country", df['Country Name (Priority)'].unique())
selected_ipcs = st.sidebar.multiselect("Filter by Classification (IPC)", df['IPC_Main'].unique())

filtered_df = df.copy()
if selected_countries:
    filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_countries)]
if selected_ipcs:
    filtered_df = filtered_df[filtered_df['IPC_Main'].isin(selected_ipcs)]

# --- MAIN DASHBOARD ---
st.title("🇦🇪 UAE Patent Analysis Engine (Type 5)")

if analysis_mode == "Growth & Trends":
    st.header("📈 Growth & 12-Month Moving Average")
    
    # Prepare monthly data
    growth_df = filtered_df.groupby('Month_Year').size().reset_index(name='New Applications')
    growth_df['Month_Year'] = pd.to_datetime(growth_df['Month_Year'])
    growth_df = growth_df.sort_values('Month_Year')
    
    # 12-Month Moving Average
    growth_df['MA12'] = growth_df['New Applications'].rolling(window=12).mean()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=growth_df['Month_Year'], y=growth_df['New Applications'], name="Monthly New Data", line=dict(color='lightblue')))
    fig.add_trace(go.Scatter(x=growth_df['Month_Year'], y=growth_df['MA12'], name="12-Month Moving Average", line=dict(color='red', width=3)))
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.header("📅 Applications vs. Earliest Priority Date")
    priority_fig = px.scatter(filtered_df, x='Earliest Priority Date', y='Application Date', 
                              color='Country Name (Priority)', hover_data=['Title'],
                              title="Timeline: Application Filing vs. Earliest Priority")
    st.plotly_chart(priority_fig, use_container_width=True)

elif analysis_mode == "Country Specialization":
    st.header("🌍 Classification Strength by Country (IPC vs. Country)")
    
    # Group by Country and IPC to find strengths
    strength_df = filtered_df.groupby(['Country Name (Priority)', 'IPC_Main']).size().reset_index(name='Activity Count')
    strength_df = strength_df[strength_df['IPC_Main'] != "Uncl"] # Filter out unclassified
    
    # Heatmap of Activity
    fig_heat = px.density_heatmap(strength_df, x="IPC_Main", y="Country Name (Priority)", z="Activity Count",
                                  color_continuous_scale="Viridis", title="Heatmap of IPC Activities per Country")
    st.plotly_chart(fig_heat, use_container_width=True)
    
    st.subheader("Top Active Classifications")
    top_ipcs = strength_df.groupby('IPC_Main')['Activity Count'].sum().nlargest(10).reset_index()
    fig_bar = px.bar(top_ipcs, x='IPC_Main', y='Activity Count', title="Most Active IPC Classes Overall")
    st.plotly_chart(fig_bar, use_container_width=True)

elif analysis_mode == "Expert Search":
    st.header("🔍 Expert & Patent Search")
    query = st.text_input("Search by Keyword (Title or Classification)")
    
    if query:
        search_df = filtered_df[filtered_df['Title'].str.contains(query, case=False, na=False) | 
                                filtered_df['Classification'].str.contains(query, case=False, na=False)]
    else:
        search_df = filtered_df
        
    st.write(f"Showing {len(search_df)} matches:")
    st.dataframe(search_df[['Application Number', 'Title', 'Classification', 'Country Name (Priority)', 'Application Date']], use_container_width=True)