#!/usr/bin/env python3
"""
Validate downtown boundaries against known landmarks
"""

import json
from shapely.geometry import Point, shape

def validate_downtown_boundaries(geojson_file):
    """Validate if downtown boundaries make sense"""
    
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
    
    print("=== Downtown Boundary Validation ===")
    print(f"Area: {data['properties']['downtown_area_km2']:.2f} km²")
    print(f"Businesses included: {data['properties']['downtown_businesses']}")
    
    # Known downtown Palm Springs landmarks and their approximate coordinates
    landmarks = {
        "Palm Springs City Hall": (33.8272, -116.5439),
        "Desert Museum (near downtown core)": (33.8238, -116.5452),
        "Downtown Convention Center": (33.8223, -116.5474),
        "Palm Canyon Drive & Tahquitz Canyon Way": (33.8206, -116.5436),
        "Indian Canyon Drive & Ramon Road": (33.7976, -116.5464),
        "Indian Canyon Drive & Alejo Road": (33.8518, -116.5459),
        "VillageFest area (Palm Canyon Dr)": (33.8200, -116.5440),
        "Moorten Botanical Garden": (33.8139, -116.5503),
    }
    
    # Test points outside expected downtown
    outside_points = {
        "Palm Springs Airport": (33.8297, -116.5067),
        "Indian Canyons (far south)": (33.7600, -116.5400),
        "Uptown District (far north)": (33.8700, -116.5500),
        "Desert Hills area (east)": (33.8200, -116.5000),
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
    
    # Known downtown boundaries
    expected_south = 33.797  # Ramon Road
    expected_north = 33.851  # Alejo Road
    expected_west = -116.570  # Approximate western boundary
    expected_east = -116.520  # Approximate eastern boundary
    
    print(f"\n=== Boundary Comparison ===")
    print(f"Expected North (Alejo Rd): ~{expected_north:.3f}° | Actual: {bounds[3]:.3f}°")
    print(f"Expected South (Ramon Rd): ~{expected_south:.3f}° | Actual: {bounds[1]:.3f}°")
    print(f"Expected range: West {expected_west:.3f}° to East {expected_east:.3f}°")
    print(f"Actual range: West {bounds[0]:.3f}° to East {bounds[2]:.3f}°")
    
    # Calculate center
    center_lon = (bounds[0] + bounds[2]) / 2
    center_lat = (bounds[1] + bounds[3]) / 2
    expected_center = (-116.5453, 33.8303)
    
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

if __name__ == "__main__":
    validate_downtown_boundaries("palm_springs_downtown.geojson")