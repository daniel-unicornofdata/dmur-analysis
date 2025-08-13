"""
Downtown boundary analysis using business density and clustering algorithms.
"""

import json
import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

from sklearn.neighbors import KernelDensity
from sklearn.cluster import DBSCAN
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
from scipy.spatial import ConvexHull, Delaunay

logger = logging.getLogger(__name__)


@dataclass
class AnalysisConfig:
    """Configuration for downtown analysis."""
    density_threshold_percentile: float = 90.0
    bandwidth: float = 0.002
    grid_size: float = 0.002
    alpha: float = 0.02
    buffer_distance: float = 0.003
    commercial_only: bool = True
    auto_focus: bool = True
    focus_area: Optional[Tuple[float, float, float, float]] = None


class DowntownAnalyzer:
    """Analyzes business density to identify downtown boundaries."""
    
    # Commercial business type filters
    COMMERCIAL_TYPES = {'shop', 'amenity', 'office', 'tourism', 'craft', 'healthcare'}
    
    COMMERCIAL_AMENITIES = {
        'restaurant', 'cafe', 'bar', 'pub', 'fast_food', 'food_court', 'ice_cream',
        'bank', 'atm', 'cinema', 'theatre', 'nightclub', 'casino', 'pharmacy',
        'clinic', 'doctors', 'dentist', 'fuel', 'car_wash', 'car_rental',
        'post_office', 'courier', 'internet_cafe', 'library', 'coworking_space'
    }
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        """Initialize analyzer with configuration."""
        self.config = config or AnalysisConfig()
        self.city_name = None
        self.businesses_df = None
        self.density_grid = None
        self.density_coords = None
        self.downtown_boundary = None
        
    def analyze(self, business_data: Union[str, Dict, Path], city_name: Optional[str] = None) -> Dict:
        """
        Complete downtown analysis pipeline.
        
        Args:
            business_data: Path to JSON file or business data dict
            city_name: Optional city name override
            
        Returns:
            Analysis results dictionary
        """
        logger.info("Starting downtown boundary analysis")
        
        # Load business data
        if isinstance(business_data, (str, Path)):
            with open(business_data, 'r') as f:
                data = json.load(f)
        else:
            data = business_data
            
        self.city_name = city_name or self._extract_city_name(data)
        logger.info(f"Analyzing downtown for {self.city_name}")
        
        # Process business data
        self._load_business_data(data)
        
        if len(self.businesses_df) < 3:
            raise ValueError(f"Insufficient business data: {len(self.businesses_df)} businesses found")
        
        # Calculate density
        self._calculate_density_grid()
        
        # Identify high-density areas
        high_density_lats, high_density_lons = self._identify_high_density_areas()
        
        # Create boundary
        self._create_downtown_boundary(high_density_lats, high_density_lons)
        
        # Generate results
        results = self._generate_results()
        
        logger.info(f"Analysis complete: {results['downtown_area_km2']:.2f} km² downtown area")
        return results
    
    def _extract_city_name(self, data: Dict) -> str:
        """Extract city name from business data."""
        return data.get('city', 'Unknown City')
    
    def _load_business_data(self, data: Dict) -> None:
        """Load and filter business data."""
        logger.info(f"Loading business data for {self.city_name}")
        
        businesses = []
        
        for business in data.get('businesses', []):
            if not business.get('lat') or not business.get('lon'):
                continue
                
            # Apply commercial filter if enabled
            if self.config.commercial_only:
                if not self._is_commercial_business(business):
                    continue
            
            businesses.append({
                'id': business['id'],
                'lat': business['lat'],
                'lon': business['lon'],
                'name': business['name'],
                'type': business['business_type'],
                'subtype': business['business_subtype']
            })
        
        temp_df = pd.DataFrame(businesses)
        logger.info(f"Loaded {len(temp_df)} businesses total")
        
        # Apply focus area
        if self.config.focus_area:
            self.businesses_df = self._apply_focus_area(temp_df, self.config.focus_area)
        elif self.config.auto_focus:
            focus_area = self._auto_determine_focus_area(temp_df)
            self.businesses_df = self._apply_focus_area(temp_df, focus_area)
        else:
            self.businesses_df = temp_df
        
        logger.info(f"Using {len(self.businesses_df)} businesses in analysis area")
        
        # Log business type distribution
        if len(self.businesses_df) > 0:
            type_counts = self.businesses_df['type'].value_counts()
            logger.info(f"Business types: {dict(type_counts.head(5))}")
    
    def _is_commercial_business(self, business: Dict) -> bool:
        """Check if business is commercial type."""
        btype = business.get('business_type', '')
        subtype = business.get('business_subtype', '')
        
        # Skip non-commercial types
        if btype not in self.COMMERCIAL_TYPES:
            return False
        
        # For amenities, only include commercial ones
        if btype == 'amenity' and subtype not in self.COMMERCIAL_AMENITIES:
            return False
        
        # Skip non-commercial buildings
        if btype == 'building' and subtype not in ['commercial', 'retail', 'office', 'hotel']:
            return False
        
        # Skip non-commercial leisure
        if btype == 'leisure' and subtype not in ['fitness_centre', 'sports_centre', 'bowling_alley']:
            return False
        
        return True
    
    def _apply_focus_area(self, df: pd.DataFrame, focus_area: Tuple[float, float, float, float]) -> pd.DataFrame:
        """Apply focus area filter to business data."""
        min_lat, min_lon, max_lat, max_lon = focus_area
        mask = ((df['lat'] >= min_lat) & (df['lat'] <= max_lat) &
                (df['lon'] >= min_lon) & (df['lon'] <= max_lon))
        return df[mask].copy()
    
    def _auto_determine_focus_area(self, businesses_df: pd.DataFrame, 
                                  density_percentile: float = 85) -> Tuple[float, float, float, float]:
        """Automatically determine focus area using clustering and density analysis."""
        if len(businesses_df) < 10:
            return (businesses_df['lat'].min(), businesses_df['lon'].min(),
                   businesses_df['lat'].max(), businesses_df['lon'].max())
        
        logger.info("Auto-detecting downtown focus area using density clustering")
        
        lats, lons = businesses_df['lat'].values, businesses_df['lon'].values
        coords = np.column_stack([lats, lons])
        
        # DBSCAN clustering
        lat_range = lats.max() - lats.min()
        lon_range = lons.max() - lons.min()
        epsilon = min(lat_range, lon_range) * 0.01
        
        clustering = DBSCAN(eps=epsilon, min_samples=10).fit(coords)
        labels = clustering.labels_
        
        # Find largest cluster
        unique_labels, counts = np.unique(labels[labels >= 0], return_counts=True)
        
        if len(unique_labels) > 0:
            largest_cluster_label = unique_labels[np.argmax(counts)]
            cluster_mask = labels == largest_cluster_label
            cluster_coords = coords[cluster_mask]
            
            logger.info(f"Found main cluster with {len(cluster_coords)} businesses")
            
            # Use cluster bounds with padding
            padding = min(lat_range, lon_range) * 0.02
            return (
                cluster_coords[:, 0].min() - padding,
                cluster_coords[:, 1].min() - padding,
                cluster_coords[:, 0].max() + padding,
                cluster_coords[:, 1].max() + padding
            )
        
        # Fallback to histogram-based peak detection
        logger.info("Using fallback: peak density area from histogram")
        lat_bins = np.linspace(lats.min(), lats.max(), 20)
        lon_bins = np.linspace(lons.min(), lons.max(), 20)
        
        hist, lat_edges, lon_edges = np.histogram2d(lats, lons, bins=[lat_bins, lon_bins])
        peak_idx = np.unravel_index(np.argmax(hist), hist.shape)
        
        # Create window around peak
        window_size = 3
        lat_start = max(0, peak_idx[0] - window_size//2)
        lat_end = min(len(lat_edges)-1, peak_idx[0] + window_size//2 + 1)
        lon_start = max(0, peak_idx[1] - window_size//2)
        lon_end = min(len(lon_edges)-1, peak_idx[1] + window_size//2 + 1)
        
        padding = min(lat_range, lon_range) * 0.02
        return (
            lat_edges[lat_start] - padding,
            lon_edges[lon_start] - padding,
            lat_edges[lat_end] + padding,
            lon_edges[lon_end] + padding
        )
    
    def _calculate_density_grid(self) -> None:
        """Calculate business density using kernel density estimation."""
        logger.info("Calculating business density grid")
        
        # Get coordinate bounds with padding
        min_lat, max_lat = self.businesses_df['lat'].min(), self.businesses_df['lat'].max()
        min_lon, max_lon = self.businesses_df['lon'].min(), self.businesses_df['lon'].max()
        
        padding = max(0.005, (max_lat - min_lat) * 0.1)
        min_lat -= padding
        max_lat += padding
        min_lon -= padding
        max_lon += padding
        
        # Create grid
        lat_range = np.arange(min_lat, max_lat, self.config.grid_size)
        lon_range = np.arange(min_lon, max_lon, self.config.grid_size)
        lon_grid, lat_grid = np.meshgrid(lon_range, lat_range)
        
        grid_coords = np.column_stack([lat_grid.ravel(), lon_grid.ravel()])
        business_coords = self.businesses_df[['lat', 'lon']].values
        
        # Apply KDE
        kde = KernelDensity(bandwidth=self.config.bandwidth, kernel='gaussian')
        kde.fit(business_coords)
        
        log_density = kde.score_samples(grid_coords)
        density = np.exp(log_density)
        
        self.density_grid = density.reshape(lat_grid.shape)
        self.density_coords = (lat_grid, lon_grid)
        
        logger.info(f"Density grid: {self.density_grid.shape}, "
                   f"range: {density.min():.6f} to {density.max():.6f}")
    
    def _identify_high_density_areas(self) -> Tuple[np.ndarray, np.ndarray]:
        """Identify high-density grid points."""
        logger.info("Identifying high-density areas")
        
        threshold = np.percentile(self.density_grid.ravel(), self.config.density_threshold_percentile)
        logger.info(f"Using density threshold: {threshold:.6f} "
                   f"({self.config.density_threshold_percentile}th percentile)")
        
        lat_grid, lon_grid = self.density_coords
        high_density_mask = self.density_grid >= threshold
        
        high_density_lats = lat_grid[high_density_mask]
        high_density_lons = lon_grid[high_density_mask]
        
        logger.info(f"Found {len(high_density_lats)} high-density grid points")
        
        if len(high_density_lats) < 3:
            logger.warning("Too few high-density points, lowering threshold")
            threshold = np.percentile(self.density_grid.ravel(), max(70, self.config.density_threshold_percentile - 20))
            high_density_mask = self.density_grid >= threshold
            high_density_lats = lat_grid[high_density_mask]
            high_density_lons = lon_grid[high_density_mask]
            logger.info(f"Using lower threshold: {threshold:.6f} - found {len(high_density_lats)} points")
        
        return high_density_lats, high_density_lons
    
    def _create_downtown_boundary(self, high_density_lats: np.ndarray, high_density_lons: np.ndarray) -> None:
        """Create downtown boundary using alpha shapes or convex hull."""
        logger.info("Creating downtown boundary")
        
        try:
            # Alpha shapes approach
            coords = np.column_stack([high_density_lons, high_density_lats])
            tri = Delaunay(coords)
            
            triangles = []
            for simplex in tri.simplices:
                triangle_coords = coords[simplex]
                # Calculate max edge length
                edge_lengths = [
                    np.sqrt(np.sum((triangle_coords[i] - triangle_coords[(i+1)%3])**2))
                    for i in range(3)
                ]
                
                if max(edge_lengths) < self.config.alpha:
                    triangles.append(triangle_coords)
            
            if triangles:
                triangle_polygons = [Polygon(t) for t in triangles]
                boundary = unary_union(triangle_polygons)
                logger.info("Created alpha shape boundary")
            else:
                raise ValueError("No triangles passed alpha test")
                
        except Exception as e:
            logger.warning(f"Alpha shape failed: {e}, falling back to convex hull")
            coords = np.column_stack([high_density_lons, high_density_lats])
            hull = ConvexHull(coords)
            hull_points = coords[hull.vertices]
            boundary = Polygon(hull_points)
            logger.info("Created convex hull boundary")
        
        # Apply buffer
        if self.config.buffer_distance > 0:
            boundary = boundary.buffer(self.config.buffer_distance)
            logger.info(f"Applied buffer of {self.config.buffer_distance} degrees")
        
        self.downtown_boundary = boundary
    
    def get_businesses_in_downtown(self) -> pd.DataFrame:
        """Get businesses within downtown boundary."""
        if self.downtown_boundary is None:
            raise ValueError("Downtown boundary not created yet")
        
        business_points = [Point(row['lon'], row['lat']) for _, row in self.businesses_df.iterrows()]
        in_downtown = [self.downtown_boundary.contains(point) for point in business_points]
        
        downtown_businesses = self.businesses_df[in_downtown].copy()
        logger.info(f"Found {len(downtown_businesses)} businesses in downtown area")
        
        return downtown_businesses
    
    def _generate_results(self) -> Dict:
        """Generate analysis results."""
        downtown_businesses = self.get_businesses_in_downtown()
        
        # Calculate area
        lat_avg = self.businesses_df['lat'].mean()
        km_per_deg_lat = 111.0
        km_per_deg_lon = 111.0 * np.cos(np.radians(lat_avg))
        area_km2 = self.downtown_boundary.area * km_per_deg_lat * km_per_deg_lon
        
        return {
            'city': self.city_name,
            'total_businesses': len(self.businesses_df),
            'downtown_businesses': len(downtown_businesses),
            'downtown_area_km2': round(area_km2, 2),
            'business_density_per_km2': round(len(downtown_businesses) / area_km2, 1) if area_km2 > 0 else 0,
            'downtown_boundary': self.downtown_boundary,
            'businesses_df': self.businesses_df,
            'downtown_businesses_df': downtown_businesses,
            'density_grid': self.density_grid,
            'density_coords': self.density_coords
        }