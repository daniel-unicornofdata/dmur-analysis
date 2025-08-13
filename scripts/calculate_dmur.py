#!/usr/bin/env python3
"""
CLI script for calculating DMUR scores.
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dmur_analysis import DMURCalculator, DMURConfig, DowntownAnalyzer
from dmur_analysis.utils.logging_config import setup_logging
from dmur_analysis.utils.validation import DataValidator


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Calculate DMUR scores using real estate listings",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    parser.add_argument(
        "--businesses",
        required=True,
        help="Business data JSON file"
    )
    parser.add_argument(
        "--listings",
        required=True,
        help="Real estate listings CSV/JSON file"
    )
    
    # Optional arguments
    parser.add_argument(
        "--downtown-boundary",
        help="Pre-computed downtown boundary GeoJSON file (will be computed if not provided)"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file for DMUR results (auto-generated if not specified)"
    )
    parser.add_argument(
        "--city-name",
        help="City name override"
    )
    
    # DMUR configuration
    parser.add_argument(
        "--mxi-weight",
        type=float,
        default=0.4,
        help="Mixed-Use Index weight"
    )
    parser.add_argument(
        "--balance-weight",
        type=float,
        default=0.3,
        help="Balance score weight"
    )
    parser.add_argument(
        "--density-weight",
        type=float,
        default=0.2,
        help="Density score weight"
    )
    parser.add_argument(
        "--diversity-weight",
        type=float,
        default=0.1,
        help="Diversity score weight"
    )
    parser.add_argument(
        "--max-distance",
        type=float,
        default=0.005,
        help="Maximum distance threshold for MXI (degrees)"
    )
    parser.add_argument(
        "--optimal-ratio",
        type=float,
        default=25.0,
        help="Optimal residential units per business"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    parser.add_argument(
        "--log-file",
        help="Log file path"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    # Validate input files
    for file_path, name in [(args.businesses, "business"), (args.listings, "listings")]:
        is_valid, error = DataValidator.validate_file_path(file_path, must_exist=True)
        if not is_valid:
            print(f"❌ {name.title()} file error: {error}")
            return 1
    
    # Validate weights sum to 1.0
    total_weight = args.mxi_weight + args.balance_weight + args.density_weight + args.diversity_weight
    if abs(total_weight - 1.0) > 0.001:
        print(f"❌ Error: Weights must sum to 1.0 (current sum: {total_weight})")
        return 1
    
    try:
        # Load business data
        with open(args.businesses, 'r') as f:
            business_data = json.load(f)
        
        city_name = args.city_name or business_data.get('city', 'Unknown City')
        
        # Load listings data
        import pandas as pd
        listings_file = Path(args.listings)
        if listings_file.suffix.lower() == '.csv':
            listings_df = pd.read_csv(args.listings)
        elif listings_file.suffix.lower() == '.json':
            listings_df = pd.read_json(args.listings)
        else:
            print(f"❌ Error: Unsupported listings file format: {listings_file.suffix}")
            return 1
        
        # Validate listings data
        is_valid, errors = DataValidator.validate_listing_data(listings_df)
        if not is_valid:
            print("❌ Listings data validation errors:")
            for error in errors:
                print(f"   - {error}")
            return 1
        
        # Get downtown boundary
        if args.downtown_boundary:
            # Load pre-computed boundary
            import geopandas as gpd
            boundary_gdf = gpd.read_file(args.downtown_boundary)
            downtown_boundary = boundary_gdf[boundary_gdf['type'] == 'downtown_boundary'].geometry.iloc[0]
            
            # Get business locations (need to analyze to get filtered businesses)
            analyzer = DowntownAnalyzer()
            analysis_results = analyzer.analyze(business_data, city_name)
            business_locations = analysis_results['downtown_businesses_df']
        else:
            # Compute downtown boundary
            print("🔄 Computing downtown boundary...")
            analyzer = DowntownAnalyzer()
            analysis_results = analyzer.analyze(business_data, city_name)
            downtown_boundary = analysis_results['downtown_boundary']
            business_locations = analysis_results['downtown_businesses_df']
            print(f"✅ Downtown boundary computed: {analysis_results['downtown_area_km2']} km²")
        
        # Configure DMUR calculation
        dmur_config = DMURConfig(
            mxi_weight=args.mxi_weight,
            balance_weight=args.balance_weight,
            density_weight=args.density_weight,
            diversity_weight=args.diversity_weight,
            max_distance_threshold=args.max_distance,
            optimal_residential_ratio=args.optimal_ratio
        )
        
        # Calculate DMUR score
        print("🔄 Calculating DMUR score...")
        calculator = DMURCalculator(dmur_config)
        dmur_results = calculator.calculate_dmur(
            listings_data=listings_df,
            downtown_boundary=downtown_boundary,
            business_locations=business_locations,
            city_name=city_name
        )
        
        # Save results
        if not args.output:
            city_safe = city_name.lower().replace(" ", "_").replace(",", "")
            args.output = f"data/output/{city_safe}_dmur_results.json"
        
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(dmur_results, f, indent=2)
        
        # Print results summary
        print(f"✅ DMUR Analysis complete for {city_name}")
        print(f"🎯 DMUR Score: {dmur_results['dmur_score']:.3f}")
        print()
        print("📊 Component Scores:")
        for component, score in dmur_results['component_scores'].items():
            weight = dmur_results['weights'][component.replace('_score', '_weight')]
            print(f"   {component.replace('_', ' ').title()}: {score:.3f} (weight: {weight})")
        print()
        print("📈 Key Metrics:")
        print(f"   Total Listings: {dmur_results['metrics']['total_listings']}")
        print(f"   Total Businesses: {dmur_results['metrics']['total_businesses']}")
        print(f"   Avg Distance to Business: {dmur_results['metrics']['avg_distance_to_business']:.6f}°")
        print(f"   Residential/Business Ratio: {dmur_results['metrics']['residential_to_business_ratio']:.1f}")
        print()
        print(f"💾 Results saved to: {output_path}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())