#!/usr/bin/env python3
"""
CLI script for fetching business data from OpenStreetMap.
"""

import argparse
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dmur_analysis import BusinessFetcher, BusinessQuery
from dmur_analysis.utils.logging_config import setup_logging
from dmur_analysis.utils.validation import DataValidator


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Fetch business data from OpenStreetMap",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    parser.add_argument(
        "--city", 
        required=True,
        help="City name"
    )
    parser.add_argument(
        "--state", 
        required=True,
        help="State or province name"
    )
    
    # Optional arguments
    parser.add_argument(
        "--country",
        default="United States",
        help="Country name"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path (auto-generated if not specified)"
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include inactive/abandoned businesses"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Query timeout in seconds"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    parser.add_argument(
        "--log-file",
        help="Log file path (logs to console if not specified)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    # Auto-generate output filename if not provided
    if not args.output:
        safe_city = args.city.lower().replace(" ", "_").replace(",", "")
        args.output = f"data/raw/{safe_city}_businesses.json"
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create query configuration
        query = BusinessQuery(
            city=args.city,
            state=args.state,
            country=args.country,
            active_only=not args.include_inactive,
            timeout=args.timeout
        )
        
        # Fetch business data
        fetcher = BusinessFetcher()
        business_data = fetcher.fetch_businesses(query, args.output)
        
        # Validate results
        is_valid, errors = DataValidator.validate_business_data(business_data)
        if not is_valid:
            print(f"Warning: Data validation issues found:")
            for error in errors:
                print(f"  - {error}")
        
        print(f"✅ Successfully fetched {business_data['total_businesses']} businesses")
        print(f"📁 Saved to: {args.output}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())