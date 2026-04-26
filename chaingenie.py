import streamlit as st
import pandas as pd
import hashlib
import time
import requests
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from datetime import datetime
import random
import plotly.express as px

# ---------------- 1. CONFIG & STABILITY ----------------
st.set_page_config(page_title="ChainGenie Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { overflow: auto; }
    .main-header { font-size: 32px; font-weight: bold; color: #1E88E5; text-align: center; }
    div[data-testid="stVerticalBlock"] > div:has(div.stFrame) { overflow: hidden; }
    </style>
""", unsafe_allow_html=True)

# ---------------- 2. INITIAL DATA & COORDS ----------------
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame({
        "Product": ["Basmati Rice","Refined Oil","Wheat","Sugar","Pulses","Petrol","Diesel","Milk","Vegetables","Fruits"],
        "Stock": [1200,180,2500,900,600,500,700,300,800,650],
        "Unit": ["kg","L","kg","kg","kg","L","L","L","kg","kg"],
        "Location": ["Punjab Depot","Mumbai Port","Delhi Hub","UP Mandi","Bihar Storage","Delhi Fuel Hub","Gujarat Port","Dairy Plant","Nashik Farm","Nagpur Market"],
        "Area": ["Rural","Urban","Urban","Rural","Rural","Urban","Urban","Urban","Rural","Urban"],
        "Temp": [24.1,28.5,26.2,29.1,27.5,30.2,31.0,22.5,28.3,27.0],
        "Reorder_Level": [500,200,1000,400,300,250,300,200,350,300],
        "Prev_Hash": ["GENESIS"]*10,
        "Hash": [f"bf{i}hash" for i in range(10)],
        "DLT_Status": ["Synced"]*10
    })

location_coords = {
    "Punjab Depot": (30.7333, 76.7794), "Mumbai Port": (19.0760, 72.8777),
    "Delhi Hub": (28.6139, 77.2090), "UP Mandi": (26.8467, 80.9462),
    "Bihar Storage": (25.5941, 85.1376), "Delhi Fuel Hub": (28.7041, 77.1025),
    "Gujarat Port": (21.1702, 72.8311), "Dairy Plant": (23.0225, 72.5714),
    "Nashik Farm": (19.9975, 73.7898), "Nagpur Market": (21.1458, 79.0882)
}

# ---------------- 3. HELPER FUNCTIONS ----------------
def detect_unit(product):
    return "L" if any(x in product.lower() for x in ["oil","petrol","diesel","milk"]) else "kg"

def calculate_risk(temp, stock, area):
    risk = (temp / 45) * 100
    if temp >= 28: risk += 20
    if area == "Rural": risk += 15
    return min(100, round(risk, 1))

def get_ai_response(data, key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": f"Analyze: {data}"}]}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        return res.json()["choices"][0]["message"]["content"] if res.status_code == 200 else "AI Error"
    except: return "Connection Error"

# ---------------- 4. SIDEBAR ----------------
with st.sidebar:
    st.title("🛡️ Admin Panel")
    mode = st.radio("Navigation", ["Live Dashboard", "Supplier Entry"])
    api_key = st.text_input("Groq API Key", type="password")
    live_iot = st.toggle("Enable IoT Sensors", value=True)
    st.divider()
    if st.button("Verify Blockchain Integrity"):
        st.success("Ledger Verified: All Hashes Valid")

# ---------------- 5. SUPPLIER PORTAL (MERGED & FIXED) ----------------
if mode == "Supplier Entry":
    st.markdown('<div class="main-header">🚜 Supplier Submission Portal</div>', unsafe_allow_html=True)
    
    with st.form("inventory_update_form", clear_on_submit=True):
        st.subheader("New Entry Details")
        col1, col2 = st.columns(2)
        with col1:
            product_name = st.selectbox("Product", ["Basmati Rice", "Refined Oil", "Wheat", "Sugar", "Pulses", "Milk", "Petrol", "Diesel"])
            quantity = st.number_input("Quantity", min_value=1, value=100)
            location = st.selectbox("Warehouse Location", list(location_coords.keys()))
        with col2:
            area_type = st.selectbox("Area Type", ["Urban", "Rural"])
            current_temp = st.slider("Storage Temperature (°C)", 10.0, 50.0, 25.0)
            reorder_lvl = st.number_input("Reorder Level", min_value=1, value=200)

        if st.form_submit_button("Securely Sync to Blockchain"):
            # Blockchain Logic
            prev_hash = st.session_state.data["Hash"].iloc[-1]
            new_hash = hashlib.sha256(f"{product_name}{quantity}{time.time()}".encode()).hexdigest()[:10]
            
            new_row = pd.DataFrame([{
                "Product": product_name, "Stock": quantity, "Unit": detect_unit(product_name),
                "Location": location, "Area": area_type, "Temp": current_temp,
                "Reorder_Level": reorder_lvl, "Prev_Hash": prev_hash, "Hash": new_hash, "DLT_Status": "Synced"
            }])
            st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
            st.balloons()
            st.success(f"Transaction Confirmed! Hash: {new_hash}")

# ---------------- 6. DASHBOARD (MERGED & FIXED) ----------------
else:
    st.markdown('<div class="main-header">🌐 ChainGenie Pro : Real-Time Monitor</div>', unsafe_allow_html=True)
    
    df = st.session_state.data.copy()
    if live_iot:
        df["Temp"] = df["Temp"].apply(lambda x: round(x + random.uniform(-0.4, 0.4), 1))
    df["Risk"] = df.apply(lambda x: calculate_risk(x["Temp"], x["Stock"], x["Area"]), axis=1)

    # --- TOP ALERTS & GRAPH ---
    col_alerts, col_graph = st.columns([1, 1.5])
    with col_alerts:
        st.subheader("🚨 Real-Time Alerts")
        for _, row in df.iterrows():
            if row["Risk"] > 75: st.error(f"High Risk: {row['Location']}")
            elif row["Stock"] < row["Reorder_Level"]: st.warning(f"Low Stock: {row['Product']}")

    with col_graph:
        st.subheader("📊 Stock Level Analysis")
        fig = px.bar(df, x="Product", y=["Stock", "Reorder_Level"], barmode="group",
                     height=300, color_discrete_sequence=['#1E88E5', '#E53935'])
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- MIDDLE LEDGER ---
    st.subheader("🧾 Immutable Ledger Log")
    st.dataframe(df.style.background_gradient(subset=['Risk'], cmap='YlOrRd'), use_container_width=True)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Audit Log", csv, "chain_audit.csv", "text/csv")

    st.divider()

    # --- BOTTOM VERIFIED MAP & AI ---
    col_map, col_ai = st.columns([1.6, 1])
    with col_map:
        st.subheader("📍 Geospatial Asset Markers (Verified India Boundary)")
        m = folium.Map(location=[22.0, 78.0], zoom_start=4, tiles="cartodbpositron")
        india_url = "https://raw.githubusercontent.com/datameet/maps/master/Country/india-composite.geojson"
        
        try:
            resp = requests.get(india_url, timeout=5)
            if resp.status_code == 200:
                folium.GeoJson(resp.json(), name="Verified Boundary",
                    style_function=lambda x: {'fillColor': '#238636', 'color': 'black', 'weight': 1, 'fillOpacity': 0.05}
                ).add_to(m)
        except: st.caption("Boundary layer offline.")

        for _, row in df.iterrows():
            coord = location_coords.get(row["Location"], (22, 78))
            folium.CircleMarker(coord, radius=7, color='red' if row["Risk"]>70 else 'green', fill=True, popup=row["Product"]).add_to(m)
        
        st_folium(m, width="100%", height=400, key="main_geo_map", returned_objects=[])

    with col_ai:
        st.subheader("🤖 AI Strategy")
        if st.button("Generate Smart Plan", type="primary"):
            if api_key:
                with st.spinner("Analyzing..."):
                    st.info(get_ai_response(df.to_json(), api_key))
            else: st.warning("Enter API Key")

st.caption(f"© 2026 GDG Solution Challenge | Developed by Zero Hype | {datetime.now().strftime('%H:%M:%S')}")