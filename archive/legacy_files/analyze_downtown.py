#!/usr/bin/env python3
"""
Analyze business density to identify downtown area and generate GeoJSON boundaries
"""

import json
import numpy as np
from typing import List, Dict, Tuple
import argparse
from scipy.stats import gaussian_kde
from scipy.spatial import ConvexHull
from shapely.geometry import Point, Polygon, MultiPoint
from shapely.ops import unary_union
import warnings
warnings.filterwarnings('ignore')


class DowntownAnalyzer:
    """Analyze business density to identify downtown areas"""
    
    def __init__(self, businesses_file: str):
        """
        Initialize analyzer with business data
        
        Args:
            businesses_file: Path to JSON file with business data
        """
        with open(businesses_file, 'r') as f:
            self.data = json.load(f)
        
        self.businesses = self.data['businesses']
        self.city_name = self.data.get('city', 'Unknown')
        self.bbox = self.data['bbox']
        
        # Extract coordinates
        self.coords = [(b['lon'], b['lat']) for b in self.businesses 
                      if 'lat' in b and 'lon' in b]
        
        print(f"Loaded {len(self.coords)} businesses from {self.city_name}")
    
    def calculate_density_grid(self, resolution: int = 100) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate business density using kernel density estimation
        
        Args:
            resolution: Grid resolution for density calculation
            
        Returns:
            Tuple of (X grid, Y grid, density values)
        """
        if not self.coords:
            raise ValueError("No coordinates available")
        
        # Convert to numpy array
        points = np.array(self.coords)
        
        # Create grid
        min_lon, max_lon = points[:, 0].min(), points[:, 0].max()
        min_lat, max_lat = points[:, 1].min(), points[:, 1].max()
        
        # Add padding
        lon_padding = (max_lon - min_lon) * 0.1
        lat_padding = (max_lat - min_lat) * 0.1
        
        xx = np.linspace(min_lon - lon_padding, max_lon + lon_padding, resolution)
        yy = np.linspace(min_lat - lat_padding, max_lat + lat_padding, resolution)
        X, Y = np.meshgrid(xx, yy)
        
        # Calculate KDE
        print("Calculating density using kernel density estimation...")
        kde = gaussian_kde(points.T)
        
        # Evaluate on grid
        positions = np.vstack([X.ravel(), Y.ravel()])
        Z = kde(positions).reshape(X.shape)
        
        return X, Y, Z
    
    def find_downtown_area(self, X: np.ndarray, Y: np.ndarray, Z: np.ndarray, 
                          threshold_percentile: float = 75) -> Polygon:
        """
        Identify downtown area based on density threshold
        
        Args:
            X: Longitude grid
            Y: Latitude grid
            Z: Density values
            threshold_percentile: Percentile threshold for high density (0-100)
            
        Returns:
            Polygon representing downtown boundary
        """
        # Find high density threshold
        threshold = np.percentile(Z, threshold_percentile)
        
        # Get points above threshold
        high_density_mask = Z > threshold
        high_density_points = []
        
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                if high_density_mask[i, j]:
                    high_density_points.append((X[i, j], Y[i, j]))
        
        if len(high_density_points) < 3:
            print("Warning: Not enough high-density points found, lowering threshold")
            threshold_percentile = max(50, threshold_percentile - 10)
            return self.find_downtown_area(X, Y, Z, threshold_percentile)
        
        print(f"Found {len(high_density_points)} high-density grid points")
        
        # Create convex hull
        points = MultiPoint(high_density_points)
        downtown_polygon = points.convex_hull
        
        # Optionally create a more refined boundary using alpha shape
        # or concave hull for better fitting
        downtown_polygon = self.refine_boundary(high_density_points, self.coords)
        
        return downtown_polygon
    
    def refine_boundary(self, high_density_points: List[Tuple], 
                       business_coords: List[Tuple]) -> Polygon:
        """
        Refine downtown boundary using business locations
        
        Args:
            high_density_points: Grid points with high density
            business_coords: Actual business coordinates
            
        Returns:
            Refined polygon boundary
        """
        # Filter businesses within high-density area
        high_density_polygon = MultiPoint(high_density_points).convex_hull
        
        downtown_businesses = []
        for coord in business_coords:
            point = Point(coord)
            if high_density_polygon.contains(point):
                downtown_businesses.append(coord)
        
        if len(downtown_businesses) < 3:
            return high_density_polygon
        
        print(f"Found {len(downtown_businesses)} businesses in high-density area")
        
        # Create refined boundary using actual business locations
        # Using convex hull for simplicity, but could use alpha shapes for concave boundaries
        downtown_points = MultiPoint(downtown_businesses)
        refined_boundary = downtown_points.convex_hull
        
        # Buffer slightly to include edge businesses
        refined_boundary = refined_boundary.buffer(0.002)  # ~200m buffer
        
        return refined_boundary
    
    def calculate_statistics(self, downtown_polygon: Polygon) -> Dict:
        """
        Calculate statistics about the downtown area
        
        Args:
            downtown_polygon: Polygon representing downtown
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_businesses': len(self.businesses),
            'downtown_businesses': 0,
            'downtown_area_km2': 0,
            'business_types': {}
        }
        
        # Count businesses in downtown
        downtown_businesses = []
        for business in self.businesses:
            if 'lat' in business and 'lon' in business:
                point = Point(business['lon'], business['lat'])
                if downtown_polygon.contains(point):
                    downtown_businesses.append(business)
                    business_type = business.get('business_type', 'unknown')
                    stats['business_types'][business_type] = \
                        stats['business_types'].get(business_type, 0) + 1
        
        stats['downtown_businesses'] = len(downtown_businesses)
        
        # Calculate area (approximate)
        # Convert to meters using simple equirectangular projection
        center_lat = downtown_polygon.centroid.y
        lat_to_m = 111000  # meters per degree latitude
        lon_to_m = 111000 * np.cos(np.radians(center_lat))  # meters per degree longitude
        
        # Transform to meters
        coords_m = [(lon * lon_to_m, lat * lat_to_m) 
                   for lon, lat in downtown_polygon.exterior.coords]
        polygon_m = Polygon(coords_m)
        stats['downtown_area_km2'] = polygon_m.area / 1000000
        
        # Calculate density
        if stats['downtown_area_km2'] > 0:
            stats['business_density_per_km2'] = \
                stats['downtown_businesses'] / stats['downtown_area_km2']
        
        return stats
    
    def create_geojson(self, downtown_polygon: Polygon, stats: Dict, 
                      output_file: str = 'downtown_boundary.geojson'):
        """
        Create GeoJSON file with downtown boundary
        
        Args:
            downtown_polygon: Polygon representing downtown
            stats: Statistics dictionary
            output_file: Output filename
        """
        # Create GeoJSON feature
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [list(downtown_polygon.exterior.coords)]
            },
            "properties": {
                "city": self.city_name,
                "downtown_businesses": stats['downtown_businesses'],
                "total_businesses": stats['total_businesses'],
                "area_km2": round(stats['downtown_area_km2'], 2),
                "business_density_per_km2": round(stats.get('business_density_per_km2', 0), 1),
                "business_types": stats['business_types']
            }
        }
        
        # Create feature collection
        geojson = {
            "type": "FeatureCollection",
            "features": [feature]
        }
        
        # Add business points as separate features (optional)
        for business in self.businesses:
            if 'lat' in business and 'lon' in business:
                point = Point(business['lon'], business['lat'])
                is_downtown = downtown_polygon.contains(point)
                
                business_feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [business['lon'], business['lat']]
                    },
                    "properties": {
                        "name": business.get('name', 'Unknown'),
                        "type": business.get('business_type', 'unknown'),
                        "subtype": business.get('business_subtype', 'unknown'),
                        "is_downtown": is_downtown
                    }
                }
                geojson["features"].append(business_feature)
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        print(f"Saved GeoJSON to {output_file}")
    
    def analyze(self, threshold_percentile: float = 75, 
               output_file: str = 'downtown_boundary.geojson'):
        """
        Run complete downtown analysis
        
        Args:
            threshold_percentile: Percentile threshold for high density
            output_file: Output GeoJSON filename
        """
        print(f"\nAnalyzing downtown area for {self.city_name}...")
        
        # Calculate density
        X, Y, Z = self.calculate_density_grid()
        
        # Find downtown area
        downtown_polygon = self.find_downtown_area(X, Y, Z, threshold_percentile)
        
        # Calculate statistics
        stats = self.calculate_statistics(downtown_polygon)
        
        # Print results
        print(f"\n=== Downtown Analysis Results ===")
        print(f"City: {self.city_name}")
        print(f"Total businesses: {stats['total_businesses']}")
        print(f"Downtown businesses: {stats['downtown_businesses']} "
              f"({100*stats['downtown_businesses']/stats['total_businesses']:.1f}%)")
        print(f"Downtown area: {stats['downtown_area_km2']:.2f} km²")
        print(f"Business density: {stats.get('business_density_per_km2', 0):.1f} per km²")
        print(f"\nBusiness types in downtown:")
        for btype, count in sorted(stats['business_types'].items(), 
                                  key=lambda x: x[1], reverse=True):
            print(f"  {btype}: {count}")
        
        # Create GeoJSON
        self.create_geojson(downtown_polygon, stats, output_file)
        
        return downtown_polygon, stats


def main():
    parser = argparse.ArgumentParser(description='Analyze business density to identify downtown')
    parser.add_argument('input', help='Input JSON file with business data')
    parser.add_argument('--output', default='downtown_boundary.geojson',
                      help='Output GeoJSON filename')
    parser.add_argument('--threshold', type=float, default=75,
                      help='Density threshold percentile (0-100, default: 75)')
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = DowntownAnalyzer(args.input)
    
    # Run analysis
    analyzer.analyze(threshold_percentile=args.threshold, output_file=args.output)


if __name__ == "__main__":
    main()