# API & Region Configuration
TOMTOM_API_KEY = "bZzH6OoOH5IciZ0rYXQ2QElpoWVzTseA"
BANGALORE_BBOX = "77.48,12.82,77.75,13.12"
BANGALORE_CENTER = [12.9716, 77.5946]

BANGALORE_AREAS = {
    'Koramangala': [12.9352, 77.6245],
    'Whitefield': [12.9698, 77.7499],
    'Electronic City': [12.8399, 77.6770],
    'MG Road': [12.9750, 77.6061],
    'Indiranagar': [12.9719, 77.6412],
    'HSR Layout': [12.9116, 77.6473],
    'Marathahalli': [12.9591, 77.6974],
    'Hebbal': [13.0358, 77.5970],
    'Jayanagar': [12.9250, 77.5838],
    'BTM Layout': [12.9165, 77.6101],
    'Yelahanka': [13.1007, 77.5963],
    'Malleshwaram': [13.0029, 77.5703]
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

TRANSPORT_MODES = {
    'car': {
        'name': 'Driving',
        'icon': '🚗',
        'color': '#2E86DE',
        'avg_speed': 30,
        'api_mode': 'car'
    },
    'pedestrian': {
        'name': 'Walking',
        'icon': '🚶',
        'color': '#27AE60',
        'avg_speed': 5,
        'api_mode': 'pedestrian'
    },
    'bicycle': {
        'name': 'Cycling',
        'icon': '🚴',
        'color': '#F39C12',
        'avg_speed': 15,
        'api_mode': 'bicycle'
    }
}
