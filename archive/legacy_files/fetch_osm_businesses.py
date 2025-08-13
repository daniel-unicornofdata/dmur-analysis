#!/usr/bin/env python3
"""
Fetch business coordinates from OpenStreetMap using Overpass API
"""

import json
import time
import requests
from typing import List, Dict, Tuple, Optional
import argparse


class OSMBusinessFetcher:
    """Fetch business data from OpenStreetMap"""
    
    def __init__(self, bbox: Optional[Tuple[float, float, float, float]] = None, 
                 city_name: Optional[str] = None, state: Optional[str] = None, 
                 country: str = "United States"):
        """
        Initialize fetcher with either bounding box or city name
        
        Args:
            bbox: Tuple of (min_lat, min_lon, max_lat, max_lon)
            city_name: Name of the city
            state: State/province name (optional)
            country: Country name (default: United States)
        """
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        
        if city_name:
            self.city_name = city_name
            self.state = state
            self.country = country
            self.bbox = self.get_city_bbox()
        elif bbox:
            self.bbox = bbox
            self.city_name = None
        else:
            raise ValueError("Either bbox or city_name must be provided")
    
    def get_city_bbox(self) -> Tuple[float, float, float, float]:
        """
        Get bounding box for a city using Nominatim API
        
        Returns:
            Tuple of (min_lat, min_lon, max_lat, max_lon)
        """
        # Build query
        query = self.city_name
        if self.state:
            query += f", {self.state}"
        query += f", {self.country}"
        
        print(f"Looking up boundaries for: {query}")
        
        params = {
            'q': query,
            'format': 'json',
            'limit': 1
        }
        
        headers = {
            'User-Agent': 'DowntownMapper/1.0'
        }
        
        try:
            response = requests.get(self.nominatim_url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                raise ValueError(f"City '{query}' not found")
            
            # Get the first result
            result = data[0]
            bbox = result['boundingbox']
            
            # Nominatim returns [min_lat, max_lat, min_lon, max_lon]
            # We need [min_lat, min_lon, max_lat, max_lon]
            min_lat = float(bbox[0])
            max_lat = float(bbox[1])
            min_lon = float(bbox[2])
            max_lon = float(bbox[3])
            
            print(f"Found {result['display_name']}")
            print(f"Bounding box: ({min_lat:.4f}, {min_lon:.4f}, {max_lat:.4f}, {max_lon:.4f})")
            
            return (min_lat, min_lon, max_lat, max_lon)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching city boundaries: {e}")
            raise
        except (KeyError, IndexError) as e:
            print(f"Error parsing city data: {e}")
            raise
        
    def build_query(self) -> str:
        """
        Build Overpass QL query for ACTIVE businesses only
        
        Excludes closed, disused, abandoned, demolished, vacant, and construction sites.
        Filters amenities to only include commercial/business types.
        
        Returns:
            Overpass QL query string
        """
        min_lat, min_lon, max_lat, max_lon = self.bbox
        
        query = f"""
        [out:json][timeout:600];
        (
          // ACTIVE shops only (exclude closed/disused)
          node["shop"][!"disused:shop"][!"abandoned:shop"][!"was:shop"][!"demolished:shop"]["shop"!="vacant"]({min_lat},{min_lon},{max_lat},{max_lon});
          way["shop"][!"disused:shop"][!"abandoned:shop"][!"was:shop"][!"demolished:shop"]["shop"!="vacant"]({min_lat},{min_lon},{max_lat},{max_lon});
          relation["shop"][!"disused:shop"][!"abandoned:shop"][!"was:shop"][!"demolished:shop"]["shop"!="vacant"]({min_lat},{min_lon},{max_lat},{max_lon});
          
          // ACTIVE commercial amenities (exclude non-business amenities)
          node["amenity"~"restaurant|cafe|bar|pub|fast_food|food_court|ice_cream|biergarten|bank|atm|bureau_de_change|money_transfer|payment_terminal|cinema|theatre|nightclub|casino|arts_centre|community_centre|conference_centre|events_venue|gambling|social_centre|pharmacy|clinic|doctors|dentist|hospital|veterinary|physiotherapist|optician|hearing_aids|fuel|car_wash|car_rental|charging_station|post_office|courier|internet_cafe|library|coworking_space"][!"disused:amenity"][!"abandoned:amenity"][!"was:amenity"][!"demolished:amenity"]({min_lat},{min_lon},{max_lat},{max_lon});
          way["amenity"~"restaurant|cafe|bar|pub|fast_food|food_court|ice_cream|biergarten|bank|atm|bureau_de_change|money_transfer|payment_terminal|cinema|theatre|nightclub|casino|arts_centre|community_centre|conference_centre|events_venue|gambling|social_centre|pharmacy|clinic|doctors|dentist|hospital|veterinary|physiotherapist|optician|hearing_aids|fuel|car_wash|car_rental|charging_station|post_office|courier|internet_cafe|library|coworking_space"][!"disused:amenity"][!"abandoned:amenity"][!"was:amenity"][!"demolished:amenity"]({min_lat},{min_lon},{max_lat},{max_lon});
          relation["amenity"~"restaurant|cafe|bar|pub|fast_food|food_court|ice_cream|biergarten|bank|atm|bureau_de_change|money_transfer|payment_terminal|cinema|theatre|nightclub|casino|arts_centre|community_centre|conference_centre|events_venue|gambling|social_centre|pharmacy|clinic|doctors|dentist|hospital|veterinary|physiotherapist|optician|hearing_aids|fuel|car_wash|car_rental|charging_station|post_office|courier|internet_cafe|library|coworking_space"][!"disused:amenity"][!"abandoned:amenity"][!"was:amenity"][!"demolished:amenity"]({min_lat},{min_lon},{max_lat},{max_lon});
          
          // ACTIVE offices only
          node["office"][!"disused:office"][!"abandoned:office"][!"was:office"][!"demolished:office"]["office"!="vacant"]({min_lat},{min_lon},{max_lat},{max_lon});
          way["office"][!"disused:office"][!"abandoned:office"][!"was:office"][!"demolished:office"]["office"!="vacant"]({min_lat},{min_lon},{max_lat},{max_lon});
          relation["office"][!"disused:office"][!"abandoned:office"][!"was:office"][!"demolished:office"]["office"!="vacant"]({min_lat},{min_lon},{max_lat},{max_lon});
          
          // ACTIVE tourism businesses
          node["tourism"~"hotel|motel|hostel|guest_house|apartment|chalet|camp_site|caravan_site|attraction|gallery|museum|information"][!"disused:tourism"][!"abandoned:tourism"][!"was:tourism"][!"demolished:tourism"]({min_lat},{min_lon},{max_lat},{max_lon});
          way["tourism"~"hotel|motel|hostel|guest_house|apartment|chalet|camp_site|caravan_site|attraction|gallery|museum|information"][!"disused:tourism"][!"abandoned:tourism"][!"was:tourism"][!"demolished:tourism"]({min_lat},{min_lon},{max_lat},{max_lon});
          relation["tourism"~"hotel|motel|hostel|guest_house|apartment|chalet|camp_site|caravan_site|attraction|gallery|museum|information"][!"disused:tourism"][!"abandoned:tourism"][!"was:tourism"][!"demolished:tourism"]({min_lat},{min_lon},{max_lat},{max_lon});
          
          // ACTIVE commercial leisure facilities
          node["leisure"~"fitness_centre|sports_centre|swimming_pool|bowling_alley|amusement_arcade|adult_gaming_centre|escape_game|miniature_golf|dance"][!"disused:leisure"][!"abandoned:leisure"][!"was:leisure"][!"demolished:leisure"]({min_lat},{min_lon},{max_lat},{max_lon});
          way["leisure"~"fitness_centre|sports_centre|swimming_pool|bowling_alley|amusement_arcade|adult_gaming_centre|escape_game|miniature_golf|dance"][!"disused:leisure"][!"abandoned:leisure"][!"was:leisure"][!"demolished:leisure"]({min_lat},{min_lon},{max_lat},{max_lon});
          relation["leisure"~"fitness_centre|sports_centre|swimming_pool|bowling_alley|amusement_arcade|adult_gaming_centre|escape_game|miniature_golf|dance"][!"disused:leisure"][!"abandoned:leisure"][!"was:leisure"][!"demolished:leisure"]({min_lat},{min_lon},{max_lat},{max_lon});
          
          // ACTIVE craft businesses
          node["craft"][!"disused:craft"][!"abandoned:craft"][!"was:craft"][!"demolished:craft"]({min_lat},{min_lon},{max_lat},{max_lon});
          way["craft"][!"disused:craft"][!"abandoned:craft"][!"was:craft"][!"demolished:craft"]({min_lat},{min_lon},{max_lat},{max_lon});
          relation["craft"][!"disused:craft"][!"abandoned:craft"][!"was:craft"][!"demolished:craft"]({min_lat},{min_lon},{max_lat},{max_lon});
          
          // ACTIVE commercial buildings only
          node["building"~"commercial|retail|office|hotel|warehouse|industrial"][!"disused:building"][!"abandoned:building"][!"was:building"][!"demolished:building"]["building"!="construction"]({min_lat},{min_lon},{max_lat},{max_lon});
          way["building"~"commercial|retail|office|hotel|warehouse|industrial"][!"disused:building"][!"abandoned:building"][!"was:building"][!"demolished:building"]["building"!="construction"]({min_lat},{min_lon},{max_lat},{max_lon});
          relation["building"~"commercial|retail|office|hotel|warehouse|industrial"][!"disused:building"][!"abandoned:building"][!"was:building"][!"demolished:building"]["building"!="construction"]({min_lat},{min_lon},{max_lat},{max_lon});
          
          // ACTIVE healthcare facilities
          node["healthcare"][!"disused:healthcare"][!"abandoned:healthcare"][!"was:healthcare"][!"demolished:healthcare"]({min_lat},{min_lon},{max_lat},{max_lon});
          way["healthcare"][!"disused:healthcare"][!"abandoned:healthcare"][!"was:healthcare"][!"demolished:healthcare"]({min_lat},{min_lon},{max_lat},{max_lon});
          relation["healthcare"][!"disused:healthcare"][!"abandoned:healthcare"][!"was:healthcare"][!"demolished:healthcare"]({min_lat},{min_lon},{max_lat},{max_lon});
          
          // ACTIVE commercial landuse
          node["landuse"~"commercial|retail|industrial"][!"disused:landuse"][!"abandoned:landuse"][!"was:landuse"][!"demolished:landuse"]({min_lat},{min_lon},{max_lat},{max_lon});
          way["landuse"~"commercial|retail|industrial"][!"disused:landuse"][!"abandoned:landuse"][!"was:landuse"][!"demolished:landuse"]({min_lat},{min_lon},{max_lat},{max_lon});
          relation["landuse"~"commercial|retail|industrial"][!"disused:landuse"][!"abandoned:landuse"][!"was:landuse"][!"demolished:landuse"]({min_lat},{min_lon},{max_lat},{max_lon});
        );
        out center;
        """
        
        return query
    
    def fetch_data(self) -> Dict:
        """
        Fetch business data from Overpass API
        
        Returns:
            JSON response from Overpass API
        """
        query = self.build_query()
        
        print(f"Fetching businesses for bbox: {self.bbox}")
        print("This may take a minute...")
        
        try:
            response = requests.post(
                self.overpass_url,
                data={"data": query},
                timeout=200
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print("Request timed out. Try a smaller bounding box.")
            raise
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            raise
    
    def extract_businesses(self, data: Dict) -> List[Dict]:
        """
        Extract business information from OSM data
        
        Args:
            data: Raw JSON response from Overpass API
            
        Returns:
            List of business dictionaries with coordinates and metadata
        """
        businesses = []
        
        for element in data.get('elements', []):
            business = {
                'id': element.get('id'),
                'type': element.get('type'),
                'tags': element.get('tags', {})
            }
            
            # Get coordinates
            if element['type'] == 'node':
                business['lat'] = element.get('lat')
                business['lon'] = element.get('lon')
            elif element['type'] == 'way' and 'center' in element:
                business['lat'] = element['center'].get('lat')
                business['lon'] = element['center'].get('lon')
            elif element['type'] == 'relation' and 'center' in element:
                business['lat'] = element['center'].get('lat')
                business['lon'] = element['center'].get('lon')
            else:
                continue  # Skip if no coordinates
            
            # Extract business type (priority order - most specific first)
            if 'shop' in business['tags']:
                business['business_type'] = 'shop'
                business['business_subtype'] = business['tags']['shop']
            elif 'amenity' in business['tags']:
                business['business_type'] = 'amenity'
                business['business_subtype'] = business['tags']['amenity']
            elif 'office' in business['tags']:
                business['business_type'] = 'office'
                business['business_subtype'] = business['tags']['office']
            elif 'tourism' in business['tags']:
                business['business_type'] = 'tourism'
                business['business_subtype'] = business['tags']['tourism']
            elif 'leisure' in business['tags']:
                business['business_type'] = 'leisure'
                business['business_subtype'] = business['tags']['leisure']
            elif 'craft' in business['tags']:
                business['business_type'] = 'craft'
                business['business_subtype'] = business['tags']['craft']
            elif 'healthcare' in business['tags']:
                business['business_type'] = 'healthcare'
                business['business_subtype'] = business['tags']['healthcare']
            elif 'emergency' in business['tags']:
                business['business_type'] = 'emergency'
                business['business_subtype'] = business['tags']['emergency']
            elif 'public_transport' in business['tags']:
                business['business_type'] = 'public_transport'
                business['business_subtype'] = business['tags']['public_transport']
            elif 'industrial' in business['tags']:
                business['business_type'] = 'industrial'
                business['business_subtype'] = business['tags']['industrial']
            elif 'aeroway' in business['tags']:
                business['business_type'] = 'aeroway'
                business['business_subtype'] = business['tags']['aeroway']
            elif 'railway' in business['tags']:
                business['business_type'] = 'railway'
                business['business_subtype'] = business['tags']['railway']
            elif 'military' in business['tags']:
                business['business_type'] = 'military'
                business['business_subtype'] = business['tags']['military']
            elif 'man_made' in business['tags']:
                business['business_type'] = 'man_made'
                business['business_subtype'] = business['tags']['man_made']
            elif 'landuse' in business['tags']:
                business['business_type'] = 'landuse'
                business['business_subtype'] = business['tags']['landuse']
            elif 'building' in business['tags']:
                business['business_type'] = 'building'
                business['business_subtype'] = business['tags']['building']
            else:
                business['business_type'] = 'unknown'
                business['business_subtype'] = 'unknown'
            
            # Extract name if available
            business['name'] = business['tags'].get('name', 'Unknown')
            
            businesses.append(business)
        
        return businesses
    
    def save_to_json(self, businesses: List[Dict], filename: str):
        """
        Save businesses to JSON file
        
        Args:
            businesses: List of business dictionaries
            filename: Output filename
        """
        output = {
            'city': self.city_name if self.city_name else 'Custom area',
            'bbox': self.bbox,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_businesses': len(businesses),
            'businesses': businesses
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"Saved {len(businesses)} businesses to {filename}")
    
    def save_to_csv(self, businesses: List[Dict], filename: str):
        """
        Save businesses to CSV file
        
        Args:
            businesses: List of business dictionaries
            filename: Output filename
        """
        import csv
        
        with open(filename, 'w', newline='') as f:
            if businesses:
                fieldnames = ['id', 'lat', 'lon', 'name', 'business_type', 
                             'business_subtype', 'type']
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(businesses)
        
        print(f"Saved {len(businesses)} businesses to {filename}")


def main():
    parser = argparse.ArgumentParser(description='Fetch business data from OpenStreetMap')
    
    # Either use city name or bbox
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--city', type=str,
                      help='City name (e.g., "Palm Springs")')
    group.add_argument('--bbox', nargs=4, type=float,
                      metavar=('min_lat', 'min_lon', 'max_lat', 'max_lon'),
                      help='Bounding box coordinates')
    
    parser.add_argument('--state', type=str,
                      help='State/province name (e.g., "California")')
    parser.add_argument('--country', type=str, default='United States',
                      help='Country name (default: United States)')
    parser.add_argument('--output', default='businesses.json',
                      help='Output filename (json or csv)')
    
    args = parser.parse_args()
    
    # Create fetcher
    if args.city:
        fetcher = OSMBusinessFetcher(city_name=args.city, state=args.state, 
                                    country=args.country)
    else:
        fetcher = OSMBusinessFetcher(bbox=tuple(args.bbox))
    
    # Fetch data
    try:
        raw_data = fetcher.fetch_data()
        businesses = fetcher.extract_businesses(raw_data)
        
        print(f"Found {len(businesses)} businesses")
        
        # Print summary by type
        type_counts = {}
        for b in businesses:
            btype = b.get('business_type', 'unknown')
            type_counts[btype] = type_counts.get(btype, 0) + 1
        
        print("\nBusiness types found:")
        for btype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {btype}: {count}")
        
        # Save to file
        if args.output.endswith('.csv'):
            fetcher.save_to_csv(businesses, args.output)
        else:
            fetcher.save_to_json(businesses, args.output)
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())