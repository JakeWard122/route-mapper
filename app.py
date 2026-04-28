import streamlit as st
import pandas as pd
import folium
import requests
import polyline
import time
import colorsys
import hashlib

# -------------------------
# PAGE CONFIG
# -------------------------
st.set_page_config(
    page_title="NWT Backload Planning Tool",
    layout="wide"
)

st.markdown("# 🚛 NWT Backload Planning Tool")
st.markdown("### Logistics Dashboard")

MAPBOX_TOKEN = st.secrets["MAPBOX_TOKEN"]

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

# -------------------------
# STATE
# -------------------------
if "selected_route" not in st.session_state:
    st.session_state.selected_route = None

# -------------------------
# CSS
# -------------------------
st.markdown("""
<style>

.block-container {
    max-width: 100% !important;
    padding-left: 2rem;
    padding-right: 2rem;
}

[data-testid="stAppViewContainer"] {
    background-color: #f4f8ff;
}

iframe {
    width: 100% !important;
    border: 3px solid #1f6feb !important;
    border-radius: 10px;
}

.stButton>button {
    background-color: #1f6feb;
    color: white;
    font-weight: 600;
    border-radius: 6px;
}

.stButton>button:hover {
    background-color: #174ea6;
}

</style>
""", unsafe_allow_html=True)

# -------------------------
# STABLE COLOUR (NO REPETITION)
# -------------------------
def route_colour(route_id: str):
    h = hashlib.md5(route_id.encode()).hexdigest()
    num = int(h[:8], 16)
    hue = (num % 360) / 360

    rgb = colorsys.hls_to_rgb(hue, 0.5, 0.85)

    return "#{:02x}{:02x}{:02x}".format(
        int(rgb[0]*255),
        int(rgb[1]*255),
        int(rgb[2]*255)
    )

# -------------------------
# HELPERS
# -------------------------
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

def shorten(text, max_len=35):
    return text if len(text) <= max_len else text[:max_len - 3] + "..."

# -------------------------
# FUEL
# -------------------------
st.subheader("⛽ Fuel Calculator (Optional)")

mpg = st.number_input("Vehicle MPG", min_value=0.0, value=0.0)
fuel_price = st.number_input("Fuel price (£/litre)", min_value=0.0, value=0.0)

use_fuel = mpg > 0 and fuel_price > 0

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

            total = len(df)

            for i, row in df.iterrows():

                status.text(f"Processing route {i+1}/{total}")
                progress.progress((i + 1) / total)

                start = row["from"]
                end = row["to"]

                route_id = f"{start}->{end}"
                colour = route_colour(route_id)

                # FILTER LOGIC
                selected = st.session_state.selected_route
                if selected is not None and i != selected:
                    continue

                start_coords = geocode(start)
                end_coords = geocode(end)

                if start_coords and end_coords:

                    route_data = get_route(start_coords, end_coords)

                    if route_data:

                        decoded = polyline.decode(route_data["geometry"])

                        fg = folium.FeatureGroup(name=shorten(route_id))

                        # ROUTE LINE
                        folium.PolyLine(
                            decoded,
                            weight=4,
                            color=colour,
                            tooltip=f"{start} → {end}"
                        ).add_to(fg)

                        # 📍 START PIN (small + coloured)
                        folium.CircleMarker(
                            location=start_coords,
                            radius=3,
                            color=colour,
                            fill=True,
                            fill_color=colour,
                            fill_opacity=0.9,
                            tooltip=f"Start: {start}"
                        ).add_to(fg)

                        # 📍 END PIN (slightly larger)
                        folium.CircleMarker(
                            location=end_coords,
                            radius=4,
                            color=colour,
                            fill=True,
                            fill_color=colour,
                            fill_opacity=1,
                            tooltip=f"End: {end}"
                        ).add_to(fg)

                        fg.add_to(m)

                        route_table.append({
                            "From": start,
                            "To": end,
                            "Distance (km)": round(route_data["distance_km"], 1),
                            "Drive Time (min)": round(route_data["duration_min"], 0),
                        })

                time.sleep(0.03)

            progress.empty()
            status.empty()

            folium.LayerControl(collapsed=False).add_to(m)

            st.session_state.map_html = m.get_root().render()

# -------------------------
# OUTPUT
# -------------------------
if "map_html" in st.session_state and st.session_state.map_html:

    st.subheader("🗺️ Map")

    if st.button("🌍 Show All Routes"):
        st.session_state.selected_route = None

    df_table = pd.DataFrame(route_table)

    selection = st.dataframe(
        df_table,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )

    if selection and selection.selection.rows:
        st.session_state.selected_route = selection.selection.rows[0]

    st.components.v1.html(
        st.session_state.map_html,
        height=800,
        scrolling=True
    )

    st.subheader("📊 Route Summary")

    st.dataframe(df_table, use_container_width=True, hide_index=True)

    st.download_button(
        "📤 Download Map (HTML)",
        data=st.session_state.map_html,
        file_name="routes_map.html",
        mime="text/html"
    )