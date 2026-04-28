import streamlit as st
import pandas as pd
import folium
import requests
import polyline

st.set_page_config(page_title="Route Mapper", layout="centered")

st.title("📍 Route Mapper (Full Analytics + Fuel)")

MAPBOX_TOKEN = st.secrets["MAPBOX_TOKEN"]

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

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
# FUEL INPUTS (OPTIONAL)
# -------------------------
st.subheader("⛽ Fuel Calculator (Optional)")

mpg = st.number_input(
    "Vehicle MPG (optional)",
    min_value=0.0,
    value=0.0,
    step=1.0
)

fuel_price = st.number_input(
    "Fuel price per litre (£) (optional)",
    min_value=0.0,
    value=0.0,
    step=0.01
)

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
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#46f0f0", "#f032e6", "#bcf60c", "#fabebe", "#008080",
]

# -------------------------
# SHORTEN
# -------------------------
def shorten(text, max_len=35):
    return text if len(text) <= max_len else text[:max_len - 3] + "..."

# -------------------------
# GEOCODE (UK ONLY)
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

                    route_data = get_route(start_coords, end_coords)

                    if route_data:

                        decoded = polyline.decode(route_data["geometry"])

                        folium.PolyLine(
                            decoded,
                            weight=4,
                            color=colour,
                            tooltip=route_name
                        ).add_to(fg)

                        folium.Marker(start_coords, popup=start).add_to(fg)
                        folium.Marker(end_coords, popup=end).add_to(fg)

                        fg.add_to(m)

                        # -------------------------
                        # FUEL CALC (OPTIONAL)
                        # -------------------------
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

            legend_html += "</div>"

            m.get_root().html.add_child(folium.Element(legend_html))

            folium.LayerControl(collapsed=False).add_to(m)

            st.session_state.map_html = m.get_root().render()

# -------------------------
# MAP DISPLAY
# -------------------------
if st.session_state.map_html:

    st.subheader("🗺️ Map")

    st.components.v1.html(
        st.session_state.map_html,
        height=map_height,
        scrolling=True,
        key=f"map_{map_height}"
    )

# -------------------------
# TABLE + FUEL SUMMARY
# -------------------------
if uploaded_file and st.session_state.map_html:

    st.subheader("📊 Route Summary")

    df_table = pd.DataFrame(route_table)

    st.dataframe(df_table, use_container_width=True, hide_index=True)

    if use_fuel:
        total_fuel = df_table["Fuel Cost (£)"].sum()
        st.metric("Total Fuel Cost", f"£{total_fuel:.2f}")

    st.download_button(
        "📤 Download Map (HTML)",
        data=st.session_state.map_html,
        file_name="routes_map.html",
        mime="text/html"
    )