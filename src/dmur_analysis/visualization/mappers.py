"""
Visualization and mapping utilities for DMUR analysis.
"""

import json
import logging
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Union

try:
    import folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

from shapely.geometry import Polygon, MultiPolygon

logger = logging.getLogger(__name__)


class AnalysisMapper:
    """Creates maps and visualizations for downtown analysis."""
    
    def create_static_plot(self, 
                          analysis_results: Dict,
                          output_file: Optional[Union[str, Path]] = None) -> Path:
        """Create static matplotlib visualization."""
        city_name = analysis_results['city']
        businesses_df = analysis_results['businesses_df']
        downtown_businesses_df = analysis_results['downtown_businesses_df']
        downtown_boundary = analysis_results['downtown_boundary']
        density_grid = analysis_results['density_grid']
        density_coords = analysis_results['density_coords']
        
        if output_file is None:
            output_file = Path(f"{city_name.lower().replace(' ', '_')}_analysis.png")
        else:
            output_file = Path(output_file)
        
        logger.info(f"Creating static visualization: {output_file}")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
        
        # Plot 1: Density heatmap
        lat_grid, lon_grid = density_coords
        im = ax1.contourf(lon_grid, lat_grid, density_grid, levels=20, cmap='YlOrRd')
        ax1.scatter(businesses_df['lon'], businesses_df['lat'], 
                   s=1, c='blue', alpha=0.3, label='All businesses')
        
        if downtown_boundary:
            self._plot_boundary(ax1, downtown_boundary, 'Downtown boundary')
        
        ax1.set_xlabel('Longitude')
        ax1.set_ylabel('Latitude')
        ax1.set_title(f'{city_name} Business Density Heatmap')
        ax1.legend()
        plt.colorbar(im, ax=ax1, label='Density')
        
        # Plot 2: Downtown businesses
        ax2.scatter(businesses_df['lon'], businesses_df['lat'], 
                   s=1, c='lightgray', alpha=0.5, label='All businesses')
        ax2.scatter(downtown_businesses_df['lon'], downtown_businesses_df['lat'], 
                   s=3, c='red', alpha=0.7, label='Downtown businesses')
        
        if downtown_boundary:
            self._plot_boundary(ax2, downtown_boundary, 'Downtown boundary')
        
        ax2.set_xlabel('Longitude')
        ax2.set_ylabel('Latitude')
        ax2.set_title(f'{city_name} Downtown Business Locations')
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved static visualization to {output_file}")
        return output_file
    
    def create_interactive_map(self,
                              analysis_results: Dict,
                              output_file: Optional[Union[str, Path]] = None) -> Optional[Path]:
        """Create interactive HTML map."""
        if not FOLIUM_AVAILABLE:
            logger.warning("Folium not available. Skipping interactive map generation.")
            return None
        
        city_name = analysis_results['city']
        businesses_df = analysis_results['businesses_df']
        downtown_businesses_df = analysis_results['downtown_businesses_df']
        downtown_boundary = analysis_results['downtown_boundary']
        
        if output_file is None:
            output_file = Path(f"{city_name.lower().replace(' ', '_')}_map.html")
        else:
            output_file = Path(output_file)
        
        logger.info(f"Creating interactive map: {output_file}")
        
        # Calculate map center
        center_lat = businesses_df['lat'].mean()
        center_lon = businesses_df['lon'].mean()
        
        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=15,
            tiles='OpenStreetMap'
        )
        
        # Add downtown boundary
        self._add_boundary_to_map(m, downtown_boundary, city_name)
        
        # Add businesses
        self._add_businesses_to_map(m, businesses_df, downtown_businesses_df)
        
        # Add legend and statistics
        self._add_map_legend(m, city_name)
        self._add_map_statistics(m, analysis_results)
        
        # Save map
        m.save(str(output_file))
        logger.info(f"Saved interactive map to {output_file}")
        
        return output_file
    
    def create_geojson(self,
                      analysis_results: Dict,
                      output_file: Optional[Union[str, Path]] = None) -> Path:
        """Create GeoJSON output."""
        city_name = analysis_results['city']
        downtown_businesses_df = analysis_results['downtown_businesses_df']
        downtown_boundary = analysis_results['downtown_boundary']
        
        if output_file is None:
            output_file = Path(f"{city_name.lower().replace(' ', '_')}_downtown.geojson")
        else:
            output_file = Path(output_file)
        
        logger.info(f"Creating GeoJSON: {output_file}")
        
        # Create GeoJSON structure
        geojson = {
            "type": "FeatureCollection",
            "properties": {
                "city": city_name,
                "analysis_timestamp": pd.Timestamp.now().isoformat(),
                "total_businesses": analysis_results['total_businesses'],
                "downtown_businesses": analysis_results['downtown_businesses'],
                "downtown_area_km2": analysis_results['downtown_area_km2']
            },
            "features": []
        }
        
        # Add downtown boundary
        boundary_feature = self._create_boundary_feature(downtown_boundary, city_name, len(downtown_businesses_df))
        geojson["features"].append(boundary_feature)
        
        # Add downtown businesses as points
        for _, business in downtown_businesses_df.iterrows():
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
        
        logger.info(f"Saved GeoJSON with {len(geojson['features'])} features to {output_file}")
        return output_file
    
    def _plot_boundary(self, ax, boundary, label):
        """Plot boundary on matplotlib axis."""
        if isinstance(boundary, Polygon):
            x, y = boundary.exterior.xy
            ax.plot(x, y, 'r-', linewidth=2, label=label)
        elif isinstance(boundary, MultiPolygon):
            for poly in boundary.geoms:
                x, y = poly.exterior.xy
                ax.plot(x, y, 'r-', linewidth=2, label=label)
                label = None  # Only label first polygon
    
    def _add_boundary_to_map(self, map_obj, boundary, city_name):
        """Add boundary to folium map."""
        if isinstance(boundary, Polygon):
            coords = list(boundary.exterior.coords)
            folium_coords = [[lat, lon] for lon, lat in coords]
            
            folium.Polygon(
                locations=folium_coords,
                color='red',
                weight=3,
                fillColor='red',
                fillOpacity=0.2,
                popup=f"Downtown {city_name}"
            ).add_to(map_obj)
        elif isinstance(boundary, MultiPolygon):
            for poly in boundary.geoms:
                coords = list(poly.exterior.coords)
                folium_coords = [[lat, lon] for lon, lat in coords]
                folium.Polygon(
                    locations=folium_coords,
                    color='red',
                    weight=3,
                    fillColor='red',
                    fillOpacity=0.2,
                    popup=f"Downtown {city_name}"
                ).add_to(map_obj)
    
    def _add_businesses_to_map(self, map_obj, all_businesses_df, downtown_businesses_df):
        """Add businesses to folium map."""
        # Color mapping for business types
        color_map = {
            'amenity': 'red',
            'shop': 'green', 
            'tourism': 'blue',
            'office': 'orange',
            'craft': 'purple'
        }
        
        # Add all businesses as light markers
        for _, business in all_businesses_df.iterrows():
            folium.CircleMarker(
                location=[business['lat'], business['lon']],
                radius=2,
                popup=f"{business['name']} ({business['type']})",
                color='lightblue',
                fillColor='lightblue',
                fillOpacity=0.5,
                weight=1
            ).add_to(map_obj)
        
        # Add downtown businesses as prominent markers
        for _, business in downtown_businesses_df.iterrows():
            color = color_map.get(business['type'], 'darkred')
            
            folium.Marker(
                location=[business['lat'], business['lon']],
                popup=f"<b>{business['name']}</b><br>{business['type']}: {business['subtype']}<br>OSM ID: {business['id']}",
                tooltip=business['name'],
                icon=folium.Icon(color=color, icon='star')
            ).add_to(map_obj)
    
    def _add_map_legend(self, map_obj, city_name):
        """Add legend to folium map."""
        legend_html = f'''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <h4>{city_name} Downtown Map</h4>
        <p><i class="fa fa-star" style="color:red"></i> Restaurants/Amenities<br>
           <i class="fa fa-star" style="color:green"></i> Shops<br>
           <i class="fa fa-star" style="color:blue"></i> Tourism<br>
           <i class="fa fa-star" style="color:orange"></i> Offices<br>
           <i class="fa fa-star" style="color:purple"></i> Wineries/Craft<br>
           <span style="color:red; font-weight:bold;">Red Area:</span> Downtown Boundary</p>
        </div>
        '''
        map_obj.get_root().html.add_child(folium.Element(legend_html))
    
    def _add_map_statistics(self, map_obj, analysis_results):
        """Add statistics panel to folium map."""
        stats_html = f'''
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 250px; height: 100px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px">
        <h4>Analysis Statistics</h4>
        <p>Total Businesses: {analysis_results['total_businesses']}<br>
           Downtown Businesses: {analysis_results['downtown_businesses']}<br>
           Downtown Area: {analysis_results['downtown_area_km2']} km²<br>
           Business Density: {analysis_results['business_density_per_km2']} per km²</p>
        </div>
        '''
        map_obj.get_root().html.add_child(folium.Element(stats_html))
    
    def _create_boundary_feature(self, boundary, city_name, business_count):
        """Create GeoJSON feature for boundary."""
        if isinstance(boundary, Polygon):
            coords = [list(boundary.exterior.coords)]
            geom_type = "Polygon"
        elif isinstance(boundary, MultiPolygon):
            coords = []
            for poly in boundary.geoms:
                coords.append(list(poly.exterior.coords))
            geom_type = "MultiPolygon"
        else:
            raise ValueError(f"Unsupported boundary type: {type(boundary)}")
        
        return {
            "type": "Feature",
            "properties": {
                "name": f"Downtown {city_name}",
                "type": "downtown_boundary",
                "business_count": business_count
            },
            "geometry": {
                "type": geom_type,
                "coordinates": coords if geom_type == "Polygon" else [coords]
            }
        }