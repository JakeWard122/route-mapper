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
# SESSION STATE
# -------------------------
if "map_html" not in st.session_state:
    st.session_state.map_html = None

# -------------------------
# INPUT
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
            box-shadow: 0px 2px 10px rgba(0,0,0,0.15);
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

                    # ROUTE LINE
                    folium.PolyLine(
                        decoded,
                        weight=4,
                        color=colour,
                        tooltip=f"{start} → {end}"
                    ).add_to(m)

                    # START PIN
                    folium.CircleMarker(
                        location=start_coords,
                        radius=3,
                        color=colour,
                        fill=True,
                        fill_color=colour,
                        fill_opacity=0.9,
                        tooltip=f"Start: {start}"
                    ).add_to(m)

                    # END PIN
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

            time.sleep(0.03)

        progress.empty()
        status.empty()

        legend_html += "</div>"
        m.get_root().html.add_child(folium.Element(legend_html))

        st.session_state.map_html = m.get_root().render()

# -------------------------
# OUTPUT (70/30 LAYOUT)
# -------------------------
if "map_html" in st.session_state:

    df_table = pd.DataFrame(route_table)

    st.subheader("🗺️ Route Dashboard")

    map_col, table_col = st.columns([7, 3])

    with map_col:

        st.markdown("### 🗺️ Map")

        st.components.v1.html(
            f"""
            <div style="
                width: 100%;
                border: 3px solid #1f6feb;
                border-radius: 10px;
                overflow: hidden;
            ">
                {st.session_state.map_html}
            </div>
            """,
            height=700,
            scrolling=True
        )

    with table_col:

        st.markdown("### 📊 Routes")

        st.dataframe(
            df_table,
            use_container_width=True,
            hide_index=True
        )

    st.download_button(
        "📤 Download Map (HTML)",
        data=st.session_state.map_html,
        file_name="routes_map.html",
        mime="text/html"
    )