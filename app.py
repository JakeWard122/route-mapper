import streamlit as st
import pandas as pd
import folium
import requests
import polyline

st.set_page_config(page_title="Route Mapper", layout="centered")

st.title("📍 Route Mapper (UK + Mapbox + Advanced UI)")

MAPBOX_TOKEN = st.secrets["MAPBOX_TOKEN"]

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

# -------------------------
# SESSION STATE FIX
# -------------------------
if "map_html" not in st.session_state:
    st.session_state.map_html = None

# -------------------------
# MAP SIZE PRESETS
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
# UK COLOURS (distinct palette)
# -------------------------
COLOURS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#46f0f0", "#f032e6", "#bcf60c", "#fabebe", "#008080",
]

# -------------------------
# SHORTEN FUNCTION
# -------------------------
def shorten(text, max_len=35):
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."

# -------------------------
# GEOCODING (UK ONLY)
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

# -------------------------
# ROUTING
# -------------------------
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
        return res["routes"][0]["geometry"]

    return None

# -------------------------
# MAIN APP
# -------------------------
if uploaded_file:

    df = pd.read_excel(uploaded_file)

    if not {"from", "to"}.issubset(df.columns):
        st.error("Excel must contain 'from' and 'to' columns")
    else:

        st.success(f"{len(df)} routes loaded")

        if st.button("Generate Map"):

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
                border: 2px solid grey;
                z-index:9999;
                font-size:14px;">
            <b>Route Key</b><br>
            """

            for i, row in df.iterrows():

                start = row["from"]
                end = row["to"]

                colour = COLOURS[i % len(COLOURS)]

                route_name = f"{start} → {end}"
                short_name = shorten(route_name)

                start_coords = geocode(start)
                end_coords = geocode(end)

                if start_coords and end_coords:

                    fg = folium.FeatureGroup(name=short_name)

                    route_poly = get_route(start_coords, end_coords)

                    if route_poly:
                        decoded = polyline.decode(route_poly)

                        folium.PolyLine(
                            decoded,
                            weight=4,
                            color=colour,
                            tooltip=route_name  # full name on hover
                        ).add_to(fg)

                    folium.Marker(start_coords, popup=start).add_to(fg)
                    folium.Marker(end_coords, popup=end).add_to(fg)

                    fg.add_to(m)

                    legend_html += f"""
                    <div>
                        <span style="
                            display:inline-block;
                            width:12px;
                            height:12px;
                            background:{colour};
                            margin-right:8px;">
                        </span>
                        {i+1}. {route_name}
                    </div>
                    """

                else:
                    st.warning(f"Could not find: {start} or {end}")

            legend_html += "</div>"

            m.get_root().html.add_child(folium.Element(legend_html))

            folium.LayerControl(collapsed=False).add_to(m)

            # IMPORTANT FIX: stable render
            st.session_state.map_html = m.get_root().render()

# -------------------------
# MAP DISPLAY
# -------------------------
if st.session_state.map_html:

    st.subheader("🗺️ Map")

    st.components.v1.html(
        st.session_state.map_html,
        height=map_height,
        scrolling=True
    )

    # -------------------------
    # EXPORT
    # -------------------------
    st.download_button(
        "📤 Download Map (HTML)",
        data=st.session_state.map_html,
        file_name="routes_map.html",
        mime="text/html"
    )