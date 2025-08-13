#!/usr/bin/env python3
"""
Generic downtown analysis for any city using business density
"""

import json
import numpy as np
import pandas as pd
from sklearn.neighbors import KernelDensity
from sklearn.cluster import DBSCAN
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
import geopandas as gpd
from scipy.spatial import ConvexHull, Delaunay
import argparse
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict, Optional
try:
    import folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    print("Warning: folium not available. HTML maps will not be generated.")


class GenericDowntownAnalyzer:
    """Generic analyzer for any city's downtown boundaries"""
    
    def __init__(self, business_data_file: str, city_name: str = None):
        """
        Initialize analyzer with business data
        
        Args:
            business_data_file: Path to JSON file with business data
            city_name: Name of the city (extracted from file if not provided)
        """
        self.business_data_file = business_data_file
        self.city_name = city_name or self._extract_city_name()
        self.businesses_df = None
        self.density_grid = None
        self.density_coords = None
        self.downtown_boundary = None
        
    def _extract_city_name(self) -> str:
        """Extract city name from filename"""
        import os
        filename = os.path.basename(self.business_data_file)
        # Remove _businesses.json suffix and replace underscores with spaces
        city = filename.replace('_businesses.json', '').replace('_', ' ')
        return city.title()
    
    def load_business_data(self, commercial_only: bool = True, 
                          focus_area: Optional[Tuple[float, float, float, float]] = None,
                          auto_focus: bool = True):
        """
        Load and prepare business data
        
        Args:
            commercial_only: Filter for commercial businesses only
            focus_area: (min_lat, min_lon, max_lat, max_lon) to focus analysis
            auto_focus: Automatically determine focus area from business distribution
        """
        print(f"Loading business data for {self.city_name}...")
        
        with open(self.business_data_file, 'r') as f:
            data = json.load(f)
        
        # Extract business coordinates and types
        businesses = []
        
        # Define core commercial business types
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
                
                businesses.append({
                    'id': business['id'],
                    'lat': business['lat'],
                    'lon': business['lon'],
                    'name': business['name'],
                    'type': business['business_type'],
                    'subtype': business['business_subtype']
                })
        
        temp_df = pd.DataFrame(businesses)
        print(f"Loaded {len(temp_df)} businesses total")
        
        # Apply focus area or auto-determine one
        if focus_area:
            print(f"Using provided focus area: {focus_area}")
            min_lat, min_lon, max_lat, max_lon = focus_area
            mask = ((temp_df['lat'] >= min_lat) & (temp_df['lat'] <= max_lat) &
                   (temp_df['lon'] >= min_lon) & (temp_df['lon'] <= max_lon))
            self.businesses_df = temp_df[mask].copy()
        elif auto_focus:
            focus_area = self._auto_determine_focus_area(temp_df)
            print(f"Auto-determined focus area: {focus_area}")
            min_lat, min_lon, max_lat, max_lon = focus_area
            mask = ((temp_df['lat'] >= min_lat) & (temp_df['lat'] <= max_lat) &
                   (temp_df['lon'] >= min_lon) & (temp_df['lon'] <= max_lon))
            self.businesses_df = temp_df[mask].copy()
        else:
            self.businesses_df = temp_df
        
        print(f"Using {len(self.businesses_df)} businesses in analysis area")
        
        # Print summary by business type
        if len(self.businesses_df) > 0:
            type_counts = self.businesses_df['type'].value_counts()
            print("\nBusiness types:")
            for btype, count in type_counts.head(10).items():
                print(f"  {btype}: {count}")
        else:
            print("Warning: No businesses found in focus area!")
    
    def _auto_determine_focus_area(self, businesses_df: pd.DataFrame, 
                                  density_percentile: float = 85) -> Tuple[float, float, float, float]:
        """
        Automatically determine focus area based on business density clustering
        
        Args:
            businesses_df: DataFrame with business data
            density_percentile: Percentile for high-density areas
            
        Returns:
            Tuple of (min_lat, min_lon, max_lat, max_lon)
        """
        if len(businesses_df) < 10:
            # If too few businesses, use entire area
            return (businesses_df['lat'].min(), businesses_df['lon'].min(),
                   businesses_df['lat'].max(), businesses_df['lon'].max())
        
        print("Auto-detecting downtown focus area using density clustering...")
        
        # Use multiple approaches to find the most compact high-density area
        lats = businesses_df['lat'].values
        lons = businesses_df['lon'].values
        
        # Approach 1: Fine-grained density analysis
        lat_bins = np.linspace(lats.min(), lats.max(), 40)  # More resolution
        lon_bins = np.linspace(lons.min(), lons.max(), 40)
        
        hist, lat_edges, lon_edges = np.histogram2d(lats, lons, bins=[lat_bins, lon_bins])
        
        # Find the peak density area (not just high percentile)
        max_density_idx = np.unravel_index(np.argmax(hist), hist.shape)
        peak_lat_idx, peak_lon_idx = max_density_idx
        
        # Approach 2: DBSCAN clustering to find the most compact cluster
        from sklearn.cluster import DBSCAN
        
        coords = np.column_stack([lats, lons])
        
        # Use adaptive epsilon based on coordinate range
        lat_range = lats.max() - lats.min()
        lon_range = lons.max() - lons.min()
        epsilon = min(lat_range, lon_range) * 0.01  # 1% of the smaller dimension
        
        clustering = DBSCAN(eps=epsilon, min_samples=10).fit(coords)
        labels = clustering.labels_
        
        # Find the largest cluster (most businesses)
        unique_labels, counts = np.unique(labels[labels >= 0], return_counts=True)
        
        if len(unique_labels) > 0:
            largest_cluster_label = unique_labels[np.argmax(counts)]
            cluster_mask = labels == largest_cluster_label
            cluster_coords = coords[cluster_mask]
            
            # Calculate density of largest cluster
            cluster_area = ((cluster_coords[:, 0].max() - cluster_coords[:, 0].min()) * 
                           (cluster_coords[:, 1].max() - cluster_coords[:, 1].min()))
            cluster_density = len(cluster_coords) / max(cluster_area, 0.0001)
            
            print(f"Found main cluster with {len(cluster_coords)} businesses")
            
            # Approach 3: Kernel density estimation to find peak
            from sklearn.neighbors import KernelDensity
            
            # Use adaptive bandwidth
            bandwidth = min(lat_range, lon_range) * 0.005
            kde = KernelDensity(bandwidth=bandwidth, kernel='gaussian')
            kde.fit(coords)
            
            # Create a grid around the main cluster for KDE evaluation
            if len(cluster_coords) > 0:
                cluster_lat_min, cluster_lat_max = cluster_coords[:, 0].min(), cluster_coords[:, 0].max()
                cluster_lon_min, cluster_lon_max = cluster_coords[:, 1].min(), cluster_coords[:, 1].max()
            else:
                # Fallback to peak density area
                cluster_lat_min = lat_edges[max(0, peak_lat_idx-2)]
                cluster_lat_max = lat_edges[min(len(lat_edges)-1, peak_lat_idx+3)]
                cluster_lon_min = lon_edges[max(0, peak_lon_idx-2)]
                cluster_lon_max = lon_edges[min(len(lon_edges)-1, peak_lon_idx+3)]
            
            # Evaluate KDE on a fine grid around the cluster
            test_lats = np.linspace(cluster_lat_min, cluster_lat_max, 20)
            test_lons = np.linspace(cluster_lon_min, cluster_lon_max, 20)
            test_lon_grid, test_lat_grid = np.meshgrid(test_lons, test_lats)
            test_coords = np.column_stack([test_lat_grid.ravel(), test_lon_grid.ravel()])
            
            kde_scores = kde.score_samples(test_coords)
            kde_density = np.exp(kde_scores).reshape(test_lat_grid.shape)
            
            # Find the highest density region in KDE
            kde_threshold = np.percentile(kde_density, 90)
            high_kde_mask = kde_density >= kde_threshold
            
            if np.any(high_kde_mask):
                high_kde_lats = test_lat_grid[high_kde_mask]
                high_kde_lons = test_lon_grid[high_kde_mask]
                
                kde_lat_min, kde_lat_max = high_kde_lats.min(), high_kde_lats.max()
                kde_lon_min, kde_lon_max = high_kde_lons.min(), high_kde_lons.max()
            else:
                kde_lat_min, kde_lat_max = cluster_lat_min, cluster_lat_max
                kde_lon_min, kde_lon_max = cluster_lon_min, cluster_lon_max
            
            # Choose the most compact area (smallest bounding box with reasonable business count)
            focus_areas = []
            
            # Option 1: Main cluster area
            if len(cluster_coords) > 0:
                padding = min(lat_range, lon_range) * 0.02
                focus_areas.append({
                    'bounds': (cluster_lat_min - padding, cluster_lon_min - padding,
                              cluster_lat_max + padding, cluster_lon_max + padding),
                    'area': (cluster_lat_max - cluster_lat_min) * (cluster_lon_max - cluster_lon_min),
                    'business_count': len(cluster_coords),
                    'method': 'clustering'
                })
            
            # Option 2: KDE peak area
            kde_area = (kde_lat_max - kde_lat_min) * (kde_lon_max - kde_lon_min)
            kde_business_count = len(businesses_df[
                (businesses_df['lat'] >= kde_lat_min) & (businesses_df['lat'] <= kde_lat_max) &
                (businesses_df['lon'] >= kde_lon_min) & (businesses_df['lon'] <= kde_lon_max)
            ])
            
            padding = min(lat_range, lon_range) * 0.02
            focus_areas.append({
                'bounds': (kde_lat_min - padding, kde_lon_min - padding,
                          kde_lat_max + padding, kde_lon_max + padding),
                'area': kde_area,
                'business_count': kde_business_count,
                'method': 'kde_peak'
            })
            
            # Choose the area with best density (businesses per unit area) but minimum size requirements
            best_area = None
            best_density = 0
            
            for area_info in focus_areas:
                density = area_info['business_count'] / max(area_info['area'], 0.0001)
                area_size = area_info['area']
                business_count = area_info['business_count']
                
                # Prefer areas with good density and reasonable business count
                if (business_count >= 20 and  # Minimum businesses
                    area_size <= lat_range * lon_range * 0.3 and  # Not too large
                    density > best_density):
                    best_density = density
                    best_area = area_info
            
            if best_area:
                print(f"Selected focus area using {best_area['method']}: "
                      f"{best_area['business_count']} businesses, "
                      f"density = {best_density:.1f} businesses/degree²")
                return best_area['bounds']
        
        # Fallback: Use peak density area from histogram
        print("Using fallback: peak density area from histogram")
        
        # Find area around peak density
        window_size = 3  # 3x3 window around peak
        lat_start = max(0, peak_lat_idx - window_size//2)
        lat_end = min(len(lat_edges)-1, peak_lat_idx + window_size//2 + 1)
        lon_start = max(0, peak_lon_idx - window_size//2)
        lon_end = min(len(lon_edges)-1, peak_lon_idx + window_size//2 + 1)
        
        padding = min(lat_range, lon_range) * 0.02
        min_lat = lat_edges[lat_start] - padding
        max_lat = lat_edges[lat_end] + padding
        min_lon = lon_edges[lon_start] - padding
        max_lon = lon_edges[lon_end] + padding
        
        return (min_lat, min_lon, max_lat, max_lon)
    
    def calculate_density_grid(self, grid_size: float = 0.002, bandwidth: float = 0.005):
        """Calculate business density on a grid using kernel density estimation"""
        print("Calculating business density...")
        
        if len(self.businesses_df) < 3:
            raise ValueError("Need at least 3 businesses for density analysis")
        
        # Get coordinate bounds
        min_lat, max_lat = self.businesses_df['lat'].min(), self.businesses_df['lat'].max()
        min_lon, max_lon = self.businesses_df['lon'].min(), self.businesses_df['lon'].max()
        
        # Add padding
        padding = max(0.005, (max_lat - min_lat) * 0.1)  # Adaptive padding
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
    
    def identify_high_density_areas(self, density_threshold_percentile: float = 90):
        """Identify high-density areas using density threshold"""
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
            threshold = np.percentile(self.density_grid.ravel(), max(70, density_threshold_percentile - 20))
            high_density_mask = self.density_grid >= threshold
            high_density_lats = lat_grid[high_density_mask]
            high_density_lons = lon_grid[high_density_mask]
            print(f"Using lower threshold: {threshold:.6f} - found {len(high_density_lats)} points")
        
        return high_density_lats, high_density_lons
    
    def create_downtown_boundary(self, high_density_lats, high_density_lons, 
                                alpha: float = 0.02, buffer_distance: float = 0.003):
        """Create downtown boundary using alpha shapes or convex hull"""
        print("Creating downtown boundary...")
        
        try:
            # Use alpha shapes approach (simplified concave hull)
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
        # Rough conversion to km2 (latitude-dependent)
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
                "city": self.city_name,
                "analysis_timestamp": pd.Timestamp.now().isoformat(),
                "total_businesses": len(self.businesses_df),
                "downtown_businesses": len(downtown_businesses),
                "downtown_area_km2": round(self.downtown_boundary.area * 111.0 * 111.0 * 
                                         np.cos(np.radians(self.businesses_df['lat'].mean())), 2)
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
                "name": f"Downtown {self.city_name}",
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
        print(f"\nDowntown Analysis Summary for {self.city_name}:")
        print(f"  Total businesses in analysis area: {len(self.businesses_df)}")
        print(f"  Businesses in downtown: {len(downtown_businesses)}")
        print(f"  Downtown area: {geojson['properties']['downtown_area_km2']} km²")
        
        # Business types in downtown
        downtown_types = downtown_businesses['type'].value_counts()
        print(f"\nTop business types in downtown:")
        for btype, count in downtown_types.head(5).items():
            print(f"  {btype}: {count}")
    
    def plot_results(self, output_file: str = None):
        """Create visualization of the analysis results"""
        if output_file is None:
            output_file = f"{self.city_name.lower().replace(' ', '_')}_analysis.png"
        
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
        ax1.set_title(f'{self.city_name} Business Density Heatmap')
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
        ax2.set_title(f'{self.city_name} Downtown Business Locations')
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved visualization to {output_file}")
    
    def create_html_map(self, output_file: str = None):
        """Create interactive HTML map with downtown boundary and businesses"""
        if not FOLIUM_AVAILABLE:
            print("Folium not available. Skipping HTML map generation.")
            return
            
        if output_file is None:
            output_file = f"{self.city_name.lower().replace(' ', '_')}_map.html"
            
        print(f"Creating interactive HTML map: {output_file}")
        
        if self.downtown_boundary is None:
            raise ValueError("Downtown boundary not created yet")
        
        # Get downtown businesses
        downtown_businesses = self.get_businesses_in_downtown()
        
        # Calculate map center
        center_lat = self.businesses_df['lat'].mean()
        center_lon = self.businesses_df['lon'].mean()
        
        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=15,
            tiles='OpenStreetMap'
        )
        
        # Add downtown boundary
        if isinstance(self.downtown_boundary, Polygon):
            # Convert Shapely polygon to coordinates for Folium
            coords = list(self.downtown_boundary.exterior.coords)
            # Convert from (lon, lat) to (lat, lon) for Folium
            folium_coords = [[lat, lon] for lon, lat in coords]
            
            folium.Polygon(
                locations=folium_coords,
                color='red',
                weight=3,
                fillColor='red',
                fillOpacity=0.2,
                popup=f"Downtown {self.city_name}"
            ).add_to(m)
        elif isinstance(self.downtown_boundary, MultiPolygon):
            for poly in self.downtown_boundary.geoms:
                coords = list(poly.exterior.coords)
                folium_coords = [[lat, lon] for lon, lat in coords]
                folium.Polygon(
                    locations=folium_coords,
                    color='red',
                    weight=3,
                    fillColor='red',
                    fillOpacity=0.2,
                    popup=f"Downtown {self.city_name}"
                ).add_to(m)
        
        # Add all businesses as light markers
        for _, business in self.businesses_df.iterrows():
            folium.CircleMarker(
                location=[business['lat'], business['lon']],
                radius=2,
                popup=f"{business['name']} ({business['type']})",
                color='lightblue',
                fillColor='lightblue',
                fillOpacity=0.5,
                weight=1
            ).add_to(m)
        
        # Add downtown businesses as prominent markers
        for _, business in downtown_businesses.iterrows():
            # Different colors for different business types
            color_map = {
                'amenity': 'red',
                'shop': 'green', 
                'tourism': 'blue',
                'office': 'orange',
                'craft': 'purple'
            }
            color = color_map.get(business['type'], 'darkred')
            
            folium.Marker(
                location=[business['lat'], business['lon']],
                popup=f"<b>{business['name']}</b><br>{business['type']}: {business['subtype']}<br>OSM ID: {business['id']}",
                tooltip=business['name'],
                icon=folium.Icon(color=color, icon='star')
            ).add_to(m)
        
        # Add a legend
        legend_html = f'''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <h4>{self.city_name} Downtown Map</h4>
        <p><i class="fa fa-star" style="color:red"></i> Restaurants/Amenities<br>
           <i class="fa fa-star" style="color:green"></i> Shops<br>
           <i class="fa fa-star" style="color:blue"></i> Tourism<br>
           <i class="fa fa-star" style="color:orange"></i> Offices<br>
           <i class="fa fa-star" style="color:purple"></i> Wineries/Craft<br>
           <span style="color:red; font-weight:bold;">Red Area:</span> Downtown Boundary</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Add statistics as a text box
        area_km2 = self.downtown_boundary.area * 111.0 * 111.0 * np.cos(np.radians(center_lat))
        stats_html = f'''
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 250px; height: 100px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px">
        <h4>Analysis Statistics</h4>
        <p>Total Businesses: {len(self.businesses_df)}<br>
           Downtown Businesses: {len(downtown_businesses)}<br>
           Downtown Area: {area_km2:.2f} km²<br>
           Business Density: {len(downtown_businesses)/area_km2:.1f} per km²</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(stats_html))
        
        # Save map
        m.save(output_file)
        print(f"Saved interactive HTML map to {output_file}")
        
        return output_file


def main():
    parser = argparse.ArgumentParser(description='Analyze business density to identify downtown boundaries for any city')
    parser.add_argument('--input', required=True,
                       help='Input JSON file with business data (e.g., cityname_businesses.json)')
    parser.add_argument('--output', 
                       help='Output GeoJSON file (auto-generated if not specified)')
    parser.add_argument('--plot', 
                       help='Output plot file (auto-generated if not specified)')
    parser.add_argument('--html-map',
                       help='Output HTML map file (auto-generated if not specified)')
    parser.add_argument('--city-name',
                       help='City name (extracted from filename if not provided)')
    parser.add_argument('--density-threshold', type=float, default=90,
                       help='Density threshold percentile (default: 90)')
    parser.add_argument('--bandwidth', type=float, default=0.002,
                       help='KDE bandwidth (default: 0.002)')
    parser.add_argument('--grid-size', type=float, default=0.002,
                       help='Grid size for density calculation (default: 0.002)')
    parser.add_argument('--alpha', type=float, default=0.02,
                       help='Alpha parameter for boundary shape (default: 0.02)')
    parser.add_argument('--focus-area', nargs=4, type=float,
                       metavar=('min_lat', 'min_lon', 'max_lat', 'max_lon'),
                       help='Manual focus area coordinates (default: auto-detect)')
    parser.add_argument('--no-auto-focus', action='store_true',
                       help='Disable automatic focus area detection')
    parser.add_argument('--include-all-businesses', action='store_true',
                       help='Include all business types (default: commercial only)')
    
    args = parser.parse_args()
    
    # Auto-generate output filenames if not provided
    if not args.output:
        base_name = args.input.replace('_businesses.json', '').replace('.json', '')
        args.output = f"{base_name}_downtown.geojson"
    
    if not args.plot:
        base_name = args.input.replace('_businesses.json', '').replace('.json', '')
        args.plot = f"{base_name}_analysis.png"
    
    if not args.html_map:
        base_name = args.input.replace('_businesses.json', '').replace('.json', '')
        args.html_map = f"{base_name}_map.html"
    
    # Create analyzer
    analyzer = GenericDowntownAnalyzer(args.input, args.city_name)
    
    try:
        # Run analysis
        focus_area = tuple(args.focus_area) if args.focus_area else None
        analyzer.load_business_data(
            commercial_only=not args.include_all_businesses,
            focus_area=focus_area,
            auto_focus=not args.no_auto_focus
        )
        
        analyzer.calculate_density_grid(grid_size=args.grid_size, bandwidth=args.bandwidth)
        
        high_density_lats, high_density_lons = analyzer.identify_high_density_areas(
            density_threshold_percentile=args.density_threshold
        )
        
        analyzer.create_downtown_boundary(high_density_lats, high_density_lons, alpha=args.alpha)
        
        # Generate outputs
        analyzer.create_geojson(args.output)
        analyzer.plot_results(args.plot)
        analyzer.create_html_map(args.html_map)
        
        print(f"\nAnalysis complete for {analyzer.city_name}!")
        print(f"Downtown boundary saved to: {args.output}")
        print(f"Visualization saved to: {args.plot}")
        print(f"Interactive map saved to: {args.html_map}")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())