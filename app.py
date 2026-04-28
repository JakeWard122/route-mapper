import streamlit as st
import pandas as pd
import folium
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium
import time

st.set_page_config(page_title="Route Mapper", layout="centered")

st.title("📍 Route Mapper")
st.markdown("Upload an Excel file with **from** and **to** columns")

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

geolocator = Nominatim(user_agent="route_mapper_app")

@st.cache_data
def get_coords(place):
    try:
        location = geolocator.geocode(place)
        time.sleep(1)
        if location:
            return (location.latitude, location.longitude)
    except:
        return None
    return None

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if not {"from", "to"}.issubset(df.columns):
        st.error("Your file must contain 'from' and 'to' columns")
    else:
        st.success(f"{len(df)} routes loaded")

        if st.button("Generate Map"):
            with st.spinner("Mapping routes..."):
                m = folium.Map(location=[54.5, -3], zoom_start=6)

                progress = st.progress(0)

                for i, row in df.iterrows():
                    start = row["from"]
                    end = row["to"]

                    start_coords = get_coords(start)
                    end_coords = get_coords(end)

                    if start_coords and end_coords:
                        folium.Marker(start_coords, popup=f"Start: {start}").add_to(m)
                        folium.Marker(end_coords, popup=f"End: {end}").add_to(m)

                        folium.PolyLine(
                            [start_coords, end_coords],
                            weight=3
                        ).add_to(m)
                    else:
                        st.warning(f"Could not find: {start} or {end}")

                    progress.progress((i + 1) / len(df))

                st.subheader("🗺️ Your Map")
                st_folium(m, height=500)

                # Download option
                m.save("routes_map.html")
                with open("routes_map.html", "rb") as f:
                    st.download_button(
                        "Download Map",
                        f,
                        file_name="routes_map.html"
                    )