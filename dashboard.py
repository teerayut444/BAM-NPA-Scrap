import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys
import re
import json
import math
from pathlib import Path

# Helper function to read total count of properties on web
def get_web_total_count():
    meta_file = Path("metadata.json")
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
                return int(meta.get("total_count", 16541))
        except Exception:
            pass
    return 16541


# Haversine distance calculation (km)
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def find_nearby_properties(input_lat, input_lon, df_bam, radius_km, match_type=None, match_name=None):
    """Find BAM properties within radius_km of the given coordinates."""
    results = []
    for _, row in df_bam.iterrows():
        bam_lat = row.get('ละติจูด')
        bam_lon = row.get('ลองจิจูด')
        if pd.isna(bam_lat) or pd.isna(bam_lon):
            continue
        # Filter by property type if specified
        if match_type and str(match_type).strip() != '' and str(match_type).lower() != 'nan':
            if str(row.get('ประเภททรัพย์', '')).strip() != str(match_type).strip():
                continue
        # Filter by name keyword if specified
        if match_name and str(match_name).strip() != '' and str(match_name).lower() != 'nan':
            if str(match_name).lower() not in str(row.get('ชื่อประกาศ', '')).lower():
                continue
        dist = haversine_distance(input_lat, input_lon, float(bam_lat), float(bam_lon))
        if dist <= radius_km:
            result_row = row.to_dict()
            result_row['ระยะทาง (กม.)'] = round(dist, 2)
            results.append(result_row)
    return pd.DataFrame(results)

# Configure Streamlit page layout
st.set_page_config(
    page_title="BAM NPA Property Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# (Static CSS block removed - style configuration moved to dynamic theme choice in sidebar)

# Helper function to find python inside .venv
def get_python_executable():
    # Windows
    venv_python = Path(".venv") / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python.resolve())
    # Linux / Streamlit Cloud
    venv_python_linux = Path(".venv") / "bin" / "python"
    if venv_python_linux.exists():
        return str(venv_python_linux.resolve())
    return sys.executable

# Helper function to safely format numeric fields (e.g., bedrooms, area) to nice string
def format_num_val(val):
    if pd.isna(val) or str(val).strip() == "" or str(val).lower() == "nan" or val is None:
        return ""
    try:
        f_val = float(val)
        if f_val.is_integer():
            return str(int(f_val))
        return str(f_val)
    except ValueError:
        return str(val)

# Cached function to load data from excel
@st.cache_data(ttl=60) # Cache for 1 minute, auto refresh if changes occur
def load_properties_data():
    excel_file = Path("BAM NPA.xlsx")
    if not excel_file.exists():
        return None
        
    try:
        # Load excel file
        df = pd.read_excel(excel_file)
        
        # Replace $undefined and undefined values with NaN
        df = df.replace(["$undefined", "undefined"], np.nan)
        
        # Clean coordinates
        df['ละติจูด'] = pd.to_numeric(df['ละติจูด'], errors='coerce')
        df['ลองจิจูด'] = pd.to_numeric(df['ลองจิจูด'], errors='coerce')
        
        # Clean prices
        df['ราคา'] = pd.to_numeric(df['ราคา'], errors='coerce')
        
        # Fill NaN values in essential text columns
        df['ชื่อประกาศ'] = df['ชื่อประกาศ'].fillna("ไม่มีชื่อประกาศ").astype(str)
        df['รหัสทรัพย์'] = df['รหัสทรัพย์'].fillna("-").astype(str)
        df['ประเภททรัพย์'] = df['ประเภททรัพย์'].fillna("อื่นๆ").astype(str)
        df['จังหวัด'] = df['จังหวัด'].fillna("ไม่ระบุ").astype(str)
        df['ตำบล'] = df['ตำบล'].fillna("").astype(str)
        df['อำเภอ'] = df['อำเภอ'].fillna("").astype(str)
        df['ชื่อโครงการ'] = df['ชื่อโครงการ'].fillna("").astype(str)
        df['ประเภทการขาย'] = df['ประเภทการขาย'].fillna("").astype(str)
        df['พื้นที่ (ไร่-งาน-วา)'] = df['พื้นที่ (ไร่-งาน-วา)'].fillna("").astype(str)
        df['วันที่ดึงข้อมูล'] = df['วันที่ดึงข้อมูล'].fillna("").astype(str)
        
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดไฟล์ Excel: {e}")
        return None

# Load the properties data
df_raw = load_properties_data()

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown('<h2 style="color: #6366f1;"><i class="fa fa-home"></i> BAM NPA Dashboard</h2>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Set Theme Variables (Forced Light Theme)
    bg_color = "rgba(243, 244, 246, 0.9)"
    border_color = "rgba(0, 0, 0, 0.08)"
    text_title = "#4b5563"
    text_value_style = "background: linear-gradient(135deg, #4f46e5 0%, #0891b2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;"
    text_sub = "#4b5563"
    card_bg = "#ffffff"
    card_border = "rgba(0, 0, 0, 0.08)"
    card_title_color = "#1f2937"
    card_text_color = "#4b5563"
    mapbox_style = "open-street-map"
    plot_font_color = "#1f2937"
    color_scale_prov = "Blues"
    map_legend_bg = "rgba(255, 255, 255, 0.9)"
    map_legend_border = "rgba(0, 0, 0, 0.08)"
    map_legend_text = "#1f2937"
    plotly_template = "plotly_white"
    
    # End of sidebar header variables
    pass

# Global CSS Inject (No indentation to prevent Markdown code block rendering)
st.html("""<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Sarabun:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stSidebar"], .stApp {
    font-family: 'Outfit', 'Sarabun', sans-serif;
}

body, .stApp {
    background-color: #f9fafb !important;
    color: #1f2937 !important;
}

h1, h2, h3, h4, h5, h6 {
    color: #1f2937 !important;
}

section[data-testid="stSidebar"] {
    background-color: #f3f4f6 !important;
    border-right: 1px solid rgba(0, 0, 0, 0.08) !important;
}

/* Top Header Bar */
header[data-testid="stHeader"] {
    background-color: #f9fafb !important;
    background: #f9fafb !important;
    border-bottom: 1px solid rgba(0, 0, 0, 0.08) !important;
}
div[data-testid="stDecoration"] {
    background: transparent !important;
}

/* Sidebar Text Color overrides */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #1f2937 !important;
}
section[data-testid="stSidebar"] i {
    color: #6366f1 !important;
}

/* Light theme overrides for Streamlit BaseWeb components */
div[data-baseweb="select"] {
    background-color: transparent !important;
}
div[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border: 1px solid rgba(0, 0, 0, 0.15) !important;
    border-radius: 4px;
}
div[data-baseweb="select"] div {
    background-color: transparent !important;
    color: #1f2937 !important;
}
div[data-baseweb="select"] input {
    color: #1f2937 !important;
}
div[data-baseweb="select"] span {
    color: #1f2937 !important;
}

/* Dropdown popups */
div[role="listbox"], ul[role="listbox"], div[data-baseweb="menu"] {
    background-color: #ffffff !important;
    border: 1px solid rgba(0, 0, 0, 0.12) !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
}
div[role="listbox"] div, ul[role="listbox"] li, div[data-baseweb="menu"] div {
    background-color: #ffffff !important;
    color: #1f2937 !important;
}
div[role="option"]:hover, li[role="option"]:hover, div[data-baseweb="menu"] div:hover {
    background-color: #f3f4f6 !important;
    color: #1f2937 !important;
}

/* Multiselect selected items (tags) */
span[data-baseweb="tag"] {
    background-color: #e5e7eb !important;
    border: 1px solid rgba(0, 0, 0, 0.08) !important;
}
span[data-baseweb="tag"] div {
    background-color: transparent !important;
}
span[data-baseweb="tag"] span {
    color: #1f2937 !important;
    background-color: transparent !important;
}

/* Input fields (Text & Number Inputs) and Buttons */
div[data-testid="stTextInput"] input, 
div[data-testid="stNumberInput"] input,
input[type="text"], 
input[type="number"] {
    background-color: #ffffff !important;
    color: #1f2937 !important;
    border: 1px solid rgba(0, 0, 0, 0.15) !important;
}

div[data-testid="stNumberInput"] button {
    background-color: #ffffff !important;
    color: #1f2937 !important;
    border: 1px solid rgba(0, 0, 0, 0.15) !important;
}
div[data-testid="stNumberInput"] button:hover {
    background-color: #f3f4f6 !important;
}

/* Slider */
div[data-testid="stSlider"] * {
    color: #1f2937 !important;
}

/* Tabs styling */
button[data-baseweb="tab"] p {
    color: #4b5563 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    border-bottom-color: #6366f1 !important;
}
button[data-baseweb="tab"][aria-selected="true"] p {
    color: #6366f1 !important;
}

/* Metrics panel styling */
.metric-card {
    background: rgba(243, 244, 246, 0.9) !important;
    border: 1px solid rgba(0, 0, 0, 0.08) !important;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    border-color: rgba(99, 102, 241, 0.4) !important;
}
.metric-title {
    font-size: 0.9rem;
    color: #4b5563 !important;
    margin-bottom: 5px;
    font-weight: 500;
}
.metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, #4f46e5 0%, #0891b2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.metric-sub {
    font-size: 0.8rem;
    color: #4b5563 !important;
    margin-top: 5px;
    font-weight: 600;
}

/* Subtitle styling */
.dashboard-subtitle {
    color: #4b5563 !important;
    margin-bottom: 25px;
    font-size: 1.1rem;
}

/* Fix label visibility for all widgets */
label, p, span,
.stTextInput label, .stNumberInput label, 
.stSelectbox label, .stMultiselect label, .stSlider label,
.stRadio label, .stCheckbox label, .stFileUploader label,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p {
    color: #1f2937 !important;
}

/* Radio button option text */
.stRadio div[role="radiogroup"] label span,
.stRadio div[role="radiogroup"] label p,
[data-testid="stRadio"] label span,
[data-testid="stRadio"] label p {
    color: #1f2937 !important;
}

/* Checkbox text */
.stCheckbox label span, .stCheckbox label p,
[data-testid="stCheckbox"] label span,
[data-testid="stCheckbox"] label p {
    color: #1f2937 !important;
}

/* Expander header text - comprehensive selectors */
.streamlit-expanderHeader, .streamlit-expanderHeader p,
details summary, details summary span, details summary p,
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] details summary,
[data-testid="stExpanderToggleDetails"] summary,
[data-testid="stExpanderToggleDetails"] summary span,
[data-testid="stExpanderToggleDetails"] summary p {
    color: #1f2937 !important;
    background-color: #f3f4f6 !important;
}

/* Info, warning, success message boxes text */
[data-testid="stAlert"] p {
    color: #1f2937 !important;
}

/* Caption text */
.stCaption, .stCaption p, [data-testid="stCaption"] p {
    color: #4b5563 !important;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""")

with st.sidebar:
    st.markdown("---")
    
    st.markdown("### <i class='fa fa-filter'></i> ตัวกรองข้อมูลทรัพย์สิน", unsafe_allow_html=True)
    
    if df_raw is not None and not df_raw.empty:
        # Search Box
        search_query = st.text_input("ค้นหา ชื่อทรัพย์ หรือรหัสทรัพย์", value="")
        
        # Property Type Filter
        unique_types = sorted(df_raw['ประเภททรัพย์'].unique().tolist())
        selected_types = st.multiselect("ประเภททรัพย์สิน", options=unique_types, default=unique_types)
        
        # Sale Type Filter
        unique_sales = sorted([x for x in df_raw['ประเภทการขาย'].unique().tolist() if pd.notnull(x) and str(x).strip() != "" and str(x).strip() != "nan"])
        if unique_sales:
            selected_sales = st.multiselect("ประเภทการขาย", options=unique_sales, default=unique_sales)
        else:
            selected_sales = []
            
        # Province Filter
        unique_provinces = sorted(df_raw['จังหวัด'].unique().tolist())
        selected_provinces = st.multiselect("จังหวัด", options=unique_provinces, default=[])
        
        # District Filter (dynamically populate from selected provinces)
        if selected_provinces:
            filtered_provinces_df = df_raw[df_raw['จังหวัด'].isin(selected_provinces)]
        else:
            filtered_provinces_df = df_raw
            
        unique_districts = sorted(filtered_provinces_df['อำเภอ'].dropna().unique().tolist())
        selected_districts = st.multiselect("อำเภอ / เขต", options=unique_districts, default=[])
        
        # Price Filter
        valid_prices = df_raw['ราคา'].dropna()
        if not valid_prices.empty:
            min_price_val = float(valid_prices.min())
            max_price_val = float(valid_prices.max())
            
            # Formatting min/max for readable slider
            price_range = st.slider(
                "ช่วงราคาขาย (บาท)",
                min_value=min_price_val,
                max_value=max_price_val,
                value=(min_price_val, max_price_val),
                format="%d"
            )
        else:
            price_range = (0.0, 1000000000.0)
    else:
        st.warning("ไม่มีตัวกรองข้อมูลเนื่องจากยังไม่มีไฟล์ข้อมูล BAM NPA.xlsx")

# ----------------- MAIN VIEW -----------------
st.markdown(f'<h1 style="margin-bottom: 0px; color: {card_title_color};">📊 BAM NPA Property Dashboard</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="dashboard-subtitle" style="color: {text_title}; margin-top: 5px;">ระบบรายงานสถิติและแผนที่เชิงวิเคราะห์สำหรับทรัพย์สินรอการขาย (NPA) ของบริษัทบริหารสินทรัพย์ กรุงเทพพาณิชย์ จำกัด (มหาชน)</p>', unsafe_allow_html=True)

# Check if data exists
if df_raw is None or df_raw.empty:
    st.markdown("""
    <div style="background-color: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 25px; text-align: center; margin-top: 20px;">
        <i class="fa-solid fa-triangle-exclamation" style="font-size: 3.5rem; color: #ef4444; margin-bottom: 15px;"></i>
        <h3 style="color: #ef4444; margin-bottom: 10px;">ไม่พบไฟล์ข้อมูล 'BAM NPA.xlsx'</h3>
        <p style="color: #1f2937; font-size: 1.05rem;">ระบบต้องการไฟล์ Excel ข้อมูลจากการรันระบบ Scraper ก่อน</p>
        <p style="color: #4b5563; font-size: 0.95rem;">ท่านสามารถรันระบบ Scraper ได้ทันทีโดยใช้แผงควบคุม <b>"🤖 ดึงข้อมูลใหม่จากเว็บ BAM"</b> บนแถบเมนูด้านซ้าย</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ----------------- DATA FILTERING LOGIC -----------------
# 1. Search Query
df_filtered = df_raw.copy()
if search_query:
    search_pattern = re.escape(search_query)
    df_filtered = df_filtered[
        df_filtered['ชื่อประกาศ'].str.contains(search_pattern, case=False, na=False) |
        df_filtered['รหัสทรัพย์'].str.contains(search_pattern, case=False, na=False) |
        df_filtered['ชื่อโครงการ'].str.contains(search_pattern, case=False, na=False)
    ]

# 2. Property Types
if selected_types:
    df_filtered = df_filtered[df_filtered['ประเภททรัพย์'].isin(selected_types)]

# 2b. Sale Types
if 'selected_sales' in locals() and selected_sales:
    df_filtered = df_filtered[df_filtered['ประเภทการขาย'].isin(selected_sales)]

# 3. Provinces
if selected_provinces:
    df_filtered = df_filtered[df_filtered['จังหวัด'].isin(selected_provinces)]

# 4. Districts
if selected_districts:
    df_filtered = df_filtered[df_filtered['อำเภอ'].isin(selected_districts)]

# 5. Price Range
if not valid_prices.empty:
    # Handle NaN values inside price (optional: treat as out of filter or default to 0)
    df_filtered = df_filtered[
        (df_filtered['ราคา'].isna()) | 
        ((df_filtered['ราคา'] >= price_range[0]) & (df_filtered['ราคา'] <= price_range[1]))
    ]

# ----------------- KPI METRICS RENDERING -----------------
# Calculate metric values
total_count = len(df_filtered)
total_value = df_filtered['ราคา'].sum() / 1e6  # Convert to Million Baht
avg_price = df_filtered['ราคา'].mean() / 1e6 if total_count > 0 else 0  # Convert to Million Baht

# Calculate scrape percentage metrics
total_scraped_local = len(df_raw) if df_raw is not None else 0
total_web_count = get_web_total_count()
scraped_percentage = (total_scraped_local / total_web_count * 100) if total_web_count > 0 else 0.0

# Calculate min/max prices
valid_prices_filtered = df_filtered['ราคา'].dropna()
min_price = valid_prices_filtered.min() if not valid_prices_filtered.empty else 0
max_price = valid_prices_filtered.max() if not valid_prices_filtered.empty else 0
min_price_str = f"{min_price:,.0f}" if min_price > 0 else "0"
max_price_str = f"{max_price:,.0f}" if max_price > 0 else "0"

# Format variables
total_value_str = f"{total_value:,.2f} ล้าน" if total_value > 0 else "0.00"
avg_price_str = f"{avg_price:,.2f} ล้าน" if avg_price > 0 else "0.00"

# KPI Display Columns (5 boxes)
kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)

with kpi_col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title"><i class="fa-solid fa-cloud-arrow-down" style="color: #6366f1;"></i> ความคืบหน้าเก็บข้อมูล</div>
        <div class="metric-value">{scraped_percentage:.1f}%</div>
        <div class="metric-sub">ดึงแล้ว {total_scraped_local:,.0f} จาก {total_web_count:,.0f} ทรัพย์</div>
        <div style="width: 100%; background-color: #e5e7eb; border-radius: 4px; height: 6px; margin-top: 10px; overflow: hidden;">
            <div style="width: {min(100.0, scraped_percentage):.1f}%; background-color: #6366f1; height: 100%; border-radius: 4px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title"><i class="fa fa-wallet" style="color: #06b6d4;"></i> มูลค่าทรัพย์สินรวม</div>
        <div class="metric-value">฿{total_value_str}</div>
        <div class="metric-sub">หน่วย: ล้านบาท</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title"><i class="fa fa-tags" style="color: #10b981;"></i> ราคาเฉลี่ย</div>
        <div class="metric-value">฿{avg_price_str}</div>
        <div class="metric-sub">หน่วย: ล้านบาท / ทรัพย์</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title"><i class="fa fa-arrow-down" style="color: #22c55e;"></i> ราคาต่ำสุด (Min)</div>
        <div class="metric-value">฿{min_price_str}</div>
        <div class="metric-sub" style="color: #22c55e;">บาท</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title"><i class="fa fa-arrow-up" style="color: #f59e0b;"></i> ราคาสูงสุด (Max)</div>
        <div class="metric-value">฿{max_price_str}</div>
        <div class="metric-sub" style="color: #f59e0b;">บาท</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# ----------------- TABS CREATION -----------------
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ แผนที่ทรัพย์สิน (Interactive Map)", "📈 สถิติ & วิเคราะห์ (Analytics)", "📋 รายการทรัพย์สิน (Property Listing)", "🔍 เปรียบเทียบทรัพย์ (Comparison)"])

# ----- TAB 1: INTERACTIVE MAP -----
with tab1:
    st.markdown("### 🗺️ แผนที่ตำแหน่งที่ตั้งทรัพย์สินรอการขาย (BAM Properties)")
    
    # Filter rows with coordinates
    map_data = df_filtered[df_filtered['ละติจูด'].notna() & df_filtered['ลองจิจูด'].notna()].copy()
    
    if map_data.empty:
        st.warning("⚠️ ไม่พบข้อมูลทรัพย์สินที่มีพิกัดละติจูด/ลองจิจูด ในรายการที่เลือกกรอง")
        st.info("คำแนะนำ: ทรัพย์สินบางประเภทหรือหน้าระดับจังหวัดอื่นอาจยังไม่ได้เปิดหน้าดูรายละเอียดเพื่อสแกนพิกัด ให้ลองคลิกเรียก Scraper ดึงข้อมูลเพิ่ม")
    else:
        # Create interactive Mapbox scatter plot
        fig_map = px.scatter_mapbox(
            map_data,
            lat="ละติจูด",
            lon="ลองจิจูด",
            color="ประเภททรัพย์",
            size=map_data["ราคา"].fillna(100000).clip(lower=100000), # Clip very small/free for circle visibility
            hover_name="ชื่อประกาศ",
            hover_data={
                "รหัสทรัพย์": True,
                "ราคา": ":,.0f",
                "จังหวัด": True,
                "ประเภททรัพย์": False,
                "ละติจูด": False,
                "ลองจิจูด": False
            },
            zoom=6,
            height=650,
            color_discrete_sequence=px.colors.qualitative.Bold,
            template=plotly_template
        )
        
        # Configure layout dynamically based on theme style
        fig_map.update_layout(
            mapbox_style=mapbox_style,
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor=map_legend_bg,
                bordercolor=map_legend_border,
                borderwidth=1,
                font=dict(color=map_legend_text, size=11)
            )
        )
        
        st.plotly_chart(fig_map, use_container_width=True, theme=None)

# ----- TAB 2: ANALYTICS -----
with tab2:
    st.markdown("### 📈 ข้อมูลเชิงสถิติและแผนภูมิวิเคราะห์")
    
    if df_filtered.empty:
        st.warning("⚠️ ไม่มีข้อมูลสำหรับใช้วิเคราะห์ทางสถิติ")
    else:
        col_chart1, col_chart2 = st.columns(2)
        
        # CHART 1: Pie chart of property types
        with col_chart1:
            type_data = df_filtered['ประเภททรัพย์'].value_counts().reset_index()
            type_data.columns = ['ประเภททรัพย์', 'จำนวนประกาศ']
            
            fig_pie = px.pie(
                type_data,
                names='ประเภททรัพย์',
                values='จำนวนประกาศ',
                hole=0.45,
                title='สัดส่วนประเภททรัพย์สินที่มีในรายการ',
                color_discrete_sequence=px.colors.qualitative.Pastel,
                template=plotly_template
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=plot_font_color),
                title_font=dict(size=16, color=plot_font_color, family="Outfit")
            )
            st.plotly_chart(fig_pie, use_container_width=True, theme=None)
            
        # CHART 2: Average price by property type
        with col_chart2:
            avg_price_data = df_filtered.groupby('ประเภททรัพย์')['ราคา'].mean().reset_index()
            avg_price_data.columns = ['ประเภททรัพย์', 'ราคาเฉลี่ย (บาท)']
            avg_price_data = avg_price_data.sort_values(by='ราคาเฉลี่ย (บาท)', ascending=False)
            
            fig_bar_avg = px.bar(
                avg_price_data,
                x='ประเภททรัพย์',
                y='ราคาเฉลี่ย (บาท)',
                title='ราคาตั้งขายเฉลี่ยแยกตามประเภททรัพย์สิน',
                color='ประเภททรัพย์',
                color_discrete_sequence=px.colors.qualitative.Pastel,
                template=plotly_template
            )
            fig_bar_avg.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=plot_font_color),
                showlegend=False,
                title_font=dict(size=16, color=plot_font_color, family="Outfit")
            )
            st.plotly_chart(fig_bar_avg, use_container_width=True, theme=None)
            
        st.markdown("<br/>", unsafe_allow_html=True)
        col_chart3, col_chart4 = st.columns(2)
        
        # CHART 3: Top provinces
        with col_chart3:
            province_data = df_filtered['จังหวัด'].value_counts().head(10).reset_index()
            province_data.columns = ['จังหวัด', 'จำนวนประกาศ']
            province_data = province_data.sort_values(by='จำนวนประกาศ', ascending=True)
            
            fig_prov = px.bar(
                province_data,
                x='จำนวนประกาศ',
                y='จังหวัด',
                orientation='h',
                title='10 ลำดับจังหวัดที่มีรายการประกาศขายมากที่สุด',
                color='จำนวนประกาศ',
                color_continuous_scale=color_scale_prov,
                template=plotly_template
            )
            fig_prov.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=plot_font_color),
                title_font=dict(size=16, color=plot_font_color, family="Outfit"),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_prov, use_container_width=True, theme=None)
            
        # CHART 4: Discount analysis histogram
        # CHART 4: Top districts
        with col_chart4:
            district_data = df_filtered['อำเภอ'].value_counts().head(10).reset_index()
            district_data.columns = ['อำเภอ', 'จำนวนประกาศ']
            district_data = district_data.sort_values(by='จำนวนประกาศ', ascending=True)
            
            fig_dist = px.bar(
                district_data,
                x='จำนวนประกาศ',
                y='อำเภอ',
                orientation='h',
                title='10 ลำดับอำเภอ/เขตที่มีรายการประกาศขายมากที่สุด',
                color='จำนวนประกาศ',
                color_continuous_scale="Purples",
                template=plotly_template
            )
            fig_dist.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=plot_font_color),
                title_font=dict(size=16, color=plot_font_color, family="Outfit"),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_dist, use_container_width=True, theme=None)

# ----- TAB 3: PROPERTY LIST -----
with tab3:
    st.markdown(f"### 📋 รายการทรัพย์สินตามข้อมูลตัวกรอง (ทั้งหมด {total_count} รายการ)")
    
    if df_filtered.empty:
        st.warning("⚠️ ไม่พบข้อมูลทรัพย์สินในขณะนี้ตามเงื่อนไขการกรอง")
    else:
        # Show interactive dataframe first
        st.dataframe(
            df_filtered[[
                "รหัสทรัพย์", "ชื่อโครงการ", "ชื่อประกาศ", "ประเภททรัพย์", "ประเภทการขาย",
                "ราคา", "จังหวัด", "อำเภอ", "ตำบล",
                "พื้นที่ (ไร่-งาน-วา)", "พื้นที่ใช้สอย (ตร.ม.)", "ห้องนอน", "ห้องน้ำ", "ที่จอดรถ",
                "วันที่ดึงข้อมูล"
            ]],
            use_container_width=True,
            column_config={
                "ราคา": st.column_config.NumberColumn("ราคาขาย (บาท)", format="%d")
            }
        )
        
        st.markdown(f"<br/><h4 style='color: {card_title_color};'>💡 การแสดงผลในรูปแบบการ์ดทรัพย์สิน (Card Layout)</h4>", unsafe_allow_html=True)
        
        # Paginate results
        items_per_page = 9
        total_pages = (total_count - 1) // items_per_page + 1
        
        # Column selection for pages
        nav_col1, nav_col2, nav_col3 = st.columns([2, 1, 2])
        with nav_col2:
            page_num = st.selectbox(
                "เลขหน้า",
                options=list(range(1, total_pages + 1)),
                index=0,
                format_func=lambda x: f"หน้า {x} / {total_pages}"
            )
            
        start_idx = (page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_count)
        
        page_df = df_filtered.iloc[start_idx:end_idx]
        
        # Render cards grid (3 columns)
        card_cols = st.columns(3)
        
        for idx, (_, row) in enumerate(page_df.iterrows()):
            col_pos = idx % 3
            with card_cols[col_pos]:
                # Fallback home icon representation since images are removed
                image_tag = f'<div style="height: 180px; background-color: #e5e7eb; border-radius: 8px 8px 0 0; display: flex; align-items: center; justify-content: center; color: #4b5563;"><i class="fa fa-home" style="font-size: 3rem;"></i></div>'
                
                # Prices formatting
                price_val = row.get("ราคา", 0)
                price_display_str = f"{price_val:,.0f} บาท" if pd.notnull(price_val) and price_val > 0 else "ไม่ทราบราคา"
                price_block = f'<div style="margin-top: 8px;"><span style="color: #6366f1; font-weight: 700; font-size: 1.2rem;">฿{price_display_str}</span></div>'
                
                # Details string (land and building)
                prop_details_list = []
                
                # Building space
                building_space = row.get("พื้นที่ใช้สอย (ตร.ม.)")
                if pd.notnull(building_space) and str(building_space).strip() != "" and str(building_space).strip() != "nan":
                    prop_details_list.append(f'{format_num_val(building_space)} ตร.ม.')
                    
                # Land size
                land_desc = row.get("พื้นที่ (ไร่-งาน-วา)")
                if land_desc and str(land_desc).strip() != "" and str(land_desc).strip() != "nan" and str(land_desc).strip() != "0-0-0":
                    if '-' in str(land_desc):
                        # format old 1-2-3 to 1 ไร่ 2 งาน 3 วา
                        parts = str(land_desc).split('-')
                        if len(parts) == 3:
                            r_val, n_val, w_val = parts
                            temp_desc = ""
                            if r_val != "0" and r_val != "0.0" and r_val != "": temp_desc += f"{format_num_val(r_val)} ไร่ "
                            if n_val != "0" and n_val != "0.0" and n_val != "": temp_desc += f"{format_num_val(n_val)} งาน "
                            if w_val != "0" and w_val != "0.0" and w_val != "": temp_desc += f"{format_num_val(w_val)} วา"
                            land_desc = temp_desc.strip()
                    if land_desc and land_desc.strip() != "":
                        prop_details_list.append(f'ที่ดิน: {land_desc.strip()}')
                    
                details_line = " | ".join(prop_details_list)
                
                # Room details
                bed = row.get("ห้องนอน")
                bath = row.get("ห้องน้ำ")
                park = row.get("ที่จอดรถ")
                room_details = []
                if pd.notnull(bed) and str(bed).strip() != "" and str(bed).strip() != "nan":
                    room_details.append(f'<i class="fa fa-bed"></i> {format_num_val(bed)} นอน')
                if pd.notnull(bath) and str(bath).strip() != "" and str(bath).strip() != "nan":
                    room_details.append(f'<i class="fa fa-bath"></i> {format_num_val(bath)} น้ำ')
                if pd.notnull(park) and str(park).strip() != "" and str(park).strip() != "nan":
                    room_details.append(f'<i class="fa fa-car"></i> {format_num_val(park)} จอดรถ')
                room_line = "  ".join(room_details) if room_details else ""
                room_block = f'<p style="color: {card_text_color}; font-size: 0.78rem; margin-bottom: 6px;">{room_line}</p>' if room_line else ""

                # Project Name
                project_block = ""
                project_name = row.get("ชื่อโครงการ", "")
                if pd.notnull(project_name) and str(project_name).strip() != "" and str(project_name).strip() != "nan":
                    project_block = f'<div style="color: #6366f1; font-weight: 600; font-size: 0.8rem; margin-top: 5px;"><i class="fa fa-building"></i> โครงการ: {project_name}</div>'
                
                # Sale Type
                sale_type_badge = ""
                sale_type = row.get("ประเภทการขาย", "")
                if pd.notnull(sale_type) and str(sale_type).strip() != "" and str(sale_type).strip() != "nan":
                    sale_type_badge = f'<span style="background-color: #f3f4f6; color: #4b5563; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; margin-left: 5px;">{sale_type}</span>'
                
                # Scraped Date
                scraped_date = row.get("วันที่ดึงข้อมูล", "")
                scraped_block = f'<div style="color: #9ca3af; font-size: 0.7rem; margin-top: 8px;"><i class="fa fa-clock"></i> ดึงข้อมูลเมื่อ: {scraped_date}</div>' if scraped_date else ""

                # Card HTML Content
                card_html = (
                    f'<div style="background-color: {card_bg}; border: 1px solid {card_border}; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); overflow: hidden; display: flex; flex-direction: column;">'
                    f'{image_tag}'
                    f'<div style="padding: 15px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between;">'
                    f'<div>'
                    f'<div>'
                    f'<span style="background-color: #e0f7fa; color: #0891b2; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase;">{row.get("ประเภททรัพย์", "")}</span>'
                    f'{sale_type_badge}'
                    f'<span style="color: {card_text_color}; font-size: 0.7rem; float: right; font-weight: 500;">รหัส: {row.get("รหัสทรัพย์", "")}</span>'
                    f'</div>'
                    f'{project_block}'
                    f'<h4 style="margin: 10px 0 5px 0; font-size: 0.95rem; color: {card_title_color}; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; line-height: 1.4; height: 2.8em;">{row.get("ชื่อประกาศ", "")}</h4>'
                    f'<p style="color: {card_text_color}; font-size: 0.78rem; margin-bottom: 6px;"><i class="fa fa-map-marker" style="margin-right: 5px; color: #6366f1;"></i>{row.get("จังหวัด", "")} &raquo; {row.get("อำเภอ", "")} &raquo; {row.get("ตำบล", "")}</p>'
                    f'<p style="color: {card_text_color}; font-size: 0.78rem; margin-bottom: 6px; font-weight: 500;">{details_line}</p>'
                    f'{room_block}'
                    f'{scraped_block}'
                    f'</div>'
                    f'<div>'
                    f'{price_block}'
                    f'</div>'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Render native button below card for redirect
                link_url = row.get("ลิงก์", "")
                if link_url:
                    st.link_button("🌐 รายละเอียดเว็บ BAM", url=link_url, use_container_width=True)
                
                st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

# ----- TAB 4: PROPERTY COMPARISON -----
with tab4:
    st.markdown("### 🔍 เปรียบเทียบทรัพย์สิน (Property Comparison)")
    st.markdown(f'<p style="color: {card_text_color};">นำเข้าทรัพย์สินที่ต้องการเปรียบเทียบ จากนั้นค้นหาทรัพย์ BAM NPA ที่อยู่ใกล้เคียงตามเงื่อนไขที่กำหนด</p>', unsafe_allow_html=True)

    st.markdown("---")

    # ===== SECTION 1: Import Properties =====
    st.markdown(f'<h4 style="color: {card_title_color};"><i class="fa fa-upload" style="color: #6366f1;"></i> ส่วนที่ 1: นำเข้าทรัพย์สินสำหรับเปรียบเทียบ</h4>', unsafe_allow_html=True)

    input_method = st.radio(
        "เลือกวิธีนำเข้าข้อมูล",
        ["📝 กรอกข้อมูลด้วยมือ", "📂 อัปโหลดไฟล์ Excel/CSV"],
        horizontal=True
    )

    if "comparison_input_df" not in st.session_state:
        st.session_state["comparison_input_df"] = pd.DataFrame(columns=["ชื่อทรัพย์", "ประเภททรัพย์", "ละติจูด", "ลองจิจูด", "ราคา"])

    if input_method == "📝 กรอกข้อมูลด้วยมือ":
        with st.expander("➕ เพิ่มทรัพย์สินใหม่", expanded=True):
            inp_col1, inp_col2 = st.columns(2)
            with inp_col1:
                inp_name = st.text_input("ชื่อทรัพย์ / ชื่อโครงการ", key="inp_name")
                inp_type = st.selectbox(
                    "ประเภททรัพย์",
                    options=["บ้านเดี่ยว", "ทาวน์เฮ้าส์", "คอนโดมิเนียม", "อาคารพาณิชย์", "ที่ดินเปล่า", "โรงงาน", "ที่เกษตร", "อพาร์ทเม้นท์", "อาคารสำนักงาน", "อื่นๆ"],
                    key="inp_type"
                )
                inp_price = st.number_input("ราคา (บาท)", min_value=0, value=0, step=100000, key="inp_price")
            with inp_col2:
                inp_lat = st.number_input("ละติจูด (Latitude)", value=13.7563, format="%.6f", key="inp_lat")
                inp_lng = st.number_input("ลองจิจูด (Longitude)", value=100.5018, format="%.6f", key="inp_lng")

            if st.button("➕ เพิ่มทรัพย์", type="primary"):
                if inp_name.strip():
                    new_row = pd.DataFrame([{
                        "ชื่อทรัพย์": inp_name,
                        "ประเภททรัพย์": inp_type,
                        "ละติจูด": inp_lat,
                        "ลองจิจูด": inp_lng,
                        "ราคา": inp_price
                    }])
                    st.session_state["comparison_input_df"] = pd.concat(
                        [st.session_state["comparison_input_df"], new_row],
                        ignore_index=True
                    )
                    st.success(f"เพิ่ม '{inp_name}' เรียบร้อยแล้ว!")
                    st.rerun()
                else:
                    st.warning("กรุณาระบุชื่อทรัพย์")

    else:  # Upload file
        uploaded_file = st.file_uploader(
            "อัปโหลดไฟล์ Excel (.xlsx) หรือ CSV (.csv)",
            type=["xlsx", "csv"],
            help="ไฟล์ต้องมีคอลัมน์: ชื่อทรัพย์, ประเภททรัพย์, ละติจูด, ลองจิจูด, ราคา"
        )
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    uploaded_df = pd.read_csv(uploaded_file)
                else:
                    uploaded_df = pd.read_excel(uploaded_file)
                required_cols = ["ชื่อทรัพย์", "ละติจูด", "ลองจิจูด"]
                missing_cols = [c for c in required_cols if c not in uploaded_df.columns]
                if missing_cols:
                    st.error(f"ไฟล์ขาดคอลัมน์ที่จำเป็น: {', '.join(missing_cols)}")
                else:
                    for col in ["ประเภททรัพย์", "ราคา"]:
                        if col not in uploaded_df.columns:
                            uploaded_df[col] = ""
                    st.session_state["comparison_input_df"] = uploaded_df[["ชื่อทรัพย์", "ประเภททรัพย์", "ละติจูด", "ลองจิจูด", "ราคา"]].copy()
                    st.success(f"นำเข้าข้อมูลสำเร็จ! {len(uploaded_df)} รายการ")
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")

    # Display current input table
    input_df = st.session_state["comparison_input_df"]
    if not input_df.empty:
        st.markdown(f'<h5 style="color: {card_title_color}; margin-top: 15px;">📋 ทรัพย์สินที่นำเข้า ({len(input_df)} รายการ)</h5>', unsafe_allow_html=True)
        st.dataframe(
            input_df,
            use_container_width=True,
            column_config={
                "ราคา": st.column_config.NumberColumn("ราคา (บาท)", format="%d"),
                "ละติจูด": st.column_config.NumberColumn(format="%.6f"),
                "ลองจิจูด": st.column_config.NumberColumn(format="%.6f")
            }
        )
        if st.button("🗑️ ล้างข้อมูลทั้งหมด", type="secondary"):
            st.session_state["comparison_input_df"] = pd.DataFrame(columns=["ชื่อทรัพย์", "ประเภททรัพย์", "ละติจูด", "ลองจิจูด", "ราคา"])
            st.rerun()

        # Show map of imported properties
        st.markdown(f'<h5 style="color: {card_title_color}; margin-top: 15px;">🗺️ แผนที่พิกัดทรัพย์สินที่นำเข้า</h5>', unsafe_allow_html=True)
        # Filter rows with coordinates
        imported_map_data = input_df[input_df['ละติจูด'].notna() & input_df['ลองจิจูด'].notna()].copy()
        imported_map_data['ละติจูด'] = pd.to_numeric(imported_map_data['ละติจูด'], errors='coerce')
        imported_map_data['ลองจิจูด'] = pd.to_numeric(imported_map_data['ลองจิจูด'], errors='coerce')
        imported_map_data = imported_map_data.dropna(subset=['ละติจูด', 'ลองจิจูด'])
        
        if not imported_map_data.empty:
            fig_imported = px.scatter_mapbox(
                imported_map_data,
                lat="ละติจูด",
                lon="ลองจิจูด",
                hover_name="ชื่อทรัพย์",
                hover_data={"ราคา": ":,.0f", "ประเภททรัพย์": True, "ละติจูด": False, "ลองจิจูด": False},
                zoom=11,
                height=350,
                template=plotly_template
            )
            fig_imported.update_layout(
                mapbox_style=mapbox_style,
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_imported, use_container_width=True, theme=None)
        else:
            st.warning("ไม่พบพิกัด ละติจูด / ลองจิจูด ที่ถูกต้องสำหรับแสดงบนแผนที่")
    else:
        st.info("ยังไม่มีข้อมูลทรัพย์สินที่นำเข้า กรุณาเพิ่มข้อมูลด้านบน")

    st.markdown("---")

    # ===== SECTION 2: Search Conditions =====
    st.markdown(f'<h4 style="color: {card_title_color};"><i class="fa fa-search" style="color: #06b6d4;"></i> ส่วนที่ 2: เงื่อนไขค้นหาทรัพย์ BAM ใกล้เคียง</h4>', unsafe_allow_html=True)

    cond_col1, cond_col2, cond_col3 = st.columns(3)
    with cond_col1:
        search_radius = st.slider("ระยะทางสูงสุด (กม.)", min_value=0.5, max_value=50.0, value=1.0, step=0.5, key="search_radius")
    with cond_col2:
        filter_by_type = st.checkbox("กรองตามประเภททรัพย์ (ให้ตรงกับทรัพย์ที่นำเข้า)", value=True, key="filter_type_check")
    with cond_col3:
        filter_name_keyword = st.text_input("ค้นหาชื่อโครงการ (keyword)", value="", key="filter_name_kw", help="กรอกคำค้น เช่น ชื่อหมู่บ้าน/คอนโด เพื่อจำกัดผลลัพธ์")

    # ===== SECTION 3: Run Comparison =====
    if st.button("🔍 ค้นหาทรัพย์ BAM ที่ใกล้เคียง", type="primary", disabled=input_df.empty):
        if input_df.empty:
            st.warning("กรุณานำเข้าทรัพย์สินก่อนกดค้นหา")
        else:
            all_results = []
            with st.spinner("กำลังค้นหาทรัพย์ใกล้เคียง..."):
                for idx, inp_row in input_df.iterrows():
                    inp_lat_val = pd.to_numeric(inp_row.get("ละติจูด"), errors='coerce')
                    inp_lon_val = pd.to_numeric(inp_row.get("ลองจิจูด"), errors='coerce')
                    if pd.isna(inp_lat_val) or pd.isna(inp_lon_val):
                        continue
                    m_type = inp_row.get("ประเภททรัพย์", "") if filter_by_type else None
                    m_name = filter_name_keyword if filter_name_keyword.strip() else None
                    nearby = find_nearby_properties(
                        inp_lat_val, inp_lon_val, df_raw, search_radius,
                        match_type=m_type, match_name=m_name
                    )
                    if not nearby.empty:
                        nearby['ทรัพย์อ้างอิง'] = inp_row.get("ชื่อทรัพย์", f"ทรัพย์ #{idx+1}")
                        inp_price_val = pd.to_numeric(inp_row.get("ราคา", 0), errors='coerce') or 0
                        if inp_price_val > 0:
                            nearby['ผลต่างราคา (บาท)'] = nearby['ราคา'].apply(lambda x: x - inp_price_val if pd.notnull(x) else None)
                            nearby['ผลต่างราคา (%)'] = nearby['ราคา'].apply(lambda x: round((x - inp_price_val) / inp_price_val * 100, 1) if pd.notnull(x) and inp_price_val > 0 else None)
                        all_results.append(nearby)

            if all_results:
                result_df = pd.concat(all_results, ignore_index=True)
                st.session_state["comparison_results"] = result_df
            else:
                st.session_state["comparison_results"] = pd.DataFrame()
                st.warning("ไม่พบทรัพย์ BAM NPA ที่ตรงตามเงื่อนไข ลองเพิ่มระยะทางหรือลดเงื่อนไขการกรอง")

    # ===== SECTION 4: Display Results =====
    if "comparison_results" in st.session_state and not st.session_state["comparison_results"].empty:
        result_df = st.session_state["comparison_results"]
        st.markdown("---")
        st.markdown(f'<h4 style="color: {card_title_color};"><i class="fa fa-list-check" style="color: #10b981;"></i> ผลการเปรียบเทียบ (พบ {len(result_df)} รายการ)</h4>', unsafe_allow_html=True)

        # Display columns
        display_cols = ["ทรัพย์อ้างอิง", "รหัสทรัพย์", "ชื่อประกาศ", "ประเภททรัพย์", "ราคา", "จังหวัด", "อำเภอ", "ระยะทาง (กม.)"]
        if "ผลต่างราคา (บาท)" in result_df.columns:
            display_cols += ["ผลต่างราคา (บาท)", "ผลต่างราคา (%)"]
        available_cols = [c for c in display_cols if c in result_df.columns]

        col_config = {
            "ราคา": st.column_config.NumberColumn("ราคาขาย (บาท)", format="%d"),
            "ระยะทาง (กม.)": st.column_config.NumberColumn("ระยะทาง (กม.)", format="%.2f"),
        }
        if "ผลต่างราคา (บาท)" in available_cols:
            col_config["ผลต่างราคา (บาท)"] = st.column_config.NumberColumn(format="%d")
        if "ผลต่างราคา (%)" in available_cols:
            col_config["ผลต่างราคา (%)"] = st.column_config.NumberColumn(format="%.1f%%")

        st.dataframe(result_df[available_cols].sort_values("ระยะทาง (กม.)"), use_container_width=True, column_config=col_config)

        # Map visualization
        st.markdown(f'<h5 style="color: {card_title_color}; margin-top: 20px;">🗺️ แผนที่เปรียบเทียบตำแหน่ง</h5>', unsafe_allow_html=True)
        st.caption("🔴 จุดสีแดง = ทรัพย์ที่นำเข้า | 🔵 จุดสีน้ำเงิน = ทรัพย์ BAM ที่พบ")

        # Prepare map data
        map_points = []
        for _, inp_row in input_df.iterrows():
            lat_v = pd.to_numeric(inp_row.get("ละติจูด"), errors='coerce')
            lon_v = pd.to_numeric(inp_row.get("ลองจิจูด"), errors='coerce')
            if pd.notna(lat_v) and pd.notna(lon_v):
                map_points.append({"ละติจูด": lat_v, "ลองจิจูด": lon_v, "ชื่อ": inp_row.get("ชื่อทรัพย์", ""), "ประเภท": "ทรัพย์ที่นำเข้า", "ราคา": inp_row.get("ราคา", 0)})

        bam_map_data = result_df[result_df['ละติจูด'].notna() & result_df['ลองจิจูด'].notna()].copy()
        for _, bam_row in bam_map_data.iterrows():
            map_points.append({"ละติจูด": bam_row["ละติจูด"], "ลองจิจูด": bam_row["ลองจิจูด"], "ชื่อ": bam_row.get("ชื่อประกาศ", ""), "ประเภท": "ทรัพย์ BAM NPA", "ราคา": bam_row.get("ราคา", 0)})

        if map_points:
            map_df = pd.DataFrame(map_points)
            fig_compare = px.scatter_mapbox(
                map_df, lat="ละติจูด", lon="ลองจิจูด", color="ประเภท",
                hover_name="ชื่อ",
                hover_data={"ราคา": ":,.0f", "ละติจูด": False, "ลองจิจูด": False, "ประเภท": False},
                zoom=12, height=500,
                color_discrete_map={"ทรัพย์ที่นำเข้า": "#ef4444", "ทรัพย์ BAM NPA": "#3b82f6"},
                template=plotly_template
            )
            fig_compare.update_layout(
                mapbox_style=mapbox_style,
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor=map_legend_bg, bordercolor=map_legend_border, borderwidth=1, font=dict(color=map_legend_text, size=12))
            )
            st.plotly_chart(fig_compare, use_container_width=True, theme=None)
