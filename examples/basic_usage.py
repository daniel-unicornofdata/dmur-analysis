#!/usr/bin/env python3
"""
Basic usage example for DMUR Analysis Toolkit.

This example demonstrates the complete workflow from fetching business data
to calculating DMUR scores.
"""

import sys
from pathlib import Path

# Add src to path for examples
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dmur_analysis import BusinessFetcher, BusinessQuery, DowntownAnalyzer, DMURCalculator
from dmur_analysis.visualization import AnalysisMapper
from dmur_analysis.utils.logging_config import setup_logging
import pandas as pd


def main():
    """Demonstrate basic DMUR analysis workflow."""
    
    # Setup logging
    setup_logging("INFO", console_output=True)
    
    print("🏙️  DMUR Analysis Toolkit - Basic Usage Example")
    print("=" * 50)
    
    # Step 1: Fetch business data
    print("\n📍 Step 1: Fetching business data from OpenStreetMap...")
    
    query = BusinessQuery(
        city="Yountville",
        state="California",
        active_only=True
    )
    
    fetcher = BusinessFetcher()
    business_data = fetcher.fetch_businesses(query, "data/raw/example_businesses.json")
    
    print(f"✅ Fetched {business_data['total_businesses']} businesses")
    
    # Step 2: Analyze downtown boundaries
    print("\n🗺️  Step 2: Analyzing downtown boundaries...")
    
    analyzer = DowntownAnalyzer()
    downtown_results = analyzer.analyze(business_data)
    
    print(f"✅ Downtown area: {downtown_results['downtown_area_km2']} km²")
    print(f"📊 Business density: {downtown_results['business_density_per_km2']} per km²")
    print(f"🏢 Downtown businesses: {downtown_results['downtown_businesses']}")
    
    # Step 3: Create visualizations
    print("\n📈 Step 3: Creating visualizations...")
    
    mapper = AnalysisMapper()
    
    # Create output directory
    output_dir = Path("data/output/examples")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate visualizations
    geojson_file = mapper.create_geojson(downtown_results, output_dir / "downtown.geojson")
    plot_file = mapper.create_static_plot(downtown_results, output_dir / "analysis.png")
    map_file = mapper.create_interactive_map(downtown_results, output_dir / "map.html")
    
    print(f"📄 GeoJSON: {geojson_file}")
    print(f"📊 Plot: {plot_file}")
    if map_file:
        print(f"🗺️  Interactive map: {map_file}")
    
    # Step 4: Calculate DMUR score (with sample data)
    print("\n🎯 Step 4: Calculating DMUR score...")
    
    # Create sample listings data for demonstration
    sample_listings = pd.DataFrame([
        {"lat": 38.4025985, "lon": -122.361948, "bedrooms": 1, "area_sqm": 65, "price": 3500},
        {"lat": 38.4022208, "lon": -122.3612217, "bedrooms": 2, "area_sqm": 85, "price": 4500},
        {"lat": 38.4024308, "lon": -122.3615648, "bedrooms": 0, "area_sqm": 45, "price": 2800},
        {"lat": 38.4024387, "lon": -122.361778, "bedrooms": 3, "area_sqm": 120, "price": 650000},
        {"lat": 38.4020177, "lon": -122.3617251, "bedrooms": 1, "area_sqm": 55, "price": 3200},
        {"lat": 38.4026073, "lon": -122.361499, "bedrooms": 2, "area_sqm": 90, "price": 4800},
    ])
    
    calculator = DMURCalculator()
    dmur_results = calculator.calculate_dmur(
        listings_data=sample_listings,
        downtown_boundary=downtown_results['downtown_boundary'],
        business_locations=downtown_results['downtown_businesses_df'],
        city_name="Yountville"
    )
    
    print(f"✅ DMUR Score: {dmur_results['dmur_score']:.3f}")
    print(f"   MXI Score: {dmur_results['component_scores']['mxi_score']:.3f}")
    print(f"   Balance Score: {dmur_results['component_scores']['balance_score']:.3f}")
    print(f"   Density Score: {dmur_results['component_scores']['density_score']:.3f}")
    print(f"   Diversity Score: {dmur_results['component_scores']['diversity_score']:.3f}")
    
    # Save DMUR results
    import json
    dmur_file = output_dir / "dmur_results.json"
    with open(dmur_file, 'w') as f:
        json.dump(dmur_results, f, indent=2)
    
    print(f"💾 DMUR results: {dmur_file}")
    
    print("\n🎉 Analysis complete!")
    print(f"📁 All outputs saved to: {output_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())