import streamlit as st

from modules.views import (
    render_dashboard_view,
    render_hotspots_view,
    render_route_planner_view,
    render_predictions_view,
    render_incidents_view,
    render_multimodal_view,
    render_analytics_view
)

# Page Configuration
st.set_page_config(
    page_title="Bangalore Traffic Dashboard",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State Variables
if 'route_results' not in st.session_state:
    st.session_state.route_results = None
if 'last_calculation_time' not in st.session_state:
    st.session_state.last_calculation_time = None
if 'multimodal_results' not in st.session_state:
    st.session_state.multimodal_results = None

# Custom Theme CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2530; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# Sidebar Navigation
st.sidebar.title("🚦 Traffic Dashboard")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Select Feature View:",
    [
        "📊 Dashboard",
        "📍 Live Hotspots",
        "🗺️ Advanced Route Planner",
        "📈 Area Predictions",
        "⚠️ Incidents",
        "🚶 Multimodal Planner",
        "📉 Analytics"
    ]
)

st.sidebar.markdown("---")

# Navigation Router
if page == "📊 Dashboard":
    render_dashboard_view()
elif page == "📍 Live Hotspots":
    render_hotspots_view()
elif page == "🗺️ Advanced Route Planner":
    render_route_planner_view()
elif page == "📈 Area Predictions":
    render_predictions_view()
elif page == "⚠️ Incidents":
    render_incidents_view()
elif page == "🚶 Multimodal Planner":
    render_multimodal_view()
elif page == "📉 Analytics":
    render_analytics_view()
else:
    st.title(f"{page}")
    st.info("Select a page from the sidebar navigation menu.")
