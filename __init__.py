"""
Utility Functions Package
=========================
Helper functions and utilities for the waste route optimization system.

Modules:
    - osm_helpers: OpenStreetMap integration utilities
"""

from .osm_helpers import OSMDataFetcher, DistanceCalculator

__all__ = [
    'OSMDataFetcher',
    'DistanceCalculator'
]

__version__ = '1.0.0'