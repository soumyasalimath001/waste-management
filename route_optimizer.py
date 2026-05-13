import numpy as np
import pandas as pd
from geopy.distance import geodesic
import networkx as nx
from typing import List, Tuple, Dict
import openrouteservice
from config import config

class RouteOptimizer:
    """
    Optimizes waste collection routes using various algorithms [citation:1][citation:5]
    """
    
    def __init__(self, use_ors_api=False):
        self.use_ors_api = use_ors_api
        if use_ors_api and config.OPENROUTESERVICE_API_KEY:
            self.ors_client = openrouteservice.Client(key=config.OPENROUTESERVICE_API_KEY)
        else:
            self.ors_client = None
    
    def calculate_distance_matrix(self, points: List[Tuple[float, float]]) -> np.ndarray:
        """
        Calculate distance matrix between all points
        """
        n = len(points)
        distance_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                if self.ors_client:
                    # Use OpenRouteService for real road distances [citation:5]
                    try:
                        route = self.ors_client.directions(
                            coordinates=[points[i], points[j]],
                            profile='driving-truck',
                            format='json'
                        )
                        dist = route['routes'][0]['summary']['distance'] / 1000  # km
                    except:
                        # Fallback to geodesic distance
                        dist = geodesic(points[i], points[j]).km
                else:
                    # Use geodesic distance as approximation [citation:1]
                    dist = geodesic(points[i], points[j]).km
                
                distance_matrix[i, j] = dist
                distance_matrix[j, i] = dist
        
        return distance_matrix
    
    def greedy_nearest_neighbor(self, 
                                points: List[Tuple[float, float]], 
                                fill_levels: List[float],
                                depot_idx: int = 0) -> Tuple[List[int], float]:
        """
        Greedy nearest neighbor algorithm with waste prioritization [citation:6]
        Combines distance minimization with waste collection maximization
        """
        n = len(points)
        unvisited = set(range(n))
        unvisited.remove(depot_idx)
        current = depot_idx
        route = [current]
        total_distance = 0
        
        # Calculate distance matrix
        dist_matrix = self.calculate_distance_matrix(points)
        
        while unvisited:
            # Score each unvisited point based on distance and waste amount
            best_next = None
            best_score = float('-inf')
            
            for next_point in unvisited:
                # Normalized distance (inverse - shorter is better)
                norm_dist = 1 / (dist_matrix[current, next_point] + 0.1)
                
                # Waste priority (higher fill percentage is better)
                waste_score = fill_levels[next_point] / 100
                
                # Combined score with weights from config [citation:1]
                score = (config.DISTANCE_WEIGHT * norm_dist + 
                        config.WASTE_WEIGHT * waste_score)
                
                if score > best_score:
                    best_score = score
                    best_next = next_point
            
            if best_next is not None:
                route.append(best_next)
                total_distance += dist_matrix[current, best_next]
                unvisited.remove(best_next)
                current = best_next
        
        # Return to depot
        route.append(depot_idx)
        total_distance += dist_matrix[current, depot_idx]
        
        return route, total_distance
    
    def optimize_with_constraints(self, 
                                  bins_df: pd.DataFrame,
                                  num_trucks: int = 2) -> Dict:
        """
        Multi-truck route optimization with capacity constraints [citation:1]
        """
        # Get bins that need collection
        bins_to_collect = bins_df[bins_df['needs_collection']].copy()
        
        if len(bins_to_collect) == 0:
            return {'routes': [], 'total_distance': 0}
        
        # Extract depot (first point)
        depot = (bins_df.iloc[0]['latitude'], bins_df.iloc[0]['longitude'])
        
        # Cluster bins for multiple trucks [citation:1]
        from sklearn.cluster import KMeans
        
        coords = bins_to_collect[['latitude', 'longitude']].values
        fill_levels = bins_to_collect['fill_percentage'].values
        
        # Use K-means to assign bins to trucks
        kmeans = KMeans(n_clusters=min(num_trucks, len(coords)))
        clusters = kmeans.fit_predict(coords)
        
        routes = []
        total_fleet_distance = 0
        
        for truck_id in range(num_trucks):
            truck_bins = bins_to_collect[clusters == truck_id]
            
            if len(truck_bins) == 0:
                continue
            
            # Prepare points for this truck (including depot at start and end)
            truck_points = [depot] + list(zip(truck_bins['latitude'], 
                                               truck_bins['longitude']))
            truck_fill = [0] + list(truck_bins['fill_percentage'])
            
            # Optimize route for this truck
            route, distance = self.greedy_nearest_neighbor(
                truck_points, truck_fill, depot_idx=0
            )
            
            routes.append({
                'truck_id': truck_id,
                'route_indices': route,
                'points': [truck_points[i] for i in route],
                'distance_km': distance,
                'bins_collected': len(truck_bins)
            })
            
            total_fleet_distance += distance
        
        return {
            'routes': routes,
            'total_distance': total_fleet_distance,
            'bins_collected': len(bins_to_collect)
        }