import requests

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
]

DISTRICT_BOUNDS = {
    "Chennai": "12.80,80.10,13.25,80.35",
    "Tiruvallur": "13.05,79.80,13.35,80.10",
    "Kanchipuram": "12.75,79.60,13.00,79.90",
    "Chengalpet": "12.60,79.90,12.85,80.15",
    "Ranipet": "12.85,79.25,13.10,79.55"
}

def search_osm_nurseries(location: str = "Chennai", limit: int = 5):
    """
    Keyless OpenStreetMap Overpass harvester fetching regional plant nurseries & organic businesses.
    """
    print(f"Executing OpenStreetMap Harvester for location={location}...")
    bbox = DISTRICT_BOUNDS.get(location, DISTRICT_BOUNDS["Chennai"])

    query = f"""
    [out:json][timeout:15];
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

    headers = {
        "User-Agent": "HeadHuntOSM/2.0"
    }

    leads = []
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            resp = requests.post(endpoint, data={"data": query}, headers=headers, timeout=12)
            if resp.status_code == 200:
                elements = resp.json().get("elements", [])
                for elem in elements:
                    tags = elem.get("tags")
                    if not tags or not tags.get("name"):
                        continue

                    name = tags.get("name")
                    shop_type = tags.get("shop", "Garden Centre").replace("_", " ").title()
                    phone = tags.get("phone") or tags.get("contact:phone") or ""
                    website = tags.get("website") or tags.get("contact:website") or ""
                    street = tags.get("addr:street") or ""
                    city = tags.get("addr:city") or location
                    full_loc = f"{street}, {city}".strip(", ")

                    leads.append({
                        "name": name,
                        "title": f"{shop_type} Owner / Manager",
                        "organization": name,
                        "email": "",
                        "phone": phone,
                        "location": full_loc,
                        "linkedin_url": website,
                        "notes": f"OSM Business Tag: {shop_type}\nPhone: {phone}\nWebsite: {website}",
                        "source": "osm",
                        "status": "discovered"
                    })
                    if len(leads) >= limit:
                        break
                if leads:
                    break
        except Exception as e:
            print(f"OSM Harvester endpoint {endpoint} notice: {e}")
            continue

    return leads
