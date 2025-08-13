"""
Downtown Mixed-Use Readiness (DMUR) score calculation.
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

from shapely.geometry import Point
from scipy.spatial.distance import cdist

logger = logging.getLogger(__name__)


@dataclass
class DMURConfig:
    """Configuration for DMUR score calculation."""
    mxi_weight: float = 0.4
    balance_weight: float = 0.3
    density_weight: float = 0.2
    diversity_weight: float = 0.1
    max_distance_threshold: float = 0.005  # degrees (~500m)
    optimal_residential_ratio: float = 25.0  # residential units per business
    urban_density_benchmark: float = 1000.0  # units per km²


class DMURCalculator:
    """Calculates Downtown Mixed-Use Readiness scores."""
    
    def __init__(self, config: Optional[DMURConfig] = None):
        """Initialize calculator with configuration."""
        self.config = config or DMURConfig()
        
    def calculate_dmur(self, 
                      listings_data: Union[str, Dict, pd.DataFrame, Path],
                      downtown_boundary,
                      business_locations: pd.DataFrame,
                      city_name: str = "Unknown") -> Dict:
        """
        Calculate DMUR score for a downtown area.
        
        Args:
            listings_data: Real estate listings data
            downtown_boundary: Shapely geometry of downtown boundary
            business_locations: DataFrame with business coordinates
            city_name: Name of the city
            
        Returns:
            DMUR analysis results
        """
        logger.info(f"Calculating DMUR score for {city_name}")
        
        # Load and filter listings data
        listings_df = self._load_listings_data(listings_data)
        downtown_listings = self._filter_downtown_listings(listings_df, downtown_boundary)
        
        if len(downtown_listings) == 0:
            logger.warning("No residential listings found in downtown area")
            return self._empty_results(city_name)
        
        logger.info(f"Found {len(downtown_listings)} listings in downtown area")
        
        # Calculate individual components
        mxi_score = self._calculate_mxi_score(downtown_listings, business_locations)
        balance_score = self._calculate_balance_score(downtown_listings, business_locations)
        density_score = self._calculate_density_score(downtown_listings, downtown_boundary)
        diversity_score = self._calculate_diversity_score(downtown_listings)
        
        # Calculate weighted DMUR score
        dmur_score = (
            self.config.mxi_weight * mxi_score +
            self.config.balance_weight * balance_score +
            self.config.density_weight * density_score +
            self.config.diversity_weight * diversity_score
        )
        
        results = {
            'city': city_name,
            'dmur_score': round(dmur_score, 3),
            'component_scores': {
                'mxi_score': round(mxi_score, 3),
                'balance_score': round(balance_score, 3),
                'density_score': round(density_score, 3),
                'diversity_score': round(diversity_score, 3)
            },
            'weights': {
                'mxi_weight': self.config.mxi_weight,
                'balance_weight': self.config.balance_weight,
                'density_weight': self.config.density_weight,
                'diversity_weight': self.config.diversity_weight
            },
            'metrics': {
                'total_listings': len(downtown_listings),
                'total_businesses': len(business_locations),
                'avg_distance_to_business': self._calculate_avg_distance(downtown_listings, business_locations),
                'residential_to_business_ratio': len(downtown_listings) / max(len(business_locations), 1),
                'bedroom_distribution': downtown_listings['bedrooms'].value_counts().to_dict()
            }
        }
        
        logger.info(f"DMUR score calculated: {dmur_score:.3f}")
        return results
    
    def _load_listings_data(self, data: Union[str, Dict, pd.DataFrame, Path]) -> pd.DataFrame:
        """Load listings data from various sources."""
        if isinstance(data, pd.DataFrame):
            return data.copy()
        elif isinstance(data, (str, Path)):
            # Assume CSV or JSON file
            file_path = Path(data)
            if file_path.suffix.lower() == '.csv':
                return pd.read_csv(file_path)
            elif file_path.suffix.lower() == '.json':
                return pd.read_json(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
        elif isinstance(data, dict):
            return pd.DataFrame(data)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
    
    def _filter_downtown_listings(self, listings_df: pd.DataFrame, downtown_boundary) -> pd.DataFrame:
        """Filter listings within downtown boundary."""
        # Validate required columns
        required_cols = ['lat', 'lon', 'bedrooms', 'area_sqm', 'price']
        missing_cols = [col for col in required_cols if col not in listings_df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Create points and filter
        listing_points = [Point(row['lon'], row['lat']) for _, row in listings_df.iterrows()]
        in_downtown = [downtown_boundary.contains(point) for point in listing_points]
        
        return listings_df[in_downtown].copy()
    
    def _calculate_mxi_score(self, listings_df: pd.DataFrame, business_locations: pd.DataFrame) -> float:
        """Calculate Mixed-Use Index (MXI) score."""
        if len(business_locations) == 0:
            return 0.0
        
        # Calculate distances from each listing to all businesses
        listing_coords = listings_df[['lat', 'lon']].values
        business_coords = business_locations[['lat', 'lon']].values
        
        distances = cdist(listing_coords, business_coords, metric='euclidean')
        min_distances = np.min(distances, axis=1)  # Distance to nearest business for each listing
        
        avg_distance = np.mean(min_distances)
        
        # MXI score: 1 - (avg_distance / max_threshold)
        mxi_score = max(0, 1 - (avg_distance / self.config.max_distance_threshold))
        
        logger.info(f"MXI Score: {mxi_score:.3f} (avg distance: {avg_distance:.6f} degrees)")
        return mxi_score
    
    def _calculate_balance_score(self, listings_df: pd.DataFrame, business_locations: pd.DataFrame) -> float:
        """Calculate Balance score (residential to commercial ratio)."""
        if len(business_locations) == 0:
            return 0.0
        
        residential_count = len(listings_df)
        business_count = len(business_locations)
        actual_ratio = residential_count / business_count
        
        # Balance score: 1 - |log10(actual_ratio / optimal_ratio)|
        # Capped at 1.0 for ratios within optimal range
        ratio_deviation = abs(np.log10(actual_ratio / self.config.optimal_residential_ratio))
        balance_score = max(0, 1 - ratio_deviation)
        
        logger.info(f"Balance Score: {balance_score:.3f} "
                   f"(ratio: {actual_ratio:.1f}, optimal: {self.config.optimal_residential_ratio})")
        return balance_score
    
    def _calculate_density_score(self, listings_df: pd.DataFrame, downtown_boundary) -> float:
        """Calculate Housing Density score."""
        # Calculate area in km²
        area_deg2 = downtown_boundary.area
        lat_avg = listings_df['lat'].mean()
        km_per_deg_lat = 111.0
        km_per_deg_lon = 111.0 * np.cos(np.radians(lat_avg))
        area_km2 = area_deg2 * km_per_deg_lat * km_per_deg_lon
        
        if area_km2 <= 0:
            return 0.0
        
        # Calculate density
        units_per_km2 = len(listings_df) / area_km2
        
        # Density score: normalize against benchmark
        density_score = min(1.0, units_per_km2 / self.config.urban_density_benchmark)
        
        logger.info(f"Density Score: {density_score:.3f} "
                   f"({units_per_km2:.1f} units/km², benchmark: {self.config.urban_density_benchmark})")
        return density_score
    
    def _calculate_diversity_score(self, listings_df: pd.DataFrame) -> float:
        """Calculate Housing Diversity score using Shannon diversity index."""
        bedroom_counts = listings_df['bedrooms'].value_counts()
        
        if len(bedroom_counts) <= 1:
            return 0.0
        
        # Shannon diversity index
        proportions = bedroom_counts / len(listings_df)
        shannon_index = -np.sum(proportions * np.log(proportions))
        
        # Normalize by maximum possible diversity (log of number of categories)
        # Assume max 5 categories (0, 1, 2, 3, 4+ bedrooms)
        max_diversity = np.log(5)
        diversity_score = min(1.0, shannon_index / max_diversity)
        
        logger.info(f"Diversity Score: {diversity_score:.3f} "
                   f"(Shannon index: {shannon_index:.3f}, categories: {len(bedroom_counts)})")
        return diversity_score
    
    def _calculate_avg_distance(self, listings_df: pd.DataFrame, business_locations: pd.DataFrame) -> float:
        """Calculate average distance from listings to nearest business."""
        if len(business_locations) == 0:
            return float('inf')
        
        listing_coords = listings_df[['lat', 'lon']].values
        business_coords = business_locations[['lat', 'lon']].values
        
        distances = cdist(listing_coords, business_coords, metric='euclidean')
        min_distances = np.min(distances, axis=1)
        
        return float(np.mean(min_distances))
    
    def _empty_results(self, city_name: str) -> Dict:
        """Return empty results structure."""
        return {
            'city': city_name,
            'dmur_score': 0.0,
            'component_scores': {
                'mxi_score': 0.0,
                'balance_score': 0.0,
                'density_score': 0.0,
                'diversity_score': 0.0
            },
            'weights': {
                'mxi_weight': self.config.mxi_weight,
                'balance_weight': self.config.balance_weight,
                'density_weight': self.config.density_weight,
                'diversity_weight': self.config.diversity_weight
            },
            'metrics': {
                'total_listings': 0,
                'total_businesses': 0,
                'avg_distance_to_business': float('inf'),
                'residential_to_business_ratio': 0.0,
                'bedroom_distribution': {}
            }
        }