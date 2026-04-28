import streamlit as st
import pandas as pd
import folium
import requests
import polyline
import time
import colorsys
import hashlib

from streamlit_folium import st_folium

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
# SESSION STATE
# -------------------------
if "map" not in st.session_state:
    st.session_state.map = None

if "route_table" not in st.session_state:
    st.session_state.route_table = []

# -------------------------
# COLOUR SYSTEM (STABLE)
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

# -------------------------
# INPUTS
# -------------------------
if uploaded_file:

    df = pd.read_excel(uploaded_file)

    if not {"from", "to"}.issubset(df.columns):
        st.error("Excel must contain 'from' and 'to'")
        st.stop()

    st.success(f"{len(df)} routes loaded")

    # -------------------------
    # FUEL INPUT (OPTIONAL)
    # -------------------------
    st.subheader("⛽ Fuel Calculator (Optional)")
    mpg = st.number_input("Vehicle MPG", min_value=0.0, value=0.0)
    fuel_price = st.number_input("Fuel price (£/litre)", min_value=0.0, value=0.0)

    use_fuel = mpg > 0 and fuel_price > 0

    # -------------------------
    # GENERATE MAP
    # -------------------------
    if st.button("Generate Map"):

        st.session_state.route_table = []

        progress = st.progress(0)
        status = st.empty()

        m = folium.Map(location=[54.5, -3], zoom_start=6)

        legend_html = """
        <div style="
            position: fixed;
            bottom: 20px;
            left: 20px;
            width: 260px;
            max-height: 320px;
            overflow-y: auto;
            background: white;
            border: 2px solid #1f6feb;
            z-index: 9999;
            padding: 10px;
            font-size: 13px;
            border-radius: 8px;
        ">
        <b>🚛 Route Key</b><br><br>
        """

        total = len(df)

        for i, row in df.iterrows():

            status.text(f"Processing route {i+1}/{total}")
            progress.progress((i + 1) / total)

            start = row["from"]
            end = row["to"]

            route_id = f"{start}->{end}"
            colour = route_colour(route_id)

            start_coords = geocode(start)
            end_coords = geocode(end)

            if start_coords and end_coords:

                route_data = get_route(start_coords, end_coords)

                if route_data:

                    decoded = polyline.decode(route_data["geometry"])

                    folium.PolyLine(
                        decoded,
                        weight=4,
                        color=colour,
                        tooltip=f"{start} → {end}"
                    ).add_to(m)

                    folium.CircleMarker(
                        location=start_coords,
                        radius=3,
                        color=colour,
                        fill=True,
                        fill_color=colour,
                        fill_opacity=0.9
                    ).add_to(m)

                    folium.CircleMarker(
                        location=end_coords,
                        radius=4,
                        color=colour,
                        fill=True,
                        fill_color=colour,
                        fill_opacity=1
                    ).add_to(m)

                    # -------------------------
                    # FUEL CALCULATION
                    # -------------------------
                    distance_miles = route_data["distance_km"] * 0.621371

                    if use_fuel:
                        gallons_used = distance_miles / mpg
                        litres_used = gallons_used * 4.54609
                        fuel_cost = litres_used * fuel_price
                    else:
                        fuel_cost = None

                    st.session_state.route_table.append({
                        "From": start,
                        "To": end,
                        "Distance (km)": round(route_data["distance_km"], 1),
                        "Drive Time (min)": round(route_data["duration_min"], 0),
                        "Fuel Cost (£)": round(fuel_cost, 2) if fuel_cost else "—"
                    })

                    legend_html += f"""
                    <div>
                        <span style="
                            display:inline-block;
                            width:10px;
                            height:10px;
                            background:{colour};
                            margin-right:6px;
                            border-radius:2px;"></span>
                        {start} → {end}
                    </div>
                    """

            time.sleep(0.02)

        progress.empty()
        status.empty()

        legend_html += "</div>"
        m.get_root().html.add_child(folium.Element(legend_html))

        st.session_state.map = m

# -------------------------
# OUTPUT (70/30)
# -------------------------
if st.session_state.map:

    df_table = pd.DataFrame(st.session_state.route_table)

    st.subheader("🗺️ Route Dashboard")

    map_col, table_col = st.columns([7, 3])

    with map_col:
        st_folium(st.session_state.map, width=1200, height=700)

    with table_col:
        st.markdown("### 📊 Routes")
        st.dataframe(df_table, use_container_width=True, hide_index=True)

    st.download_button(
        "📤 Download Map (HTML)",
        data=st.session_state.map._repr_html_(),
        file_name="routes_map.html",
        mime="text/html"
    )