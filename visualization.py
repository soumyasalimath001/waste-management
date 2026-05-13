import folium
from streamlit_folium import folium_static
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import streamlit as st

class MapVisualizer:
    """
    Creates interactive maps and charts for waste collection visualization
    """
    
    def __init__(self):
        self.map = None
    
    def create_base_map(self, center_lat=30.7333, center_lon=76.7794, zoom=13):
        """Create base Folium map"""
        self.map = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom,
            tiles='OpenStreetMap'  # Using OpenStreetMap tiles [citation:5]
        )
        return self.map
    
    def add_bin_markers(self, bins_df: pd.DataFrame):
        """
        Add bin markers colored by fill level [citation:8]
        Blue: <50%, Yellow: 50-80%, Red: >80%
        """
        if self.map is None:
            self.create_base_map()
        
        for _, bin_data in bins_df.iterrows():
            # Determine color based on fill level
            fill = bin_data['fill_percentage']
            if fill < 50:
                color = 'blue'
                icon = 'info-sign'
            elif fill < 80:
                color = 'orange'
                icon = 'warning-sign'
            else:
                color = 'red'
                icon = 'exclamation-sign'
            
            # Create popup text
            popup_text = f"""
            <b>Bin ID:</b> {bin_data['bin_id']}<br>
            <b>Fill Level:</b> {fill:.1f}%<br>
            <b>Zone:</b> {bin_data['zone']}<br>
            <b>Type:</b> {bin_data['bin_type']}<br>
            <b>Needs Collection:</b> {bin_data['needs_collection']}
            """
            
            folium.Marker(
                location=[bin_data['latitude'], bin_data['longitude']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=f"Bin {bin_data['bin_id']}: {fill:.1f}%",
                icon=folium.Icon(color=color, icon=icon)
            ).add_to(self.map)
    
    def add_route(self, route_points: list, color: str = 'green', 
                  truck_id: int = 0, weight: int = 5):
        """
        Add optimized route to map [citation:5][citation:6]
        """
        if self.map is None:
            self.create_base_map()
        
        # Create route line
        folium.PolyLine(
            locations=route_points,
            color=color,
            weight=weight,
            opacity=0.8,
            popup=f"Truck {truck_id} Route",
            tooltip=f"Truck {truck_id} Route"
        ).add_to(self.map)
        
        # Add start and end markers
        if route_points:
            folium.Marker(
                location=route_points[0],
                popup='Depot (Start)',
                icon=folium.Icon(color='green', icon='play')
            ).add_to(self.map)
            
            folium.Marker(
                location=route_points[-1],
                popup='Depot (End)',
                icon=folium.Icon(color='red', icon='stop')
            ).add_to(self.map)
    
    def render(self):
        """Render the map in Streamlit"""
        if self.map:
            folium_static(self.map)

class ChartVisualizer:
    """Creates interactive charts using Plotly"""
    
    @staticmethod
    def create_fill_level_chart(bins_df: pd.DataFrame):
        """Create bar chart of bin fill levels"""
        fig = px.bar(
            bins_df.sort_values('fill_percentage', ascending=False),
            x='bin_id',
            y='fill_percentage',
            color='fill_percentage',
            color_continuous_scale=['green', 'yellow', 'red'],
            title='Current Bin Fill Levels',
            labels={'fill_percentage': 'Fill %', 'bin_id': 'Bin ID'}
        )
        fig.add_hline(y=80, line_dash="dash", line_color="red",
                     annotation_text="Collection Threshold (80%)")
        return fig
    
    @staticmethod
    def create_zone_distribution(bins_df: pd.DataFrame):
        """Create pie chart of bins by zone"""
        zone_counts = bins_df['zone'].value_counts()
        fig = px.pie(
            values=zone_counts.values,
            names=zone_counts.index,
            title='Bins by Zone'
        )
        return fig
    
    @staticmethod
    def create_fill_trend(historical_data: pd.DataFrame):
        """Create time series of fill levels"""
        fig = px.line(
            historical_data,
            x='timestamp',
            y='fill_percentage',
            color='bin_id',
            title='Historical Fill Level Trends'
        )
        return fig
    
    @staticmethod
    def create_efficiency_metrics(optimization_results: dict):
        """Create gauge charts for efficiency metrics"""
        if not optimization_results['routes']:
            return None
        
        total_bins = len(optimization_results.get('bins_collected', 0))
        total_distance = optimization_results.get('total_distance', 0)
        
        fig = go.Figure()
        
        # Add bins collected gauge
        fig.add_trace(go.Indicator(
            mode="number+gauge+delta",
            value=total_bins,
            title={'text': "Bins Collected"},
            domain={'row': 0, 'column': 0}
        ))
        
        # Add distance gauge
        fig.add_trace(go.Indicator(
            mode="number+gauge",
            value=total_distance,
            title={'text': "Total Distance (km)"},
            domain={'row': 0, 'column': 1}
        ))
        
        fig.update_layout(grid={'rows': 1, 'columns': 2})
        return fig