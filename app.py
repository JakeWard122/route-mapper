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
# MAIN INPUT
# -------------------------
if uploaded_file:

    df = pd.read_excel(uploaded_file)

    if not {"from", "to"}.issubset(df.columns):
        st.error("Excel must contain 'from' and 'to'")
        st.stop()

    st.success(f"{len(df)} routes loaded")

    route_table = []

    # -------------------------
    # GENERATE MAP
    # -------------------------
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

                    # 📍 START PIN
                    folium.CircleMarker(
                        location=start_coords,
                        radius=3,
                        color=colour,
                        fill=True,
                        fill_color=colour,
                        fill_opacity=0.9,
                        tooltip=f"Start: {start}"
                    ).add_to(m)

                    # 📍 END PIN
                    folium.CircleMarker(
                        location=end_coords,
                        radius=4,
                        color=colour,
                        fill=True,
                        fill_color=colour,
                        fill_opacity=1,
                        tooltip=f"End: {end}"
                    ).add_to(m)

                    route_table.append({
                        "From": start,
                        "To": end,
                        "Distance (km)": round(route_data["distance_km"], 1),
                        "Drive Time (min)": round(route_data["duration_min"], 0)
                    })

            time.sleep(0.03)

        progress.empty()
        status.empty()

        st.session_state.map_html = m.get_root().render()

# -------------------------
# OUTPUT
# -------------------------
if "map_html" in st.session_state:

    st.subheader("🗺️ Map")

    df_table = pd.DataFrame(route_table)

    # -------------------------
    # RESET VIEW
    # -------------------------
    if st.button("🌍 Show All Routes"):
        st.session_state.selected_route = None

    # -------------------------
    # SINGLE CLEAN TABLE (NO DUPLICATES)
    # -------------------------
    st.subheader("📊 Route List")

    for i, row in df_table.iterrows():

        col1, col2, col3, col4 = st.columns([4, 2, 2, 1])

        with col1:
            st.write(f"**{row['From']} → {row['To']}**")

        with col2:
            st.write(f"{row['Distance (km)']} km")

        with col3:
            st.write(f"{row['Drive Time (min)']} min")

        with col4:
            if st.button("View", key=f"view_{i}"):
                st.session_state.selected_route = i

    # -------------------------
    # FILTER MAP (STABLE)
    # -------------------------
    selected = st.session_state.selected_route

    m = folium.Map(location=[54.5, -3], zoom_start=6)

    for i, row in df_table.iterrows():

        if selected is not None and i != selected:
            continue

        route_id = f"{row['From']}->{row['To']}"
        colour = route_colour(route_id)

        start_coords = geocode(row["From"])
        end_coords = geocode(row["To"])

        if start_coords and end_coords:

            route_data = get_route(start_coords, end_coords)

            if route_data:

                decoded = polyline.decode(route_data["geometry"])

                folium.PolyLine(
                    decoded,
                    weight=4,
                    color=colour,
                    tooltip=f"{row['From']} → {row['To']}"
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

    st.components.v1.html(
        m.get_root().render(),
        height=800,
        scrolling=True
    )

    st.download_button(
        "📤 Download Map (HTML)",
        data=m.get_root().render(),
        file_name="routes_map.html",
        mime="text/html"
    )