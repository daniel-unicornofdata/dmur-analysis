#!/usr/bin/env python3
"""
CLI script for analyzing downtown boundaries.
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dmur_analysis import DowntownAnalyzer, AnalysisConfig
from dmur_analysis.visualization import AnalysisMapper
from dmur_analysis.utils.logging_config import setup_logging
from dmur_analysis.utils.validation import DataValidator


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Analyze downtown boundaries using business density",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    parser.add_argument(
        "--input",
        required=True,
        help="Input JSON file with business data"
    )
    
    # Optional arguments
    parser.add_argument(
        "--output-dir",
        default="data/output",
        help="Output directory for results"
    )
    parser.add_argument(
        "--city-name",
        help="City name override (extracted from data if not provided)"
    )
    parser.add_argument(
        "--density-threshold",
        type=float,
        default=90.0,
        help="Density threshold percentile"
    )
    parser.add_argument(
        "--bandwidth",
        type=float,
        default=0.002,
        help="KDE bandwidth for density estimation"
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.02,
        help="Alpha parameter for boundary shape"
    )
    parser.add_argument(
        "--focus-area",
        nargs=4,
        type=float,
        metavar=("min_lat", "min_lon", "max_lat", "max_lon"),
        help="Manual focus area coordinates"
    )
    parser.add_argument(
        "--no-auto-focus",
        action="store_true",
        help="Disable automatic focus area detection"
    )
    parser.add_argument(
        "--include-all-businesses",
        action="store_true",
        help="Include all business types (default: commercial only)"
    )
    parser.add_argument(
        "--skip-visualizations",
        action="store_true",
        help="Skip generating visualizations"
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
    
    # Validate input file
    is_valid, error = DataValidator.validate_file_path(args.input, must_exist=True)
    if not is_valid:
        print(f"❌ Input file error: {error}")
        return 1
    
    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Load and validate business data
        with open(args.input, 'r') as f:
            business_data = json.load(f)
        
        is_valid, errors = DataValidator.validate_business_data(business_data)
        if not is_valid:
            print("⚠️  Data validation warnings:")
            for error in errors:
                print(f"   - {error}")
        
        # Configure analysis
        config = AnalysisConfig(
            density_threshold_percentile=args.density_threshold,
            bandwidth=args.bandwidth,
            alpha=args.alpha,
            commercial_only=not args.include_all_businesses,
            auto_focus=not args.no_auto_focus,
            focus_area=tuple(args.focus_area) if args.focus_area else None
        )
        
        # Run analysis
        analyzer = DowntownAnalyzer(config)
        results = analyzer.analyze(business_data, args.city_name)
        
        # Generate output filenames
        city_safe = results['city'].lower().replace(" ", "_").replace(",", "")
        geojson_file = output_dir / f"{city_safe}_downtown.geojson"
        
        # Create mapper for visualizations
        if not args.skip_visualizations:
            mapper = AnalysisMapper()
            
            # Generate outputs
            mapper.create_geojson(results, geojson_file)
            
            plot_file = mapper.create_static_plot(
                results, 
                output_dir / f"{city_safe}_analysis.png"
            )
            
            map_file = mapper.create_interactive_map(
                results,
                output_dir / f"{city_safe}_map.html"
            )
            
            print(f"📊 Static plot: {plot_file}")
            if map_file:
                print(f"🗺️  Interactive map: {map_file}")
        else:
            # Just create GeoJSON
            mapper = AnalysisMapper()
            mapper.create_geojson(results, geojson_file)
        
        # Print summary
        print(f"✅ Analysis complete for {results['city']}")
        print(f"📍 Downtown area: {results['downtown_area_km2']} km²")
        print(f"🏢 Businesses in downtown: {results['downtown_businesses']}")
        print(f"📈 Business density: {results['business_density_per_km2']} per km²")
        print(f"🗂️  GeoJSON boundary: {geojson_file}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())