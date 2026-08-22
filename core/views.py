import os
import re
import random
import json
import requests
import sys
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count
from .models import Lead, Interaction

# Add scraper directory to sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scraper"))
try:
    from linkedin_xray_scraper import search_duckduckgo_osint, parse_xray_result
except ImportError:
    search_duckduckgo_osint, parse_xray_result = None, None

try:
    from bing_osint.bing_scraper import search_bing_osint, parse_bing_result
except ImportError:
    search_bing_osint, parse_bing_result = None, None

try:
    from github_harvester.github_scraper import search_github_leaders
except ImportError:
    search_github_leaders = None

try:
    from searxng_aggregator.searxng_scraper import search_searxng_aggregator, parse_searxng_result
except ImportError:
    search_searxng_aggregator, parse_searxng_result = None, None

try:
    from reddit_harvester.reddit_scraper import search_reddit_harvester
except ImportError:
    search_reddit_harvester = None

try:
    from osm_harvester.osm_scraper import search_osm_nurseries
except ImportError:
    search_osm_nurseries = None

try:
    from email_verifier.mx_verifier import verify_and_enrich_lead_email
except ImportError:
    verify_and_enrich_lead_email = None

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

def calculate_inclination_score(name="", title="", org="", notes="", location=""):
    text = f"{name or ''} {title or ''} {org or ''} {notes or ''} {location or ''}".lower()
    
    high_keywords = [
        "permaculture", "organic", "food forest", "farmland", "heirloom", 
        "rainwater harvesting", "climate adaptation", "green asset", "impact investing", "bio-organic"
    ]
    med_keywords = [
        "sustainability", "esg", "csr", "solar", "kitchen gardening", 
        "agriculture", "home schooling", "trees", "rural", "healthy lifestyle", "values", "eco", "nursery"
    ]
    seniority_keywords = [
        "director", "vp", "vice president", "head", "partner", "senior", "lead", "architect", "manager"
    ]
    
    matched = []
    score = 55  # Base score
    
    for kw in high_keywords:
        if kw in text:
            score += 15
            matched.append(kw.title())
            
    for kw in med_keywords:
        if kw in text:
            score += 10
            matched.append(kw.title())
            
    for kw in seniority_keywords:
        if kw in text:
            score += 5
            matched.append("Senior Profile")
            break
            
    score = min(score, 98)
    reasons = ", ".join(list(dict.fromkeys(matched))) if matched else "Standard Corporate Match"
    return score, reasons

def home(request):
    return render(request, "core/home.html")

def diagnostic(request):
    return render(request, "core/diagnostic.html")

def get_user_leads(request):
    """
    Returns filtered Lead queryset based on user role:
    - Superuser (admin): Returns ALL leads combined across all accounts.
    - Standard User (sea_movement, aditya): Returns ONLY leads owned by current user.
    """
    user_role = request.session.get("user_role", "superuser")
    user_id = request.session.get("user_id", "admin")
    
    if user_role == "superuser" or user_id == "admin":
        return Lead.objects.all()
    else:
        return Lead.objects.filter(owner_username=user_id)


@csrf_exempt
def dashboard(request):
    """
    Core OSINT Lead Generation & Prospecting Dashboard View.
    Supports multi-source OSINT harvesting and multi-tenant lead saving.
    """
    prospects = []
    error = None
    using_mock_data = False
    snov_key_missing = False
    prospeo_key_missing = False
    current_user_id = request.session.get("user_id", "admin")

    keywords = ""
    titles_input = ""
    locations_input = ""
    search_source = "ddg"
    per_page = 5

    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        if action == "save_lead":
            name = request.POST.get("lead_name", request.POST.get("name", "")).strip()
            title = request.POST.get("lead_title", request.POST.get("title", "")).strip()
            org = request.POST.get("lead_organization", request.POST.get("organization", "")).strip()
            email = request.POST.get("lead_email", request.POST.get("email", "")).strip() or None
            location = request.POST.get("lead_location", request.POST.get("location", "")).strip()
            linkedin = request.POST.get("lead_linkedin_url", request.POST.get("linkedin_url", "")).strip()
            source = request.POST.get("lead_source", request.POST.get("source", "manual")).strip()
            inclination_score = int(request.POST.get("inclination_score", 50))
            inclination_reasons = request.POST.get("inclination_reasons", "").strip()
            
            if name:
                lead, created = Lead.objects.get_or_create(
                    name=name,
                    email=email,
                    organization=org,
                    owner_username=current_user_id,
                    defaults={
                        'title': title,
                        'location': location,
                        'linkedin_url': linkedin,
                        'source': source,
                        'status': 'vetted',
                        'inclination_score': inclination_score,
                        'inclination_reasons': inclination_reasons,
                        'owner_username': current_user_id,
                    }
                )
                if not created:
                    lead.title = title or lead.title
                    lead.location = location or lead.location
                    lead.linkedin_url = linkedin or lead.linkedin_url
                    lead.owner_username = current_user_id
                    lead.save()

                if request.headers.get("HX-Request"):
                    from django.http import HttpResponse
                    return HttpResponse('<span class="bg-emerald-100 text-emerald-800 border border-emerald-300 text-xs font-bold px-3 py-1.5 rounded-xl inline-flex items-center gap-1">✓ Saved to CRM</span>')
                    
        elif action == "update_status":
            lead_id = request.POST.get("lead_id")
            new_status = request.POST.get("status")
            notes = request.POST.get("notes", "").strip()
            
            if lead_id and new_status:
                try:
                    lead = get_user_leads(request).get(id=lead_id)
                    old_status = lead.status
                    lead.status = new_status
                    if notes:
                        lead.notes = notes
                    lead.save()
                    
                    if old_status != new_status:
                        Interaction.objects.create(
                            lead=lead,
                            interaction_type="status_change",
                            content=f"Status changed from {old_status} to {new_status}"
                        )
                except Lead.DoesNotExist:
                    pass

        elif action == "fetch_batch_2":
            keywords = request.POST.get("keywords", "").strip()
            titles_input = request.POST.get("titles", "").strip()
            locations_input = request.POST.get("locations", "").strip()
            search_source = request.POST.get("search_source", "ddg").strip()
            
            raw_locs = [re.sub(r'\(.*?\)', '', loc).strip() for loc in (locations_input or "Chennai").split(",") if loc.strip()]
            clean_locs = [l for l in raw_locs if l] or ["Chennai"]
            loc_query = " OR ".join([f'"{l}"' for l in clean_locs[:2]])
            
            raw_titles = [t.strip() for t in (titles_input or "VP, Director, Manager").split(",") if t.strip()]
            clean_titles = [t for t in raw_titles if t] or ["VP", "Director", "Manager"]
            title_query = " OR ".join([f'"{t}"' for t in clean_titles[:4]])
            
            raw_kws = [k.strip() for k in (keywords or "Permaculture, Organic, Sustainability").split(",") if k.strip()]
            clean_kws = [k for k in raw_kws if k] or ["Permaculture", "Organic", "Sustainability"]
            kw_query = " OR ".join([f'"{k}"' for k in clean_kws[:4]])
            
            dork_query = f'site:in.linkedin.com/in/ ({loc_query}) ({title_query}) ({kw_query})'
            batch_prospects = []
            
            if search_source == "ddg" and search_duckduckgo_osint:
                try:
                    raw_items = search_duckduckgo_osint(dork_query, max_results=5, offset=5)
                    for raw in raw_items:
                        parsed = parse_xray_result(raw, target_location=clean_locs[0])
                        batch_prospects.append(parsed)
                except Exception:
                    pass
            elif search_source == "bing" and search_bing_osint:
                try:
                    raw_items = search_bing_osint(dork_query, max_results=10)
                    for raw in raw_items[5:10]:
                        parsed = parse_bing_result(raw, target_location=clean_locs[0])
                        batch_prospects.append(parsed)
                except Exception:
                    pass
                    
            for person in batch_prospects:
                if person.get("is_local_db"):
                    continue
                email = person.get("email")
                name = person.get("name")
                org = person.get("organization")
                
                db_lead = None
                if email and email != "No email found":
                    db_lead = Lead.objects.filter(email=email).first()
                if not db_lead and org and name:
                    db_lead = Lead.objects.filter(name=name, organization=org).first()
                    
                if db_lead:
                    person["is_local_db"] = True
                    person["id"] = db_lead.id
                    person["status"] = db_lead.status
                    person["notes"] = db_lead.notes
                    
            return render(request, "core/partials/prospect_batch.html", {"batch_prospects": batch_prospects})

        keywords = request.POST.get("keywords", "").strip()
        titles_input = request.POST.get("titles", "").strip()
        locations_input = request.POST.get("locations", "").strip()
        search_source = request.POST.get("search_source", "hunter").strip()
        
        try:
            per_page = int(request.POST.get("per_page", "5"))
        except ValueError:
            per_page = 5

        titles = [t.strip() for t in titles_input.split(",") if t.strip()]
        locations = [l.strip() for l in locations_input.split(",") if l.strip()]

        if search_source in ("hunter", "local", "mock"):
            query = get_user_leads(request)
            
            if keywords:
                query = query.filter(
                    Q(name__icontains=keywords) | 
                    Q(organization__icontains=keywords) | 
                    Q(notes__icontains=keywords) |
                    Q(location__icontains=keywords) |
                    Q(title__icontains=keywords)
                )
            
            if titles:
                title_query = Q()
                for title in titles:
                    title_query |= Q(title__icontains=title)
                query = query.filter(title_query)
                
            if locations:
                location_query = Q()
                for loc in locations:
                    location_query |= Q(location__icontains=loc)
                query = query.filter(location_query)
                
            db_leads = query.order_by('-created_at')[:per_page]
            
            for lead in db_leads:
                prospects.append({
                    "id": lead.id,
                    "name": lead.name,
                    "title": lead.title or "N/A",
                    "organization": lead.organization or "N/A",
                    "email": lead.email,
                    "phone": lead.phone,
                    "location": lead.location or "Unknown",
                    "linkedin_url": lead.linkedin_url,
                    "status": lead.status,
                    "notes": lead.notes,
                    "source": lead.source,
                    "is_local_db": True
                })
                
        elif search_source == "ddg":
            raw_locs = [re.sub(r'\(.*?\)', '', loc).strip() for loc in (locations_input or "Chennai").split(",") if loc.strip()]
            clean_locs = [l for l in raw_locs if l] or ["Chennai"]
            loc_query = " OR ".join([f'"{l}"' for l in clean_locs[:2]])
            
            raw_titles = [t.strip() for t in (titles_input or "VP, Director, Manager").split(",") if t.strip()]
            clean_titles = [t for t in raw_titles if t] or ["VP", "Director", "Manager"]
            title_query = " OR ".join([f'"{t}"' for t in clean_titles[:4]])
            
            raw_kws = [k.strip() for k in (keywords or "Permaculture, Organic, Sustainability").split(",") if k.strip()]
            clean_kws = [k for k in raw_kws if k] or ["Permaculture", "Organic", "Sustainability"]
            kw_query = " OR ".join([f'"{k}"' for k in clean_kws[:4]])
            
            dork_query = f'site:in.linkedin.com/in/ ({loc_query}) ({title_query}) ({kw_query})'
            
            if search_duckduckgo_osint:
                try:
                    raw_items = search_duckduckgo_osint(dork_query, max_results=per_page, offset=0)
                    for raw in raw_items:
                        parsed = parse_xray_result(raw, target_location=clean_locs[0])
                        prospects.append(parsed)
                except Exception as exc:
                    error = f"DuckDuckGo OSINT search failed: {exc}"
            else:
                error = "DuckDuckGo scraper module unavailable."

        elif search_source == "bing":
            loc_str = locations_input or "Chennai"
            title_str = titles_input or "VP, Director"
            kw_str = keywords or "Permaculture, Organic Farming"

            clean_titles = ' OR '.join([f'"{t.strip()}"' for t in title_str.split(",") if t.strip()]) if title_str else '"VP" OR "Director"'
            clean_kws = ' OR '.join([f'"{k.strip()}"' for k in kw_str.split(",") if k.strip()]) if kw_str else '"Permaculture" OR "Organic"'
            dork_query = f'site:in.linkedin.com/in/ "{loc_str.split(",")[0].strip()}" ({clean_titles}) ({clean_kws})'

            if search_bing_osint:
                try:
                    raw_items = search_bing_osint(dork_query, max_results=per_page)
                    for raw in raw_items:
                        parsed = parse_bing_result(raw, target_location=loc_str.split(",")[0].strip())
                        prospects.append(parsed)
                except Exception as exc:
                    error = f"Bing OSINT search failed: {exc}"
            else:
                error = "Bing OSINT scraper module unavailable."

        elif search_source == "github":
            loc_str = locations_input.split(",")[0].strip() if locations_input else "Chennai"
            kw_str = keywords.split(",")[0].strip() if keywords else ""

            if search_github_leaders:
                try:
                    prospects = search_github_leaders(location=loc_str, keyword=kw_str, limit=per_page)
                except Exception as exc:
                    error = f"GitHub Harvester failed: {exc}"
            else:
                error = "GitHub scraper module unavailable."

        elif search_source == "searxng":
            loc_str = locations_input or "Chennai"
            title_str = titles_input or "VP, Director"
            kw_str = keywords or "Permaculture, Organic"
            dork_query = f'site:in.linkedin.com/in/ "{loc_str.split(",")[0].strip()}" {title_str} {kw_str}'

            if search_searxng_aggregator:
                try:
                    raw_items = search_searxng_aggregator(dork_query, max_results=per_page)
                    for raw in raw_items:
                        parsed = parse_searxng_result(raw, target_location=loc_str.split(",")[0].strip())
                        prospects.append(parsed)
                except Exception as exc:
                    error = f"SearXNG Aggregator search failed: {exc}"
            else:
                error = "SearXNG scraper module unavailable."

        elif search_source == "reddit":
            sub_str = locations_input.split(",")[0].strip() if locations_input else "Chennai"
            kw_str = keywords.split(",")[0].strip() if keywords else "permaculture"

            if search_reddit_harvester:
                try:
                    prospects = search_reddit_harvester(subreddit=sub_str, keyword=kw_str, limit=per_page)
                except Exception as exc:
                    error = f"Reddit Harvester search failed: {exc}"
            else:
                error = "Reddit scraper module unavailable."

        elif search_source == "osm":
            loc_str = locations_input.split(",")[0].strip() if locations_input else "Chennai"

            if search_osm_nurseries:
                try:
                    prospects = search_osm_nurseries(location=loc_str, limit=per_page)
                except Exception as exc:
                    error = f"OpenStreetMap Harvester failed: {exc}"
            else:
                error = "OpenStreetMap scraper module unavailable."

        elif search_source == "snov":
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
                    
                    start_url = "https://api.snov.io/v2/domain-search/domain-emails/start"
                    payload = {
                        "domain": domain,
                        "type": "all",
                        "limit": per_page
                    }
                    start_resp = requests.post(start_url, json=payload, headers=headers, timeout=10)
                    start_resp.raise_for_status()
                    start_data = start_resp.json()
                    
                    emails_data = start_data.get("emails") or start_data.get("data", [])
                    org = start_data.get("companyName") or domain.split(".")[0].title()
                    
                    if not emails_data:
                        task_hash = start_data.get("task_hash") or start_data.get("meta", {}).get("task_hash")
                        if task_hash:
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
                    
                    if emails_data and isinstance(emails_data, list):
                        for email_item in emails_data[:per_page]:
                            email_val = email_item.get("email") or email_item.get("value")
                            first = email_item.get("firstName") or email_item.get("first_name") or ""
                            last = email_item.get("lastName") or email_item.get("last_name") or ""
                            name = f"{first} {last}".strip()
                            if not name and email_val:
                                name = email_val.split("@")[0].replace(".", " ").title()
                                
                            p_item = {
                                "name": name or "Unknown Lead",
                                "title": email_item.get("position") or email_item.get("position_raw") or "Employee",
                                "organization": org,
                                "email": email_val,
                                "location": domain,
                                "linkedin_url": email_item.get("linkedin"),
                            }
                            prospects.append(p_item)
                            
                            # AUTO-SAVE Snov.io prospects into SQLite DB
                            if name:
                                Lead.objects.get_or_create(
                                    name=name,
                                    email=email_val,
                                    organization=org,
                                    defaults={
                                        'title': p_item['title'],
                                        'location': domain,
                                        'linkedin_url': email_item.get("linkedin"),
                                        'source': 'snov',
                                        'status': 'discovered'
                                    }
                                )
                except requests.exceptions.RequestException as exc:
                    error = f"Snov.io API request failed: {exc}"
                    
        elif search_source == "prospeo":
            domain = keywords.lower().strip()
            if "://" in domain:
                domain = domain.split("://")[1]
            domain = domain.split("/")[0]
            if domain.startswith("www."):
                domain = domain[4:]
            if not domain:
                domain = "example.com"
                
            api_key = os.environ.get("PROSPEO_API_KEY")
            if not api_key:
                using_mock_data = True
                prospeo_key_missing = True
                prospects = generate_mock_hunter_prospects(domain, per_page)
            else:
                try:
                    search_url = "https://api.prospeo.io/search-person"
                    headers = {
                        "Content-Type": "application/json",
                        "X-KEY": api_key
                    }
                    search_payload = {
                        "filters": {
                            "company": {
                                "websites": {
                                    "include": [domain]
                                }
                            }
                        },
                        "limit": per_page
                    }
                    search_resp = requests.post(search_url, json=search_payload, headers=headers, timeout=15)
                    
                    if search_resp.status_code in (401, 403):
                        using_mock_data = True
                        prospeo_key_missing = True
                        prospects = generate_mock_hunter_prospects(domain, per_page)
                    else:
                        search_resp.raise_for_status()
                        results = search_resp.json().get("results", [])
                        
                        for item in results[:per_page]:
                            person_data = item.get("person", {})
                            comp_data = item.get("company", {})
                            
                            first_name = person_data.get("first_name")
                            last_name = person_data.get("last_name")
                            full_name = person_data.get("full_name") or f"{first_name} {last_name}".strip()
                            
                            email_obj = person_data.get("email") or {}
                            email_val = None
                            
                            if email_obj.get("revealed") and email_obj.get("email"):
                                email_val = email_obj.get("email")
                            else:
                                try:
                                    enrich_url = "https://api.prospeo.io/enrich-person"
                                    enrich_payload = {
                                        "data": {
                                            "first_name": first_name,
                                            "last_name": last_name,
                                            "company_website": domain
                                        }
                                    }
                                    enrich_resp = requests.post(enrich_url, json=enrich_payload, headers=headers, timeout=10)
                                    if enrich_resp.status_code == 200:
                                        enrich_data = enrich_resp.json()
                                        email_val = enrich_data.get("person", {}).get("email", {}).get("email")
                                except Exception:
                                    pass
                                    
                            if not email_val:
                                email_val = email_obj.get("email") or "No email found"
                                
                            loc = person_data.get("location", {})
                            loc_str = loc.get("country") or loc.get("state") or loc.get("city") or domain
                            org_name = comp_data.get("name") or domain.split(".")[0].title()
                            
                            p_item = {
                                "name": full_name,
                                "title": person_data.get("current_job_title") or "Employee",
                                "organization": org_name,
                                "email": email_val,
                                "location": loc_str,
                                "linkedin_url": person_data.get("linkedin_url")
                            }
                            prospects.append(p_item)
                            
                            # AUTO-SAVE Prospeo.io prospects into SQLite DB
                            if full_name:
                                Lead.objects.get_or_create(
                                    name=full_name,
                                    email=email_val if email_val != "No email found" else None,
                                    organization=org_name,
                                    defaults={
                                        'title': p_item['title'],
                                        'location': loc_str,
                                        'linkedin_url': person_data.get("linkedin_url"),
                                        'source': 'prospeo',
                                        'status': 'discovered'
                                    }
                                )
                except requests.exceptions.RequestException as exc:
                    error = f"Prospeo API request failed: {exc}"

    # Auto-link database saved status for all rendered prospect cards
    for person in prospects:
        if person.get("is_local_db"):
            continue
        email = person.get("email")
        name = person.get("name")
        org = person.get("organization")
        
        db_lead = None
        if email and email != "No email found":
            db_lead = Lead.objects.filter(email=email).first()
        if not db_lead and org and name:
            db_lead = Lead.objects.filter(name=name, organization=org).first()
            
        if db_lead:
            person["is_local_db"] = True
            person["id"] = db_lead.id
            person["status"] = db_lead.status
            person["notes"] = db_lead.notes

    context = {
        "prospects": prospects,
        "error": error,
        "using_mock_data": using_mock_data,
        "snov_key_missing": snov_key_missing,
        "prospeo_key_missing": prospeo_key_missing,
        "keywords": keywords,
        "titles": titles_input,
        "locations": locations_input,
        "search_source": search_source,
        "per_page": per_page,
    }
    return render(request, "core/dashboard.html", context)


def master_view(request):
    """
    Master Database / CRM View - Displays all saved leads from SQLite database
    with full pipeline management controls, filters, and interaction history.
    """
    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        
        if action == "update_status":
            lead_id = request.POST.get("lead_id")
            new_status = request.POST.get("status")
            notes = request.POST.get("notes", "").strip()
            
            if lead_id and new_status:
                try:
                    lead = Lead.objects.get(id=lead_id)
                    old_status = lead.status
                    lead.status = new_status
                    if notes:
                        lead.notes = notes
                    lead.save()
                    
                    if old_status != new_status:
                        Interaction.objects.create(
                            lead=lead,
                            interaction_type="status_change",
                            content=f"Status updated from {old_status} to {new_status}"
                        )
                except Lead.DoesNotExist:
                    pass
                    
        elif action == "delete_lead":
            lead_id = request.POST.get("lead_id")
            if lead_id:
                Lead.objects.filter(id=lead_id).delete()
                
    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    source_filter = request.GET.get("source", "").strip()
    
    leads = get_user_leads(request).order_by("-created_at")
    
    if q:
        leads = leads.filter(
            Q(name__icontains=q) |
            Q(organization__icontains=q) |
            Q(title__icontains=q) |
            Q(email__icontains=q) |
            Q(location__icontains=q) |
            Q(notes__icontains=q)
        )
        
    if status_filter:
        leads = leads.filter(status=status_filter)
        
    if source_filter:
        leads = leads.filter(source=source_filter)

    # CRM Summary Stats
    total_leads = get_user_leads(request).count()
    contacted_count = get_user_leads(request).filter(status="contacted").count()
    interested_count = get_user_leads(request).filter(status="interested").count()
    joined_count = get_user_leads(request).filter(status="joined").count()

    context = {
        "leads": leads,
        "q": q,
        "status_filter": status_filter,
        "source_filter": source_filter,
        "total_leads": total_leads,
        "contacted_count": contacted_count,
        "interested_count": interested_count,
        "joined_count": joined_count,
        "status_choices": Lead.STATUS_CHOICES,
        "source_choices": Lead.SOURCE_CHOICES,
    }
    return render(request, "core/master.html", context)


def crm_view(request):
    """
    Dedicated CRM Pipeline Board View - Visual Stage-by-Stage Kanban Pipeline
    for managing lead flow, status transitions, investor tracking, and outreach.
    """
    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        
        if action == "update_status":
            lead_id = request.POST.get("lead_id")
            new_status = request.POST.get("status")
            notes = request.POST.get("notes", "").strip()
            
            if lead_id and new_status:
                try:
                    lead = get_user_leads(request).get(id=lead_id)
                    old_status = lead.status
                    lead.status = new_status
                    if notes:
                        lead.notes = notes
                    lead.save()
                    
                    if old_status != new_status:
                        Interaction.objects.create(
                            lead=lead,
                            interaction_type="status_change",
                            content=f"Pipeline stage moved from {old_status} to {new_status}"
                        )
                except Lead.DoesNotExist:
                    pass
                    
        elif action == "delete_lead":
            lead_id = request.POST.get("lead_id")
            if lead_id:
                get_user_leads(request).filter(id=lead_id).delete()

    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    source_filter = request.GET.get("source", "").strip()
    
    leads = get_user_leads(request).order_by("-created_at")
    
    if q:
        leads = leads.filter(
            Q(name__icontains=q) |
            Q(organization__icontains=q) |
            Q(title__icontains=q) |
            Q(email__icontains=q) |
            Q(location__icontains=q) |
            Q(notes__icontains=q)
        )
        
    if source_filter:
        leads = leads.filter(source=source_filter)

    if status_filter and status_filter != "all":
        leads = leads.filter(status=status_filter)

    total_leads = get_user_leads(request).count()
    discovered_count = get_user_leads(request).filter(status="discovered").count()
    vetted_count = get_user_leads(request).filter(status="vetted").count()
    contacted_count = get_user_leads(request).filter(status="contacted").count()
    interested_count = get_user_leads(request).filter(status="interested").count()
    joined_count = get_user_leads(request).filter(status="joined").count()

    context = {
        "leads": leads,
        "total_leads": total_leads,
        "discovered_count": discovered_count,
        "vetted_count": vetted_count,
        "contacted_count": contacted_count,
        "interested_count": interested_count,
        "joined_count": joined_count,
        "q": q,
        "status_filter": status_filter,
        "source_filter": source_filter,
        "status_choices": Lead.STATUS_CHOICES,
        "source_choices": Lead.SOURCE_CHOICES,
    }
    return render(request, "core/crm.html", context)



@csrf_exempt
def import_leads(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    upload_secret = os.environ.get("UPLOAD_SECRET_KEY")
    if not upload_secret:
        return JsonResponse({"error": "Server configuration error: Upload secret not set"}, status=500)
    
    auth_header = request.headers.get("Authorization")
    provided_token = None
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() in ("bearer", "token"):
            provided_token = parts[1]
        else:
            provided_token = parts[0]
            
    if not provided_token:
        provided_token = request.headers.get("X-Upload-Secret")
        
    if provided_token != upload_secret:
        return JsonResponse({"error": "Unauthorized"}, status=401)
        
    try:
        data = json.loads(request.body)
        if not isinstance(data, list):
            return JsonResponse({"error": "Invalid body format. Expected a JSON list of leads."}, status=400)
            
        created_count = 0
        updated_count = 0
        
        for item in data:
            name = item.get("name", "").strip()
            if not name:
                continue
                
            email = item.get("email", "").strip() or None
            org = item.get("organization", "").strip() or None
            
            lead = None
            if email:
                lead = Lead.objects.filter(email=email).first()
            if not lead and org:
                lead = Lead.objects.filter(name=name, organization=org).first()
            if not lead:
                lead = Lead.objects.filter(name=name, email__isnull=True, organization__isnull=True).first()
                
            score, reasons = calculate_inclination_score(
                name=name,
                title=item.get("title", ""),
                org=org or "",
                notes=item.get("notes", ""),
                location=item.get("location", "")
            )

            if lead:
                if item.get("title"):
                    lead.title = item.get("title")
                if org:
                    lead.organization = org
                if email:
                    lead.email = email
                if item.get("phone"):
                    lead.phone = item.get("phone")
                if item.get("location"):
                    lead.location = item.get("location")
                if item.get("notes"):
                    if lead.notes:
                        lead.notes += f"\n\n[Import Update]: {item.get('notes')}"
                    else:
                        lead.notes = item.get("notes")
                if item.get("status"):
                    lead.status = item.get("status")
                if item.get("source"):
                    lead.source = item.get("source")
                lead.inclination_score = score
                lead.inclination_reasons = reasons
                lead.save()
                updated_count += 1
            else:
                lead = Lead.objects.create(
                    name=name,
                    title=item.get("title"),
                    organization=org,
                    email=email,
                    phone=item.get("phone"),
                    location=item.get("location"),
                    linkedin_url=item.get("linkedin_url"),
                    source=item.get("source", "manual"),
                    status=item.get("status", "discovered"),
                    notes=item.get("notes"),
                    inclination_score=score,
                    inclination_reasons=reasons,
                    owner_username="admin"
                )
                created_count += 1
                
        return JsonResponse({
            "success": True,
            "created": created_count,
            "updated": updated_count
        })
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def about_view(request):
    return render(request, "core/about.html")

def support_view(request):
    return render(request, "core/support.html")

def login_view(request):
    error = None
    if request.method == "POST":
        userid_input = request.POST.get("userid", "").strip()
        password_input = request.POST.get("password", "").strip()
        
        # Load 3 accounts from environment variables (.env)
        accounts = {
            "admin": {
                "userid": os.environ.get("ADMIN_USERID", "admin").strip(),
                "password": os.environ.get("ADMIN_PASSWORD", "admin@123").strip(),
                "role": "superuser",
                "display_name": "Admin Superuser"
            },
            "sea_movement": {
                "userid": os.environ.get("USER1_USERID", "sea_movement").strip(),
                "password": os.environ.get("USER1_PASSWORD", "sea@1234").strip(),
                "role": "user",
                "display_name": "SEA Movement"
            },
            "aditya": {
                "userid": os.environ.get("USER2_USERID", "aditya").strip(),
                "password": os.environ.get("USER2_PASSWORD", "aditya@123").strip(),
                "role": "user",
                "display_name": "Aditya Pandey"
            }
        }
        
        authenticated_user = None
        for key, acc in accounts.items():
            valid_id = acc["userid"]
            if (userid_input == valid_id or userid_input.lower() == f"{valid_id}@greenerafarms.org") and password_input == acc["password"]:
                authenticated_user = (key, acc)
                break
                
        if authenticated_user:
            key, acc = authenticated_user
            request.session["is_authenticated"] = True
            request.session["is_admin"] = (acc["role"] == "superuser")
            request.session["user_role"] = acc["role"]
            request.session["user_id"] = key
            request.session["user_name"] = acc["display_name"]
            return redirect("dashboard")
        else:
            error = "Invalid User ID or Password."
            
    return render(request, "core/login.html", {"error": error})

def signup_view(request):
    if request.method == "POST":
        name = request.POST.get("name", "Standard User").strip()
        request.session["is_authenticated"] = True
        request.session["is_admin"] = False
        request.session["user_role"] = "user"
        request.session["user_id"] = name.lower().replace(" ", "_")
        request.session["user_name"] = name
        return redirect("dashboard")
    return render(request, "core/signup.html")

def logout_view(request):
    request.session.flush()
    return redirect("home")

def overview_view(request):
    user_leads = get_user_leads(request)
    total_leads = user_leads.count()
    high_inclination = user_leads.filter(inclination_score__gte=70).count()
    contacted_count = user_leads.filter(status="contacted").count()
    vetted_count = user_leads.filter(status="vetted").count()
    
    # Priority people to connect with (highest inclination score first)
    people_to_connect = user_leads.order_by("-inclination_score", "-created_at")[:8]
    
    context = {
        "total_leads": total_leads,
        "high_inclination": high_inclination,
        "contacted_count": contacted_count,
        "vetted_count": vetted_count,
        "people_to_connect": people_to_connect,
    }
    return render(request, "core/overview.html", context)
