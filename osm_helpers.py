import requests
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
import time

class OSMDataFetcher:
    """
    Fetches real road network data from OpenStreetMap [citation:2]
    """
    
    def __init__(self):
        self.geolocator = Nominatim(user_agent="waste_route_optimizer")
    
    def get_city_bounds(self, city_name: str) -> tuple:
        """
        Get bounding box for a city
        """
        location = self.geolocator.geocode(city_name)
        if location:
            return location.raw['boundingbox']
        return None
    
    def fetch_roads_in_area(self, bbox: tuple) -> dict:
        """
        Fetch road network within bounding box using Overpass API
        """
        overpass_url = "http://overpass-api.de/api/interpreter"
        
        # Overpass QL query for roads
        overpass_query = f"""
        [out:json];
        (
          way["highway"]({bbox[0]},{bbox[2]},{bbox[1]},{bbox[3]});
        );
        out body;
        >;
        out skel qt;
        """
        
        response = requests.get(overpass_url, params={'data': overpass_query})
        
        if response.status_code == 200:
            return response.json()
        return None
    
    def geocode_address(self, address: str) -> tuple:
        """
        Convert address to coordinates
        """
        try:
            location = self.geolocator.geocode(address)
            if location:
                return (location.latitude, location.longitude)
        except:
            pass
        return None

class DistanceCalculator:
    """
    Calculate real road distances using OSRM or OpenRouteService
    """
    
    def __init__(self, service='osrm'):
        self.service = service
        
    def get_osrm_distance(self, coord1: tuple, coord2: tuple) -> float:
        """
        Get road distance using OSRM
        """
        # OSRM public instance
        url = f"http://router.project-osrm.org/route/v1/driving/{coord1[1]},{coord1[0]};{coord2[1]},{coord2[0]}"
        
        params = {
            'overview': 'false',
            'geometries': 'geojson'
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['routes']:
                    # Distance in meters, convert to km
                    return data['routes'][0]['distance'] / 1000
        except:
            pass
        
        # Fallback to geodesic distance
        from geopy.distance import geodesic
        return geodesic(coord1, coord2).km