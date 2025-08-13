"""
Unit tests for DowntownAnalyzer class.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch

from dmur_analysis.core.downtown_analyzer import DowntownAnalyzer, AnalysisConfig
from shapely.geometry import Polygon


class TestDowntownAnalyzer:
    """Test cases for DowntownAnalyzer."""
    
    def test_init_default_config(self):
        """Test analyzer initialization with default config."""
        analyzer = DowntownAnalyzer()
        assert analyzer.config is not None
        assert analyzer.config.density_threshold_percentile == 90.0
        assert analyzer.config.commercial_only == True
        assert analyzer.config.auto_focus == True
    
    def test_init_custom_config(self):
        """Test analyzer initialization with custom config."""
        config = AnalysisConfig(
            density_threshold_percentile=85.0,
            bandwidth=0.001,
            commercial_only=False
        )
        analyzer = DowntownAnalyzer(config)
        assert analyzer.config.density_threshold_percentile == 85.0
        assert analyzer.config.bandwidth == 0.001
        assert analyzer.config.commercial_only == False
    
    def test_extract_city_name(self, sample_business_data):
        """Test city name extraction from business data."""
        analyzer = DowntownAnalyzer()
        city_name = analyzer._extract_city_name(sample_business_data)
        assert city_name == "Test City"
    
    def test_extract_city_name_missing(self):
        """Test city name extraction with missing city field."""
        analyzer = DowntownAnalyzer()
        city_name = analyzer._extract_city_name({})
        assert city_name == "Unknown City"
    
    def test_is_commercial_business_amenity_commercial(self):
        """Test commercial business detection for commercial amenities."""
        analyzer = DowntownAnalyzer()
        business = {
            "business_type": "amenity",
            "business_subtype": "restaurant"
        }
        assert analyzer._is_commercial_business(business) == True
    
    def test_is_commercial_business_amenity_non_commercial(self):
        """Test commercial business detection for non-commercial amenities."""
        analyzer = DowntownAnalyzer()
        business = {
            "business_type": "amenity", 
            "business_subtype": "playground"
        }
        assert analyzer._is_commercial_business(business) == False
    
    def test_is_commercial_business_shop(self):
        """Test commercial business detection for shops."""
        analyzer = DowntownAnalyzer()
        business = {
            "business_type": "shop",
            "business_subtype": "clothing"
        }
        assert analyzer._is_commercial_business(business) == True
    
    def test_is_commercial_business_non_commercial_type(self):
        """Test commercial business detection for non-commercial types."""
        analyzer = DowntownAnalyzer()
        business = {
            "business_type": "natural",
            "business_subtype": "tree"
        }
        assert analyzer._is_commercial_business(business) == False
    
    def test_apply_focus_area(self, sample_business_df):
        """Test focus area application."""
        analyzer = DowntownAnalyzer()
        focus_area = (40.050, -73.952, 40.053, -73.950)
        
        filtered_df = analyzer._apply_focus_area(sample_business_df, focus_area)
        
        # Should include businesses within the focus area
        assert len(filtered_df) >= 1
        assert all(filtered_df['lat'] >= 40.050)
        assert all(filtered_df['lat'] <= 40.053)
        assert all(filtered_df['lon'] >= -73.952)
        assert all(filtered_df['lon'] <= -73.950)
    
    def test_auto_determine_focus_area_small_dataset(self):
        """Test auto focus area determination with small dataset."""
        analyzer = DowntownAnalyzer()
        
        # Create small dataset
        small_df = pd.DataFrame([
            {"lat": 40.05, "lon": -73.95},
            {"lat": 40.06, "lon": -73.96}
        ])
        
        focus_area = analyzer._auto_determine_focus_area(small_df)
        
        # Should return entire area for small datasets
        assert len(focus_area) == 4
        min_lat, min_lon, max_lat, max_lon = focus_area
        assert min_lat <= 40.05
        assert max_lat >= 40.06
        assert min_lon <= -73.96
        assert max_lon >= -73.95
    
    def test_get_businesses_in_downtown_no_boundary(self):
        """Test getting businesses in downtown without boundary."""
        analyzer = DowntownAnalyzer()
        analyzer.downtown_boundary = None
        
        with pytest.raises(ValueError, match="Downtown boundary not created yet"):
            analyzer.get_businesses_in_downtown()
    
    def test_get_businesses_in_downtown_with_boundary(self, sample_business_df, sample_downtown_boundary):
        """Test getting businesses within downtown boundary."""
        analyzer = DowntownAnalyzer()
        analyzer.businesses_df = sample_business_df
        analyzer.downtown_boundary = sample_downtown_boundary
        
        downtown_businesses = analyzer.get_businesses_in_downtown()
        
        # Should return businesses within the boundary
        assert isinstance(downtown_businesses, pd.DataFrame)
        assert len(downtown_businesses) >= 0
    
    def test_analyze_insufficient_data(self):
        """Test analysis with insufficient business data."""
        analyzer = DowntownAnalyzer()
        
        # Create data with too few businesses
        insufficient_data = {
            "city": "Test City",
            "businesses": [
                {"id": 1, "lat": 40.05, "lon": -73.95, "name": "Test", 
                 "business_type": "amenity", "business_subtype": "restaurant"}
            ]
        }
        
        with pytest.raises(ValueError, match="Insufficient business data"):
            analyzer.analyze(insufficient_data)
    
    @patch('dmur_analysis.core.downtown_analyzer.KernelDensity')
    def test_calculate_density_grid(self, mock_kde, sample_business_df):
        """Test density grid calculation."""
        # Mock KDE
        mock_kde_instance = Mock()
        mock_kde_instance.score_samples.return_value = np.array([1.0, 2.0, 3.0, 4.0])
        mock_kde.return_value = mock_kde_instance
        
        analyzer = DowntownAnalyzer()
        analyzer.businesses_df = sample_business_df
        
        analyzer._calculate_density_grid()
        
        assert analyzer.density_grid is not None
        assert analyzer.density_coords is not None
        mock_kde.assert_called_once()
        mock_kde_instance.fit.assert_called_once()
    
    def test_identify_high_density_areas(self, sample_business_df):
        """Test high-density area identification."""
        analyzer = DowntownAnalyzer()
        analyzer.businesses_df = sample_business_df
        
        # Create mock density grid
        analyzer.density_grid = np.array([[1, 2], [3, 4]])
        lat_grid = np.array([[40.0, 40.0], [40.1, 40.1]])
        lon_grid = np.array([[-74.0, -73.9], [-74.0, -73.9]])
        analyzer.density_coords = (lat_grid, lon_grid)
        
        high_lats, high_lons = analyzer._identify_high_density_areas()
        
        assert len(high_lats) > 0
        assert len(high_lons) > 0
        assert len(high_lats) == len(high_lons)
    
    def test_generate_results(self, sample_business_df, sample_downtown_boundary):
        """Test results generation."""
        analyzer = DowntownAnalyzer()
        analyzer.city_name = "Test City"
        analyzer.businesses_df = sample_business_df
        analyzer.downtown_boundary = sample_downtown_boundary
        
        results = analyzer._generate_results()
        
        assert results['city'] == "Test City"
        assert 'total_businesses' in results
        assert 'downtown_businesses' in results
        assert 'downtown_area_km2' in results
        assert 'business_density_per_km2' in results
        assert 'downtown_boundary' in results