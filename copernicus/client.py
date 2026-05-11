"""
Copernicus Data Space Ecosystem Client
Fetches real Sentinel-2 satellite imagery using OAuth2 authentication.
Uses intelligent query parsing with LLM + geocoding.
"""
import os
import requests
from datetime import datetime, timedelta
from typing import Optional, List
import base64

from query_parser import query_parser

class CopernicusClient:
    TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"
    
    def __init__(self):
        self.client_id = os.getenv("COPERNICUS_CLIENT_ID")
        self.client_secret = os.getenv("COPERNICUS_CLIENT_SECRET")
        self.access_token = None
        self.token_expiry = None
        # Reuse HTTP connections for better performance
        self.session = requests.Session()
        
    def _get_token(self) -> str:
        """Get OAuth2 access token."""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
            
        if not self.client_id or not self.client_secret:
            raise ValueError("Copernicus credentials not configured")
            
        response = self.session.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data["access_token"]
        self.token_expiry = datetime.now() + timedelta(seconds=data.get("expires_in", 300) - 30)
        return self.access_token
    
    def search_scenes(self, query: str) -> List[dict]:
        """
        Search for Sentinel-2 scenes using intelligent query parsing.
        Uses LLM to extract features and geocoding for locations.
        """
        # Parse the query using LLM + geocoding
        parsed = query_parser.parse_query(query)
        print(f"[EU Earth Monitor] Parsed query: {parsed}")
        
        results = []
        feature_name = parsed.get("feature", "satellite view")
        
        # If we got a bounding box from geocoding, use it
        if parsed.get("bbox"):
            location_name = parsed.get("location", "Unknown Location")
            city = parsed.get("city", "Unknown City")
            country = parsed.get("country", "Unknown Country")
            
            # Try to fetch 2 different time ranges to guarantee 2 images
            time_ranges = [
                (datetime.now() - timedelta(days=30), datetime.now()),
                (datetime.now() - timedelta(days=90), datetime.now() - timedelta(days=31))
            ]
            
            for i, (start_date, end_date) in enumerate(time_ranges):
                try:
                    image_data = self._get_sentinel_image(parsed["bbox"], start_date, end_date)
                    results.append({
                        "id": f"S2_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}",
                        "title": f"{feature_name.title()} - {location_name}",
                        "location": location_name,
                        "city": city,
                        "country": country,
                        "imageUrl": image_data,
                        "description": f"Sentinel-2 imagery of {location_name} showing {feature_name}. Capture window: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}.",
                        "date": end_date.strftime("%Y-%m-%d"),
                        "source": "Copernicus Sentinel-2"
                    })
                except Exception as e:
                    print(f"Error fetching Copernicus data for range {start_date}-{end_date}: {e}")
            
            if results:
                return results
                
        # No location found or both requests failed - try fallback predefined locations for the feature
        if parsed.get("feature"):
            return self._search_predefined_locations(parsed["feature"])
        
        # Nothing found
        return []
    
    def _search_predefined_locations(self, feature: str) -> List[dict]:
        """Fallback to predefined locations if geocoding fails."""
        feature_locations = {
            "snow": [
                {"bbox": [9.5, 46.0, 10.5, 47.0], "name": "Swiss Alps", "city": "Zermatt", "country": "Switzerland"},
                {"bbox": [10.5, 46.5, 12.0, 47.5], "name": "Austrian Alps", "city": "Innsbruck", "country": "Austria"},
            ],
            "flood": [
                {"bbox": [4.0, 51.0, 6.0, 53.0], "name": "Netherlands", "city": "Rotterdam", "country": "Netherlands"},
                {"bbox": [7.0, 50.0, 8.0, 51.0], "name": "Rhine Valley", "city": "Cologne", "country": "Germany"},
            ],
            "fire": [
                {"bbox": [-9.0, 37.0, -7.0, 39.0], "name": "Portugal", "city": "Faro", "country": "Portugal"},
                {"bbox": [23.0, 37.0, 24.0, 38.0], "name": "Greece", "city": "Athens", "country": "Greece"},
            ],
            "forest": [
                {"bbox": [23.0, 47.0, 25.0, 49.0], "name": "Carpathian Mountains", "city": "Brașov", "country": "Romania"},
                {"bbox": [8.0, 47.5, 9.5, 48.5], "name": "Black Forest", "city": "Freiburg", "country": "Germany"},
            ],
            "urban": [
                {"bbox": [13.0, 52.0, 14.0, 53.0], "name": "Berlin", "city": "Berlin", "country": "Germany"},
                {"bbox": [2.0, 48.5, 3.0, 49.0], "name": "Paris", "city": "Paris", "country": "France"},
            ],
            "coast": [
                {"bbox": [12.0, 43.0, 14.0, 45.0], "name": "Adriatic Coast", "city": "Split", "country": "Croatia"},
                {"bbox": [-9.5, 38.5, -8.5, 39.5], "name": "Atlantic Coast", "city": "Lisbon", "country": "Portugal"},
            ],
            "drought": [
                {"bbox": [-5.0, 38.0, -2.0, 40.0], "name": "Central Spain", "city": "Madrid", "country": "Spain"},
                {"bbox": [14.0, 37.0, 15.0, 38.0], "name": "Sicily", "city": "Palermo", "country": "Italy"},
            ],
            "agriculture": [
                {"bbox": [11.0, 48.0, 13.0, 49.0], "name": "Bavaria", "city": "Munich", "country": "Germany"},
                {"bbox": [3.0, 49.0, 5.0, 50.0], "name": "Champagne", "city": "Reims", "country": "France"},
            ],
        }
        
        locations = feature_locations.get(feature, [])
        results = []
        
        for loc in locations[:2]:  # Max 2 results
            try:
                # Use standard 60 day window for predefined
                end_date = datetime.now()
                start_date = end_date - timedelta(days=60)
                image_data = self._get_sentinel_image(loc["bbox"], start_date, end_date)
                
                results.append({
                    "id": f"S2_{feature.upper()}_{datetime.now().strftime('%Y%m%d')}_{len(results)+1}",
                    "title": f"{feature.title()} - {loc['name']}",
                    "location": loc["name"],
                    "city": loc.get("city", "Unknown"),
                    "country": loc.get("country", "Unknown"),
                    "imageUrl": image_data,
                    "description": f"Sentinel-2 imagery showing {feature} conditions in {loc['name']}.",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "Copernicus Sentinel-2"
                })
            except Exception as e:
                print(f"Error fetching {loc['name']}: {e}")
                continue
                
        return results
    
    def _get_sentinel_image(self, bbox: list, start_date: datetime, end_date: datetime, width: int = 512, height: int = 512) -> str:
        """
        Fetch a Sentinel-2 true color image for the given bounding box.
        Returns a base64 data URL.
        """
        token = self._get_token()
        
        # Sentinel Hub Process API evalscript for true color
        evalscript = """
//VERSION=3
function setup() {
    return {
        input: [{
            bands: ["B04", "B03", "B02"],
            units: "DN"
        }],
        output: {
            bands: 3,
            sampleType: "AUTO"
        }
    };
}

function evaluatePixel(sample) {
    return [sample.B04 / 3000, sample.B03 / 3000, sample.B02 / 3000];
}
"""
        
        request_body = {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                },
                "data": [{
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                            "to": end_date.strftime("%Y-%m-%dT23:59:59Z")
                        },
                        "maxCloudCoverage": 50
                    }
                }]
            },
            "output": {
                "width": width,
                "height": height,
                "responses": [{"identifier": "default", "format": {"type": "image/png"}}]
            },
            "evalscript": evalscript
        }
        
        response = self.session.post(
            self.PROCESS_URL,
            json=request_body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "image/png"
            }
        )
        
        if response.status_code != 200:
            error_detail = response.text[:500] if response.text else "No details"
            print(f"Copernicus API error: {response.status_code} - {error_detail}")
            response.raise_for_status()
        
        # Convert to base64 data URL
        image_base64 = base64.b64encode(response.content).decode("utf-8")
        return f"data:image/png;base64,{image_base64}"
    
    def get_hotspots(self) -> list:
        # We will handle this logic in main.py instead
        return []

# Singleton instance
copernicus_client = CopernicusClient()
