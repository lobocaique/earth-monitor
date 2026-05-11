"""
Intelligent Query Parser using HuggingFace LLM + OpenStreetMap Geocoding
Extracts environmental features and locations from natural language queries.
"""
import os
import re
import requests
from typing import Optional, Dict, Tuple
import time
from functools import lru_cache

class QueryParser:
    """Parse natural language queries using HuggingFace LLM and geocode locations."""
    
    HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    
    # Fallback regex patterns if LLM fails
    LOCATION_PATTERNS = [
        r"(?:near|in|around|at)\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|,|\.)",
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+(?:coast|mountains?|forest|river|lake|city|area)",
        r"([A-Z][a-zA-Z]+)\s*$",  # Last capitalized word
    ]
    
    FEATURE_KEYWORDS = {
        "snow": ["snow", "winter", "ice", "frost", "glacier", "frozen"],
        "flood": ["flood", "flooding", "flooded", "water", "rain", "storm"],
        "fire": ["fire", "wildfire", "burn", "burning", "smoke"],
        "forest": ["forest", "tree", "woodland", "deforestation", "logging"],
        "urban": ["urban", "city", "town", "building", "metropolitan"],
        "coast": ["coast", "coastal", "beach", "shore", "sea", "ocean"],
        "drought": ["drought", "dry", "arid", "desert"],
        "agriculture": ["farm", "agriculture", "crop", "field", "harvest"],
    }
    
    def __init__(self):
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN")
        self._last_geocode_time = 0
        
    def parse_query(self, query: str) -> Dict:
        """
        Parse a natural language query into structured data.
        Returns: {"feature": str, "location": str, "bbox": [w, s, e, n] or None, "city": str, "country": str}
        """
        result = {"feature": None, "location": None, "bbox": None, "city": None, "country": None, "raw_query": query}
        
        # Try LLM parsing first
        if self.hf_token:
            llm_result = self._parse_with_llm(query)
            if llm_result:
                result.update(llm_result)
        
        # Fallback to regex if LLM didn't extract location
        if not result.get("location"):
            result["location"] = self._extract_location_regex(query)
            
        # Fallback feature extraction
        if not result.get("feature"):
            result["feature"] = self._extract_feature_regex(query)
        
        # Geocode the location if found
        if result.get("location"):
            geo_data = self._geocode_location(result["location"])
            if geo_data:
                result["bbox"] = geo_data["bbox"]
                result["city"] = geo_data["city"]
                result["country"] = geo_data["country"]
                
        return result
    
    def _parse_with_llm(self, query: str) -> Optional[Dict]:
        """Use HuggingFace LLM to parse the query."""
        if not self.hf_token:
            return None
            
        prompt = f"""<s>[INST] Extract the environmental feature and location from this satellite imagery search query.

Query: "{query}"

Respond with ONLY a JSON object like this:
{{"feature": "snow|flood|fire|forest|urban|coast|drought|agriculture", "location": "city or region name"}}

If no location is mentioned, use null for location.
If no clear feature, use null for feature.
[/INST]"""
        
        try:
            response = requests.post(
                self.HF_API_URL,
                headers={"Authorization": f"Bearer {self.hf_token}"},
                json={
                    "inputs": prompt,
                    "parameters": {"max_new_tokens": 100, "temperature": 0.1}
                },
                timeout=10
            )
            
            if response.status_code == 200:
                text = response.json()[0].get("generated_text", "")
                # Extract JSON from response
                json_match = re.search(r'\{[^}]+\}', text)
                if json_match:
                    import json
                    parsed = json.loads(json_match.group())
                    return {
                        "feature": parsed.get("feature") if parsed.get("feature") != "null" else None,
                        "location": parsed.get("location") if parsed.get("location") != "null" else None
                    }
            else:
                print(f"HuggingFace API error: {response.status_code}")
        except Exception as e:
            print(f"LLM parsing error: {e}")
            
        return None
    
    def _extract_location_regex(self, query: str) -> Optional[str]:
        """Extract location using regex patterns."""
        for pattern in self.LOCATION_PATTERNS:
            match = re.search(pattern, query)
            if match:
                location = match.group(1).strip()
                # Filter out feature keywords
                if location.lower() not in ["snow", "flood", "fire", "forest", "urban", "coast"]:
                    return location
        return None
    
    def _extract_feature_regex(self, query: str) -> Optional[str]:
        """Extract environmental feature from query."""
        query_lower = query.lower()
        for feature, keywords in self.FEATURE_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                return feature
        return None
    
    def _geocode_location(self, location: str) -> Optional[Dict]:
        """
        Geocode a location name to bounding box using OpenStreetMap Nominatim.
        """
        return self._geocode_cached(location)
    
    @staticmethod
    @lru_cache(maxsize=100)
    def _geocode_cached(location: str) -> Optional[Dict]:
        """Cached geocoding to avoid repeated API calls for same locations."""
        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": f"{location}",
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1
                },
                headers={"User-Agent": "EU-Earth-Monitor/1.0"},
                timeout=5
            )
            
            if response.status_code == 200 and response.json():
                result = response.json()[0]
                bbox = result.get("boundingbox")
                address = result.get("address", {})
                
                # Extract city (could be town, village, county, etc.)
                city = address.get("city") or address.get("town") or address.get("village") or address.get("county") or location
                country = address.get("country", "Unknown")
                
                if bbox:
                    south, north, west, east = map(float, bbox)
                    buffer = 0.2
                    return {
                        "bbox": [west - buffer, south - buffer, east + buffer, north + buffer],
                        "city": city,
                        "country": country
                    }
        except Exception as e:
            print(f"Geocoding error: {e}")
            
        return None


# Singleton instance
query_parser = QueryParser()
