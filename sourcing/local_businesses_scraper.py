import os
import json
import time
import requests
import argparse

def query_overpass_api(query_str):
    """
    Executes a query against the OpenStreetMap Overpass API interpreter, supporting fallbacks.
    """
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.n.osm.ch/api/interpreter"
    ]
    
    headers = {
        "User-Agent": "HeadHuntOSMScraper/1.0 (contact: support@seamovement.org)"
    }
    
    for url in endpoints:
        print(f"Sending query to OpenStreetMap Overpass API endpoint: {url}...")
        try:
            response = requests.post(url, data={"data": query_str}, headers=headers, timeout=20)
            if response.status_code == 200:
                return response.json().get("elements", [])
            else:
                print(f" -> Server returned status code: {response.status_code}. Retrying fallback...")
        except Exception as e:
            print(f" -> Error connecting to {url}: {e}. Retrying fallback...")
            
    print("Error: All Overpass API endpoints failed or timed out.")
    return []

def main():
    parser = argparse.ArgumentParser(description="Find regional plant nurseries, organic shops, and agricultural stores in Chennai & Bangalore.")
    parser.add_argument("--location", default="Chennai", choices=["Chennai", "Bangalore", "Vandavasi"], 
                        help="Target area for OSM Overpass search (Chennai, Bangalore, or Vandavasi)")
    parser.add_argument("--output", default="nursery_leads.json", help="Path to save the resulting leads JSON")
    
    args = parser.parse_args()
    
    # Define bounding boxes roughly for regional search:
    # coordinates in format (min_lat, min_lon, max_lat, max_lon)
    bounds = {
        "Chennai": "12.80,80.10,13.25,80.35",
        "Bangalore": "12.85,77.40,13.15,77.80",
        "Vandavasi": "12.45,79.50,12.90,79.80"
    }
    
    bbox = bounds.get(args.location)
    
    # Overpass Query QL:
    # Query nodes/ways in the bbox that are shops for garden centres, organic products, or florists/farmers
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["shop"="garden_centre"]({bbox});
      way["shop"="garden_centre"]({bbox});
      node["shop"="organic"]({bbox});
      way["shop"="organic"]({bbox});
      node["shop"="farm"]({bbox});
      way["shop"="farm"]({bbox});
    );
    out body;
    >;
    out skel qt;
    """
    
    elements = query_overpass_api(overpass_query)
    print(f"Retrieved {len(elements)} items from OpenStreetMap.")
    
    leads = []
    for elem in elements:
        tags = elem.get("tags")
        if not tags:
            continue
            
        name = tags.get("name")
        if not name:
            continue
            
        shop_type = tags.get("shop", "Agricultural Shop")
        title = f"{shop_type.replace('_', ' ').title()} Owner/Manager"
        
        phone = tags.get("phone") or tags.get("contact:phone") or "N/A"
        website = tags.get("website") or tags.get("contact:website") or "N/A"
        
        # Build location description
        street = tags.get("addr:street") or ""
        suburb = tags.get("addr:suburb") or ""
        city = tags.get("addr:city") or args.location
        full_location = ", ".join(filter(None, [street, suburb, city]))
        
        # Formulate notes
        notes = f"OSM Tag: {shop_type}\nWebsite: {website}\nPhone: {phone}\nOSM ID: {elem.get('id')}"
        
        lead = {
            "name": name,
            "title": title,
            "organization": name,
            "email": "", # Email is usually not in OSM data
            "phone": phone if phone != "N/A" else "",
            "location": full_location,
            "linkedin_url": website if website != "N/A" else "",
            "notes": notes,
            "source": "gmaps", # Group under gmaps/local business source
            "status": "discovered"
        }
        leads.append(lead)
        
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.output)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(leads, f, indent=4, ensure_ascii=False)
        print(f"\nDone! Extracted {len(leads)} local business leads for {args.location}. Saved to: {output_path}")
        print("To sync this to your hosted dashboard database, run:")
        print(f"python sync_leads.py {args.output}")
    except Exception as e:
        print(f"Error saving leads file: {e}")

if __name__ == "__main__":
    main()
