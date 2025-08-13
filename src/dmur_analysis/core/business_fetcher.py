"""
Business data fetching from OpenStreetMap using Overpass API.
"""

import json
import logging
import requests
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BusinessQuery:
    """Configuration for business data queries."""
    city: str
    state: str
    country: str = "United States"
    active_only: bool = True
    timeout: int = 180


class BusinessFetcher:
    """Fetches business data from OpenStreetMap using Overpass API."""
    
    OVERPASS_URL = "http://overpass-api.de/api/interpreter"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DMUR-Analysis/1.0 (Downtown Mixed-Use Readiness Analysis)'
        })
    
    def fetch_businesses(self, query: BusinessQuery, output_file: Optional[str] = None) -> Dict:
        """
        Fetch business data for a city.
        
        Args:
            query: BusinessQuery configuration
            output_file: Optional output file path
            
        Returns:
            Dictionary containing business data
        """
        logger.info(f"Fetching business data for {query.city}, {query.state}")
        
        overpass_query = self._build_overpass_query(query)
        
        try:
            response = self._execute_query(overpass_query, query.timeout)
            business_data = self._process_response(response, query)
            
            if output_file:
                self._save_data(business_data, output_file)
                
            return business_data
            
        except Exception as e:
            logger.error(f"Failed to fetch business data: {e}")
            raise
    
    def _build_overpass_query(self, query: BusinessQuery) -> str:
        """Build Overpass QL query for business data."""
        area_filter = f'"{query.city}", "{query.state}", "{query.country}"'
        
        # Base query structure
        base_query = f'''
        [out:json][timeout:{query.timeout}];
        area[name~{area_filter}][admin_level~"[4-8]"]->.searchArea;
        '''
        
        # Business type queries
        business_queries = []
        
        if query.active_only:
            # Shops (excluding disused)
            business_queries.append('''
            node["shop"][!"disused:shop"][!"abandoned:shop"][!"demolished:shop"]
            [!"vacant:shop"](area.searchArea);
            ''')
            
            # Amenities (commercial only, excluding disused)
            business_queries.append('''
            node["amenity"~"restaurant|cafe|bar|pub|fast_food|food_court|ice_cream|bank|atm|cinema|theatre|nightclub|casino|pharmacy|clinic|doctors|dentist|fuel|car_wash|car_rental|post_office|courier|internet_cafe|library|coworking_space"]
            [!"disused:amenity"][!"abandoned:amenity"](area.searchArea);
            ''')
            
            # Offices (excluding disused)
            business_queries.append('''
            node["office"][!"disused:office"][!"abandoned:office"](area.searchArea);
            ''')
        else:
            # All shops, amenities, and offices
            business_queries.extend([
                'node["shop"](area.searchArea);',
                'node["amenity"](area.searchArea);',
                'node["office"](area.searchArea);'
            ])
        
        # Additional commercial categories
        business_queries.extend([
            'node["tourism"~"hotel|motel|guest_house|hostel|attraction|museum|gallery|information"](area.searchArea);',
            'node["leisure"~"fitness_centre|sports_centre|bowling_alley"](area.searchArea);',
            'node["craft"~"winery|brewery|distillery"](area.searchArea);',
            'node["building"~"commercial|retail|office|hotel"](area.searchArea);',
            'node["healthcare"~"clinic|hospital|pharmacy|dentist|doctor"](area.searchArea);',
            'way["landuse"~"commercial|retail"](area.searchArea);'
        ])
        
        # Combine all queries
        full_query = base_query + "(\n" + "\n".join(business_queries) + "\n);\nout center meta;"
        
        return full_query
    
    def _execute_query(self, query: str, timeout: int) -> requests.Response:
        """Execute Overpass query with retries."""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Executing Overpass query (attempt {attempt + 1}/{max_retries})")
                
                response = self.session.post(
                    self.OVERPASS_URL,
                    data=query,
                    timeout=timeout + 30
                )
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Query failed, retrying in {retry_delay}s: {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise
    
    def _process_response(self, response: requests.Response, query: BusinessQuery) -> Dict:
        """Process Overpass API response into structured business data."""
        data = response.json()
        
        businesses = []
        bbox = [float('inf'), float('inf'), float('-inf'), float('-inf')]  # min_lat, min_lon, max_lat, max_lon
        
        for element in data.get('elements', []):
            if not self._is_valid_business(element):
                continue
                
            business = self._extract_business_info(element)
            if business:
                businesses.append(business)
                
                # Update bounding box
                lat, lon = business['lat'], business['lon']
                bbox[0] = min(bbox[0], lat)  # min_lat
                bbox[1] = min(bbox[1], lon)  # min_lon
                bbox[2] = max(bbox[2], lat)  # max_lat
                bbox[3] = max(bbox[3], lon)  # max_lon
        
        result = {
            "city": query.city,
            "state": query.state,
            "country": query.country,
            "bbox": bbox if bbox[0] != float('inf') else [],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_businesses": len(businesses),
            "businesses": businesses
        }
        
        logger.info(f"Processed {len(businesses)} businesses for {query.city}")
        return result
    
    def _is_valid_business(self, element: Dict) -> bool:
        """Check if element represents a valid business."""
        if element['type'] not in ['node', 'way']:
            return False
            
        # Must have coordinates
        if element['type'] == 'node':
            if 'lat' not in element or 'lon' not in element:
                return False
        elif element['type'] == 'way':
            if 'center' not in element:
                return False
                
        # Must have relevant tags
        tags = element.get('tags', {})
        if not tags:
            return False
            
        # Check for business-relevant tags
        business_tags = ['shop', 'amenity', 'office', 'tourism', 'leisure', 'craft', 'building', 'healthcare', 'landuse']
        return any(tag in tags for tag in business_tags)
    
    def _extract_business_info(self, element: Dict) -> Optional[Dict]:
        """Extract structured business information from OSM element."""
        tags = element.get('tags', {})
        
        # Get coordinates
        if element['type'] == 'node':
            lat, lon = element['lat'], element['lon']
        elif element['type'] == 'way' and 'center' in element:
            lat, lon = element['center']['lat'], element['center']['lon']
        else:
            return None
        
        # Determine business type and subtype
        business_type, business_subtype = self._classify_business(tags)
        if not business_type:
            return None
        
        # Extract name
        name = tags.get('name', tags.get('brand', 'Unknown'))
        
        return {
            "id": element['id'],
            "type": element['type'],
            "tags": tags,
            "lat": lat,
            "lon": lon,
            "business_type": business_type,
            "business_subtype": business_subtype,
            "name": name
        }
    
    def _classify_business(self, tags: Dict) -> Tuple[Optional[str], Optional[str]]:
        """Classify business type and subtype from OSM tags."""
        # Priority order for classification
        type_priorities = ['shop', 'amenity', 'office', 'tourism', 'craft', 'healthcare', 'leisure', 'building', 'landuse']
        
        for tag_type in type_priorities:
            if tag_type in tags:
                return tag_type, tags[tag_type]
        
        return None, None
    
    def _save_data(self, data: Dict, output_file: str) -> None:
        """Save business data to JSON file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved business data to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save data to {output_file}: {e}")
            raise