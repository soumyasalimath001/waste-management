import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration settings for the application"""
    
    # API Keys
    OPENROUTESERVICE_API_KEY = os.getenv('ORS_API_KEY', '')
    
    # Data paths
    BIN_LOCATIONS_PATH = 'data/bin_locations.csv'
    DISTANCE_MATRIX_PATH = 'data/distance_matrix.csv'
    
    # Simulation parameters
    DEFAULT_NUM_BINS = 50
    DEFAULT_FILL_THRESHOLD = 80  # Collect bins above 80% full [citation:6]
    
    # Vehicle parameters
    TRUCK_CAPACITY = 1000  # kg [citation:1]
    BIN_CAPACITY = 100  # kg
    
    # Optimization weights
    DISTANCE_WEIGHT = 0.5
    WASTE_WEIGHT = 0.5

config = Config()