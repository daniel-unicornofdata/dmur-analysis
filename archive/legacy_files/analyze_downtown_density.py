#!/usr/bin/env python3
"""
Analyze business density to identify downtown boundaries
"""

import json
import numpy as np
import pandas as pd
from sklearn.neighbors import KernelDensity
from sklearn.cluster import DBSCAN
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
# from shapely.concave_hull import concave_hull  # Not available in all versions
import geopandas as gpd
from scipy.spatial import ConvexHull
import argparse
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict, Optional


class DowntownAnalyzer:
    """Analyze business density to identify downtown boundaries"""
    
    def __init__(self, business_data_file: str):
        """
        Initialize analyzer with business data
        
        Args:
            business_data_file: Path to JSON file with business data
        """
        self.business_data_file = business_data_file
        self.businesses_df = None
        self.density_grid = None
        self.density_coords = None
        self.downtown_boundary = None
        
    def load_business_data(self, commercial_only=False, focus_area=None):
        """Load and prepare business data"""
        print("Loading business data...")
        
        with open(self.business_data_file, 'r') as f:
            data = json.load(f)
        
        # Extract business coordinates and types
        businesses = []
        
        # Define core commercial business types for downtown analysis
        commercial_types = {
            'shop', 'amenity', 'office', 'tourism', 'craft', 'healthcare'
        }
        
        # Define commercial amenity subtypes (exclude parks, public facilities, etc.)
        commercial_amenities = {
            'restaurant', 'cafe', 'bar', 'pub', 'fast_food', 'food_court', 'ice_cream',
            'bank', 'atm', 'cinema', 'theatre', 'nightclub', 'casino', 'pharmacy',
            'clinic', 'doctors', 'dentist', 'fuel', 'car_wash', 'car_rental',
            'post_office', 'courier', 'internet_cafe', 'library', 'coworking_space'
        }
        
        for business in data['businesses']:
            if business.get('lat') and business.get('lon'):
                # Filter for commercial businesses if requested
                if commercial_only:
                    btype = business['business_type']
                    subtype = business['business_subtype']
                    
                    # Skip non-commercial types
                    if btype not in commercial_types:
                        continue
                    
                    # For amenities, only include commercial ones
                    if btype == 'amenity' and subtype not in commercial_amenities:
                        continue
                    
                    # Skip residential buildings, parks, etc.
                    if btype == 'building' and subtype not in ['commercial', 'retail', 'office', 'hotel']:
                        continue
                    
                    if btype == 'leisure' and subtype not in ['fitness_centre', 'sports_centre', 'bowling_alley']:
                        continue
                
                # Apply focus area filter if specified
                if focus_area:
                    lat, lon = business['lat'], business['lon']
                    min_lat, min_lon, max_lat, max_lon = focus_area
                    if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                        continue
                
                businesses.append({
                    'id': business['id'],
                    'lat': business['lat'],
                    'lon': business['lon'],
                    'name': business['name'],
                    'type': business['business_type'],
                    'subtype': business['business_subtype']
                })
        
        self.businesses_df = pd.DataFrame(businesses)
        print(f"Loaded {len(self.businesses_df)} businesses with coordinates")
        
        # Print summary by business type
        type_counts = self.businesses_df['type'].value_counts()
        print("\nBusiness types:")
        for btype, count in type_counts.head(10).items():
            print(f"  {btype}: {count}")
    
    def calculate_density_grid(self, grid_size: float = 0.002, bandwidth: float = 0.005):
        """
        Calculate business density on a grid using kernel density estimation
        
        Args:
            grid_size: Size of grid cells in degrees
            bandwidth: Bandwidth for kernel density estimation
        """
        print("Calculating business density...")
        
        # Get coordinate bounds
        min_lat, max_lat = self.businesses_df['lat'].min(), self.businesses_df['lat'].max()
        min_lon, max_lon = self.businesses_df['lon'].min(), self.businesses_df['lon'].max()
        
        # Add padding
        padding = 0.01
        min_lat -= padding
        max_lat += padding
        min_lon -= padding
        max_lon += padding
        
        # Create coordinate grid
        lat_range = np.arange(min_lat, max_lat, grid_size)
        lon_range = np.arange(min_lon, max_lon, grid_size)
        lon_grid, lat_grid = np.meshgrid(lon_range, lat_range)
        
        # Flatten for KDE
        grid_coords = np.column_stack([lat_grid.ravel(), lon_grid.ravel()])
        
        # Prepare business coordinates for KDE
        business_coords = self.businesses_df[['lat', 'lon']].values
        
        # Apply kernel density estimation
        kde = KernelDensity(bandwidth=bandwidth, kernel='gaussian')
        kde.fit(business_coords)
        
        # Calculate density at grid points
        log_density = kde.score_samples(grid_coords)
        density = np.exp(log_density)
        
        # Reshape back to grid
        self.density_grid = density.reshape(lat_grid.shape)
        self.density_coords = (lat_grid, lon_grid)
        
        print(f"Density grid: {self.density_grid.shape}")
        print(f"Density range: {density.min():.6f} to {density.max():.6f}")
    
    def identify_high_density_areas(self, density_threshold_percentile: float = 80):
        """
        Identify high-density areas using density threshold
        
        Args:
            density_threshold_percentile: Percentile threshold for high density
        """
        print("Identifying high-density areas...")
        
        # Calculate threshold
        threshold = np.percentile(self.density_grid.ravel(), density_threshold_percentile)
        print(f"Using density threshold: {threshold:.6f} ({density_threshold_percentile}th percentile)")
        
        # Find high-density grid points
        lat_grid, lon_grid = self.density_coords
        high_density_mask = self.density_grid >= threshold
        
        # Extract coordinates of high-density points
        high_density_lats = lat_grid[high_density_mask]
        high_density_lons = lon_grid[high_density_mask]
        
        print(f"Found {len(high_density_lats)} high-density grid points")
        
        if len(high_density_lats) < 3:
            print("Warning: Too few high-density points found. Lowering threshold...")
            threshold = np.percentile(self.density_grid.ravel(), 70)
            high_density_mask = self.density_grid >= threshold
            high_density_lats = lat_grid[high_density_mask]
            high_density_lons = lon_grid[high_density_mask]
            print(f"Using lower threshold: {threshold:.6f} - found {len(high_density_lats)} points")
        
        return high_density_lats, high_density_lons
    
    def create_downtown_boundary(self, high_density_lats, high_density_lons, 
                                alpha: float = 0.1, buffer_distance: float = 0.003):
        """
        Create downtown boundary using concave hull
        
        Args:
            high_density_lats: Latitudes of high-density points
            high_density_lons: Longitudes of high-density points
            alpha: Alpha parameter for concave hull (lower = more concave)
            buffer_distance: Buffer distance around boundary
        """
        print("Creating downtown boundary...")
        
        # Create points
        points = [Point(lon, lat) for lat, lon in zip(high_density_lats, high_density_lons)]
        
        try:
            # Use alpha shapes approach (simplified concave hull)
            from scipy.spatial import Delaunay
            coords = np.column_stack([high_density_lons, high_density_lats])
            
            # Create Delaunay triangulation
            tri = Delaunay(coords)
            
            # Filter triangles by edge length (alpha parameter)
            triangles = []
            for simplex in tri.simplices:
                triangle_coords = coords[simplex]
                # Calculate max edge length
                edge_lengths = []
                for i in range(3):
                    p1, p2 = triangle_coords[i], triangle_coords[(i+1)%3]
                    edge_lengths.append(np.sqrt(np.sum((p1-p2)**2)))
                max_edge = max(edge_lengths)
                
                # Include triangle if all edges are below alpha threshold
                if max_edge < alpha:
                    triangles.append(triangle_coords)
            
            if triangles:
                # Create union of triangles
                triangle_polygons = [Polygon(t) for t in triangles]
                boundary = unary_union(triangle_polygons)
                print("Created alpha shape boundary")
            else:
                raise ValueError("No triangles passed alpha test")
                
        except Exception as e:
            print(f"Alpha shape failed: {e}")
            print("Falling back to convex hull...")
            
            # Fall back to convex hull
            coords = np.column_stack([high_density_lons, high_density_lats])
            hull = ConvexHull(coords)
            hull_points = coords[hull.vertices]
            boundary = Polygon(hull_points)
            print("Created convex hull boundary")
        
        # Apply buffer to smooth boundary
        if buffer_distance > 0:
            boundary = boundary.buffer(buffer_distance)
            print(f"Applied buffer of {buffer_distance} degrees")
        
        self.downtown_boundary = boundary
        
        # Calculate area (approximate)
        area_deg2 = boundary.area
        # Rough conversion to km2 (at ~33.8°N latitude)
        lat_avg = np.mean(high_density_lats)
        km_per_deg_lat = 111.0
        km_per_deg_lon = 111.0 * np.cos(np.radians(lat_avg))
        area_km2 = area_deg2 * km_per_deg_lat * km_per_deg_lon
        
        print(f"Downtown boundary area: {area_km2:.2f} km²")
        
        return boundary
    
    def get_businesses_in_downtown(self) -> pd.DataFrame:
        """Get businesses within the downtown boundary"""
        if self.downtown_boundary is None:
            raise ValueError("Downtown boundary not created yet")
        
        # Create points for all businesses
        business_points = [Point(row['lon'], row['lat']) for _, row in self.businesses_df.iterrows()]
        
        # Check which businesses are in downtown
        in_downtown = [self.downtown_boundary.contains(point) for point in business_points]
        
        downtown_businesses = self.businesses_df[in_downtown].copy()
        print(f"Found {len(downtown_businesses)} businesses in downtown area")
        
        return downtown_businesses
    
    def create_geojson(self, output_file: str):
        """Create GeoJSON file with downtown boundary and business data"""
        print(f"Creating GeoJSON output: {output_file}")
        
        if self.downtown_boundary is None:
            raise ValueError("Downtown boundary not created yet")
        
        # Get downtown businesses
        downtown_businesses = self.get_businesses_in_downtown()
        
        # Create GeoJSON structure
        geojson = {
            "type": "FeatureCollection",
            "properties": {
                "city": "Palm Springs",
                "analysis_timestamp": pd.Timestamp.now().isoformat(),
                "total_businesses": len(self.businesses_df),
                "downtown_businesses": len(downtown_businesses),
                "downtown_area_km2": round(self.downtown_boundary.area * 111.0 * 111.0 * np.cos(np.radians(33.8)), 2)
            },
            "features": []
        }
        
        # Add downtown boundary
        if isinstance(self.downtown_boundary, Polygon):
            coords = [list(self.downtown_boundary.exterior.coords)]
        elif isinstance(self.downtown_boundary, MultiPolygon):
            coords = []
            for poly in self.downtown_boundary.geoms:
                coords.append(list(poly.exterior.coords))
        
        boundary_feature = {
            "type": "Feature",
            "properties": {
                "name": "Downtown Palm Springs",
                "type": "downtown_boundary",
                "business_count": len(downtown_businesses)
            },
            "geometry": {
                "type": "Polygon" if isinstance(self.downtown_boundary, Polygon) else "MultiPolygon",
                "coordinates": coords if isinstance(self.downtown_boundary, Polygon) else [coords]
            }
        }
        geojson["features"].append(boundary_feature)
        
        # Add downtown businesses as points
        for _, business in downtown_businesses.iterrows():
            business_feature = {
                "type": "Feature",
                "properties": {
                    "name": business['name'],
                    "business_type": business['type'],
                    "business_subtype": business['subtype'],
                    "osm_id": business['id']
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [business['lon'], business['lat']]
                }
            }
            geojson["features"].append(business_feature)
        
        # Save GeoJSON
        with open(output_file, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        print(f"Saved GeoJSON with {len(geojson['features'])} features")
        
        # Print summary
        print(f"\nDowntown Analysis Summary:")
        print(f"  Total businesses in city: {len(self.businesses_df)}")
        print(f"  Businesses in downtown: {len(downtown_businesses)}")
        print(f"  Downtown density: {len(downtown_businesses)/self.downtown_boundary.area:.1f} businesses/deg²")
        
        # Business types in downtown
        downtown_types = downtown_businesses['type'].value_counts()
        print(f"\nTop business types in downtown:")
        for btype, count in downtown_types.head(5).items():
            print(f"  {btype}: {count}")
    
    def plot_results(self, output_file: str = "downtown_analysis.png"):
        """Create visualization of the analysis results"""
        print(f"Creating visualization: {output_file}")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
        
        # Plot 1: Density heatmap
        lat_grid, lon_grid = self.density_coords
        im = ax1.contourf(lon_grid, lat_grid, self.density_grid, levels=20, cmap='YlOrRd')
        ax1.scatter(self.businesses_df['lon'], self.businesses_df['lat'], 
                   s=1, c='blue', alpha=0.3, label='All businesses')
        
        if self.downtown_boundary:
            # Plot downtown boundary
            if isinstance(self.downtown_boundary, Polygon):
                x, y = self.downtown_boundary.exterior.xy
                ax1.plot(x, y, 'r-', linewidth=2, label='Downtown boundary')
            
        ax1.set_xlabel('Longitude')
        ax1.set_ylabel('Latitude')
        ax1.set_title('Business Density Heatmap')
        ax1.legend()
        plt.colorbar(im, ax=ax1, label='Density')
        
        # Plot 2: Downtown businesses
        downtown_businesses = self.get_businesses_in_downtown()
        ax2.scatter(self.businesses_df['lon'], self.businesses_df['lat'], 
                   s=1, c='lightgray', alpha=0.5, label='All businesses')
        ax2.scatter(downtown_businesses['lon'], downtown_businesses['lat'], 
                   s=3, c='red', alpha=0.7, label='Downtown businesses')
        
        if self.downtown_boundary:
            if isinstance(self.downtown_boundary, Polygon):
                x, y = self.downtown_boundary.exterior.xy
                ax2.plot(x, y, 'r-', linewidth=2, label='Downtown boundary')
        
        ax2.set_xlabel('Longitude')
        ax2.set_ylabel('Latitude')
        ax2.set_title('Downtown Business Locations')
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved visualization to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Analyze business density to identify downtown boundaries')
    parser.add_argument('--input', default='palm_springs_businesses.json',
                       help='Input JSON file with business data')
    parser.add_argument('--output', default='palm_springs_downtown.geojson',
                       help='Output GeoJSON file')
    parser.add_argument('--plot', default='palm_springs_analysis.png',
                       help='Output plot file')
    parser.add_argument('--density-threshold', type=float, default=80,
                       help='Density threshold percentile (default: 80)')
    parser.add_argument('--bandwidth', type=float, default=0.005,
                       help='KDE bandwidth (default: 0.005)')
    parser.add_argument('--grid-size', type=float, default=0.002,
                       help='Grid size for density calculation (default: 0.002)')
    parser.add_argument('--alpha', type=float, default=0.1,
                       help='Alpha parameter for concave hull (default: 0.1)')
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = DowntownAnalyzer(args.input)
    
    try:
        # Determine focus area based on input file
        if "palm_springs" in args.input.lower():
            # Focus on known downtown area (roughly downtown Palm Springs)
            # North: Alejo Rd (~33.851), South: Ramon Rd (~33.797) 
            # West: ~-116.570, East: ~-116.520
            focus_area = (33.790, -116.570, 33.860, -116.520)
            print("Using Palm Springs downtown focus area")
        elif "truckee" in args.input.lower():
            # Focus on downtown Truckee area
            # Roughly around downtown commercial district
            focus_area = (39.320, -120.240, 39.340, -120.180)
            print("Using Truckee downtown focus area")
        else:
            focus_area = None
            print("No specific focus area - analyzing entire region")
        
        # Run analysis
        analyzer.load_business_data(commercial_only=True, focus_area=focus_area)
        analyzer.calculate_density_grid(grid_size=args.grid_size, bandwidth=args.bandwidth)
        
        high_density_lats, high_density_lons = analyzer.identify_high_density_areas(
            density_threshold_percentile=args.density_threshold
        )
        
        analyzer.create_downtown_boundary(high_density_lats, high_density_lons, alpha=args.alpha)
        
        # Generate outputs
        analyzer.create_geojson(args.output)
        analyzer.plot_results(args.plot)
        
        print(f"\nAnalysis complete!")
        print(f"Downtown boundary saved to: {args.output}")
        print(f"Visualization saved to: {args.plot}")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())