"""
Unit tests for data validation utilities.
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import os

from dmur_analysis.utils.validation import DataValidator


class TestDataValidator:
    """Test cases for DataValidator."""
    
    def test_validate_business_data_valid(self, sample_business_data):
        """Test validation of valid business data."""
        is_valid, errors = DataValidator.validate_business_data(sample_business_data)
        
        assert is_valid == True
        assert len(errors) == 0
    
    def test_validate_business_data_not_dict(self):
        """Test validation with non-dictionary data."""
        is_valid, errors = DataValidator.validate_business_data("not_a_dict")
        
        assert is_valid == False
        assert "Data must be a dictionary" in errors
    
    def test_validate_business_data_missing_city(self, sample_business_data):
        """Test validation with missing city field."""
        del sample_business_data['city']
        
        is_valid, errors = DataValidator.validate_business_data(sample_business_data)
        
        assert is_valid == False
        assert any("Missing required field: city" in error for error in errors)
    
    def test_validate_business_data_missing_businesses(self, sample_business_data):
        """Test validation with missing businesses field."""
        del sample_business_data['businesses']
        
        is_valid, errors = DataValidator.validate_business_data(sample_business_data)
        
        assert is_valid == False
        assert any("Missing required field: businesses" in error for error in errors)
    
    def test_validate_business_data_empty_businesses(self, sample_business_data):
        """Test validation with empty businesses list."""
        sample_business_data['businesses'] = []
        
        is_valid, errors = DataValidator.validate_business_data(sample_business_data)
        
        assert is_valid == False
        assert "No businesses found in data" in errors
    
    def test_validate_business_data_businesses_not_list(self, sample_business_data):
        """Test validation with businesses not being a list."""
        sample_business_data['businesses'] = "not_a_list"
        
        is_valid, errors = DataValidator.validate_business_data(sample_business_data)
        
        assert is_valid == False
        assert "'businesses' must be a list" in errors
    
    def test_validate_business_record_not_dict(self):
        """Test validation of business record that's not a dictionary."""
        errors = DataValidator._validate_business_record("not_a_dict", 0)
        
        assert len(errors) > 0
        assert "Business 0: must be a dictionary" in errors
    
    def test_validate_business_record_missing_fields(self):
        """Test validation of business record with missing fields."""
        incomplete_business = {"id": 1, "lat": 40.0}  # Missing required fields
        
        errors = DataValidator._validate_business_record(incomplete_business, 0)
        
        assert len(errors) > 0
        assert any("missing required field" in error for error in errors)
    
    def test_validate_business_record_invalid_coordinates(self):
        """Test validation of business record with invalid coordinates."""
        invalid_business = {
            "id": 1,
            "lat": 200.0,  # Invalid latitude
            "lon": 400.0,  # Invalid longitude
            "name": "Test",
            "business_type": "shop",
            "business_subtype": "clothing"
        }
        
        errors = DataValidator._validate_business_record(invalid_business, 0)
        
        assert len(errors) >= 2  # Both lat and lon should be invalid
        assert any("'lat' must be between -90 and 90" in error for error in errors)
        assert any("'lon' must be between -180 and 180" in error for error in errors)
    
    def test_validate_listing_data_valid_dataframe(self, sample_listings_data):
        """Test validation of valid listings DataFrame."""
        is_valid, errors = DataValidator.validate_listing_data(sample_listings_data)
        
        assert is_valid == True
        assert len(errors) == 0
    
    def test_validate_listing_data_dict(self, sample_listings_data):
        """Test validation of listings data as dictionary."""
        data_dict = sample_listings_data.to_dict('list')
        
        is_valid, errors = DataValidator.validate_listing_data(data_dict)
        
        assert is_valid == True
        assert len(errors) == 0
    
    def test_validate_listing_data_list(self, sample_listings_data):
        """Test validation of listings data as list."""
        data_list = sample_listings_data.to_dict('records')
        
        is_valid, errors = DataValidator.validate_listing_data(data_list)
        
        assert is_valid == True
        assert len(errors) == 0
    
    def test_validate_listing_data_empty_list(self):
        """Test validation of empty listings list."""
        is_valid, errors = DataValidator.validate_listing_data([])
        
        assert is_valid == False
        assert "No listing data provided" in errors
    
    def test_validate_listing_data_unsupported_type(self):
        """Test validation of unsupported data type."""
        is_valid, errors = DataValidator.validate_listing_data("unsupported")
        
        assert is_valid == False
        assert any("Unsupported data type" in error for error in errors)
    
    def test_validate_listing_data_missing_fields(self):
        """Test validation of listings with missing required fields."""
        incomplete_data = pd.DataFrame([{"lat": 40.0, "lon": -73.0}])  # Missing bedrooms, area_sqm, price
        
        is_valid, errors = DataValidator.validate_listing_data(incomplete_data)
        
        assert is_valid == False
        assert any("Missing required fields" in error for error in errors)
    
    def test_validate_listing_data_invalid_coordinates(self):
        """Test validation of listings with invalid coordinates."""
        invalid_data = pd.DataFrame([{
            "lat": 200.0,  # Invalid
            "lon": 400.0,  # Invalid
            "bedrooms": 1,
            "area_sqm": 50,
            "price": 2000
        }])
        
        is_valid, errors = DataValidator.validate_listing_data(invalid_data)
        
        assert is_valid == False
        assert any("'lat' values must be between -90 and 90" in error for error in errors)
        assert any("'lon' values must be between -180 and 180" in error for error in errors)
    
    def test_validate_listing_data_negative_values(self):
        """Test validation of listings with negative values where not allowed."""
        invalid_data = pd.DataFrame([{
            "lat": 40.0,
            "lon": -73.0,
            "bedrooms": -1,  # Invalid
            "area_sqm": -50,  # Invalid
            "price": -2000  # Invalid
        }])
        
        is_valid, errors = DataValidator.validate_listing_data(invalid_data)
        
        assert is_valid == False
        assert any("'bedrooms' must be non-negative" in error for error in errors)
        assert any("'area_sqm' must be positive" in error for error in errors)
        assert any("'price' must be positive" in error for error in errors)
    
    def test_validate_coordinates_insufficient_businesses(self):
        """Test coordinate validation with insufficient businesses."""
        few_businesses = [
            {"lat": 40.0, "lon": -73.0},
            {"lat": 40.1, "lon": -73.1}
        ]
        
        errors = DataValidator._validate_coordinates(few_businesses)
        
        assert len(errors) > 0
        assert "Need at least 3 businesses with valid coordinates" in errors
    
    def test_validate_coordinates_large_range(self):
        """Test coordinate validation with unreasonably large range."""
        wide_businesses = [
            {"lat": 40.0, "lon": -73.0},
            {"lat": 42.0, "lon": -70.0},  # Large range
            {"lat": 41.0, "lon": -71.0}
        ]
        
        errors = DataValidator._validate_coordinates(wide_businesses)
        
        assert len(errors) > 0
        assert any("too large" in error for error in errors)
    
    def test_validate_coordinates_small_range(self):
        """Test coordinate validation with unreasonably small range."""
        close_businesses = [
            {"lat": 40.0000, "lon": -73.0000},
            {"lat": 40.0001, "lon": -73.0001},  # Very small range
            {"lat": 40.0002, "lon": -73.0002}
        ]
        
        errors = DataValidator._validate_coordinates(close_businesses)
        
        assert len(errors) > 0
        assert any("too small" in error for error in errors)
    
    def test_validate_file_path_existing_file(self, temp_json_file):
        """Test file path validation for existing file."""
        is_valid, error = DataValidator.validate_file_path(temp_json_file, must_exist=True)
        
        assert is_valid == True
        assert error is None
    
    def test_validate_file_path_nonexistent_file(self):
        """Test file path validation for non-existent file."""
        is_valid, error = DataValidator.validate_file_path("/nonexistent/file.json", must_exist=True)
        
        assert is_valid == False
        assert "File does not exist" in error
    
    def test_validate_file_path_directory_as_file(self, temp_dir):
        """Test file path validation when path is directory."""
        is_valid, error = DataValidator.validate_file_path(str(temp_dir), must_exist=True)
        
        assert is_valid == False
        assert "Path is not a file" in error
    
    def test_validate_file_path_new_file_valid_parent(self, temp_dir):
        """Test file path validation for new file with valid parent."""
        new_file = temp_dir / "new_file.json"
        
        is_valid, error = DataValidator.validate_file_path(str(new_file), must_exist=False)
        
        assert is_valid == True
        assert error is None
    
    def test_validate_file_path_new_file_invalid_parent(self):
        """Test file path validation for new file with invalid parent."""
        invalid_path = "/nonexistent/directory/file.json"
        
        is_valid, error = DataValidator.validate_file_path(invalid_path, must_exist=False)
        
        assert is_valid == False
        assert "Parent directory does not exist" in error