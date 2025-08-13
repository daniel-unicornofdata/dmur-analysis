#!/usr/bin/env python3
"""
Generic validation script for downtown boundaries
"""

import json
import sys
from shapely.geometry import Point, shape

def validate_downtown_boundaries(geojson_file, expected_center=None, expected_size_range=None):
    """
    Generic validation for downtown boundaries
    
    Args:
        geojson_file: Path to GeoJSON file
        expected_center: (lat, lon) of expected downtown center
        expected_size_range: (min_km2, max_km2) expected size range
    """
    
    # Load our generated downtown GeoJSON
    with open(geojson_file, 'r') as f:
        data = json.load(f)
    
    # Extract the downtown boundary polygon
    downtown_boundary = None
    for feature in data['features']:
        if feature['properties'].get('type') == 'downtown_boundary':
            downtown_boundary = shape(feature['geometry'])
            break
    
    if not downtown_boundary:
        print("No downtown boundary found in GeoJSON")
        return
    
    city_name = data['properties'].get('city', 'Unknown City')
    area_km2 = data['properties'].get('downtown_area_km2', 0)
    business_count = data['properties'].get('downtown_businesses', 0)
    
    print(f"=== {city_name} Downtown Boundary Validation ===")
    print(f"Area: {area_km2:.2f} km²")
    print(f"Businesses included: {business_count}")
    
    # Get boundary extent
    bounds = downtown_boundary.bounds
    print(f"\n=== Boundary Extent ===")
    print(f"West:  {bounds[0]:.4f}°")
    print(f"South: {bounds[1]:.4f}°") 
    print(f"East:  {bounds[2]:.4f}°")
    print(f"North: {bounds[3]:.4f}°")
    
    # Calculate center
    center_lon = (bounds[0] + bounds[2]) / 2
    center_lat = (bounds[1] + bounds[3]) / 2
    print(f"\n=== Center Point ===")
    print(f"Computed center: {center_lat:.4f}°N, {center_lon:.4f}°W")
    
    # Validate against expected center if provided
    if expected_center:
        expected_lat, expected_lon = expected_center
        print(f"Expected center: {expected_lat:.4f}°N, {expected_lon:.4f}°W")
        
        # Distance from expected center
        import math
        distance = math.sqrt((center_lat - expected_lat)**2 + (center_lon - expected_lon)**2)
        print(f"Distance from expected: {distance:.4f}° (~{distance * 111:.1f} km)")
        
        center_score = 1.0 if distance < 0.02 else max(0.0, 1.0 - distance / 0.05)
    else:
        center_score = 1.0  # No expected center to compare against
    
    # Validate size if range provided
    if expected_size_range:
        min_size, max_size = expected_size_range
        print(f"\n=== Size Validation ===")
        print(f"Expected size range: {min_size:.1f} - {max_size:.1f} km²")
        print(f"Actual size: {area_km2:.2f} km²")
        
        if min_size <= area_km2 <= max_size:
            size_score = 1.0
            size_status = "✓ WITHIN EXPECTED RANGE"
        elif area_km2 < min_size:
            size_score = max(0.0, area_km2 / min_size)
            size_status = "⚠ SMALLER THAN EXPECTED"
        else:
            size_score = max(0.0, max_size / area_km2)
            size_status = "⚠ LARGER THAN EXPECTED"
        
        print(f"Size assessment: {size_status}")
    else:
        size_score = 1.0  # No size range to compare against
    
    # Business density assessment
    density = business_count / area_km2
    print(f"\n=== Business Density ===")
    print(f"Density: {density:.1f} businesses/km²")
    
    # Typical downtown densities range from 50-500 businesses/km²
    if 50 <= density <= 500:
        density_score = 1.0
        density_status = "✓ TYPICAL DOWNTOWN DENSITY"
    elif density < 50:
        density_score = max(0.5, density / 50)
        density_status = "⚠ LOW DENSITY (might be too large area)"
    else:
        density_score = max(0.5, 500 / density)
        density_status = "⚠ HIGH DENSITY (might be too small area)"
    
    print(f"Density assessment: {density_status}")
    
    # Overall assessment
    print(f"\n=== Overall Assessment ===")
    overall_score = (center_score + size_score + density_score) / 3
    
    print(f"Center accuracy: {center_score:.2f}")
    print(f"Size appropriateness: {size_score:.2f}")
    print(f"Density reasonableness: {density_score:.2f}")
    print(f"Overall score: {overall_score:.2f}")
    
    if overall_score >= 0.8:
        assessment = "EXCELLENT - boundaries appear accurate"
    elif overall_score >= 0.6:
        assessment = "GOOD - boundaries mostly reasonable"
    elif overall_score >= 0.4:
        assessment = "FAIR - boundaries may need adjustment"
    else:
        assessment = "POOR - boundaries likely need significant adjustment"
    
    print(f"Assessment: {assessment}")
    
    # Recommendations
    print(f"\n=== Recommendations ===")
    if area_km2 > 50:
        print("• Consider increasing density threshold to focus on core downtown")
    elif area_km2 < 1:
        print("• Consider decreasing density threshold to capture more downtown area")
    
    if density < 50:
        print("• Downtown area may be too large - try higher density threshold")
    elif density > 500:
        print("• Downtown area may be too small - try lower density threshold")
    
    print("• Validate results by checking if known landmarks are included")
    print("• Consider manual focus area if auto-detection is inaccurate")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_generic.py <geojson_file> [expected_lat expected_lon] [min_size_km2 max_size_km2]")
        print("Example: python3 validate_generic.py downtown.geojson")
        print("Example: python3 validate_generic.py downtown.geojson 39.3275 -120.1830 2 8")
        return 1
    
    geojson_file = sys.argv[1]
    
    expected_center = None
    if len(sys.argv) >= 4:
        expected_center = (float(sys.argv[2]), float(sys.argv[3]))
    
    expected_size_range = None
    if len(sys.argv) >= 6:
        expected_size_range = (float(sys.argv[4]), float(sys.argv[5]))
    
    validate_downtown_boundaries(geojson_file, expected_center, expected_size_range)
    return 0

if __name__ == "__main__":
    exit(main())