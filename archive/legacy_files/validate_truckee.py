#!/usr/bin/env python3
"""
Validate Truckee downtown boundaries against known landmarks
"""

import json
from shapely.geometry import Point, shape

def validate_truckee_boundaries(geojson_file):
    """Validate if Truckee downtown boundaries make sense"""
    
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
    
    print("=== Truckee Downtown Boundary Validation ===")
    print(f"Area: {data['properties']['downtown_area_km2']:.2f} km²")
    print(f"Businesses included: {data['properties']['downtown_businesses']}")
    
    # Known downtown Truckee landmarks and their approximate coordinates
    landmarks = {
        "Truckee Train Depot/Downtown": (39.3275, -120.1838),
        "Historic Downtown Truckee": (39.3275, -120.1830),
        "Donner Pass Road (main street)": (39.3270, -120.1850),
        "Commercial Row": (39.3278, -120.1825),
        "Truckee River": (39.3265, -120.1840),
        "Town Square": (39.3280, -120.1820),
        "Old Town Truckee": (39.3275, -120.1835),
    }
    
    # Test points outside expected downtown
    outside_points = {
        "Northstar California (ski resort)": (39.2583, -120.1194),
        "Truckee Tahoe Airport": (39.3200, -120.1400),
        "Lake Tahoe (south)": (39.3000, -120.1500),
        "Donner Lake (west)": (39.3200, -120.2400),
    }
    
    print("\n=== Landmark Validation ===")
    print("Expected INSIDE downtown:")
    inside_count = 0
    total_landmarks = len(landmarks)
    
    for name, (lat, lon) in landmarks.items():
        point = Point(lon, lat)
        is_inside = downtown_boundary.contains(point)
        status = "✓ INSIDE" if is_inside else "✗ OUTSIDE"
        print(f"  {name}: {status} ({lat:.4f}, {lon:.4f})")
        if is_inside:
            inside_count += 1
    
    print(f"\nLandmarks inside: {inside_count}/{total_landmarks} ({inside_count/total_landmarks*100:.1f}%)")
    
    print("\nExpected OUTSIDE downtown:")
    outside_count = 0
    total_outside = len(outside_points)
    
    for name, (lat, lon) in outside_points.items():
        point = Point(lon, lat)
        is_inside = downtown_boundary.contains(point)
        status = "✗ INSIDE" if is_inside else "✓ OUTSIDE"
        print(f"  {name}: {status} ({lat:.4f}, {lon:.4f})")
        if not is_inside:
            outside_count += 1
    
    print(f"\nPoints correctly outside: {outside_count}/{total_outside} ({outside_count/total_outside*100:.1f}%)")
    
    # Get boundary extent
    bounds = downtown_boundary.bounds
    print(f"\n=== Boundary Extent ===")
    print(f"West:  {bounds[0]:.4f}°")
    print(f"South: {bounds[1]:.4f}°") 
    print(f"East:  {bounds[2]:.4f}°")
    print(f"North: {bounds[3]:.4f}°")
    
    # Expected downtown boundaries for Truckee
    expected_center = (-120.1830, 39.3275)  # Historic downtown area
    
    # Calculate center
    center_lon = (bounds[0] + bounds[2]) / 2
    center_lat = (bounds[1] + bounds[3]) / 2
    
    print(f"\n=== Center Point ===")
    print(f"Expected center: {expected_center[1]:.4f}°N, {expected_center[0]:.4f}°W")
    print(f"Actual center: {center_lat:.4f}°N, {center_lon:.4f}°W")
    
    # Distance from expected center
    import math
    distance = math.sqrt((center_lat - expected_center[1])**2 + (center_lon - expected_center[0])**2)
    print(f"Distance from expected: {distance:.4f}° (~{distance * 111:.1f} km)")
    
    # Overall assessment
    print(f"\n=== Assessment ===")
    landmark_score = inside_count / total_landmarks
    boundary_score = outside_count / total_outside
    overall_score = (landmark_score + boundary_score) / 2
    
    if overall_score >= 0.8:
        assessment = "EXCELLENT - boundaries align well with known downtown"
    elif overall_score >= 0.6:
        assessment = "GOOD - boundaries mostly align with downtown"
    elif overall_score >= 0.4:
        assessment = "FAIR - boundaries partially align with downtown"
    else:
        assessment = "POOR - boundaries do not align well with downtown"
    
    print(f"Overall score: {overall_score:.2f} - {assessment}")
    
    # Truckee-specific notes
    print(f"\n=== Truckee-Specific Notes ===")
    print(f"Truckee is a small mountain town with historic downtown along Donner Pass Road")
    print(f"Main commercial area is compact and walkable")
    print(f"Downtown area size of {data['properties']['downtown_area_km2']:.2f} km² seems {'reasonable' if data['properties']['downtown_area_km2'] < 10 else 'large'} for Truckee")

if __name__ == "__main__":
    validate_truckee_boundaries("truckee_downtown.geojson")