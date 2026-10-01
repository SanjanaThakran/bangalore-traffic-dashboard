import pandas as pd
import requests
import streamlit as st
from io import StringIO
from modules.config import TOMTOM_API_KEY

def calculate_calories_burned(distance_km, mode):
    """Calculate estimated calories burned for active transport modes"""
    if mode == 'pedestrian':
        return int(distance_km * 50)
    elif mode == 'bicycle':
        return int(distance_km * 40)
    return 0

def calculate_carbon_footprint(distance_km, mode):
    """Calculate CO2 emissions in grams"""
    emissions_per_km = {
        'car': 120,
        'motorcycle': 80,
        'bicycle': 0,
        'pedestrian': 0,
        'public_transport': 30
    }
    return round(distance_km * emissions_per_km.get(mode, 0), 1)

def estimate_cost(distance_km, mode):
    """Estimate travel cost in INR"""
    cost_per_km = {
        'car': 8,
        'motorcycle': 3,
        'bicycle': 0,
        'pedestrian': 0,
        'public_transport': 2
    }
    return round(distance_km * cost_per_km.get(mode, 0), 2)

def calculate_congestion_score(current_speed, free_flow_speed):
    """Calculate congestion percentage score (1 to 100)"""
    if free_flow_speed == 0:
        return 0
    drop = free_flow_speed - current_speed
    percent = (drop / free_flow_speed) * 100
    return min(100, max(1, percent))

def predict_area_congestion(area_name, lat, lon):
    """Fetch live speed data and return predicted congestion status for an area"""
    try:
        response = requests.get(
            "https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json",
            params={"key": TOMTOM_API_KEY, "point": f"{lat},{lon}"},
            timeout=5
        )
        if response.status_code == 200:
            seg = response.json().get("flowSegmentData", {})
            current_speed = int(seg.get("currentSpeed", 0))
            free_flow_speed = int(seg.get("freeFlowSpeed", 1))
            congestion = calculate_congestion_score(current_speed, free_flow_speed)
            return {
                "area": area_name,
                "current_speed": current_speed,
                "free_flow_speed": free_flow_speed,
                "congestion": congestion,
                "status": "High" if congestion > 60 else "Moderate" if congestion > 30 else "Low"
            }
    except Exception:
        pass
    return None

@st.cache_data(ttl=3600)
def load_historical_data():
    """Load sample historical traffic dataset for analytics"""
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
Koramangala,Monday,19,18,75,4,Clear,2024-12-01
Koramangala,Monday,20,25,60,2,Clear,2024-12-01
Koramangala,Monday,21,35,40,1,Clear,2024-12-01
Koramangala,Monday,22,40,25,0,Clear,2024-12-01
Koramangala,Monday,23,42,20,0,Clear,2024-12-01
Whitefield,Monday,8,12,88,5,Clear,2024-12-01
Whitefield,Monday,9,15,82,4,Clear,2024-12-01
Whitefield,Monday,18,10,92,6,Clear,2024-12-01
Electronic City,Monday,8,15,85,3,Clear,2024-12-01
Electronic City,Monday,18,14,88,4,Clear,2024-12-01
Hebbal,Monday,8,16,82,4,Clear,2024-12-01
Hebbal,Monday,18,12,90,5,Clear,2024-12-01
Marathahalli,Monday,8,10,92,5,Clear,2024-12-01
Marathahalli,Monday,18,8,95,6,Clear,2024-12-01
"""
    return pd.read_csv(StringIO(csv_data))
