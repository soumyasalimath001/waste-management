"""
Waste Route Optimization Agent - Core Modules Package
=====================================================
This package contains the core functionality for the waste route optimization system.

Modules:
    - data_simulator: Simulates smart bin data
    - route_optimizer: Optimizes collection routes
    - visualization: Creates maps and charts
    - ml_models: Machine learning predictions
"""

from .data_simulator import BinDataSimulator
from .route_optimizer import RouteOptimizer
from .visualization import MapVisualizer, ChartVisualizer
from .ml_models import FillLevelPredictor

__all__ = [
    'BinDataSimulator',
    'RouteOptimizer', 
    'MapVisualizer',
    'ChartVisualizer',
    'FillLevelPredictor'
]

__version__ = '1.0.0'
__author__ = 'Your Team Name'