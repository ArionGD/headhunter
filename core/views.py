import os
import random
import requests
from django.shortcuts import render

APOLLO_API_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/api_search"
APOLLO_CONTACTS_SEARCH_URL = "https://api.apollo.io/api/v1/contacts/search"

# Dynamic Mock Data Generation
MOCK_FIRST_NAMES = ["Rajesh", "Aishwarya", "Vikram", "Priyanka", "Sanjay", "Anitha", "Karthik", "Deepa", "Arun", "Meera", "Vijay", "Divya", "Suresh", "Lakshmi", "Rohan", "Shruti"]
MOCK_LAST_NAMES = ["Kumar", "Rajan", "Sundaram", "Krishnan", "Iyer", "Naidu", "Pillai", "Reddy", "Sharma", "Joshi", "Patel", "Das", "Sen", "Nair", "Murthy", "Rao"]
MOCK_COMPANIES = [
    ("Coromandel Green Ventures", "coromandelgreen.example.com"),
    ("Greenera Farms", "greenerafarms.example.com"),
    ("Deccan Agri-Tech", "deccanagri.example.com"),
    ("Sahyadri Bio-Organics", "sahyadribio.example.com"),
    ("Tamil Nadu Agro Industries", "tnagro.example.com"),
    ("Southern Canopy Capital", "southerncanopy.example.com"),
    ("Indus Seed Fund", "indusseed.example.com"),
    ("Cauvery Sustainable Forestry", "cauveryforest.example.com"),
    ("Nilgiri Eco-Holdings", "nilgirieco.example.com"),
    ("Kisan Growth Partners", "kisangrowth.example.com")
]

def generate_mock_prospects(keywords, titles, locations, count):
    prospects = []
    default_titles = ["Sustainability Director", "Agrotech Investor", "Sustainability Partner", "Product Manager"]
    default_locations = ["Chennai", "Bangalore", "Coimbatore"]
    
    active_titles = titles if titles else default_titles
    active_locations = locations if locations else default_locations
    
    for _ in range(count):
        first = random.choice(MOCK_FIRST_NAMES)
        last = random.choice(MOCK_LAST_NAMES)
        title = random.choice(active_titles)
        location = random.choice(active_locations)
        org, domain = random.choice(MOCK_COMPANIES)
        
        email = f"{first.lower()}.{last.lower()}@{domain}"
        
        prospects.append({
            "name": f"{first} {last}",
            "title": title,
            "organization": org,
            "email": email,
            "location": location,
        })
    return prospects

def generate_mock_hunter_prospects(domain, count):
    prospects = []
    company_name = domain.split(".")[0].title()
    first_names = ["Sarah", "Michael", "David", "Jessica", "James", "Emily", "Robert", "Amanda", "William", "Ashley"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Wilson"]
    titles = ["HR Manager", "Software Engineer", "Sales Executive", "Product Designer", "Operations Lead", "Financial Analyst"]
    
    for _ in range(count):
        first = random.choice(first_names)
        last = random.choice(last_names)
        title = random.choice(titles)
        email = f"{first.lower()}.{last.lower()}@{domain}"
        
        prospects.append({
            "name": f"{first} {last}",
            "title": title,
            "organization": f"{company_name} Corp",
            "email": email,
            "location": domain,
        })
    return prospects

def home(request):
    return render(request, "core/home.html")


def diagnostic(request):
    return render(request, "core/diagnostic.html")


def dashboard(request):
    prospects = []
    error = None
    using_mock_data = False
    plan_restricted = False
    snov_key_missing = False
    
    # Retain input values for rendering in the form
    keywords = ""
    titles_input = ""
    locations_input = ""
    search_source = "global"
    per_page = 5

    if request.method == "POST":
        keywords = request.POST.get("keywords", "").strip()
        titles_input = request.POST.get("titles", "").strip()
        locations_input = request.POST.get("locations", "").strip()
        search_source = request.POST.get("search_source", "global").strip()
        
        try:
            per_page = int(request.POST.get("per_page", "5"))
        except ValueError:
            per_page = 5

        # Format list arguments
        titles = [t.strip() for t in titles_input.split(",") if t.strip()]
        locations = [l.strip() for l in locations_input.split(",") if l.strip()]

        if search_source == "mock":
            using_mock_data = True
            prospects = generate_mock_prospects(keywords, titles, locations, per_page)
            
        elif search_source == "snov":
            # Clean domain
            domain = keywords.lower().strip()
            if "://" in domain:
                domain = domain.split("://")[1]
            domain = domain.split("/")[0]
            if domain.startswith("www."):
                domain = domain[4:]
            if not domain:
                domain = "example.com"
                
            client_id = os.environ.get("SNOV_CLIENT_ID")
            client_secret = os.environ.get("SNOV_CLIENT_SECRET")
            if not client_id or not client_secret:
                using_mock_data = True
                snov_key_missing = True
                prospects = generate_mock_hunter_prospects(domain, per_page)
            else:
                try:
                    # 1. Get access token
                    auth_url = "https://api.snov.io/v1/oauth/access_token"
                    auth_data = {
                        "grant_type": "client_credentials",
                        "client_id": client_id,
                        "client_secret": client_secret
                    }
                    auth_resp = requests.post(auth_url, data=auth_data, timeout=10)
                    auth_resp.raise_for_status()
                    token = auth_resp.json().get("access_token")
                    
                    headers = {
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                    
                    # 2. Start search
                    start_url = "https://api.snov.io/v2/domain-search/domain-emails/start"
                    payload = {
                        "domain": domain,
                        "type": "all",
                        "limit": per_page
                    }
                    start_resp = requests.post(start_url, json=payload, headers=headers, timeout=10)
                    start_resp.raise_for_status()
                    start_data = start_resp.json()
                    
                    # Check if ready immediately
                    emails_data = start_data.get("emails") or start_data.get("data", [])
                    org = start_data.get("companyName") or domain.split(".")[0].title()
                    
                    if not emails_data:
                        task_hash = start_data.get("meta", {}).get("task_hash")
                        if task_hash:
                            # Poll up to 5 times (wait 1.5s each)
                            import time
                            result_url = f"https://api.snov.io/v2/domain-search/domain-emails/result/{task_hash}"
                            for _ in range(5):
                                time.sleep(1.5)
                                res_resp = requests.get(result_url, headers=headers, timeout=10)
                                res_resp.raise_for_status()
                                res_data = res_resp.json()
                                
                                status = res_data.get("status")
                                if status == "completed" or "emails" in res_data or (res_data.get("data") and len(res_data.get("data", [])) > 0):
                                    emails_data = res_data.get("data") or res_data.get("emails", [])
                                    org = res_data.get("meta", {}).get("domain", domain).split(".")[0].title()
                                    break
                    
                    # Parse results
                    if emails_data and isinstance(emails_data, list):
                        for email_item in emails_data[:per_page]:
                            email_val = email_item.get("email") or email_item.get("value")
                            first = email_item.get("firstName") or email_item.get("first_name") or ""
                            last = email_item.get("lastName") or email_item.get("last_name") or ""
                            name = f"{first} {last}".strip()
                            if not name and email_val:
                                name = email_val.split("@")[0].replace(".", " ").title()
                                
                            prospects.append({
                                "name": name,
                                "title": email_item.get("position") or email_item.get("position_raw") or "Employee",
                                "organization": org,
                                "email": email_val,
                                "location": domain,
                                "linkedin_url": email_item.get("linkedin"),
                            })
                except requests.exceptions.RequestException as exc:
                    error = f"Snov.io API request failed: {exc}"
                    
        else:
            api_key = os.environ.get("APOLLO_API_KEY")
            if not api_key:
                error = "APOLLO_API_KEY environment variable is not set. Please check your .env file."
            else:
                headers = {
                    "Content-Type": "application/json",
                    "X-Api-Key": api_key,
                    "Cache-Control": "no-cache",
                }
                
                if search_source == "global":
                    url = APOLLO_API_SEARCH_URL
                    payload = {
                        "per_page": per_page,
                    }
                    if locations:
                        payload["person_locations"] = locations
                    if titles:
                        payload["person_titles"] = titles
                    if keywords:
                        payload["q_keywords"] = keywords
                        
                    try:
                        response = requests.post(url, json=payload, headers=headers, timeout=15)
                        
                        if response.status_code in (401, 403):
                            using_mock_data = True
                            plan_restricted = True
                            prospects = generate_mock_prospects(keywords, titles, locations, per_page)
                        else:
                            response.raise_for_status()
                            data = response.json()
                            for person in data.get("people", []):
                                loc = ", ".join(filter(None, [person.get("city"), person.get("state"), person.get("country")]))
                                prospects.append({
                                    "name": person.get("name") or f"{person.get('first_name', '')} {person.get('last_name', '')}".strip() or "Unknown",
                                    "title": person.get("title") or "N/A",
                                    "organization": person.get("organization_name") or "Unknown Company",
                                    "email": person.get("email"),
                                    "location": loc or "Unknown Location",
                                    "linkedin_url": person.get("linkedin_url"),
                                })
                    except requests.exceptions.RequestException as exc:
                        error = f"Apollo API request failed: {exc}"
                        
                elif search_source == "contacts":
                    url = APOLLO_CONTACTS_SEARCH_URL
                    payload = {
                        "per_page": per_page,
                    }
                    if keywords:
                        payload["q_keywords"] = keywords
                    try:
                        response = requests.post(url, json=payload, headers=headers, timeout=15)
                        
                        if response.status_code in (401, 403):
                            error = f"Apollo API request failed (HTTP {response.status_code}). Ensure your key is valid and has Contacts access."
                        else:
                            response.raise_for_status()
                            data = response.json()
                            for contact in data.get("contacts", []):
                                loc = ", ".join(filter(None, [contact.get("city"), contact.get("state"), contact.get("country")]))
                                prospects.append({
                                    "name": contact.get("name") or f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip() or "Unknown",
                                    "title": contact.get("title") or "N/A",
                                    "organization": contact.get("organization_name") or (contact.get("organization") or {}).get("name") or "Unknown Company",
                                    "email": contact.get("email"),
                                    "location": loc or "Unknown Location",
                                    "linkedin_url": contact.get("linkedin_url"),
                                })
                    except requests.exceptions.RequestException as exc:
                        error = f"Apollo API request failed: {exc}"

    context = {
        "prospects": prospects,
        "error": error,
        "using_mock_data": using_mock_data,
        "plan_restricted": plan_restricted,
        "snov_key_missing": snov_key_missing,
        "keywords": keywords,
        "titles": titles_input,
        "locations": locations_input,
        "search_source": search_source,
        "per_page": per_page,
    }
    return render(request, "core/dashboard.html", context)


