"""
Data validation utilities for DMUR analysis.
"""

import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates input data for DMUR analysis."""
    
    REQUIRED_BUSINESS_FIELDS = ['id', 'lat', 'lon', 'name', 'business_type', 'business_subtype']
    REQUIRED_LISTING_FIELDS = ['lat', 'lon', 'bedrooms', 'area_sqm', 'price']
    
    @classmethod
    def validate_business_data(cls, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate business data structure.
        
        Args:
            data: Business data dictionary
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check top-level structure
        if not isinstance(data, dict):
            errors.append("Data must be a dictionary")
            return False, errors
        
        # Check required top-level fields
        required_top_fields = ['city', 'businesses']
        for field in required_top_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Check businesses array
        businesses = data.get('businesses', [])
        if not isinstance(businesses, list):
            errors.append("'businesses' must be a list")
            return False, errors
        
        if len(businesses) == 0:
            errors.append("No businesses found in data")
            return False, errors
        
        # Check individual business records
        for i, business in enumerate(businesses[:10]):  # Check first 10
            business_errors = cls._validate_business_record(business, i)
            errors.extend(business_errors)
        
        # Check for reasonable coordinate bounds
        coords_errors = cls._validate_coordinates(businesses)
        errors.extend(coords_errors)
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @classmethod
    def validate_listing_data(cls, data: Union[pd.DataFrame, Dict, List]) -> Tuple[bool, List[str]]:
        """
        Validate real estate listing data.
        
        Args:
            data: Listing data (DataFrame, dict, or list)
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Convert to DataFrame if needed
        if isinstance(data, dict):
            df = pd.DataFrame(data)
        elif isinstance(data, list):
            if len(data) == 0:
                errors.append("No listing data provided")
                return False, errors
            df = pd.DataFrame(data)
        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            errors.append(f"Unsupported data type: {type(data)}")
            return False, errors
        
        # Check required fields
        missing_fields = [field for field in cls.REQUIRED_LISTING_FIELDS if field not in df.columns]
        if missing_fields:
            errors.append(f"Missing required fields: {missing_fields}")
        
        # Check data types and ranges
        if 'lat' in df.columns:
            if not pd.api.types.is_numeric_dtype(df['lat']):
                errors.append("'lat' must be numeric")
            elif df['lat'].isna().any():
                errors.append("'lat' contains missing values")
            elif not df['lat'].between(-90, 90).all():
                errors.append("'lat' values must be between -90 and 90")
        
        if 'lon' in df.columns:
            if not pd.api.types.is_numeric_dtype(df['lon']):
                errors.append("'lon' must be numeric")
            elif df['lon'].isna().any():
                errors.append("'lon' contains missing values")
            elif not df['lon'].between(-180, 180).all():
                errors.append("'lon' values must be between -180 and 180")
        
        if 'bedrooms' in df.columns:
            if not pd.api.types.is_numeric_dtype(df['bedrooms']):
                errors.append("'bedrooms' must be numeric")
            elif df['bedrooms'].isna().any():
                errors.append("'bedrooms' contains missing values")
            elif (df['bedrooms'] < 0).any():
                errors.append("'bedrooms' must be non-negative")
        
        if 'area_sqm' in df.columns:
            if not pd.api.types.is_numeric_dtype(df['area_sqm']):
                errors.append("'area_sqm' must be numeric")
            elif df['area_sqm'].isna().any():
                errors.append("'area_sqm' contains missing values")
            elif (df['area_sqm'] <= 0).any():
                errors.append("'area_sqm' must be positive")
        
        if 'price' in df.columns:
            if not pd.api.types.is_numeric_dtype(df['price']):
                errors.append("'price' must be numeric")
            elif df['price'].isna().any():
                errors.append("'price' contains missing values")
            elif (df['price'] <= 0).any():
                errors.append("'price' must be positive")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @classmethod
    def _validate_business_record(cls, business: Dict, index: int) -> List[str]:
        """Validate individual business record."""
        errors = []
        
        if not isinstance(business, dict):
            errors.append(f"Business {index}: must be a dictionary")
            return errors
        
        # Check required fields
        for field in cls.REQUIRED_BUSINESS_FIELDS:
            if field not in business:
                errors.append(f"Business {index}: missing required field '{field}'")
        
        # Check coordinate validity
        if 'lat' in business:
            lat = business['lat']
            if not isinstance(lat, (int, float)):
                errors.append(f"Business {index}: 'lat' must be numeric")
            elif not -90 <= lat <= 90:
                errors.append(f"Business {index}: 'lat' must be between -90 and 90")
        
        if 'lon' in business:
            lon = business['lon']
            if not isinstance(lon, (int, float)):
                errors.append(f"Business {index}: 'lon' must be numeric")
            elif not -180 <= lon <= 180:
                errors.append(f"Business {index}: 'lon' must be between -180 and 180")
        
        return errors
    
    @classmethod
    def _validate_coordinates(cls, businesses: List[Dict]) -> List[str]:
        """Validate coordinate bounds and distribution."""
        errors = []
        
        # Extract coordinates
        lats = []
        lons = []
        
        for business in businesses:
            if 'lat' in business and 'lon' in business:
                lat, lon = business['lat'], business['lon']
                if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                    lats.append(lat)
                    lons.append(lon)
        
        if len(lats) < 3:
            errors.append("Need at least 3 businesses with valid coordinates")
            return errors
        
        # Check coordinate spread
        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        
        if lat_range > 1.0 or lon_range > 1.0:
            errors.append("Coordinate range seems too large (>1 degree), check data quality")
        
        if lat_range < 0.001 or lon_range < 0.001:
            errors.append("Coordinate range seems too small (<0.001 degree), check data quality")
        
        return errors
    
    @classmethod
    def validate_file_path(cls, file_path: Union[str, Path], must_exist: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Validate file path.
        
        Args:
            file_path: Path to validate
            must_exist: Whether file must already exist
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            path = Path(file_path)
            
            if must_exist and not path.exists():
                return False, f"File does not exist: {path}"
            
            if must_exist and not path.is_file():
                return False, f"Path is not a file: {path}"
            
            if not must_exist:
                # Check if parent directory exists
                if not path.parent.exists():
                    return False, f"Parent directory does not exist: {path.parent}"
                
                # Check if parent is writable
                if not path.parent.is_dir():
                    return False, f"Parent is not a directory: {path.parent}"
            
            return True, None
            
        except Exception as e:
            return False, f"Invalid path: {e}"