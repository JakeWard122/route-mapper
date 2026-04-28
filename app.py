import streamlit as st
import pandas as pd
import folium
import requests
import polyline
import time

st.set_page_config(
    page_title="NWT Backload Planning Tool",
    layout="centered"
)

st.markdown("# 🚛 NWT Backload Planning Tool")
st.markdown("### Logistics Dashboard")

MAPBOX_TOKEN = st.secrets["MAPBOX_TOKEN"]

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

# -------------------------
# BLUE / WHITE THEME
# -------------------------
st.markdown("""
<style>

/* App background */
[data-testid="stAppViewContainer"] {
    background-color: #f4f8ff;
}

/* Header */
h1 {
    color: #0b3d91;
    font-weight: 800;
    border-left: 8px solid #1f6feb;
    padding-left: 12px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #0b3d91;
    color: white;
}

[data-testid="stSidebar"] * {
    color: white;
}

/* Buttons */
.stButton>button {
    background-color: #1f6feb;
    color: white;
    font-weight: 600;
    border-radius: 6px;
    border: none;
}

.stButton>button:hover {
    background-color: #174ea6;
}

/* Metrics */
[data-testid="stMetric"] {
    background-color: white;
    padding: 12px;
    border-radius: 10px;
    border-left: 6px solid #1f6feb;
    box-shadow: 0px 2px 6px rgba(0,0,0,0.08);
}

/* Table */
[data-testid="stDataFrame"] {
    border: 2px solid #1f6feb;
    border-radius: 10px;
    overflow: hidden;
}

/* Map frame */
iframe {
    border: 3px solid #1f6feb !important;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)

# -------------------------
# SIDEBAR TOGGLE
# -------------------------
if "sidebar" not in st.session_state:
    st.session_state.sidebar = True

if st.button("🧭 Toggle Sidebar"):
    st.session_state.sidebar = not st.session_state.sidebar

if st.session_state.sidebar:
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { display: block; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { display: none; }
        </style>
    """, unsafe_allow_html=True)

# -------------------------
# MAP SIZE
# -------------------------
size_option = st.radio(
    "Map size",
    ["Small", "Medium", "Large", "Fullscreen"],
    horizontal=True
)

size_map = {
    "Small": 450,
    "Medium": 600,
    "Large": 800,
    "Fullscreen": 1000
}

map_height = size_map[size_option]

# -------------------------
# FUEL INPUTS
# -------------------------
st.subheader("⛽ Fuel Calculator (Optional)")

mpg = st.number_input("Vehicle MPG", min_value=0.0, value=0.0)
fuel_price = st.number_input("Fuel price (£/litre)", min_value=0.0, value=0.0)

use_fuel = mpg > 0 and fuel_price > 0

# -------------------------
# SESSION STATE
# -------------------------
if "map_html" not in st.session_state:
    st.session_state.map_html = None

# -------------------------
# COLOURS
# -------------------------
COLOURS = [
    "#1f6feb", "#0b3d91", "#2f81f7", "#58a6ff", "#79c0ff",
    "#3b82f6", "#2563eb", "#1d4ed8", "#60a5fa", "#93c5fd",
]

# -------------------------
# HELPERS
# -------------------------
def shorten(text, max_len=35):
    return text if len(text) <= max_len else text[:max_len - 3] + "..."

@st.cache_data
def geocode(place):
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{place}.json"

    params = {
        "access_token": MAPBOX_TOKEN,
        "limit": 1,
        "country": "gb",
        "proximity": "-0.1276,51.5072"
    }

    res = requests.get(url, params=params).json()

    if res.get("features"):
        coords = res["features"][0]["center"]
        return (coords[1], coords[0])

    return None

@st.cache_data
def get_route(start_coords, end_coords):
    url = "https://api.mapbox.com/directions/v5/mapbox/driving"

    coords = f"{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"

    params = {
        "access_token": MAPBOX_TOKEN,
        "geometries": "polyline"
    }

    res = requests.get(f"{url}/{coords}", params=params).json()

    if res.get("routes"):
        route = res["routes"][0]
        return {
            "geometry": route["geometry"],
            "distance_km": route["distance"] / 1000,
            "duration_min": route["duration"] / 60
        }

    return None

# -------------------------
# MAIN
# -------------------------
if uploaded_file:

    df = pd.read_excel(uploaded_file)

    if not {"from", "to"}.issubset(df.columns):
        st.error("Excel must contain 'from' and 'to'")
    else:

        st.success(f"{len(df)} routes loaded")

        route_table = []

        if st.button("Generate Map"):

            progress = st.progress(0)
            status = st.empty()

            m = folium.Map(location=[54.5, -3], zoom_start=6)

            legend_html = """
            <div style="
                position: fixed;
                bottom: 20px;
                left: 20px;
                width: 260px;
                max-height: 300px;
                overflow-y: auto;
                background: white;
                padding: 10px;
                border: 2px solid #1f6feb;
                z-index:9999;
                font-size:14px;">
            <b>Route Key</b><br>
            """

            total = len(df)

            for i, row in df.iterrows():

                status.text(f"Processing route {i+1} of {total}")
                progress.progress((i + 1) / total)

                start = row["from"]
                end = row["to"]

                colour = COLOURS[i % len(COLOURS)]

                route_name = f"{start} → {end}"
                short_name = shorten(route_name)

                start_coords = geocode(start)
                end_coords = geocode(end)

                if start_coords and end_coords:

                    fg = folium.FeatureGroup(name=short_name)

                    route_data = get_route(start_coords, end_coords)

                    if route_data:

                        decoded = polyline.decode(route_data["geometry"])

                        folium.PolyLine(
                            decoded,
                            weight=4,
                            color=colour,
                            tooltip=route_name
                        ).add_to(fg)

                        fg.add_to(m)

                        distance_km = route_data["distance_km"]
                        duration_min = route_data["duration_min"]

                        fuel_cost = None

                        if use_fuel:
                            litres_per_100km = 282.481 / mpg
                            fuel_used = (distance_km / 100) * litres_per_100km
                            fuel_cost = fuel_used * fuel_price

                        route_table.append({
                            "From": start,
                            "To": end,
                            "Distance (km)": round(distance_km, 1),
                            "Drive Time (min)": round(duration_min, 0),
                            "Fuel Cost (£)": round(fuel_cost, 2) if fuel_cost else None
                        })

                        legend_html += f"""
                        <div>
                            <span style="display:inline-block;width:12px;height:12px;background:{colour};margin-right:8px;"></span>
                            {i+1}. {route_name}
                        </div>
                        """

                time.sleep(0.05)

            progress.empty()
            status.empty()

            legend_html += "</div>"

            m.get_root().html.add_child(folium.Element(legend_html))

            folium.LayerControl(collapsed=False).add_to(m)

            st.session_state.map_html = m.get_root().render()

# -------------------------
# OUTPUT
# -------------------------
if st.session_state.map_html:

    st.subheader("🗺️ Map")

    st.components.v1.html(
        st.session_state.map_html,
        height=map_height,
        scrolling=True
    )

    st.subheader("📊 Route Summary")

    df_table = pd.DataFrame(route_table)

    st.dataframe(df_table, use_container_width=True, hide_index=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Routes", len(df_table))

    with col2:
        st.metric("Total Distance", f"{df_table['Distance (km)'].sum():.1f} km")

    with col3:
        if use_fuel:
            st.metric("Fuel Cost", f"£{df_table['Fuel Cost (£)'].sum():.2f}")
        else:
            st.metric("Fuel Cost", "N/A")

    st.download_button(
        "📤 Download Map (HTML)",
        data=st.session_state.map_html,
        file_name="routes_map.html",
        mime="text/html"
    )