"""
Unit tests for DMURCalculator class.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch

from dmur_analysis.core.dmur_calculator import DMURCalculator, DMURConfig


class TestDMURCalculator:
    """Test cases for DMURCalculator."""
    
    def test_init_default_config(self):
        """Test calculator initialization with default config."""
        calculator = DMURCalculator()
        assert calculator.config is not None
        assert calculator.config.mxi_weight == 0.4
        assert calculator.config.balance_weight == 0.3
        assert calculator.config.density_weight == 0.2
        assert calculator.config.diversity_weight == 0.1
    
    def test_init_custom_config(self):
        """Test calculator initialization with custom config."""
        config = DMURConfig(
            mxi_weight=0.5,
            balance_weight=0.25,
            density_weight=0.15,
            diversity_weight=0.1
        )
        calculator = DMURCalculator(config)
        assert calculator.config.mxi_weight == 0.5
        assert calculator.config.balance_weight == 0.25
    
    def test_load_listings_data_dataframe(self, sample_listings_data):
        """Test loading listings data from DataFrame."""
        calculator = DMURCalculator()
        result = calculator._load_listings_data(sample_listings_data)
        
        pd.testing.assert_frame_equal(result, sample_listings_data)
    
    def test_load_listings_data_dict(self, sample_listings_data):
        """Test loading listings data from dictionary."""
        calculator = DMURCalculator()
        data_dict = sample_listings_data.to_dict('list')
        
        result = calculator._load_listings_data(data_dict)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_listings_data)
    
    def test_load_listings_data_invalid_type(self):
        """Test loading listings data with invalid type."""
        calculator = DMURCalculator()
        
        with pytest.raises(ValueError, match="Unsupported data type"):
            calculator._load_listings_data("invalid_type")
    
    def test_filter_downtown_listings_missing_columns(self, sample_downtown_boundary):
        """Test filtering listings with missing required columns."""
        calculator = DMURCalculator()
        
        # DataFrame missing required columns
        invalid_df = pd.DataFrame([{"lat": 40.05, "lon": -73.95}])
        
        with pytest.raises(ValueError, match="Missing required columns"):
            calculator._filter_downtown_listings(invalid_df, sample_downtown_boundary)
    
    def test_filter_downtown_listings_valid(self, sample_listings_data, sample_downtown_boundary):
        """Test filtering listings within downtown boundary."""
        calculator = DMURCalculator()
        
        downtown_listings = calculator._filter_downtown_listings(
            sample_listings_data, sample_downtown_boundary
        )
        
        assert isinstance(downtown_listings, pd.DataFrame)
        assert len(downtown_listings) >= 0
        # All filtered listings should be within the boundary
        for _, listing in downtown_listings.iterrows():
            from shapely.geometry import Point
            point = Point(listing['lon'], listing['lat'])
            assert sample_downtown_boundary.contains(point) or sample_downtown_boundary.touches(point)
    
    def test_calculate_mxi_score_no_businesses(self, sample_listings_data):
        """Test MXI score calculation with no businesses."""
        calculator = DMURCalculator()
        empty_businesses = pd.DataFrame(columns=['lat', 'lon'])
        
        mxi_score = calculator._calculate_mxi_score(sample_listings_data, empty_businesses)
        
        assert mxi_score == 0.0
    
    def test_calculate_mxi_score_with_businesses(self, sample_listings_data, sample_business_df):
        """Test MXI score calculation with businesses."""
        calculator = DMURCalculator()
        
        mxi_score = calculator._calculate_mxi_score(sample_listings_data, sample_business_df)
        
        assert 0.0 <= mxi_score <= 1.0
        assert isinstance(mxi_score, float)
    
    def test_calculate_balance_score_no_businesses(self, sample_listings_data):
        """Test balance score calculation with no businesses."""
        calculator = DMURCalculator()
        empty_businesses = pd.DataFrame(columns=['lat', 'lon'])
        
        balance_score = calculator._calculate_balance_score(sample_listings_data, empty_businesses)
        
        assert balance_score == 0.0
    
    def test_calculate_balance_score_with_businesses(self, sample_listings_data, sample_business_df):
        """Test balance score calculation with businesses."""
        calculator = DMURCalculator()
        
        balance_score = calculator._calculate_balance_score(sample_listings_data, sample_business_df)
        
        assert 0.0 <= balance_score <= 1.0
        assert isinstance(balance_score, float)
    
    def test_calculate_density_score_zero_area(self, sample_listings_data):
        """Test density score calculation with zero area."""
        calculator = DMURCalculator()
        
        # Create a boundary with zero area
        from shapely.geometry import Point
        zero_area_boundary = Point(40.05, -73.95).buffer(0)
        
        density_score = calculator._calculate_density_score(sample_listings_data, zero_area_boundary)
        
        assert density_score == 0.0
    
    def test_calculate_density_score_with_area(self, sample_listings_data, sample_downtown_boundary):
        """Test density score calculation with valid area."""
        calculator = DMURCalculator()
        
        density_score = calculator._calculate_density_score(sample_listings_data, sample_downtown_boundary)
        
        assert 0.0 <= density_score <= 1.0
        assert isinstance(density_score, float)
    
    def test_calculate_diversity_score_single_type(self):
        """Test diversity score calculation with single bedroom type."""
        calculator = DMURCalculator()
        
        # All listings have same bedroom count
        single_type_df = pd.DataFrame([
            {"bedrooms": 1}, {"bedrooms": 1}, {"bedrooms": 1}
        ])
        
        diversity_score = calculator._calculate_diversity_score(single_type_df)
        
        assert diversity_score == 0.0
    
    def test_calculate_diversity_score_multiple_types(self, sample_listings_data):
        """Test diversity score calculation with multiple bedroom types."""
        calculator = DMURCalculator()
        
        diversity_score = calculator._calculate_diversity_score(sample_listings_data)
        
        assert 0.0 <= diversity_score <= 1.0
        assert isinstance(diversity_score, float)
    
    def test_calculate_avg_distance_no_businesses(self, sample_listings_data):
        """Test average distance calculation with no businesses."""
        calculator = DMURCalculator()
        empty_businesses = pd.DataFrame(columns=['lat', 'lon'])
        
        avg_distance = calculator._calculate_avg_distance(sample_listings_data, empty_businesses)
        
        assert avg_distance == float('inf')
    
    def test_calculate_avg_distance_with_businesses(self, sample_listings_data, sample_business_df):
        """Test average distance calculation with businesses."""
        calculator = DMURCalculator()
        
        avg_distance = calculator._calculate_avg_distance(sample_listings_data, sample_business_df)
        
        assert avg_distance >= 0.0
        assert isinstance(avg_distance, float)
        assert avg_distance != float('inf')
    
    def test_empty_results(self):
        """Test empty results generation."""
        calculator = DMURCalculator()
        
        results = calculator._empty_results("Test City")
        
        assert results['city'] == "Test City"
        assert results['dmur_score'] == 0.0
        assert all(score == 0.0 for score in results['component_scores'].values())
        assert results['metrics']['total_listings'] == 0
        assert results['metrics']['total_businesses'] == 0
    
    def test_calculate_dmur_no_listings(self, sample_business_df, sample_downtown_boundary):
        """Test DMUR calculation with no downtown listings."""
        calculator = DMURCalculator()
        
        # Create listings outside downtown boundary
        outside_listings = pd.DataFrame([{
            "lat": 45.0, "lon": -75.0, "bedrooms": 1, 
            "area_sqm": 50, "price": 2000
        }])
        
        results = calculator.calculate_dmur(
            outside_listings, sample_downtown_boundary, 
            sample_business_df, "Test City"
        )
        
        assert results['dmur_score'] == 0.0
        assert results['metrics']['total_listings'] == 0
    
    def test_calculate_dmur_with_listings(self, sample_listings_data, sample_business_df, sample_downtown_boundary):
        """Test DMUR calculation with valid listings."""
        calculator = DMURCalculator()
        
        results = calculator.calculate_dmur(
            sample_listings_data, sample_downtown_boundary,
            sample_business_df, "Test City"
        )
        
        assert results['city'] == "Test City"
        assert 0.0 <= results['dmur_score'] <= 1.0
        assert 'component_scores' in results
        assert 'weights' in results
        assert 'metrics' in results
        
        # Check component scores
        for score in results['component_scores'].values():
            assert 0.0 <= score <= 1.0
        
        # Check weights sum to 1.0
        total_weight = sum(results['weights'].values())
        assert abs(total_weight - 1.0) < 0.001