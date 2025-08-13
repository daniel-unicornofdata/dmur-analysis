"""
Pytest configuration and shared fixtures.
"""

import pytest
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon
from pathlib import Path
import json
import tempfile
import os


@pytest.fixture
def sample_business_data():
    """Sample business data for testing."""
    return {
        "city": "Test City",
        "state": "Test State", 
        "country": "Test Country",
        "bbox": [40.0, -74.0, 40.1, -73.9],
        "timestamp": "2024-01-01 12:00:00",
        "total_businesses": 5,
        "businesses": [
            {
                "id": 1,
                "type": "node",
                "tags": {"amenity": "restaurant", "name": "Test Restaurant"},
                "lat": 40.05,
                "lon": -73.95,
                "business_type": "amenity",
                "business_subtype": "restaurant",
                "name": "Test Restaurant"
            },
            {
                "id": 2,
                "type": "node", 
                "tags": {"shop": "clothing", "name": "Test Shop"},
                "lat": 40.051,
                "lon": -73.951,
                "business_type": "shop",
                "business_subtype": "clothing",
                "name": "Test Shop"
            },
            {
                "id": 3,
                "type": "node",
                "tags": {"office": "company", "name": "Test Office"},
                "lat": 40.052,
                "lon": -73.952,
                "business_type": "office", 
                "business_subtype": "company",
                "name": "Test Office"
            },
            {
                "id": 4,
                "type": "node",
                "tags": {"tourism": "hotel", "name": "Test Hotel"},
                "lat": 40.053,
                "lon": -73.953,
                "business_type": "tourism",
                "business_subtype": "hotel", 
                "name": "Test Hotel"
            },
            {
                "id": 5,
                "type": "node",
                "tags": {"craft": "winery", "name": "Test Winery"},
                "lat": 40.054,
                "lon": -73.954,
                "business_type": "craft",
                "business_subtype": "winery",
                "name": "Test Winery"
            }
        ]
    }


@pytest.fixture
def sample_listings_data():
    """Sample real estate listings data for testing."""
    return pd.DataFrame([
        {
            "lat": 40.050,
            "lon": -73.950,
            "bedrooms": 1,
            "area_sqm": 50,
            "price": 2000,
            "listing_type": "rental"
        },
        {
            "lat": 40.051,
            "lon": -73.951, 
            "bedrooms": 2,
            "area_sqm": 75,
            "price": 3000,
            "listing_type": "rental"
        },
        {
            "lat": 40.052,
            "lon": -73.952,
            "bedrooms": 0,  # studio
            "area_sqm": 35,
            "price": 1500,
            "listing_type": "rental"
        },
        {
            "lat": 40.053,
            "lon": -73.953,
            "bedrooms": 3,
            "area_sqm": 100,
            "price": 500000,
            "listing_type": "sale"
        }
    ])


@pytest.fixture
def sample_downtown_boundary():
    """Sample downtown boundary polygon for testing."""
    # Create a simple rectangular boundary around the test businesses
    return Polygon([
        (-73.96, 40.045),
        (-73.94, 40.045), 
        (-73.94, 40.055),
        (-73.96, 40.055),
        (-73.96, 40.045)
    ])


@pytest.fixture
def sample_business_df():
    """Sample business DataFrame for testing."""
    return pd.DataFrame([
        {"id": 1, "lat": 40.05, "lon": -73.95, "name": "Restaurant", "type": "amenity", "subtype": "restaurant"},
        {"id": 2, "lat": 40.051, "lon": -73.951, "name": "Shop", "type": "shop", "subtype": "clothing"},
        {"id": 3, "lat": 40.052, "lon": -73.952, "name": "Office", "type": "office", "subtype": "company"},
        {"id": 4, "lat": 40.053, "lon": -73.953, "name": "Hotel", "type": "tourism", "subtype": "hotel"},
        {"id": 5, "lat": 40.054, "lon": -73.954, "name": "Winery", "type": "craft", "subtype": "winery"}
    ])


@pytest.fixture
def temp_json_file(sample_business_data):
    """Create a temporary JSON file with sample business data."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_business_data, f)
        temp_file = f.name
    
    yield temp_file
    
    # Cleanup
    if os.path.exists(temp_file):
        os.unlink(temp_file)


@pytest.fixture
def temp_csv_file(sample_listings_data):
    """Create a temporary CSV file with sample listings data."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        sample_listings_data.to_csv(f.name, index=False)
        temp_file = f.name
    
    yield temp_file
    
    # Cleanup
    if os.path.exists(temp_file):
        os.unlink(temp_file)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)