import streamlit as st
import pandas as pd
import folium
import requests
import polyline

st.set_page_config(page_title="Route Mapper", layout="centered")

st.title("📍 Route Mapper (Mapbox)")

# --- Session state (FIX for disappearing map) ---
if "map_html" not in st.session_state:
    st.session_state.map_html = None

MAPBOX_TOKEN = st.secrets["MAPBOX_TOKEN"]

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

# --- Geocoding ---
@st.cache_data
def geocode(place):
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{place}.json"
    params = {"access_token": MAPBOX_TOKEN, "limit": 1}
    res = requests.get(url, params=params).json()

    if res.get("features"):
        coords = res["features"][0]["center"]
        return (coords[1], coords[0])  # lat, lon
    return None

# --- Routing ---
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

# --- Main logic ---
if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if not {"from", "to"}.issubset(df.columns):
        st.error("Excel must contain 'from' and 'to'")
    else:
        st.success(f"{len(df)} routes loaded")

        if st.button("Generate Map"):
            with st.spinner("Mapping routes..."):
                m = folium.Map(
                    location=[54.5, -3],
                    zoom_start=6,
                    tiles="OpenStreetMap"
                )

                for _, row in df.iterrows():
                    start = row["from"]
                    end = row["to"]

                    start_coords = geocode(start)
                    end_coords = geocode(end)

                    if start_coords and end_coords:
                        # markers
                        folium.Marker(start_coords, popup=f"Start: {start}").add_to(m)
                        folium.Marker(end_coords, popup=f"End: {end}").add_to(m)

                        # route
                        route_poly = get_route(start_coords, end_coords)

                        if route_poly:
                            decoded = polyline.decode(route_poly)
                            folium.PolyLine(decoded, weight=4).add_to(m)
                    else:
                        st.warning(f"Could not find: {start} or {end}")

                # ✅ STORE MAP (fix)
                st.session_state.map_html = m._repr_html_()

# --- DISPLAY MAP (outside button) ---
if st.session_state.map_html:
    st.subheader("🗺️ Map")
    st.components.v1.html(st.session_state.map_html, height=500)