# DMUR Analysis Toolkit Documentation

Welcome to the **Downtown Mixed-Use Readiness (DMUR) Analysis Toolkit** documentation.

## Overview

This toolkit provides comprehensive capabilities for analyzing downtown areas and calculating their readiness for mixed-use development. It combines OpenStreetMap business data with real estate listings to generate actionable insights for urban planning.

## Quick Start

```python
from dmur_analysis import BusinessFetcher, DowntownAnalyzer, DMURCalculator

# 1. Fetch business data
fetcher = BusinessFetcher()
business_data = fetcher.fetch_businesses(city="Yountville", state="California")

# 2. Analyze downtown boundaries  
analyzer = DowntownAnalyzer()
downtown_results = analyzer.analyze(business_data)

# 3. Calculate DMUR score
calculator = DMURCalculator()
dmur_score = calculator.calculate_dmur(
    listings_data="listings.csv",
    downtown_boundary=downtown_results['downtown_boundary'],
    business_locations=downtown_results['downtown_businesses_df']
)
```

## Key Features

- **Autonomous downtown boundary detection** using business density analysis
- **DMUR scoring system** with 4 weighted components
- **Rich visualizations** including interactive maps and statistical plots
- **Professional architecture** with comprehensive testing and validation

## Documentation Sections

- [Installation](installation.md) - Setup and installation guide
- [User Guide](user_guide.md) - Comprehensive usage examples
- [API Reference](api_reference.md) - Detailed API documentation
- [Methodology](methodology.md) - Technical details of algorithms
- [Examples](examples.md) - Real-world usage examples
- [Contributing](contributing.md) - Development guidelines

## Support

- **GitHub Issues**: [Report bugs and request features](https://github.com/your-org/dmur-analysis/issues)
- **Discussions**: [Community support and questions](https://github.com/your-org/dmur-analysis/discussions)
- **Email**: contact@dmur-analysis.com