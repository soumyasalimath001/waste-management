"""
OpenStreetMap Data Fetcher for Waste Route Optimization
"""

import requests
import numpy as np
import pandas as pd
import streamlit as st
from geopy.geocoders import Nominatim
import asyncio
import time


class OSMDataFetcher:
    """Fetch real waste bin data from OpenStreetMap"""

    def __init__(self):

        # Multiple Overpass API endpoints (backup servers)
        self.overpass_urls = [
            "https://overpass-api.de/api/interpreter",
            "https://lz4.overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter"
        ]

        self.geolocator = Nominatim(
            user_agent="waste_route_optimizer"
        )

    def geocode_city(self, city_name):
        """Convert city name to bounding box"""

        try:
            location = self.geolocator.geocode(
                city_name,
                exactly_one=True,
                timeout=10  # type: ignore[arg-type]
            )

            # Handle async issue safely
            if asyncio.iscoroutine(location):
                try:
                    location = asyncio.run(location)
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    location = loop.run_until_complete(location)
                    loop.close()

            if location:

                bbox = location.raw['boundingbox']

                return {
                    'display_name': location.address,
                    'lat': float(location.latitude),
                    'lon': float(location.longitude),
                    'bbox': f"({bbox[0]},{bbox[2]},{bbox[1]},{bbox[3]})",
                    'bbox_raw': bbox
                }

        except Exception as e:
            st.error(f"Geocoding error: {e}")

        return None

    def fetch_waste_bins(self, bbox):
        """Fetch waste bins from Overpass API"""

        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="waste_basket"]{bbox};
          node["amenity"="recycling"]{bbox};
        );
        out body;
        """

        headers = {
            "User-Agent": "waste_route_optimizer/1.0"
        }

        # Try multiple API servers
        for url in self.overpass_urls:

            try:
                response = requests.get(
                    url,
                    params={'data': query},
                    headers=headers,
                    timeout=60
                )

                # Check status code
                if response.status_code != 200:
                    continue

                # Safe JSON parsing
                try:
                    data = response.json()
                except Exception:
                    st.warning(f"Invalid JSON from {url}")
                    continue

                # Check if elements exist
                if 'elements' not in data:
                    continue

                bins = []

                for element in data['elements']:

                    if 'lat' in element and 'lon' in element:

                        tags = element.get('tags', {})

                        bin_data = {
                            'osm_id': element['id'],
                            'bin_id': f"OSM_{element['id']}",
                            'latitude': element['lat'],
                            'longitude': element['lon'],
                            'amenity': tags.get('amenity', 'unknown'),
                            'material': tags.get('material', 'unknown'),
                            'operator': tags.get('operator', 'unknown'),
                            'capacity': 100,
                            'zone': tags.get('district', 'Unknown'),
                            'bin_type': tags.get(
                                'amenity',
                                'waste_basket'
                            ).capitalize(),
                        }

                        bins.append(bin_data)

                return pd.DataFrame(bins)

            except requests.exceptions.Timeout:
                st.warning(f"Timeout from {url}")
                continue

            except Exception as e:
                st.warning(f"Server failed: {url}")
                continue

        # If all APIs fail
        st.error("All Overpass API servers failed.")
        return pd.DataFrame()


def render_osm_fetcher():
    """Render OSM fetcher in Streamlit"""

    st.subheader("🌍 Fetch Real Waste Bin Data")

    fetcher = OSMDataFetcher()

    col1, col2 = st.columns([2, 1])

    with col1:

        city = st.text_input(
            "Enter city name",
            "London"
        )

        if st.button("🔍 Find Bins", use_container_width=True):

            with st.spinner(f"Searching for bins in {city}..."):

                city_info = fetcher.geocode_city(city)

                if city_info:

                    st.success(
                        f"📍 Found: {city_info['display_name']}"
                    )

                    bins_df = fetcher.fetch_waste_bins(
                        city_info['bbox']
                    )

                    if len(bins_df) > 0:

                        st.session_state[
                            'osm_explorer_data'
                        ] = bins_df

                        # Metrics
                        m1, m2, m3 = st.columns(3)

                        m1.metric(
                            "Total Bins",
                            len(bins_df)
                        )

                        m2.metric(
                            "Waste Baskets",
                            len(
                                bins_df[
                                    bins_df['amenity']
                                    == 'waste_basket'
                                ]
                            )
                        )

                        m3.metric(
                            "Recycling",
                            len(
                                bins_df[
                                    bins_df['amenity']
                                    == 'recycling'
                                ]
                            )
                        )

                        # Map
                        st.map(
                            bins_df[
                                ['latitude', 'longitude']
                            ]
                        )

                        # Table
                        with st.expander("View Raw Data"):
                            st.dataframe(bins_df)

                        # Load into optimizer
                        if st.button(
                            "🚛 Use This Data for Optimization"
                        ):

                            bins_df[
                                'fill_percentage'
                            ] = np.random.uniform(
                                20,
                                90,
                                len(bins_df)
                            )

                            bins_df[
                                'needs_collection'
                            ] = (
                                bins_df[
                                    'fill_percentage'
                                ] >= 80
                            )

                            bins_df[
                                'fill_level_kg'
                            ] = (
                                bins_df[
                                    'fill_percentage'
                                ] / 100
                            ) * bins_df['capacity']

                            bins_df['zone'] = (
                                bins_df['zone']
                                .fillna('Unknown')
                            )

                            st.session_state.current_bins = bins_df
                            st.session_state.data_source = (
                                f"OSM: {city}"
                            )

                            st.success(
                                f"✅ Loaded {len(bins_df)} real bins from {city}!"
                            )

                    else:
                        st.warning(
                            f"No bins found in {city}."
                        )

                else:
                    st.error(
                        f"Could not find city: {city}"
                    )

    with col2:

        st.markdown("""
        ### 💡 Tips
        - Try London, Paris, Berlin
        - OpenStreetMap coverage varies
        - Public bins only are available

        ### 📝 License
        Data © OpenStreetMap contributors
        """)