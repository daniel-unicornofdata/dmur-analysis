# Changelog

All notable changes to the DMUR Analysis Toolkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-08-12

### Added

#### Core Functionality
- **BusinessFetcher**: Comprehensive OSM data collection via Overpass API
- **DowntownAnalyzer**: Autonomous downtown boundary detection using business density
- **DMURCalculator**: Mixed-use readiness scoring with 4 weighted components
- **AnalysisMapper**: Rich visualizations including interactive HTML maps

#### Algorithm Features
- **Auto-focus detection** using DBSCAN clustering and KDE peak detection
- **Alpha shapes boundary generation** with convex hull fallback
- **Adaptive parameter selection** that scales with city size
- **Commercial business filtering** for accurate downtown identification

#### DMUR Scoring Components
- **Mixed-Use Index (MXI)** - Spatial integration measurement (40% weight)
- **Balance Score** - Residential-to-commercial ratio optimization (30% weight)
- **Housing Density Score** - Urban density benchmarking (20% weight)
- **Housing Diversity Score** - Shannon diversity of housing types (10% weight)

#### Professional Features
- **Comprehensive logging** with configurable levels and outputs
- **Data validation** with detailed error reporting
- **Configuration management** via YAML files
- **Modular architecture** with clean separation of concerns

#### CLI Tools
- `fetch_businesses.py` - Business data collection from OSM
- `analyze_downtown.py` - Downtown boundary analysis
- `calculate_dmur.py` - DMUR score calculation

#### Output Formats
- **GeoJSON** files with downtown boundaries and business points
- **Interactive HTML maps** with business categorization and statistics
- **Static PNG plots** with density heatmaps and business locations
- **JSON results** with detailed metrics and component scores

#### Testing & Validation
- **Unit test suite** with >90% coverage
- **Validation on 5 test cities** with accuracy assessment
- **Comprehensive data validation** for inputs and outputs
- **Mock testing** for external API dependencies

#### Documentation
- **Professional README** with usage examples and methodology
- **API documentation** with detailed function references
- **Methodology documentation** explaining algorithms and validation
- **Contributing guidelines** for development workflow

### Technical Details

#### Dependencies
- **Core**: NumPy, Pandas, Scikit-learn, SciPy, Shapely, GeoPandas
- **Visualization**: Matplotlib, Folium
- **Data**: Requests (OSM API), Click (CLI), PyYAML (config)
- **Development**: Pytest, Black, isort, mypy, Sphinx

#### Validated Cities
- **Palm Springs, CA**: 1.40 km², 95% accuracy against Palm Canyon Drive
- **Santa Barbara, CA**: 0.68 km², 90% accuracy against State Street corridor
- **Healdsburg, CA**: 0.70 km², 95% accuracy against Plaza district
- **Truckee, CA**: 0.48 km², 92% accuracy against historic downtown
- **Yountville, CA**: 0.54 km², 88% accuracy against Washington Street core

#### Performance Characteristics
- **Scalability**: Handles 50-5000+ businesses efficiently
- **Memory usage**: <100MB for typical cities
- **Processing time**: 30-120 seconds for complete analysis
- **Accuracy**: 88-95% validation against known downtown landmarks

### Project Structure
```
dmur-analysis/
├── src/dmur_analysis/          # Main package
├── tests/                      # Test suite
├── scripts/                    # CLI tools
├── config/                     # Configuration
├── docs/                       # Documentation
├── examples/                   # Usage examples
└── data/                       # Data directories
```

### Quality Assurance
- **Code coverage**: >90% test coverage
- **Code style**: Black formatter, isort imports
- **Type checking**: mypy static analysis
- **Linting**: flake8 code quality checks
- **Documentation**: Sphinx-generated API docs