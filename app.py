import streamlit as st
import pandas as pd
import folium
import requests
import polyline

st.set_page_config(page_title="Route Mapper", layout="centered")

st.title("📍 Route Mapper (Stable Version)")

MAPBOX_TOKEN = st.secrets["MAPBOX_TOKEN"]

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

# -------------------------
# SESSION STATE FIX
# -------------------------
if "map_html" not in st.session_state:
    st.session_state.map_html = None

# -------------------------
# COLOURS
# -------------------------
COLOURS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#46f0f0", "#f032e6", "#bcf60c", "#fabebe", "#008080",
]

# -------------------------
# GEOCODING (Mapbox)
# -------------------------
@st.cache_data
def geocode(place):
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{place}.json"
    params = {"access_token": MAPBOX_TOKEN, "limit": 1}
    res = requests.get(url, params=params).json()

    if res.get("features"):
        coords = res["features"][0]["center"]
        return (coords[1], coords[0])  # lat, lon
    return None

# -------------------------
# ROUTING (Mapbox)
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
# MAIN LOGIC
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

                start_coords = geocode(start)
                end_coords = geocode(end)

                if start_coords and end_coords:

                    fg = folium.FeatureGroup(name=f"Route {i+1}")

                    route_poly = get_route(start_coords, end_coords)

                    if route_poly:
                        decoded = polyline.decode(route_poly)

                        folium.PolyLine(
                            decoded,
                            weight=4,
                            color=colour
                        ).add_to(fg)

                    folium.Marker(start_coords, popup=start).add_to(fg)
                    folium.Marker(end_coords, popup=end).add_to(fg)

                    fg.add_to(m)

                    legend_html += f"""
                    <div>
                        <span style="display:inline-block;width:12px;height:12px;background:{colour};margin-right:8px;"></span>
                        {i+1}. {start} → {end}
                    </div>
                    """

            legend_html += "</div>"

            m.get_root().html.add_child(folium.Element(legend_html))

            folium.LayerControl().add_to(m)

            # 🔥 CRITICAL FIX
            st.session_state.map_html = m.get_root().render()

# -------------------------
# STABLE RENDER (IMPORTANT)
# -------------------------
if st.session_state.map_html:

    st.subheader("🗺️ Map")

    st.components.v1.html(
        st.session_state.map_html,
        height=550,
        scrolling=True
    )