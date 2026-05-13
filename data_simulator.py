import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

class BinDataSimulator:
    """
    Simulates smart bin data when real IoT data isn't available [citation:6]
    """
    
    def __init__(self, num_bins=50):
        self.num_bins = num_bins
        self.bins = None
        self.generate_bins()
    
    def generate_bins(self):
        """Generate random bin locations with realistic patterns"""
        
        # City center coordinates (example: Chandigarh, India) [citation:1]
        center_lat, center_lon = 30.7333, 76.7794
        
        bins = []
        for i in range(self.num_bins):
            # Generate bins with clustered patterns (residential areas)
            if random.random() < 0.7:
                # Clustered bins (residential/commercial areas)
                lat_offset = np.random.normal(0, 0.01)
                lon_offset = np.random.normal(0, 0.01)
            else:
                # Scattered bins (rural/sparse areas)
                lat_offset = np.random.uniform(-0.05, 0.05)
                lon_offset = np.random.uniform(-0.05, 0.05)
            
            bin_data = {
                'bin_id': f'BIN_{i:03d}',
                'latitude': center_lat + lat_offset,
                'longitude': center_lon + lon_offset,
                'capacity': 100,  # kg
                'zone': random.choice(['Residential', 'Commercial', 'Industrial', 'Park']),
                'bin_type': random.choice(['General', 'Recyclable', 'Organic'])
            }
            bins.append(bin_data)
        
        self.bins = pd.DataFrame(bins)
        return self.bins
    
    def simulate_fill_levels(self, time_of_day=None):
        """
        Simulate realistic fill levels based on time patterns [citation:8]
        """
        if self.bins is None:
            self.generate_bins()
        
        df = self.bins.copy()
        
        # Base fill levels with random variation
        base_fill = np.random.uniform(20, 90, len(df))
        
        # Time-based adjustments
        if time_of_day is None:
            time_of_day = datetime.now().hour
        
        # Residential areas fill more in evenings
        residential_mask = df['zone'] == 'Residential'
        if 18 <= time_of_day <= 22:  # Evening peak
            base_fill[residential_mask] += np.random.uniform(10, 30, residential_mask.sum())
        elif 9 <= time_of_day <= 17:  # Work hours
            base_fill[~residential_mask] += np.random.uniform(5, 20, (~residential_mask).sum())
        
        # Commercial areas fill during business hours
        commercial_mask = df['zone'] == 'Commercial'
        if 8 <= time_of_day <= 18:
            base_fill[commercial_mask] += np.random.uniform(15, 35, commercial_mask.sum())
        
        # Add noise and clip to valid range
        noise = np.random.normal(0, 5, len(df))
        df['fill_percentage'] = np.clip(base_fill + noise, 0, 100)
        df['fill_level_kg'] = (df['fill_percentage'] / 100) * df['capacity']
        
        # Mark bins needing collection
        df['needs_collection'] = df['fill_percentage'] >= 80  # 80% threshold [citation:6]
        
        return df
    
    def update_bin_status(self, bin_id, new_fill_level):
        """Update individual bin status after collection"""
        # In a real system, this would come from IoT sensors
        pass