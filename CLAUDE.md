# Downtown Mapping Analysis Project

## Project Goal
Create a GeoJSON file showing the approximate borders of a downtown area by analyzing business density from OpenStreetMap data, then evaluate Downtown Mixed-Use Readiness (DMUR) using real estate listing data.

## Current Status: PHASE 1 COMPLETE ✅
Successfully developed and tested a fully autonomous downtown boundary detection algorithm that works across multiple cities without manual intervention.

## Phase 1: Downtown Boundary Detection (COMPLETED)

### Data Collection
- **OSM Business Data**: Comprehensive Overpass API queries fetching all commercial establishments
- **Active Business Filtering**: Excludes disused, abandoned, demolished, and vacant businesses
- **Commercial Focus**: Filters for shops, amenities, offices, tourism, craft businesses, and healthcare

### Algorithm Implementation
- **Auto-Focus Detection**: DBSCAN clustering + KDE peak detection to automatically identify downtown core areas
  - Adaptive epsilon based on coordinate range (1% of smaller dimension)
  - Multi-method approach: clustering + histogram + KDE peak detection
  - Selects most compact high-density area (minimum 20 businesses, <30% of total area)
- **Density Analysis**: Kernel Density Estimation with adaptive bandwidth and grid-based analysis
  - Adaptive bandwidth: 0.5% of coordinate range
  - 90th percentile density threshold with fallback to 70th percentile
  - Commercial business filtering (excludes parks, residential, swimming pools)
- **Boundary Generation**: Alpha shapes (concave hull) with fallback to convex hull for optimal boundary smoothing
  - Delaunay triangulation with alpha parameter filtering (default 0.02)
  - 0.003 degree buffer for boundary smoothing
  - Handles both Polygon and MultiPolygon geometries
- **Multi-Format Output**: GeoJSON boundaries, PNG visualizations, and interactive HTML maps
  - Folium-based interactive maps with business type color coding
  - Density heatmaps with business location overlays
  - Statistics panels showing area, density, and business counts

### Validation Results
Tested successfully on multiple cities with accurate downtown identification:
- **Palm Springs**: 1.40 km² (95% validation accuracy)
- **Truckee**: 0.48 km² (captures main commercial district)
- **Santa Barbara**: 0.68 km² (State Street corridor)
- **Healdsburg**: 0.70 km² (Plaza area)
- **Yountville**: 0.54 km² (Washington Street core, includes Bouchon establishments)

### Technical Implementation
- **Script**: `analyze_downtown_generic.py` - Fully autonomous algorithm requiring only city business JSON input
- **Command**: `python3 analyze_downtown_generic.py --input {city}.json`
- **Auto-generated outputs**: 
  - `{city}_downtown.geojson` (boundary data with business points)
  - `{city}_analysis.png` (density heatmap + business locations)
  - `{city}_map.html` (interactive Folium map with legend and statistics)
- **Key Parameters**:
  - `--density-threshold` (default: 90) - Percentile for high-density areas
  - `--bandwidth` (default: 0.002) - KDE bandwidth for density estimation
  - `--alpha` (default: 0.02) - Alpha shapes parameter for boundary smoothing
  - `--focus-area` - Manual focus coordinates (optional, auto-detected by default)

## Phase 2: DMUR Score Calculation (NEXT PHASE)

### Objective
Calculate Downtown Mixed-Use Readiness (DMUR) score (0-1) using real estate listing data within identified downtown boundaries.

### DMUR Score Components
1. **Mixed-Use Index (MXI) Score (0.4 weight)**
   - Measures spatial integration of residential and commercial uses
   - Calculate distance from each residential listing to nearest businesses
   - Formula: `MXI = 1 - (avg_distance_to_businesses / max_distance_threshold)`
   - Uses existing business location data from Phase 1

2. **Balance Score (0.3 weight)**
   - Ratio of residential units to commercial establishments
   - Optimal range: 10-50 residential units per commercial business
   - Formula: `Balance = 1 - |log10(residential_ratio/optimal_ratio)|`

3. **Housing Density Score (0.2 weight)**
   - Residential units per km² within downtown boundary
   - Normalize against urban density benchmarks

4. **Housing Diversity Score (0.1 weight)**
   - Bedroom mix variety using Shannon diversity index
   - More variety = better mixed demographics

### Required Listing Data Format
- `lat`, `lon` (coordinates for geospatial filtering)
- `bedrooms` (0=studio, 1, 2, 3+)
- `area_sqm` (square meters)
- `price` (rental/sale price)
- `listing_type` (rental/sale)

### Implementation Plan
1. Load Zillow/Airbnb scraped listing data
2. Filter listings within downtown boundaries using Phase 1 results
3. Calculate MXI using distance analysis to existing business locations
4. Compute Balance ratio between residential and commercial density
5. Generate weighted composite DMUR score
6. Output scored results with geographic visualization

## Technical Stack
- **Phase 1**: Python, OSM Overpass API, scikit-learn, shapely, folium, matplotlib
- **Phase 2**: Add real estate data processing, spatial distance calculations, urban planning metrics

## Files Structure
- `fetch_osm_businesses.py` - OSM data collection
- `analyze_downtown_generic.py` - Boundary detection algorithm
- `validate_generic.py` - Validation against known landmarks
- `{city}_downtown.geojson` - Generated downtown boundaries
- `{city}_map.html` - Interactive downtown maps

## Next Steps
Implement DMUR scoring system using scraped real estate listing data to evaluate downtown mixed-use development potential.