import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from modules.config import TOMTOM_API_KEY, BANGALORE_CENTER, BANGALORE_AREAS, INCIDENT_CATEGORIES, TRANSPORT_MODES
from modules.api import (
    fetch_live_traffic_incidents,
    parse_coordinates,
    fetch_routes_with_geometry,
    fetch_multimodal_routes,
    geocode_place
)
from modules.analytics import (
    calculate_congestion_score,
    predict_area_congestion,
    load_historical_data
)
from modules.maps import (
    create_gauge_chart,
    create_route_map,
    create_multimodal_map
)

def render_dashboard_view():
        st.title("🚦 Real-Time Traffic Dashboard - Bangalore")

        with st.spinner("Fetching live traffic data..."):

            hotspots, total_incidents = fetch_live_traffic_incidents()


        if not hotspots:

            st.info("✅ No live congestion detected")

            st.stop()


        avg_speed = round(sum([h["speed"] for h in hotspots]) / len(hotspots))

        avg_congestion = round(sum([h["congestion"] for h in hotspots]) / len(hotspots))


        col1, col2, col3 = st.columns(3)

        with col1: st.plotly_chart(create_gauge_chart(avg_speed, 60, "Avg Speed (km/h)"), use_container_width=True)

        with col2: st.plotly_chart(create_gauge_chart(avg_congestion, 100, "Congestion Index"), use_container_width=True)

        with col3: st.plotly_chart(create_gauge_chart(total_incidents, 50, "Active Incidents"), use_container_width=True)


        st.subheader(f"🗺️ Live Traffic Map - {len(hotspots)} Hotspots")

        m = folium.Map(location=BANGALORE_CENTER, zoom_start=11)

        for spot in hotspots:

            color = 'red' if spot['severity'] == 'High' else 'orange' if spot['severity'] == 'Medium' else 'green'

            folium.CircleMarker(

                [spot['lat'], spot['lon']], radius=8,

                popup=f"<b>{spot['name']}</b><br>Speed: {spot['speed']} km/h<br>Congestion: {round(spot['congestion'])}%",

                color=color, fill=True, fillColor=color, fillOpacity=0.7

            ).add_to(m)

        st_folium(m, width=None, height=500, key="dashboard_map")


def render_hotspots_view():
        import os

        import math

        import requests

        import streamlit as st

        import folium

        from streamlit_folium import st_folium

        from dotenv import load_dotenv


        # -------------------- CONFIG --------------------

        load_dotenv()

        TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")


        st.set_page_config(

            page_title="Area Traffic Hotspots",

            layout="wide",

        )


        # -------------------- PREDEFINED AREAS --------------------

        BENGALURU_AREAS = [

            "Koramangala",

            "Indiranagar",

            "Whitefield",

            "Electronic City",

            "HSR Layout",

            "Jayanagar",

            "Malleshwaram",

            "MG Road",

            "Hebbal",

            "BTM Layout",

            "JP Nagar",

            "Marathahalli",

            "Bellandur",

            "Yelahanka",

            "Banashankari",

            "Silk Board",

            "KR Puram",

            "Sarjapur Road",

            "Outer Ring Road",

            "Rajajinagar",

            "Custom Location"

        ]


        # -------------------- HEADER --------------------

        st.markdown(

            """

            <h1>🚦 Area-Specific Traffic Congestion</h1>

            <p style="color:gray">

                Live traffic visualization using TomTom Traffic API

            </p>

            """,

            unsafe_allow_html=True

        )


        # -------------------- CONTROLS ABOVE MAP --------------------

        col1, col2, col3 = st.columns([2, 1, 1])


        with col1:

            area_selection = st.selectbox(

                "📍 Select Area (Bengaluru)",

                options=BENGALURU_AREAS,

                index=0

            )


        with col2:

            zoom_level = st.slider(

                "🔍 Zoom level",

                min_value=12,

                max_value=17,

                value=15

            )


        # Show text input only if "Custom Location" is selected

        if area_selection == "Custom Location":

            area_name = st.text_input(

                "Enter custom area name",

                value="",

                placeholder="e.g., Brigade Road, Koramangala 5th Block"

            )

            if not area_name:

                st.warning("⚠️ Please enter a location name")

        else:

            area_name = area_selection


        st.divider()


        # -------------------- GEOCODE --------------------

        # Only proceed if we have a valid area name

        if not area_name:

            st.warning("⚠️ Please select or enter an area name to view traffic")

            st.stop()


        try:

            with st.spinner(f"Loading traffic data for {area_name}..."):

                lat, lon = geocode_place(area_name)

            st.success(f"📌 Location found: {area_name}")

        except Exception as e:

            st.error(f"Failed to locate area: {area_name}. Please try another name.")

            st.info("💡 Try using a well-known landmark or main area name")

            st.stop()


        # -------------------- MAP --------------------

        m = folium.Map(

            location=[lat, lon],

            zoom_start=zoom_level,

            tiles="CartoDB positron",

            control_scale=True

        )


        # -------------------- TOMTOM TRAFFIC TILE LAYER --------------------

        traffic_layer = folium.TileLayer(

            tiles=(

                "https://api.tomtom.com/traffic/map/4/tile/flow/"

                "relative/{z}/{x}/{y}.png?key=" + TOMTOM_API_KEY

            ),

            attr="TomTom Traffic",

            name="Live Traffic",

            overlay=True,

            control=True,

            opacity=0.9

        )


        traffic_layer.add_to(m)


        # -------------------- CENTER MARKER --------------------

        folium.Marker(

            [lat, lon],

            tooltip=area_name,

            icon=folium.Icon(color="blue", icon="info-sign")

        ).add_to(m)


        folium.LayerControl(collapsed=False).add_to(m)


        # -------------------- RENDER --------------------

        st_folium(

            m,

            width=None,

            height=650

        )


        # -------------------- LEGEND --------------------

        with st.expander("ℹ️ How to interpret traffic colors"):

            st.markdown(

                """

                **🟢 Green** — Free-flowing traffic  

                **🟡 Bright Yellow** — Mild / moving traffic  

                **🔴 Red** — Heavy congestion / traffic jam  


                Traffic data is updated live using TomTom Traffic APIs.

                """

            )


def render_route_planner_view():
        st.title("🗺️ Advanced Route Planner with Traffic Analysis")

        st.markdown("Plan your journey with real-time traffic data.")


        st.markdown("### 🎯 Quick Presets")

        preset_col1, preset_col2, preset_col3 = st.columns(3)

        presets = {

            "Koramangala → Whitefield": ("12.9352,77.6245", "12.9698,77.7499"),

            "MG Road → Electronic City": ("12.9750,77.6061", "12.8399,77.6770"),

            "Indiranagar → Hebbal": ("12.9719,77.6412", "13.0358,77.5970")

        }

        selected_preset = None

        for idx, (name, coords) in enumerate(presets.items()):

            col = [preset_col1, preset_col2, preset_col3][idx]

            if col.button(name, key=f"preset_{idx}"):

                selected_preset = coords

                st.session_state.route_results = None


        st.markdown("---")

        st.markdown("### 📍 Enter Route Details")

        col1, col2 = st.columns(2)

        with col1:

            origin_input = st.text_input("🟢 Origin (lat,lng)", 

                                         value=selected_preset[0] if selected_preset else "",

                                         placeholder="12.9716,77.5946",

                                         key="origin_input")

        with col2:

            dest_input = st.text_input("🔴 Destination (lat,lng)", 

                                       value=selected_preset[1] if selected_preset else "",

                                       placeholder="12.9352,77.6245",

                                       key="dest_input")


        col_opt1, col_opt2 = st.columns(2)

        with col_opt1: num_alternatives = st.slider("Alternative routes", 0, 3, 2, key="num_alt")

        with col_opt2: show_details = st.checkbox("Show detailed info", value=True, key="show_details")


        if st.button("🚀 Find Best Routes", type="primary", use_container_width=True, key="find_routes"):

            origin_coords = parse_coordinates(origin_input)

            dest_coords = parse_coordinates(dest_input)


            if not origin_coords:

                st.error("❌ Invalid origin coordinates")

                st.stop()

            if not dest_coords:

                st.error("❌ Invalid destination coordinates")

                st.stop()


            with st.spinner("🔄 Calculating routes with real-time traffic..."):

                routes = fetch_routes_with_geometry(origin_coords, dest_coords, TOMTOM_API_KEY, num_alternatives)


            if not routes:

                st.warning("⚠️ No routes found")

                st.stop()


            st.session_state.route_results = {

                'origin': origin_coords,

                'dest': dest_coords,

                'routes': routes

            }

            st.session_state.last_calculation_time = datetime.now().strftime('%H:%M:%S')


        if st.session_state.route_results:

            data = st.session_state.route_results

            routes = data['routes']

            origin_coords = data['origin']

            dest_coords = data['dest']


            st.success(f"✅ Found {len(routes)} route(s) - Calculated at {st.session_state.last_calculation_time}")

            st.markdown("### 🏆 Route Comparison")


            for idx, route in enumerate(routes):

                with st.container():

                    col_icon, col_info = st.columns([1, 20])

                    with col_icon:

                        st.markdown("### ⭐" if idx == 0 else f"### {idx + 1}")

                    with col_info:

                        st.markdown(f"**{route['name']}**" + (" 🏆 *Recommended*" if idx == 0 else ""))

                        m1, m2, m3, m4, m5 = st.columns(5)

                        m1.metric("📏 Distance", f"{route['distance_km']} km")

                        m2.metric("⏱️ Travel Time", f"{route['travel_time_min']} min")

                        m3.metric("🚦 Delay", f"+{route['traffic_delay_min']} min")

                        m4.metric("Traffic", f"{'🔴' if route['traffic_status']=='Heavy' else '🟡' if route['traffic_status']=='Moderate' else '🟢'} {route['traffic_status']}")

                        m5.metric("⚡ Efficiency", f"{route['efficiency']}%")

                        st.progress(route['efficiency'] / 100)

                    st.markdown("---")


            st.markdown("### 🗺️ Route Visualization")

            st.info("💡 Showing recommended route on map. Click route for details.")


            route_map = create_route_map(origin_coords, dest_coords, [routes[0]])

            st_folium(route_map, width=None, height=600, key=f"route_map_{st.session_state.last_calculation_time}")


            if show_details:

                st.markdown("### 📋 Detailed Route Information")

                for idx, route in enumerate(routes):

                    with st.expander(f"🛣️ {route['name']} Details", expanded=(idx == 0)):

                        d1, d2 = st.columns(2)

                        with d1:

                            st.markdown(f"**Route Metrics:**\n- Distance: `{route['distance_km']} km`\n- Travel Time: `{route['travel_time_min']} min`\n- Delay: `+{route['traffic_delay_min']} min`")

                        with d2:

                            st.markdown(f"**Traffic:**\n- Status: `{route['traffic_status']}`\n- Efficiency: `{route['efficiency']}%`")

                        if idx == 0:

                            st.success("✅ Recommended route")


def render_predictions_view():
        st.title("📈 Traffic Predictions for Bangalore Areas")


        historical_df = load_historical_data()


        if historical_df is not None:

            tab1, tab2, tab3 = st.tabs(["🕐 Time-Based Prediction", "📊 Area Comparison", "🔮 Live vs Historical"])


            with tab1:

                st.subheader("🕐 Predict Congestion by Area and Time")


                col1, col2 = st.columns(2)


                with col1:

                    selected_area = st.selectbox(

                        "🏙️ Select Area",

                        list(BANGALORE_AREAS.keys()),

                        key="time_pred_area"

                    )


                with col2:

                    selected_hour = st.slider(

                        "🕒 Select Hour (24-hour format)",

                        0, 23, datetime.now().hour,

                        key="time_pred_hour"

                    )


                if st.button("🔍 Predict Traffic", type="primary", key="predict_time"):

                    area_data = historical_df[historical_df['area'] == selected_area]


                    if len(area_data) > 0:

                        hour_data = area_data[area_data['hour'] == selected_hour]


                        if len(hour_data) > 0:

                            avg_speed = hour_data['avg_speed'].mean()

                            avg_congestion = hour_data['congestion_level'].mean()

                            avg_incidents = hour_data['incident_count'].mean()


                            st.markdown("### 📊 Predicted Conditions")

                            col_a, col_b, col_c, col_d = st.columns(4)


                            col_a.metric("Area", selected_area)

                            col_b.metric("Time", f"{selected_hour:02d}:00")

                            col_c.metric("Avg Speed", f"{int(avg_speed)} km/h")

                            col_d.metric("Congestion", f"{int(avg_congestion)}%")


                            if avg_congestion > 70:

                                st.error("🔴 **HIGH CONGESTION** - Heavy traffic expected. Avoid if possible!")

                            elif avg_congestion > 40:

                                st.warning("🟡 **MODERATE CONGESTION** - Expect some delays")

                            else:

                                st.success("🟢 **LOW CONGESTION** - Good time to travel!")


                            st.plotly_chart(

                                create_gauge_chart(int(avg_congestion), 100, f"Predicted Congestion at {selected_hour:02d}:00"),

                                use_container_width=True

                            )


                            st.markdown("### 🔥 24-Hour Congestion Heatmap")

                            hourly_congestion = area_data.groupby('hour')['congestion_level'].mean().reset_index()


                            fig_heatmap = go.Figure()

                            colors = ['green' if c < 40 else 'yellow' if c < 70 else 'red' 

                                     for c in hourly_congestion['congestion_level']]


                            fig_heatmap.add_trace(go.Bar(

                                x=hourly_congestion['hour'],

                                y=hourly_congestion['congestion_level'],

                                marker=dict(color=colors),

                                text=[f"{int(c)}%" for c in hourly_congestion['congestion_level']],

                                textposition='outside'

                            ))


                            fig_heatmap.add_vline(

                                x=selected_hour,

                                line_dash="dash",

                                line_color="blue",

                                line_width=3,

                                annotation_text="Selected Hour"

                            )


                            fig_heatmap.update_layout(

                                title=f"Hourly Congestion Pattern for {selected_area}",

                                xaxis_title="Hour of Day",

                                yaxis_title="Congestion Level (%)",

                                height=400,

                                showlegend=False

                            )


                            st.plotly_chart(fig_heatmap, use_container_width=True)

                        else:

                            st.warning("No historical data available for this hour.")

                    else:

                        st.warning("No historical data available for this area.")


            with tab2:

                st.subheader("📊 Compare Multiple Areas")


                selected_time = st.slider("🕒 Select Time for Comparison", 0, 23, 8, key="compare_time")


                if st.button("🔄 Compare All Areas", type="primary", key="compare_areas"):

                    with st.spinner("Analyzing all areas..."):

                        comparison_data = []


                        for area in BANGALORE_AREAS.keys():

                            area_hour_data = historical_df[

                                (historical_df['area'] == area) & 

                                (historical_df['hour'] == selected_time)

                            ]


                            if len(area_hour_data) > 0:

                                comparison_data.append({

                                    'area': area,

                                    'congestion': area_hour_data['congestion_level'].mean(),

                                    'speed': area_hour_data['avg_speed'].mean()

                                })


                        if comparison_data:

                            df_comparison = pd.DataFrame(comparison_data)

                            df_comparison = df_comparison.sort_values('congestion', ascending=False)


                            fig_compare = px.bar(

                                df_comparison,

                                x='congestion',

                                y='area',

                                orientation='h',

                                color='congestion',

                                color_continuous_scale=['green', 'yellow', 'red'],

                                title=f"Area Congestion Comparison at {selected_time:02d}:00"

                            )

                            st.plotly_chart(fig_compare, use_container_width=True)


            with tab3:

                st.subheader("🔮 Live vs Historical Comparison")


                selected_area_live = st.selectbox("🏙️ Select Area", list(BANGALORE_AREAS.keys()), key="live_vs_hist")


                if st.button("📊 Compare Now", type="primary", key="compare_live"):

                    current_hour = datetime.now().hour


                    hist_data = historical_df[

                        (historical_df['area'] == selected_area_live) & 

                        (historical_df['hour'] == current_hour)

                    ]


                    lat, lon = BANGALORE_AREAS[selected_area_live]

                    live_pred = predict_area_congestion(selected_area_live, lat, lon)


                    if len(hist_data) > 0 and live_pred:

                        hist_congestion = hist_data['congestion_level'].mean()

                        live_congestion = live_pred['congestion']


                        col_l1, col_l2, col_l3 = st.columns(3)


                        with col_l1:

                            st.metric("📚 Historical Avg", f"{int(hist_congestion)}%")


                        with col_l2:

                            st.metric("🔴 Live Current", f"{int(live_congestion)}%")


                        with col_l3:

                            diff = live_congestion - hist_congestion

                            st.metric("📈 Difference", f"{abs(int(diff))}%", delta=f"{int(diff)}%")


                        if diff > 15:

                            st.error("⚠️ **Traffic is significantly worse than usual!**")

                        elif diff < -15:

                            st.success("✅ **Traffic is better than usual!**")

                        else:

                            st.info("ℹ️ **Traffic is about normal for this time.**")


def render_incidents_view():

        with st.spinner("Fetching live incident data..."):

            hotspots, total_incidents = fetch_live_traffic_incidents()


        if not hotspots:

            st.success("✅ No incidents reported at the moment!")

            st.info("🎉 All roads are clear. Safe travels!")

            st.stop()


        accidents = [h for h in hotspots if h['category'] == 'ACCIDENT']

        construction = [h for h in hotspots if h['category'] == 'CONSTRUCTION']

        road_closed = [h for h in hotspots if h['category'] == 'ROAD_CLOSED']

        flooding = [h for h in hotspots if h['category'] == 'FLOODING']

        other = [h for h in hotspots if h['category'] == 'OTHER']


        st.subheader("📊 Incident Summary")

        col1, col2, col3, col4, col5 = st.columns(5)


        with col1:

            st.metric(

                label="🚗💥 Accidents",

                value=len(accidents),

                delta="Critical" if len(accidents) > 0 else None,

                delta_color="inverse"

            )


        with col2:

            st.metric(

                label="🚧 Construction",

                value=len(construction),

                delta="Active" if len(construction) > 0 else None,

                delta_color="off"

            )


        with col3:

            st.metric(

                label="🚫 Roads Closed",

                value=len(road_closed),

                delta="Blocked" if len(road_closed) > 0 else None,

                delta_color="inverse"

            )


        with col4:

            st.metric(

                label="🌊 Flooding",

                value=len(flooding),

                delta="Warning" if len(flooding) > 0 else None,

                delta_color="inverse"

            )


        with col5:

            st.metric(

                label="🚦 Other Issues",

                value=len(other),

                delta="Various" if len(other) > 0 else None,

                delta_color="off"

            )


        st.markdown("---")


        st.subheader("🗺️ Incident Locations Map")


        incident_map = folium.Map(location=BANGALORE_CENTER, zoom_start=11, tiles='OpenStreetMap')


        category_colors = {

            'ACCIDENT': 'red',

            'CONSTRUCTION': 'orange',

            'ROAD_CLOSED': 'darkred',

            'FLOODING': 'blue',

            'OTHER': 'gray'

        }


        for spot in hotspots:

            color = category_colors.get(spot['category'], 'gray')

            icon_emoji = INCIDENT_CATEGORIES.get(spot['category'], {}).get('icon', '🚦')


            folium.CircleMarker(

                [spot['lat'], spot['lon']],

                radius=10,

                popup=f"<b>{icon_emoji} {spot['name']}</b><br>{spot['description']}<br>Speed: {spot['speed']} km/h",

                color=color,

                fill=True,

                fillColor=color,

                fillOpacity=0.7

            ).add_to(incident_map)


        st_folium(incident_map, width=1400, height=550)


def render_multimodal_view():
        st.title("🚶 Multimodal Transport Planner")

        st.markdown("Compare different ways to travel - car, bike, walk, motorcycle, or public transit!")


        st.markdown("### 🎯 Quick Presets")

        preset_col1, preset_col2, preset_col3 = st.columns(3)

        multimodal_presets = {

            "Koramangala → Indiranagar": ("12.9352,77.6245", "12.9719,77.6412"),

            "MG Road → Cubbon Park": ("12.9750,77.6061", "12.9763,77.5993"),

            "BTM → HSR Layout": ("12.9165,77.6101", "12.9116,77.6473")

        }


        selected_multimodal_preset = None

        for idx, (name, coords) in enumerate(multimodal_presets.items()):

            col = [preset_col1, preset_col2, preset_col3][idx]

            if col.button(name, key=f"multimodal_preset_{idx}"):

                selected_multimodal_preset = coords

                st.session_state.multimodal_results = None


        st.markdown("---")

        st.markdown("### 📍 Enter Journey Details")


        col1, col2 = st.columns(2)

        with col1:

            multi_origin = st.text_input(

                "🟢 Starting Point (lat,lng)",

                value=selected_multimodal_preset[0] if selected_multimodal_preset else "",

                placeholder="12.9352,77.6245",

                key="multi_origin"

            )

        with col2:

            multi_dest = st.text_input(

                "🔴 Destination (lat,lng)",

                value=selected_multimodal_preset[1] if selected_multimodal_preset else "",

                placeholder="12.9719,77.6412",

                key="multi_dest"

            )


        st.markdown("### 🚦 Select Transport Modes to Compare")


        mode_cols = st.columns(5)

        selected_modes = []


        mode_keys = list(TRANSPORT_MODES.keys())

        for idx, mode_key in enumerate(mode_keys):

            mode_info = TRANSPORT_MODES[mode_key]

            with mode_cols[idx]:

                if st.checkbox(

                    f"{mode_info['icon']} {mode_info['name']}",

                    value=True,

                    key=f"mode_{mode_key}"

                ):

                    selected_modes.append(mode_key)


        if not selected_modes:

            st.warning("⚠️ Please select at least one transport mode!")

            st.stop()


        if st.button("🚀 Compare Transport Options", type="primary", use_container_width=True, key="compare_multimodal"):

            origin_coords = parse_coordinates(multi_origin)

            dest_coords = parse_coordinates(multi_dest)


            if not origin_coords:

                st.error("❌ Invalid origin coordinates")

                st.stop()

            if not dest_coords:

                st.error("❌ Invalid destination coordinates")

                st.stop()


            with st.spinner("🔄 Calculating routes for all transport modes..."):

                routes = fetch_multimodal_routes(origin_coords, dest_coords, TOMTOM_API_KEY, selected_modes)


            if not routes:

                st.warning("⚠️ No routes found")

                st.stop()


            st.session_state.multimodal_results = {

                'origin': origin_coords,

                'dest': dest_coords,

                'routes': routes

            }


        if st.session_state.multimodal_results:

            data = st.session_state.multimodal_results

            routes = data['routes']

            origin_coords = data['origin']

            dest_coords = data['dest']


            st.success(f"✅ Found {len(routes)} route option(s)")


            st.markdown("### 🏆 Transport Mode Comparison")


            # Create comparison cards

            for idx, route in enumerate(routes):

                with st.container():

                    border_color = route['color']


                    st.markdown(f"""

                        <div style='border-left: 4px solid {border_color}; padding-left: 15px; margin-bottom: 20px;'>

                            <h3>{route['icon']} {route['mode_name']}</h3>

                        </div>

                    """, unsafe_allow_html=True)


                    metrics_col = st.columns([1,1,1,1,1])


                    with metrics_col[0]:

                        st.metric("⏱️ Time", f"{route['total_time_min']} min")


                    with metrics_col[1]:

                        st.metric("📏 Distance", f"{route['distance_km']} km")


                    with metrics_col[2]:

                        st.metric("💰 Cost", f"₹{route['estimated_cost']}")


                    # Additional info

                    info_col = st.columns([2,1])

                    with info_col[0]:

                        if route['mode'] == 'car' and route['traffic_delay_min'] > 0:

                            st.warning(f"⚠️ Traffic delay: +{route['traffic_delay_min']} min")


                        # Recommendations

                        if route['mode'] == 'pedestrian' and route['distance_km'] > 5:

                            st.info("🚶 Long walk - Consider cycling or transit")

                        elif route['mode'] == 'bicycle' and route['distance_km'] < 2:

                            st.info("🚴 Short distance - Walking is also great!")

                        elif route['co2_emissions'] == 0:

                            st.success("🌱 Zero emissions - Eco-friendly choice!")


                    with info_col[1]:

                        if idx == 0:

                            st.success("⭐ Fastest")

                        elif route['co2_emissions'] == 0 and any(r['co2_emissions'] > 0 for r in routes):

                            st.success("🌱 Greenest")

                        elif route['estimated_cost'] == min(r['estimated_cost'] for r in routes):

                            st.success("💰 Cheapest")


                    st.markdown("---")


            # Comparison Charts

            st.markdown("### 📊 Visual Comparison")


            chart_tab1, chart_tab2, chart_tab3 = st.tabs(["⏱️ Time & Cost", "🌱 Environmental", "📈 Overview"])


            with chart_tab1:

                col_chart1, col_chart2 = st.columns(2)


                with col_chart1:

                    fig_time = go.Figure()

                    fig_time.add_trace(go.Bar(

                        x=[r['mode_name'] for r in routes],

                        y=[r['total_time_min'] for r in routes],

                        marker_color=[r['color'] for r in routes],

                        text=[f"{r['total_time_min']} min" for r in routes],

                        textposition='outside'

                    ))

                    fig_time.update_layout(

                        title="Travel Time Comparison",

                        yaxis_title="Time (minutes)",

                        height=400

                    )

                    st.plotly_chart(fig_time, use_container_width=True)


                with col_chart2:

                    fig_cost = go.Figure()

                    fig_cost.add_trace(go.Bar(

                        x=[r['mode_name'] for r in routes],

                        y=[r['estimated_cost'] for r in routes],

                        marker_color=[r['color'] for r in routes],

                        text=[f"₹{r['estimated_cost']}" for r in routes],

                        textposition='outside'

                    ))

                    fig_cost.update_layout(

                        title="Cost Comparison",

                        yaxis_title="Cost (₹)",

                        height=400

                    )

                    st.plotly_chart(fig_cost, use_container_width=True)


            with chart_tab2:

                col_env1, col_env2 = st.columns(2)


                with col_env1:

                    fig_co2 = go.Figure()

                    fig_co2.add_trace(go.Bar(

                        x=[r['mode_name'] for r in routes],

                        y=[r['co2_emissions'] for r in routes],

                        marker_color=['green' if r['co2_emissions'] == 0 else 'orange' if r['co2_emissions'] < 500 else 'red' for r in routes],

                        text=[f"{r['co2_emissions']}g" for r in routes],

                        textposition='outside'

                    ))

                    fig_co2.update_layout(

                        title="CO₂ Emissions",

                        yaxis_title="CO₂ (grams)",

                        height=400

                    )

                    st.plotly_chart(fig_co2, use_container_width=True)


                with col_env2:

                    active_routes = [r for r in routes if r['calories_burned'] > 0]

                    if active_routes:

                        fig_cal = go.Figure()

                        fig_cal.add_trace(go.Bar(

                            x=[r['mode_name'] for r in active_routes],

                            y=[r['calories_burned'] for r in active_routes],

                            marker_color=[r['color'] for r in active_routes],

                            text=[f"{r['calories_burned']} kcal" for r in active_routes],

                            textposition='outside'

                        ))

                        fig_cal.update_layout(

                            title="Calories Burned (Active Transport)",

                            yaxis_title="Calories (kcal)",

                            height=400

                        )

                        st.plotly_chart(fig_cal, use_container_width=True)

                    else:

                        st.info("No active transport modes selected for calorie comparison")


            with chart_tab3:

                # Radar chart for overall comparison

                categories = ['Speed Score', 'Cost Score', 'Environmental Score', 'Health Score']


                fig_radar = go.Figure()


                for route in routes:

                    # Calculate normalized scores (0-100)

                    max_time = max([r['total_time_min'] for r in routes])

                    speed_score = 100 - (route['total_time_min'] / max_time * 100)


                    max_cost = max([r['estimated_cost'] for r in routes]) or 1

                    cost_score = 100 - (route['estimated_cost'] / max_cost * 100)


                    max_co2 = max([r['co2_emissions'] for r in routes]) or 1

                    env_score = 100 - (route['co2_emissions'] / max_co2 * 100)


                    max_cal = max([r['calories_burned'] for r in routes]) or 1

                    health_score = (route['calories_burned'] / max_cal * 100) if max_cal > 0 else 50


                    fig_radar.add_trace(go.Scatterpolar(

                        r=[speed_score, cost_score, env_score, health_score],

                        theta=categories,

                        fill='toself',

                        name=f"{route['icon']} {route['mode_name']}",

                        line_color=route['color']

                    ))


                fig_radar.update_layout(

                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),

                    showlegend=True,

                    title="Overall Comparison (Higher is Better)",

                    height=500

                )

                st.plotly_chart(fig_radar, use_container_width=True)


            # Map visualization

            st.markdown("### 🗺️ Route Visualization")

            st.info("💡 All transport modes shown on map. Click routes for details.")


            multimodal_map = create_multimodal_map(origin_coords, dest_coords, routes)

            st_folium(multimodal_map, width=None, height=600, key="multimodal_map")


            # Recommendations

            st.markdown("### 💡 Smart Recommendations")


            fastest = min(routes, key=lambda x: x['total_time_min'])

            cheapest = min(routes, key=lambda x: x['estimated_cost'])

            greenest = min(routes, key=lambda x: x['co2_emissions'])

            healthiest = max(routes, key=lambda x: x['calories_burned'])


            rec_col1, rec_col2 = st.columns(2)


            with rec_col1:

                st.markdown(f"**🏃 Fastest:** {fastest['icon']} {fastest['mode_name']} ({fastest['total_time_min']} min)")

                st.markdown(f"**💰 Cheapest:** {cheapest['icon']} {cheapest['mode_name']} (₹{cheapest['estimated_cost']})")


            with rec_col2:

                st.markdown(f"**🌱 Greenest:** {greenest['icon']} {greenest['mode_name']} ({greenest['co2_emissions']}g CO₂)")

                if healthiest['calories_burned'] > 0:

                    st.markdown(f"**💪 Healthiest:** {healthiest['icon']} {healthiest['mode_name']} ({healthiest['calories_burned']} kcal)")


def render_analytics_view():
        st.title("📉 Traffic Analytics Dashboard")

        st.markdown("Deep insights into Bangalore's traffic patterns")


        historical_df = load_historical_data()


        if historical_df is not None:

            tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🕐 Peak Hours", "📍 Area Analysis", "📈 Trends"])


            with tab1:

                st.subheader("📊 Traffic Overview")


                col1, col2, col3, col4 = st.columns(4)


                with col1:

                    avg_speed_all = historical_df['avg_speed'].mean()

                    st.metric("Average Speed", f"{int(avg_speed_all)} km/h")


                with col2:

                    avg_congestion_all = historical_df['congestion_level'].mean()

                    st.metric("Avg Congestion", f"{int(avg_congestion_all)}%")


                with col3:

                    total_incidents = historical_df['incident_count'].sum()

                    st.metric("Total Incidents", int(total_incidents))


                with col4:

                    areas_tracked = historical_df['area'].nunique()

                    st.metric("Areas Tracked", areas_tracked)


                st.markdown("---")


                st.markdown("### 📈 Speed vs Congestion Correlation")

                fig_scatter = px.scatter(

                    historical_df,

                    x='avg_speed',

                    y='congestion_level',

                    color='area',

                    size='incident_count',

                    hover_data=['hour'],

                    title="Speed vs Congestion Level by Area",

                    labels={'avg_speed': 'Average Speed (km/h)', 'congestion_level': 'Congestion Level (%)'}

                )

                st.plotly_chart(fig_scatter, use_container_width=True)


            with tab2:

                st.subheader("🕐 Peak Hours Analysis")


                hourly_stats = historical_df.groupby('hour').agg({

                    'congestion_level': 'mean',

                    'avg_speed': 'mean',

                    'incident_count': 'sum'

                }).reset_index()


                fig_peak = go.Figure()


                fig_peak.add_trace(go.Scatter(

                    x=hourly_stats['hour'],

                    y=hourly_stats['congestion_level'],

                    mode='lines+markers',

                    name='Congestion Level',

                    line=dict(color='red', width=3),

                    yaxis='y'

                ))


                fig_peak.add_trace(go.Scatter(

                    x=hourly_stats['hour'],

                    y=hourly_stats['avg_speed'],

                    mode='lines+markers',

                    name='Average Speed',

                    line=dict(color='blue', width=3),

                    yaxis='y2'

                ))


                fig_peak.update_layout(

                    title='Hourly Traffic Patterns',

                    xaxis=dict(title='Hour of Day'),

                    yaxis=dict(title='Congestion Level (%)', side='left'),

                    yaxis2=dict(title='Average Speed (km/h)', side='right', overlaying='y'),

                    height=500

                )


                st.plotly_chart(fig_peak, use_container_width=True)


                peak_hours = hourly_stats.nlargest(3, 'congestion_level')

                st.markdown("### 🔴 Top 3 Peak Congestion Hours")

                for idx, row in peak_hours.iterrows():

                    st.error(f"**{int(row['hour']):02d}:00** - Congestion: {int(row['congestion_level'])}%, Speed: {int(row['avg_speed'])} km/h")


            with tab3:

                st.subheader("📍 Area-wise Analysis")


                area_stats = historical_df.groupby('area').agg({

                    'congestion_level': 'mean',

                    'avg_speed': 'mean',

                    'incident_count': 'sum'

                }).reset_index()


                area_stats = area_stats.sort_values('congestion_level', ascending=False)


                fig_area_congestion = px.bar(

                    area_stats,

                    x='area',

                    y='congestion_level',

                    color='congestion_level',

                    color_continuous_scale=['green', 'yellow', 'red'],

                    title='Average Congestion by Area',

                    labels={'congestion_level': 'Congestion Level (%)'}

                )

                fig_area_congestion.update_xaxes(tickangle=-45)

                st.plotly_chart(fig_area_congestion, use_container_width=True)


                st.markdown("### 🎯 Area Comparison Table")

                area_stats_display = area_stats.copy()

                area_stats_display['congestion_level'] = area_stats_display['congestion_level'].apply(lambda x: f"{int(x)}%")

                area_stats_display['avg_speed'] = area_stats_display['avg_speed'].apply(lambda x: f"{int(x)} km/h")

                area_stats_display['incident_count'] = area_stats_display['incident_count'].apply(lambda x: int(x))

                area_stats_display.columns = ['Area', 'Avg Congestion', 'Avg Speed', 'Total Incidents']

                st.dataframe(area_stats_display, use_container_width=True, hide_index=True)


            with tab4:

                st.subheader("📈 Traffic Trends & Heatmap")


                st.markdown("### 🔥 Congestion Heatmap: Hour vs Area")


                pivot_data = historical_df.pivot_table(

                    values='congestion_level',

                    index='area',

                    columns='hour',

                    aggfunc='mean'

                )


                fig_heatmap = px.imshow(

                    pivot_data,

                    labels=dict(x="Hour of Day", y="Area", color="Congestion %"),

                    x=pivot_data.columns,

                    y=pivot_data.index,

                    color_continuous_scale='RdYlGn_r',

                    title="Traffic Congestion Heatmap"

                )

                fig_heatmap.update_layout(height=600)

                st.plotly_chart(fig_heatmap, use_container_width=True)


                st.markdown("### 📊 Incident Distribution")

                incident_by_area = historical_df.groupby('area')['incident_count'].sum().reset_index()

                incident_by_area = incident_by_area.sort_values('incident_count', ascending=False)


                fig_incidents = px.pie(

                    incident_by_area,

                    values='incident_count',

                    names='area',

                    title='Incident Distribution by Area'

                )

                st.plotly_chart(fig_incidents, use_container_width=True)

        else:

            st.error("Historical data could not be loaded. Please check the data source.")

