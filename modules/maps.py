import folium
import plotly.graph_objects as go

def create_gauge_chart(value, max_value, title):
    """Create a speed/congestion gauge chart using Plotly"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title, 'font': {'size': 16}},
        gauge={
            'axis': {'range': [None, max_value]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, max_value/3], 'color': "lightgreen"},
                {'range': [max_value/3, 2*max_value/3], 'color': "yellow"},
                {'range': [2*max_value/3, max_value], 'color': "red"}
            ],
            'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': value}
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
    return fig

def create_route_map(origin_coords, dest_coords, routes):
    """Create a Folium map displaying driving routes with traffic info"""
    center_lat = (origin_coords[0] + dest_coords[0]) / 2
    center_lon = (origin_coords[1] + dest_coords[1]) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    
    colors = ['#2E86DE', '#FF6B6B', '#95A5A6', '#F39C12', '#9B59B6']
    
    for idx, route in enumerate(routes):
        if not route["coordinates"]:
            continue
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
            locations=route["coordinates"],
            color=color,
            weight=weight,
            opacity=opacity,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{route['name']}: {route['distance_km']} km, {route['total_time_min']} min"
        ).add_to(m)
        
        if len(route["coordinates"]) > 0:
            mid_point = route["coordinates"][len(route["coordinates"]) // 2]
            icon_html = f"<div style='background-color:{color}; color:white; font-weight:bold; padding:3px 8px; border-radius:10px; border:2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);'>{idx+1}</div>"
            folium.Marker(location=mid_point, icon=folium.DivIcon(html=icon_html)).add_to(m)
    
    folium.Marker(
        origin_coords,
        popup=f"<b>🟢 Origin</b><br>{origin_coords[0]:.4f}, {origin_coords[1]:.4f}",
        tooltip="Origin",
        icon=folium.Icon(color='green', icon='play', prefix='fa')
    ).add_to(m)
    
    folium.Marker(
        dest_coords,
        popup=f"<b>🔴 Destination</b><br>{dest_coords[0]:.4f}, {dest_coords[1]:.4f}",
        tooltip="Destination",
        icon=folium.Icon(color='red', icon='flag-checkered', prefix='fa')
    ).add_to(m)
    
    all_coords = [origin_coords, dest_coords]
    for route in routes:
        all_coords.extend(route["coordinates"])
    if len(all_coords) > 2:
        m.fit_bounds(all_coords)
    return m

def create_multimodal_map(origin_coords, dest_coords, routes):
    """Create a Folium map displaying multimodal routes (driving, walking, cycling)"""
    center_lat = (origin_coords[0] + dest_coords[0]) / 2
    center_lon = (origin_coords[1] + dest_coords[1]) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    
    for idx, route in enumerate(routes):
        if not route["coordinates"]:
            continue
            
        color = route['color']
        weight = 5 if idx == 0 else 3
        opacity = 0.8 if idx == 0 else 0.6
        
        popup_html = f"""
        <div style='font-family: Arial; min-width: 220px;'>
            <h4 style='margin: 0 0 10px 0; color: {color};'>{route['icon']} {route['mode_name']}</h4>
            <hr style='margin: 5px 0;'>
            <b>📏 Distance:</b> {route['distance_km']} km<br>
            <b>⏱️ Travel Time:</b> {route['total_time_min']} min<br>
            <b>💰 Est. Cost:</b> ₹{route['estimated_cost']}<br>
            <b>🌱 CO₂:</b> {route['co2_emissions']}g<br>
            {'<b>🔥 Calories:</b> ' + str(route['calories_burned']) + ' kcal<br>' if route['calories_burned'] > 0 else ''}
            <b>🚀 Avg Speed:</b> {route['avg_speed']} km/h
        </div>
        """
        
        folium.PolyLine(
            locations=route["coordinates"],
            color=color,
            weight=weight,
            opacity=opacity,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{route['icon']} {route['mode_name']}: {route['total_time_min']} min"
        ).add_to(m)
        
        if len(route["coordinates"]) > 0:
            mid_point = route["coordinates"][len(route["coordinates"]) // 2]
            icon_html = f"<div style='font-size: 20px;'>{route['icon']}</div>"
            folium.Marker(
                location=mid_point,
                icon=folium.DivIcon(html=icon_html)
            ).add_to(m)
    
    folium.Marker(
        origin_coords,
        popup=f"<b>🟢 Origin</b><br>{origin_coords[0]:.4f}, {origin_coords[1]:.4f}",
        tooltip="Origin",
        icon=folium.Icon(color='green', icon='play', prefix='fa')
    ).add_to(m)
    
    folium.Marker(
        dest_coords,
        popup=f"<b>🔴 Destination</b><br>{dest_coords[0]:.4f}, {dest_coords[1]:.4f}",
        tooltip="Destination",
        icon=folium.Icon(color='red', icon='flag-checkered', prefix='fa')
    ).add_to(m)
    
    all_coords = [origin_coords, dest_coords]
    for route in routes:
        all_coords.extend(route["coordinates"])
    if len(all_coords) > 2:
        m.fit_bounds(all_coords)
    
    return m
