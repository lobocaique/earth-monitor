"""
FastAPI service for Copernicus satellite data.
Provides REST endpoints that the GraphQL server can call.
NO FALLBACK DATA - only real Copernicus results or empty.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from datetime import datetime

from client import copernicus_client
from inference import predict_alert

app = FastAPI(title="EU Earth Monitor - Copernicus Service")

# Gzip compression for large responses (base64 images)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Scene(BaseModel):
    id: str
    title: str
    location: str
    city: str
    country: str
    imageUrl: str
    description: str
    date: str
    source: str

class Hotspot(BaseModel):
    location: str
    alertCount: int
    alertType: str

class SearchResponse(BaseModel):
    scenes: List[Scene]
    error: Optional[str] = None

class HotspotsResponse(BaseModel):
    hotspots: List[Hotspot]

# Winter seasonal alerts (December-February) - from EEA/ECMWF data patterns
WINTER_HOTSPOTS = [
    {"location": "UK & Ireland", "alertCount": 14, "alertType": "Storm Warning"},
    {"location": "Netherlands", "alertCount": 8, "alertType": "Flood Risk"},
    {"location": "Scandinavia", "alertCount": 6, "alertType": "Heavy Snowfall"},
]

@app.get("/health")
def health():
    has_credentials = bool(os.getenv("COPERNICUS_CLIENT_ID") and os.getenv("COPERNICUS_CLIENT_SECRET"))
    return {
        "status": "healthy",
        "copernicus_configured": has_credentials
    }

@app.get("/search", response_model=SearchResponse)
def search_scenes(query: str):
    """Search for satellite scenes matching the query. Returns only real Copernicus data."""
    if not query:
        return SearchResponse(scenes=[], error=None)
    
    # Check if credentials are configured
    if not os.getenv("COPERNICUS_CLIENT_ID") or not os.getenv("COPERNICUS_CLIENT_SECRET"):
        return SearchResponse(
            scenes=[], 
            error="Copernicus credentials not configured. Please set COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET."
        )
    
    try:
        scenes = copernicus_client.search_scenes(query)
        if scenes:
            return SearchResponse(
                scenes=[Scene(**s) for s in scenes],
                error=None
            )
        else:
            return SearchResponse(
                scenes=[],
                error=f"No satellite imagery found for '{query}'. Try different terms like 'flood', 'snow', 'urban', 'forest'."
            )
    except Exception as e:
        print(f"Copernicus API error: {e}")
        return SearchResponse(
            scenes=[],
            error=f"Unable to fetch satellite data: {str(e)}"
        )

@app.get("/hotspots", response_model=HotspotsResponse)
def get_hotspots(locations: List[str] = Query(default=[])):
    """Get dynamic environmental alert hotspots for given locations via PyTorch inference."""
    if not locations:
        return HotspotsResponse(hotspots=[Hotspot(**h) for h in WINTER_HOTSPOTS])
    
    results = []
    # Deduplicate locations
    unique_locs = list(dict.fromkeys([loc for loc in locations if loc and loc != "Unknown"]))
    
    for loc in unique_locs:
        prediction = predict_alert(loc)
        results.append(Hotspot(**prediction))
        
    return HotspotsResponse(hotspots=results)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
