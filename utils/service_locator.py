"""
Service station locator for the Eonix insurance platform.
Finds actual repair shops near the customer's location.
"""
import os
import logging
import requests
import json
import math
from typing import Dict, List, Any, Optional
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import googlemaps

# Configure logger
logger = logging.getLogger(__name__)

class ServiceLocator:
    """
    Locates repair service stations near a given location.
    Uses geocoding and distance calculations to find closest service options.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the service locator.
        
        Args:
            api_key: API key for mapping service (defaults to env var MAPS_API_KEY)
        """
        self.api_key = api_key or os.environ.get('MAPS_API_KEY')
        self.service_stations_file = os.path.join(os.path.dirname(__file__), '../data/service_stations.json')
        
        # Initialize Google Maps client
        if self.api_key:
            self.gmaps = googlemaps.Client(key=self.api_key)
        else:
            logger.warning("No Maps API key provided, directions functionality will be limited")
            self.gmaps = None
            
        # Load service stations from JSON file
        self.service_stations = self._load_service_stations()
        
        # Set up geocoder
        self.geocoder = Nominatim(user_agent="eonix_insurance_app")
        
        logger.info("Service station locator initialized")
    
    def _load_service_stations(self) -> List[Dict[str, Any]]:
        """
        Load service stations from the data file.
        
        Returns:
            List of service stations with location data
        """
        try:
            if os.path.exists(self.service_stations_file):
                with open(self.service_stations_file, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Service stations file not found: {self.service_stations_file}")
                return []
        except Exception as e:
            logger.error(f"Error loading service stations: {e}")
            return []
    
    def find_nearby_stations(self, location: str, max_distance: float = 25.0, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find service stations near the given location.
        
        Args:
            location: Location string (address, city, zip code)
            max_distance: Maximum distance in miles
            limit: Maximum number of results to return
            
        Returns:
            List of nearby service stations with distance information
        """
        try:
            # Geocode the input location
            location_data = self.geocoder.geocode(location)
            
            if not location_data:
                logger.warning(f"Could not geocode location: {location}")
                return []
            
            user_coords = (location_data.latitude, location_data.longitude)
            
            # Find stations within max_distance
            nearby_stations = []
            
            for station in self.service_stations:
                station_coords = (station['latitude'], station['longitude'])
                
                # Calculate distance
                distance = geodesic(user_coords, station_coords).miles
                
                if distance <= max_distance:
                    # Add distance to station data
                    station_copy = station.copy()
                    station_copy['distance_miles'] = round(distance, 1)
                    station_copy['directions_link'] = self._get_directions_link(user_coords, station_coords)
                    nearby_stations.append(station_copy)
            
            # Sort by distance and limit results
            nearby_stations.sort(key=lambda x: x['distance_miles'])
            return nearby_stations[:limit]
            
        except Exception as e:
            logger.error(f"Error finding nearby service stations: {e}")
            return []
    
    def _get_directions_link(self, from_coords: tuple, to_coords: tuple) -> str:
        """
        Generate a Google Maps directions link.
        
        Args:
            from_coords: Starting coordinates (latitude, longitude)
            to_coords: Destination coordinates (latitude, longitude)
            
        Returns:
            URL for directions
        """
        return f"https://www.google.com/maps/dir/{from_coords[0]},{from_coords[1]}/{to_coords[0]},{to_coords[1]}"
    
    def get_station_by_id(self, station_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a service station by its ID.
        
        Args:
            station_id: Unique identifier for the service station
            
        Returns:
            Service station data or None if not found
        """
        for station in self.service_stations:
            if station.get('id') == station_id:
                return station
        
        return None 