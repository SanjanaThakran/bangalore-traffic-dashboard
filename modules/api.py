import requests
import streamlit as st
from modules.config import TOMTOM_API_KEY, BANGALORE_BBOX, INCIDENT_CATEGORIES, TRANSPORT_MODES
from modules.analytics import (
    calculate_congestion_score,
    calculate_calories_burned,
    calculate_carbon_footprint,
    estimate_cost
)

def categorize_incident(description):
    """Categorize incident based on description keywords"""
    description_lower = description.lower()
    for category, details in INCIDENT_CATEGORIES.items():
        for keyword in details['keywords']:
            if keyword in description_lower:
                return category
    return 'OTHER'

def geocode_place(place):
    """Geocode a location string within Bengaluru"""
    url = f"https://api.tomtom.com/search/2/geocode/{place}, Bengaluru.json"
    params = {"key": TOMTOM_API_KEY, "limit": 1}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data.get("results"):
        raise ValueError("No results found for this location")
    pos = data["results"][0]["position"]
    return pos["lat"], pos["lon"]

def parse_coordinates(coord_string):
    """Parse lat,lon coordinate string"""
    try:
        parts = coord_string.replace(" ", "").split(",")
        if len(parts) != 2:
            return None
        lat, lon = float(parts[0]), float(parts[1])
        if not (12.5 <= lat <= 13.5 and 77.0 <= lon <= 78.0):
            st.warning("⚠️ Coordinates outside Bangalore region")
        return (lat, lon)
    except Exception:
        return None

def fetch_live_traffic_incidents():
    """Fetch live traffic incidents from TomTom API"""
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
            except Exception:
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

def fetch_routes_with_geometry(origin_coords, dest_coords, api_key, max_alternatives=2):
    """Fetch driving routes with traffic data and route geometries"""
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

def fetch_multimodal_routes(origin_coords, dest_coords, api_key, selected_modes):
    """Fetch routes for multiple transport modes (car, walking, cycling)"""
    origin_str = f"{origin_coords[0]},{origin_coords[1]}"
    dest_str = f"{dest_coords[0]},{dest_coords[1]}"
    all_routes = []
    
    for mode_key in selected_modes:
        if mode_key not in TRANSPORT_MODES:
            continue
        mode_info = TRANSPORT_MODES[mode_key]
        try:
            params = {
                "key": api_key,
                "travelMode": mode_info['api_mode'],
                "traffic": "true" if mode_key == 'car' else "false",
                "routeType": "fastest"
            }
            url = f"https://api.tomtom.com/routing/1/calculateRoute/{origin_str}:{dest_str}/json"
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                st.warning(f"Could not fetch route for {mode_info['name']}")
                continue
                
            data = response.json()
            if not data.get("routes"):
                continue
                
            route = data["routes"][0]
            summary = route["summary"]
            
            route_coords = []
            for leg in route.get("legs", []):
                for point in leg.get("points", []):
                    lat = point.get("latitude")
                    lon = point.get("longitude")
                    if lat is not None and lon is not None:
                        route_coords.append((lat, lon))
            
            distance_km = round(summary["lengthInMeters"] / 1000, 2)
            travel_time_sec = summary.get("travelTimeInSeconds", 0)
            traffic_delay_sec = summary.get("trafficDelayInSeconds", 0) if mode_key == 'car' else 0
            
            calories = calculate_calories_burned(distance_km, mode_key)
            carbon = calculate_carbon_footprint(distance_km, mode_key)
            cost = estimate_cost(distance_km, mode_key)
            
            all_routes.append({
                "mode": mode_key,
                "mode_name": mode_info['name'],
                "icon": mode_info['icon'],
                "color": mode_info['color'],
                "distance_km": distance_km,
                "travel_time_min": round(travel_time_sec / 60, 1),
                "traffic_delay_min": round(traffic_delay_sec / 60, 1),
                "total_time_min": round((travel_time_sec + traffic_delay_sec) / 60, 1),
                "calories_burned": calories,
                "co2_emissions": carbon,
                "estimated_cost": cost,
                "coordinates": route_coords,
                "avg_speed": round((distance_km / (travel_time_sec / 3600)) if travel_time_sec > 0 else 0, 1)
            })
        except Exception as e:
            st.warning(f"Could not fetch route for {mode_info['name']}: {str(e)}")
            continue
            
    all_routes.sort(key=lambda x: x['total_time_min'])
    return all_routes
