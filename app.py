import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
import os
import math
from io import StringIO

# Page Configuration
st.set_page_config(
    page_title="Bangalore Traffic Dashboard",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for route data persistence
if 'route_results' not in st.session_state:
    st.session_state.route_results = None
if 'last_calculation_time' not in st.session_state:
    st.session_state.last_calculation_time = None

# Custom CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2530; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# API Configuration
TOMTOM_API_KEY = "bZzH6OoOH5IciZ0rYXQ2QElpoWVzTseA"
BANGALORE_BBOX = "77.48,12.82,77.75,13.12"
BANGALORE_CENTER = [12.9716, 77.5946]

BANGALORE_AREAS = {
    'Koramangala': [12.9352, 77.6245], 'Whitefield': [12.9698, 77.7499],
    'Electronic City': [12.8399, 77.6770], 'MG Road': [12.9750, 77.6061],
    'Indiranagar': [12.9719, 77.6412], 'HSR Layout': [12.9116, 77.6473],
    'Marathahalli': [12.9591, 77.6974], 'Hebbal': [13.0358, 77.5970],
    'Jayanagar': [12.9250, 77.5838], 'BTM Layout': [12.9165, 77.6101],
    'Yelahanka': [13.1007, 77.5963], 'Malleshwaram': [13.0029, 77.5703]
}

INCIDENT_CATEGORIES = {
    'ACCIDENT': {
        'icon': '🚗💥',
        'color': '#ff4444',
        'keywords': ['accident', 'collision', 'crash', 'vehicle accident', 'car accident']
    },
    'CONSTRUCTION': {
        'icon': '🚧',
        'color': '#ffa500',
        'keywords': ['construction', 'roadwork', 'road work', 'maintenance', 'repair']
    },
    'ROAD_CLOSED': {
        'icon': '🚫',
        'color': '#dc143c',
        'keywords': ['road closed', 'blocked', 'closure', 'closed road', 'obstruction']
    },
    'FLOODING': {
        'icon': '🌊',
        'color': '#4169e1',
        'keywords': ['flood', 'flooding', 'water', 'waterlogged', 'heavy rain']
    }
}

def categorize_incident(description):
    """Categorize incident based on description keywords"""
    description_lower = description.lower()
    
    for category, details in INCIDENT_CATEGORIES.items():
        for keyword in details['keywords']:
            if keyword in description_lower:
                return category
    
    return 'OTHER'

# === UTILITY FUNCTIONS ===
def calculate_congestion_score(current_speed, free_flow_speed):
    if free_flow_speed == 0: return 0
    drop = free_flow_speed - current_speed
    percent = (drop / free_flow_speed) * 100
    return min(100, max(1, percent))

def create_gauge_chart(value, max_value, title):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        title={'text': title, 'font': {'size': 16}},
        gauge={
            'axis': {'range': [None, max_value]}, 'bar': {'color': "darkblue"},
            'steps': [{'range': [0, max_value/3], 'color': "lightgreen"},
                     {'range': [max_value/3, 2*max_value/3], 'color': "yellow"},
                     {'range': [2*max_value/3, max_value], 'color': "red"}],
            'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': value}
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
    return fig


@st.cache_data(ttl=60)
def fetch_live_traffic_incidents():
    """Fetch live traffic incidents from TomTom API - optimized for all hotspots"""
    try:
        incident_url = "https://api.tomtom.com/traffic/services/5/incidentDetails"
        params = {"key": TOMTOM_API_KEY, "bbox": BANGALORE_BBOX, "timeValidityFilter": "present"}
        
        response = requests.get(incident_url, params=params, timeout=10)
        
        if response.status_code != 200:
            st.error(f"Failed to load traffic data. Status: {response.status_code}")
            return [], 0
        
        data = response.json()
        incidents = data.get("incidents", [])
        
        if not incidents:
            return [], 0
        
        hotspots = []
        flow_url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json"
        
        incidents_to_process = incidents[:200]
        
        for inc in incidents_to_process:
            coords = inc["geometry"]["coordinates"]
            
            if isinstance(coords[0], list):
                lon, lat = coords[0][0], coords[0][1]
            else:
                lon, lat = coords[0], coords[1]
            
            lat, lon = float(lat), float(lon)
            
            try:
                flow_params = {"key": TOMTOM_API_KEY, "point": f"{lat},{lon}"}
                flow_response = requests.get(flow_url, params=flow_params, timeout=3)
                
                if flow_response.status_code == 200:
                    seg = flow_response.json().get("flowSegmentData", {})
                    current_speed = int(seg.get("currentSpeed", 0))
                    free_flow_speed = int(seg.get("freeFlowSpeed", 1))
                else:
                    current_speed = 15
                    free_flow_speed = 40
                    
            except:
                current_speed = 15
                free_flow_speed = 40
            
            congestion_score = calculate_congestion_score(current_speed, free_flow_speed)
            road_name = (inc["properties"].get("from", "") or 
                       inc["properties"].get("to", "") or 
                       f"Location ({round(lat,3)}, {round(lon,3)})")
            
            delay = round((free_flow_speed - current_speed) / free_flow_speed * 15) if free_flow_speed > 0 else 0
            
            description = inc["properties"].get("description", "Traffic congestion")
            incident_category = categorize_incident(description)
            
            hotspots.append({
                "name": road_name,
                "lat": lat,
                "lon": lon,
                "speed": current_speed,
                "free_flow_speed": free_flow_speed,
                "congestion": congestion_score,
                "delay": max(0, delay),
                "severity": "High" if congestion_score > 60 else "Medium" if congestion_score > 30 else "Low",
                "description": description,
                "category": incident_category,
                "icon_data": inc.get("iconCategory", 0)
            })
        
        return hotspots, len(incidents)
    
    except Exception as e:
        st.error(f"Error fetching traffic data: {str(e)}")
        return [], 0


@st.cache_data(ttl=300)
def predict_area_congestion(area_name, lat, lon):
    try:
        response = requests.get(
            "https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json",
            params={"key": TOMTOM_API_KEY, "point": f"{lat},{lon}"}, timeout=5
        )
        if response.status_code == 200:
            seg = response.json().get("flowSegmentData", {})
            current_speed = int(seg.get("currentSpeed", 0))
            free_flow_speed = int(seg.get("freeFlowSpeed", 1))
            congestion = calculate_congestion_score(current_speed, free_flow_speed)
            return {
                "area": area_name, "current_speed": current_speed,
                "free_flow_speed": free_flow_speed, "congestion": congestion,
                "status": "High" if congestion > 60 else "Moderate" if congestion > 30 else "Low"
            }
    except: pass
    return None

# === ROUTE PLANNER FUNCTIONS ===
def parse_coordinates(coord_string):
    try:
        parts = coord_string.replace(" ", "").split(",")
        if len(parts) != 2: return None
        lat, lon = float(parts[0]), float(parts[1])
        if not (12.5 <= lat <= 13.5 and 77.0 <= lon <= 78.0):
            st.warning("⚠️ Coordinates outside Bangalore region")
        return (lat, lon)
    except: return None

def fetch_routes_with_geometry(origin_coords, dest_coords, api_key, max_alternatives=2):
    try:
        origin_str = f"{origin_coords[0]},{origin_coords[1]}"
        dest_str = f"{dest_coords[0]},{dest_coords[1]}"
        response = requests.get(
            f"https://api.tomtom.com/routing/1/calculateRoute/{origin_str}:{dest_str}/json",
            params={
                "key": api_key, 
                "traffic": "true", 
                "routeType": "fastest",
                "travelMode": "car", 
                "maxAlternatives": max_alternatives
            }, 
            timeout=15
        )
        if response.status_code != 200:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return []
        
        routes = []
        for idx, route in enumerate(response.json().get("routes", [])):
            summary = route["summary"]
            
            route_coords = []
            for leg in route.get("legs", []):
                for point in leg.get("points", []):
                    lat = point.get("latitude")
                    lon = point.get("longitude")
                    if lat is not None and lon is not None:
                        route_coords.append((lat, lon))
            
            traffic_delay = summary.get("trafficDelayInSeconds", 0)
            travel_time = summary.get("travelTimeInSeconds", 0)
            
            routes.append({
                "id": idx, 
                "name": f"Route {idx + 1}",
                "distance_km": round(summary["lengthInMeters"] / 1000, 2),
                "travel_time_min": round(travel_time / 60, 1),
                "traffic_delay_min": round(traffic_delay / 60, 1),
                "total_time_min": round((travel_time + traffic_delay) / 60, 1),
                "traffic_status": "Heavy" if traffic_delay > 300 else "Moderate" if traffic_delay > 120 else "Light",
                "efficiency": round(100 - (traffic_delay / max(travel_time, 1) * 100), 1),
                "coordinates": route_coords
            })
        return routes
    except Exception as e:
        st.error(f"Route fetch error: {str(e)}")
        return []

def create_route_map(origin_coords, dest_coords, routes):
    center_lat = (origin_coords[0] + dest_coords[0]) / 2
    center_lon = (origin_coords[1] + dest_coords[1]) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    
    colors = ['#2E86DE', '#FF6B6B', '#95A5A6', '#F39C12', '#9B59B6']
    
    for idx, route in enumerate(routes):
        if not route["coordinates"]: continue
        color = colors[idx % len(colors)]
        weight = 5 if idx == 0 else 3
        opacity = 0.8 if idx == 0 else 0.6
        
        popup_html = f"""
        <div style='font-family: Arial; min-width: 200px;'>
            <h4 style='margin: 0 0 10px 0; color: {color};'>{route['name']}</h4>
            <hr style='margin: 5px 0;'>
            <b>📏 Distance:</b> {route['distance_km']} km<br>
            <b>⏱️ Travel Time:</b> {route['travel_time_min']} min<br>
            <b>🚦 Traffic Delay:</b> +{route['traffic_delay_min']} min<br>
            <b>📊 Total Time:</b> {route['total_time_min']} min<br>
            <b>🚗 Traffic:</b> {route['traffic_status']}<br>
            <b>⚡ Efficiency:</b> {route['efficiency']}%
        </div>
        """
        
        folium.PolyLine(
            locations=route["coordinates"], color=color, weight=weight, opacity=opacity,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{route['name']}: {route['distance_km']} km, {route['total_time_min']} min"
        ).add_to(m)
        
        if len(route["coordinates"]) > 0:
            mid_point = route["coordinates"][len(route["coordinates"]) // 2]
            icon_html = f"<div style='background-color:{color}; color:white; font-weight:bold; padding:3px 8px; border-radius:10px; border:2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);'>{idx+1}</div>"
            folium.Marker(location=mid_point, icon=folium.DivIcon(html=icon_html)).add_to(m)
    
    folium.Marker(origin_coords, popup=f"<b>🟢 Origin</b><br>{origin_coords[0]:.4f}, {origin_coords[1]:.4f}",
                 tooltip="Origin", icon=folium.Icon(color='green', icon='play', prefix='fa')).add_to(m)
    folium.Marker(dest_coords, popup=f"<b>🔴 Destination</b><br>{dest_coords[0]:.4f}, {dest_coords[1]:.4f}",
                 tooltip="Destination", icon=folium.Icon(color='red', icon='flag-checkered', prefix='fa')).add_to(m)
    
    all_coords = [origin_coords, dest_coords]
    for route in routes:
        all_coords.extend(route["coordinates"])
    if len(all_coords) > 2:
        m.fit_bounds(all_coords)
    return m

@st.cache_data
def load_historical_data():
    csv_data = """area,day_of_week,hour,avg_speed,congestion_level,incident_count,weather,date
Koramangala,Monday,0,45,15,0,Clear,2024-12-01
Koramangala,Monday,1,48,12,0,Clear,2024-12-01
Koramangala,Monday,2,50,10,0,Clear,2024-12-01
Koramangala,Monday,3,50,10,0,Clear,2024-12-01
Koramangala,Monday,4,48,12,0,Clear,2024-12-01
Koramangala,Monday,5,45,18,0,Clear,2024-12-01
Koramangala,Monday,6,38,32,1,Clear,2024-12-01
Koramangala,Monday,7,28,55,2,Clear,2024-12-01
Koramangala,Monday,8,18,78,4,Clear,2024-12-01
Koramangala,Monday,9,22,68,3,Clear,2024-12-01
Koramangala,Monday,10,30,52,2,Clear,2024-12-01
Koramangala,Monday,11,32,48,1,Clear,2024-12-01
Koramangala,Monday,12,35,42,1,Clear,2024-12-01
Koramangala,Monday,13,33,45,1,Clear,2024-12-01
Koramangala,Monday,14,30,50,2,Clear,2024-12-01
Koramangala,Monday,15,28,55,2,Clear,2024-12-01
Koramangala,Monday,16,25,62,3,Clear,2024-12-01
Koramangala,Monday,17,20,72,4,Clear,2024-12-01
Koramangala,Monday,18,15,82,5,Clear,2024-12-01
Koramangala,Monday,19,18,78,4,Clear,2024-12-01
Koramangala,Monday,20,25,62,2,Clear,2024-12-01
Koramangala,Monday,21,32,48,1,Clear,2024-12-01
Koramangala,Monday,22,40,28,0,Clear,2024-12-01
Koramangala,Monday,23,45,20,0,Clear,2024-12-01
Whitefield,Monday,0,48,12,0,Clear,2024-12-01
Whitefield,Monday,1,50,10,0,Clear,2024-12-01
Whitefield,Monday,2,50,8,0,Clear,2024-12-01
Whitefield,Monday,3,50,8,0,Clear,2024-12-01
Whitefield,Monday,4,48,12,0,Clear,2024-12-01
Whitefield,Monday,5,42,22,0,Clear,2024-12-01
Whitefield,Monday,6,35,40,1,Clear,2024-12-01
Whitefield,Monday,7,25,65,3,Clear,2024-12-01
Whitefield,Monday,8,15,85,5,Clear,2024-12-01
Whitefield,Monday,9,18,80,4,Clear,2024-12-01
Whitefield,Monday,10,25,65,3,Clear,2024-12-01
Whitefield,Monday,11,28,58,2,Clear,2024-12-01
Whitefield,Monday,12,30,55,2,Clear,2024-12-01
Whitefield,Monday,13,28,58,2,Clear,2024-12-01
Whitefield,Monday,14,26,62,3,Clear,2024-12-01
Whitefield,Monday,15,24,68,3,Clear,2024-12-01
Whitefield,Monday,16,22,72,4,Clear,2024-12-01
Whitefield,Monday,17,18,80,5,Clear,2024-12-01
Whitefield,Monday,18,12,88,6,Clear,2024-12-01
Whitefield,Monday,19,15,85,5,Clear,2024-12-01
Whitefield,Monday,20,22,72,3,Clear,2024-12-01
Whitefield,Monday,21,30,55,2,Clear,2024-12-01
Whitefield,Monday,22,38,35,1,Clear,2024-12-01
Whitefield,Monday,23,45,20,0,Clear,2024-12-01
Electronic City,Monday,0,50,10,0,Clear,2024-12-01
Electronic City,Monday,1,50,8,0,Clear,2024-12-01
Electronic City,Monday,2,50,5,0,Clear,2024-12-01
Electronic City,Monday,3,50,5,0,Clear,2024-12-01
Electronic City,Monday,4,48,12,0,Clear,2024-12-01
Electronic City,Monday,5,45,18,0,Clear,2024-12-01
Electronic City,Monday,6,38,35,1,Clear,2024-12-01
Electronic City,Monday,7,30,52,2,Clear,2024-12-01
Electronic City,Monday,8,20,75,4,Clear,2024-12-01
Electronic City,Monday,9,25,68,3,Clear,2024-12-01
Electronic City,Monday,10,32,50,2,Clear,2024-12-01
Electronic City,Monday,11,35,45,1,Clear,2024-12-01
Electronic City,Monday,12,38,38,1,Clear,2024-12-01
Electronic City,Monday,13,35,42,1,Clear,2024-12-01
Electronic City,Monday,14,33,48,2,Clear,2024-12-01
Electronic City,Monday,15,30,55,2,Clear,2024-12-01
Electronic City,Monday,16,28,60,3,Clear,2024-12-01
Electronic City,Monday,17,22,72,4,Clear,2024-12-01
Electronic City,Monday,18,18,78,5,Clear,2024-12-01
Electronic City,Monday,19,22,70,4,Clear,2024-12-01
Electronic City,Monday,20,28,58,2,Clear,2024-12-01
Electronic City,Monday,21,35,42,1,Clear,2024-12-01
Electronic City,Monday,22,42,25,0,Clear,2024-12-01
Electronic City,Monday,23,48,15,0,Clear,2024-12-01
MG Road,Monday,0,42,28,0,Clear,2024-12-01
MG Road,Monday,1,45,22,0,Clear,2024-12-01
MG Road,Monday,2,48,18,0,Clear,2024-12-01
MG Road,Monday,3,48,18,0,Clear,2024-12-01
MG Road,Monday,4,45,22,0,Clear,2024-12-01
MG Road,Monday,5,40,32,1,Clear,2024-12-01
MG Road,Monday,6,32,52,2,Clear,2024-12-01
MG Road,Monday,7,25,68,3,Clear,2024-12-01
MG Road,Monday,8,15,85,5,Clear,2024-12-01
MG Road,Monday,9,20,78,4,Clear,2024-12-01
MG Road,Monday,10,28,60,3,Clear,2024-12-01
MG Road,Monday,11,32,52,2,Clear,2024-12-01
MG Road,Monday,12,35,48,2,Clear,2024-12-01
MG Road,Monday,13,33,50,2,Clear,2024-12-01
MG Road,Monday,14,30,58,3,Clear,2024-12-01
MG Road,Monday,15,28,62,3,Clear,2024-12-01
MG Road,Monday,16,25,68,4,Clear,2024-12-01
MG Road,Monday,17,18,82,5,Clear,2024-12-01
MG Road,Monday,18,12,88,6,Clear,2024-12-01
MG Road,Monday,19,15,85,5,Clear,2024-12-01
MG Road,Monday,20,22,72,4,Clear,2024-12-01
MG Road,Monday,21,30,55,2,Clear,2024-12-01
MG Road,Monday,22,38,38,1,Clear,2024-12-01
MG Road,Monday,23,42,28,0,Clear,2024-12-01
Indiranagar,Monday,0,45,20,0,Clear,2024-12-01
Indiranagar,Monday,1,48,15,0,Clear,2024-12-01
Indiranagar,Monday,2,50,12,0,Clear,2024-12-01
Indiranagar,Monday,3,50,12,0,Clear,2024-12-01
Indiranagar,Monday,4,48,18,0,Clear,2024-12-01
Indiranagar,Monday,5,42,28,0,Clear,2024-12-01
Indiranagar,Monday,6,35,45,1,Clear,2024-12-01
Indiranagar,Monday,7,28,60,2,Clear,2024-12-01
Indiranagar,Monday,8,18,80,4,Clear,2024-12-01
Indiranagar,Monday,9,22,72,3,Clear,2024-12-01
Indiranagar,Monday,10,30,55,2,Clear,2024-12-01
Indiranagar,Monday,11,35,48,2,Clear,2024-12-01
Indiranagar,Monday,12,38,42,1,Clear,2024-12-01
Indiranagar,Monday,13,35,45,2,Clear,2024-12-01
Indiranagar,Monday,14,32,52,2,Clear,2024-12-01
Indiranagar,Monday,15,30,58,3,Clear,2024-12-01
Indiranagar,Monday,16,28,62,3,Clear,2024-12-01
Indiranagar,Monday,17,22,75,4,Clear,2024-12-01
Indiranagar,Monday,18,15,85,5,Clear,2024-12-01
Indiranagar,Monday,19,18,80,4,Clear,2024-12-01
Indiranagar,Monday,20,25,68,3,Clear,2024-12-01
Indiranagar,Monday,21,32,52,2,Clear,2024-12-01
Indiranagar,Monday,22,40,35,1,Clear,2024-12-01
Indiranagar,Monday,23,45,22,0,Clear,2024-12-01
HSR Layout,Monday,0,48,15,0,Clear,2024-12-01
HSR Layout,Monday,1,50,12,0,Clear,2024-12-01
HSR Layout,Monday,2,50,10,0,Clear,2024-12-01
HSR Layout,Monday,3,50,10,0,Clear,2024-12-01
HSR Layout,Monday,4,48,15,0,Clear,2024-12-01
HSR Layout,Monday,5,43,25,0,Clear,2024-12-01
HSR Layout,Monday,6,36,42,1,Clear,2024-12-01
HSR Layout,Monday,7,28,58,2,Clear,2024-12-01
HSR Layout,Monday,8,20,75,4,Clear,2024-12-01
HSR Layout,Monday,9,24,68,3,Clear,2024-12-01
HSR Layout,Monday,10,32,52,2,Clear,2024-12-01
HSR Layout,Monday,11,36,45,2,Clear,2024-12-01
HSR Layout,Monday,12,38,40,1,Clear,2024-12-01
HSR Layout,Monday,13,36,42,2,Clear,2024-12-01
HSR Layout,Monday,14,33,48,2,Clear,2024-12-01
HSR Layout,Monday,15,30,55,3,Clear,2024-12-01
HSR Layout,Monday,16,28,60,3,Clear,2024-12-01
HSR Layout,Monday,17,22,72,4,Clear,2024-12-01
HSR Layout,Monday,18,16,82,5,Clear,2024-12-01
HSR Layout,Monday,19,20,75,4,Clear,2024-12-01
HSR Layout,Monday,20,26,65,3,Clear,2024-12-01
HSR Layout,Monday,21,33,50,2,Clear,2024-12-01
HSR Layout,Monday,22,40,32,1,Clear,2024-12-01
HSR Layout,Monday,23,46,18,0,Clear,2024-12-01
Marathahalli,Monday,0,46,18,0,Clear,2024-12-01
Marathahalli,Monday,1,48,15,0,Clear,2024-12-01
Marathahalli,Monday,2,50,12,0,Clear,2024-12-01
Marathahalli,Monday,3,50,12,0,Clear,2024-12-01
Marathahalli,Monday,4,46,20,0,Clear,2024-12-01
Marathahalli,Monday,5,40,32,1,Clear,2024-12-01
Marathahalli,Monday,6,32,52,2,Clear,2024-12-01
Marathahalli,Monday,7,24,68,3,Clear,2024-12-01
Marathahalli,Monday,8,16,82,5,Clear,2024-12-01
Marathahalli,Monday,9,20,78,4,Clear,2024-12-01
Marathahalli,Monday,10,28,62,3,Clear,2024-12-01
Marathahalli,Monday,11,32,55,2,Clear,2024-12-01
Marathahalli,Monday,12,35,48,2,Clear,2024-12-01
Marathahalli,Monday,13,33,50,2,Clear,2024-12-01
Marathahalli,Monday,14,30,58,3,Clear,2024-12-01
Marathahalli,Monday,15,28,62,3,Clear,2024-12-01
Marathahalli,Monday,16,24,70,4,Clear,2024-12-01
Marathahalli,Monday,17,18,80,5,Clear,2024-12-01
Marathahalli,Monday,18,14,85,6,Clear,2024-12-01
Marathahalli,Monday,19,18,80,5,Clear,2024-12-01
Marathahalli,Monday,20,24,70,3,Clear,2024-12-01
Marathahalli,Monday,21,32,52,2,Clear,2024-12-01
Marathahalli,Monday,22,38,38,1,Clear,2024-12-01
Marathahalli,Monday,23,44,22,0,Clear,2024-12-01
Hebbal,Monday,0,48,15,0,Clear,2024-12-01
Hebbal,Monday,1,50,12,0,Clear,2024-12-01
Hebbal,Monday,2,50,10,0,Clear,2024-12-01
Hebbal,Monday,3,50,10,0,Clear,2024-12-01
Hebbal,Monday,4,48,15,0,Clear,2024-12-01
Hebbal,Monday,5,42,25,0,Clear,2024-12-01
Hebbal,Monday,6,34,48,2,Clear,2024-12-01
Hebbal,Monday,7,26,65,3,Clear,2024-12-01
Hebbal,Monday,8,18,78,5,Clear,2024-12-01
Hebbal,Monday,9,22,72,4,Clear,2024-12-01
Hebbal,Monday,10,30,58,3,Clear,2024-12-01
Hebbal,Monday,11,34,50,2,Clear,2024-12-01
Hebbal,Monday,12,36,45,2,Clear,2024-12-01
Hebbal,Monday,13,34,48,2,Clear,2024-12-01
Hebbal,Monday,14,32,52,3,Clear,2024-12-01
Hebbal,Monday,15,30,58,3,Clear,2024-12-01
Hebbal,Monday,16,26,65,4,Clear,2024-12-01
Hebbal,Monday,17,20,75,5,Clear,2024-12-01
Hebbal,Monday,18,16,82,5,Clear,2024-12-01
Hebbal,Monday,19,20,75,4,Clear,2024-12-01
Hebbal,Monday,20,26,65,3,Clear,2024-12-01
Hebbal,Monday,21,34,48,2,Clear,2024-12-01
Hebbal,Monday,22,40,32,1,Clear,2024-12-01
Hebbal,Monday,23,46,18,0,Clear,2024-12-01"""
    df = pd.read_csv(StringIO(csv_data))
    df["hour"] = df["hour"].astype(int)
    df["avg_speed"] = df["avg_speed"].astype(float)
    df["congestion_level"] = df["congestion_level"].astype(float)
    df["incident_count"] = df["incident_count"].astype(int)
    st.sidebar.success("✅ Historical data loaded")
    return df

# === SIDEBAR ===
st.sidebar.title("🚦 Traffic Dashboard")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", [
    "📊 Dashboard", "📍 Live Hotspots", "🗺️ Advanced Route Planner",
    "📈 Area Predictions", "⚠️ Incidents", "📉 Analytics"
], key="page_selector")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Refresh Data", key="refresh_btn"):
    st.cache_data.clear()
    st.session_state.route_results = None
    st.session_state.last_calculation_time = None
    st.rerun()

# === PAGES ===
if page == "📊 Dashboard":
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

elif page == "📍 Live Hotspots":
    st.title("📍 Live Traffic Hotspots - Area Analysis")
    st.markdown("Analyze live traffic congestion in any Bangalore area with grid-based sampling")
    
    # Helper functions for Live Hotspots
    def calculate_bbox_hotspots(lat, lon, radius_km=2):
        """Calculate bounding box around a center point."""
        earth_radius = 6371.0
        
        lat_offset = (radius_km / earth_radius) * (180 / math.pi)
        lon_offset = (radius_km / earth_radius) * (180 / math.pi) / math.cos(lat * math.pi / 180)
        
        min_lat = lat - lat_offset
        max_lat = lat + lat_offset
        min_lon = lon - lon_offset
        max_lon = lon + lon_offset
        
        return min_lat, min_lon, max_lat, max_lon

    def generate_grid_points_hotspots(lat, lon, radius_km, grid_size=5):
        """Generate a grid of points within the radius for traffic sampling."""
        points = []
        
        # Calculate step size
        step_lat = (radius_km * 2) / grid_size / 111  # roughly 111 km per degree
        step_lon = (radius_km * 2) / grid_size / (111 * math.cos(lat * math.pi / 180))
        
        # Generate grid
        for i in range(grid_size):
            for j in range(grid_size):
                point_lat = lat - radius_km/111 + (i * step_lat)
                point_lon = lon - radius_km/(111 * math.cos(lat * math.pi / 180)) + (j * step_lon)
                
                # Check if point is within circle
                distance = math.sqrt((point_lat - lat)**2 * 111**2 + 
                                   (point_lon - lon)**2 * (111 * math.cos(lat * math.pi / 180))**2)
                if distance <= radius_km:
                    points.append((point_lat, point_lon))
        
        return points

    @st.cache_data(ttl=180)
    def fetch_flow_data_bulk_hotspots(points, api_key):
        """Fetch traffic flow data for multiple points."""
        flow_data = []
        
        for point_lat, point_lon in points:
            url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json"
            params = {
                "key": api_key,
                "point": f"{point_lat},{point_lon}"
            }
            
            try:
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json().get("flowSegmentData", {})
                    if data:
                        current_speed = data.get("currentSpeed", 0)
                        free_flow_speed = data.get("freeFlowSpeed", 1)
                        
                        # Calculate congestion
                        if free_flow_speed > 0:
                            congestion = ((free_flow_speed - current_speed) / free_flow_speed) * 100
                        else:
                            congestion = 0
                        
                        flow_data.append({
                            'lat': point_lat,
                            'lon': point_lon,
                            'current_speed': current_speed,
                            'free_flow_speed': free_flow_speed,
                            'congestion': congestion
                        })
            except:
                continue
        
        return flow_data

    @st.cache_data(ttl=180)
    def fetch_traffic_incidents_hotspots(bbox, api_key):
        """Fetch traffic incidents within bounding box."""
        url = "https://api.tomtom.com/traffic/services/5/incidentDetails"
        params = {
            "key": api_key,
            "bbox": bbox,
            "timeValidityFilter": "present"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get("incidents", [])
        except:
            pass
        return []

    def get_color_for_congestion_hotspots(congestion):
        """Determine color based on congestion level."""
        if congestion < 20:
            return 'green'
        elif congestion < 40:
            return 'lightgreen'
        elif congestion < 60:
            return 'orange'
        else:
            return 'red'

    @st.cache_data(show_spinner=False)
    def geocode_place_hotspots(place):
        url = f"https://api.tomtom.com/search/2/geocode/{place}, Bengaluru.json"
        params = {"key": TOMTOM_API_KEY, "limit": 1}
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        pos = data["results"][0]["position"]
        return pos["lat"], pos["lon"]
    
    # Controls
    col_ctrl1, col_ctrl2 = st.columns([2, 3])
    
    with col_ctrl1:
        area_name_hotspots = st.text_input(
            "📍 Area name (Bengaluru only)",
            value="Koramangala",
            key="hotspot_area"
        )
        
        radius_km_hotspots = st.slider(
            "📏 Coverage radius (km)",
            min_value=0.5,
            max_value=3.0,
            value=1.5,
            step=0.5,
            key="hotspot_radius"
        )
    
    with col_ctrl2:
        grid_density_hotspots = st.slider(
            "🎯 Traffic sampling density",
            min_value=3,
            max_value=8,
            value=5,
            help="Higher values = more traffic data points but slower loading",
            key="hotspot_density"
        )
        
        col_check1, col_check2 = st.columns(2)
        with col_check1:
            show_incidents_hotspots = st.checkbox("Show Traffic Incidents", value=True, key="hotspot_incidents")
        with col_check2:
            show_heatmap_hotspots = st.checkbox("Show Congestion Heatmap", value=True, key="hotspot_heatmap")
    
    st.info(f"Analyzing traffic within {radius_km_hotspots} km radius with {grid_density_hotspots}x{grid_density_hotspots} sampling grid.")
    
    # Geocode
    try:
        lat_hotspots, lon_hotspots = geocode_place_hotspots(area_name_hotspots)
        st.success(f"📌 Location found: {area_name_hotspots} ({lat_hotspots:.4f}, {lon_hotspots:.4f})")
    except Exception as e:
        st.error("Failed to locate area. Please try another name.")
        st.stop()
    
    # Calculate bounding box
    min_lat_h, min_lon_h, max_lat_h, max_lon_h = calculate_bbox_hotspots(lat_hotspots, lon_hotspots, radius_km_hotspots)
    bbox_string_h = f"{min_lon_h},{min_lat_h},{max_lon_h},{max_lat_h}"
    
    # Generate sampling grid
    grid_points_h = generate_grid_points_hotspots(lat_hotspots, lon_hotspots, radius_km_hotspots, grid_density_hotspots)
    
    # Fetch data
    with st.spinner(f"Fetching traffic data from {len(grid_points_h)} sampling points..."):
        flow_data_h = fetch_flow_data_bulk_hotspots(grid_points_h, TOMTOM_API_KEY)
        if show_incidents_hotspots:
            incidents_h = fetch_traffic_incidents_hotspots(bbox_string_h, TOMTOM_API_KEY)
        else:
            incidents_h = []
    
    # Create map
    m_hotspots = folium.Map(
        location=[lat_hotspots, lon_hotspots],
        zoom_start=15,
        tiles="CartoDB positron",
        control_scale=True
    )
    
    # Coverage area circle
    folium.Circle(
        location=[lat_hotspots, lon_hotspots],
        radius=radius_km_hotspots * 1000,
        color='blue',
        fill=True,
        fillColor='lightblue',
        fillOpacity=0.1,
        weight=2,
        popup=f'{radius_km_hotspots} km coverage radius',
        tooltip=f'Coverage area: {radius_km_hotspots} km'
    ).add_to(m_hotspots)
    
    # Traffic flow markers
    if flow_data_h:
        for data in flow_data_h:
            congestion = data['congestion']
            color = get_color_for_congestion_hotspots(congestion)
            
            # Only show markers with significant data
            if data['current_speed'] > 0:
                folium.CircleMarker(
                    location=[data['lat'], data['lon']],
                    radius=6,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7,
                    weight=1,
                    popup=f"""
                        <b>Traffic Flow</b><br>
                        Current Speed: {data['current_speed']} km/h<br>
                        Free Flow: {data['free_flow_speed']} km/h<br>
                        Congestion: {int(congestion)}%
                    """,
                    tooltip=f"{int(congestion)}% congestion"
                ).add_to(m_hotspots)
        
        # Add heatmap if enabled
        if show_heatmap_hotspots and len(flow_data_h) > 0:
            from folium import plugins
            
            heat_data = [[d['lat'], d['lon'], d['congestion']/100] for d in flow_data_h if d['current_speed'] > 0]
            
            if heat_data:
                plugins.HeatMap(
                    heat_data,
                    min_opacity=0.2,
                    max_opacity=0.6,
                    radius=25,
                    blur=20,
                    gradient={0.0: 'green', 0.5: 'yellow', 0.75: 'orange', 1.0: 'red'}
                ).add_to(m_hotspots)
    
    # Traffic incidents
    if show_incidents_hotspots and incidents_h:
        for inc in incidents_h:
            coords = inc["geometry"]["coordinates"]
            
            if isinstance(coords[0], list):
                inc_lon, inc_lat = coords[0][0], coords[0][1]
            else:
                inc_lon, inc_lat = coords[0], coords[1]
            
            inc_lat, inc_lon = float(inc_lat), float(inc_lon)
            
            # Only show if within radius
            distance = math.sqrt((inc_lat - lat_hotspots)**2 * 111**2 + 
                               (inc_lon - lon_hotspots)**2 * (111 * math.cos(lat_hotspots * math.pi / 180))**2)
            
            if distance <= radius_km_hotspots:
                description = inc["properties"].get("description", "Traffic incident")
                delay = inc["properties"].get("delay", 0)
                
                folium.Marker(
                    location=[inc_lat, inc_lon],
                    icon=folium.Icon(color='red', icon='exclamation-triangle', prefix='fa'),
                    popup=f"<b>⚠️ {description}</b><br>Delay: {delay//60} min",
                    tooltip="Traffic Incident"
                ).add_to(m_hotspots)
    
    # Center marker
    folium.Marker(
        [lat_hotspots, lon_hotspots],
        tooltip=f"{area_name_hotspots} (Center)",
        icon=folium.Icon(color="darkblue", icon="info-sign"),
        popup=f"<b>{area_name_hotspots}</b><br>Center Point"
    ).add_to(m_hotspots)
    
    # Render map
    st_folium(m_hotspots, width=None, height=650, key="hotspots_map")
    
    # Stats
    if flow_data_h:
        avg_congestion_h = sum([d['congestion'] for d in flow_data_h]) / len(flow_data_h)
        avg_speed_h = sum([d['current_speed'] for d in flow_data_h if d['current_speed'] > 0]) / max(1, len([d for d in flow_data_h if d['current_speed'] > 0]))
        high_congestion_count_h = len([d for d in flow_data_h if d['congestion'] > 60])
    else:
        avg_congestion_h = 0
        avg_speed_h = 0
        high_congestion_count_h = 0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📍 Area", area_name_hotspots)
    with col2:
        st.metric("📏 Radius", f"{radius_km_hotspots} km")
    with col3:
        st.metric("📊 Avg Congestion", f"{int(avg_congestion_h)}%")
    with col4:
        st.metric("🚗 Avg Speed", f"{int(avg_speed_h)} km/h")
    with col5:
        st.metric("🔴 Hotspots", high_congestion_count_h)
    
    # Congestion breakdown
    if flow_data_h:
        st.markdown("### 🎯 Congestion Breakdown")
        
        green_count = len([d for d in flow_data_h if d['congestion'] < 20])
        yellow_count = len([d for d in flow_data_h if 20 <= d['congestion'] < 40])
        orange_count = len([d for d in flow_data_h if 40 <= d['congestion'] < 60])
        red_count = len([d for d in flow_data_h if d['congestion'] >= 60])
        
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("🟢 Free Flow", green_count)
        col_b.metric("🟡 Light", yellow_count)
        col_c.metric("🟠 Moderate", orange_count)
        col_d.metric("🔴 Heavy", red_count)
    else:
        st.warning("⚠️ No traffic data available for this area. Try a different location or increase the radius.")
    
    # Incident details
    if show_incidents_hotspots and incidents_h:
        with st.expander(f"⚠️ Traffic Incidents ({len(incidents_h)} found)"):
            for idx, inc in enumerate(incidents_h, 1):
                description = inc["properties"].get("description", "Traffic incident")
                delay = inc["properties"].get("delay", 0)
                st.write(f"**{idx}.** {description} - Delay: {delay//60} min")
    
    # Legend
    with st.expander("ℹ️ How to interpret the map"):
        st.markdown(
            f"""
            **Circle Markers (Traffic Sampling Points):**
            - **🟢 Green** — Free flow (<20% congestion)
            - **🟡 Yellow** — Light traffic (20-40% congestion)
            - **🟠 Orange** — Moderate congestion (40-60% congestion)
            - **🔴 Red** — Heavy congestion (>60% congestion)
            
            **Other Elements:**
            - **🔵 Blue Circle** — {radius_km_hotspots} km coverage boundary
            - **🔷 Dark Blue Marker** — Center of selected area
            - **⚠️ Red Warning Markers** — Traffic incidents/accidents
            - **Heat Overlay** — Overall congestion density (if enabled)
            
            **Sampling Grid:** {grid_density_hotspots}x{grid_density_hotspots} = {len(grid_points_h)} points analyzed
            
            Data updates every 3 minutes from TomTom Traffic API.
            """
        )

elif page == "🗺️ Advanced Route Planner":
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

elif page == "📈 Area Predictions":
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

elif page == "⚠️ Incidents":
    st.title("⚠️ Traffic Incidents - Bangalore")
    
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

elif page == "📉 Analytics":
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

else:
    st.title(f"{page}")
    st.info("-------------------")