# Advanced B2B Lead Generation & Email Finding Techniques (Free & High-Volume)

This document provides a detailed technical blueprint for setting up high-volume B2B lead generation systems using free tiers, custom scripts, and Open-Source Intelligence (OSINT) tools.

---

## 1. API Stacking & Key Rotation (Method 1)
Many B2B data providers offer free API keys with monthly replenishing credits. By stacking multiple providers and programmatically rotating keys, you can build a combined pool of **200+ free lookups per month**.

### Key Providers (Free Tiers)
| API Provider | Free Credits / Month | Sign-Up Rule | Key Strengths |
| :--- | :--- | :--- | :--- |
| **Prospeo.io** | 75 - 100 credits | Gmail allowed | High accuracy, SMTP-verified data |
| **Snov.io** | 50 credits | Gmail allowed | Strong domain search, async API |
| **GetProspect** | 50 credits | Gmail allowed | LinkedIn profile extraction |
| **Tomba.io** | 25 credits | Gmail allowed | Direct clone of Hunter.io, easy schema |
| **Hunter.io** | 25 credits | Business email | Premium domain matching accuracy |

### Programmatic Rotation Implementation
To implement this in Python, you can set up a simple API registry that falls back to the next provider if a key runs out of credits or encounters rate limits:

```python
class EmailFinderRegistry:
    def __init__(self, keys):
        self.keys = keys # dict of provider: api_key

    def find_email(self, first_name, last_name, domain):
        # 1. Try Prospeo
        if self.keys.get("PROSPEO"):
            try:
                # Call Prospeo enrich-person...
                return prospeo_result
            except Exception:
                pass # Fall back
        
        # 2. Try Snov.io
        if self.keys.get("SNOV_SECRET"):
            try:
                # Call Snov.io API...
                return snov_result
            except Exception:
                pass
                
        # 3. Try Tomba.io
        # ...
```

---

## 2. LinkedIn X-Ray Search via Google Custom Search API (Method 2)
LinkedIn search limits (such as the "commercial use limit") and API walls can be bypassed by using Google's index to search LinkedIn profiles. This is called **X-Ray Searching**.

### Step A: Google Custom Search Engine (CSE) Setup
1. Go to the **[Google Programmable Search Engine Dashboard](https://programmable-search.google.com/)**.
2. Click **Add** and create a search engine restricted to: `linkedin.com/in/*`
3. Retrieve your **Search Engine ID (CX)**.
4. Go to **[Google Cloud Console](https://console.cloud.google.com/)**, enable the **Custom Search API**, and generate a free API Key.
5. Google gives you **100 free search queries per day** (which returns up to 1,000 profiles/day).

### Step B: Python Search Query Implementation
Run Google search queries programmatically to retrieve target profile names and companies:

```python
import requests

def search_linkedin_profiles(query, api_key, cx):
    # E.g., query = 'site:linkedin.com/in/ "Sustainability Director" "Bangalore"'
    url = "https://customsearch.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query
    }
    resp = requests.get(url, params=params)
    items = resp.json().get("items", [])
    
    profiles = []
    for item in items:
        title = item.get("title", "") # E.g., "John Doe - VP Sustainability - Stripe"
        link = item.get("link", "")   # LinkedIn URL
        profiles.append({"meta": title, "link": link})
    return profiles
```

---

## 3. Email Pattern Guessing & SMTP Handshake Verification (Method 3)
Most companies configure their corporate emails under standard naming patterns. Once you have a name (from Step 2) and a company domain, you can guess and verify their email for free.

### Step A: Common Email Patterns
* `{first}@{domain}` (e.g. `john@company.com`)
* `{first}.{last}@{domain}` (e.g. `john.doe@company.com`)
* `{first_initial}{last}@{domain}` (e.g. `jdoe@company.com`)
* `{first}{last}@{domain}` (e.g. `johndoe@company.com`)

### Step B: SMTP Verification Script (Verify without sending emails)
This script does a TCP handshake on port 25 with the recipient's mail server to check if the address is valid.

```python
import smtplib
import socket
import dns.resolver

def verify_email_smtp(email_address):
    domain = email_address.split('@')[1]
    
    try:
        # 1. Resolve MX records for the domain
        records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(sorted(records, key=lambda record: record.preference)[0].exchange)
        
        # 2. Establish socket connection to port 25
        host = socket.gethostname()
        server = smtplib.SMTP(timeout=10)
        server.set_debuglevel(0)
        server.connect(mx_record, 25)
        
        # 3. SMTP Handshake
        server.helo(host)
        server.mail('sender@example.com') # Your dummy sender email
        code, message = server.rcpt(str(email_address))
        server.quit()
        
        # 4. Check response status code
        if code == 250:
            return "VALID"
        elif code == 550:
            return "INVALID"
        else:
            return "UNSURE (MX responded with code: {})".format(code)
            
    except Exception as e:
        return f"ERROR: {str(e)}"
```
> [!WARNING]
> **Catch-All Domains**: Some mail servers (like those running on Microsoft Outlook/Exchange) are configured as "Catch-All". They will respond with `250 OK` for *any* email address you check. You should check a randomized fake address (e.g., `xyz987@company.com`) first. If that returns `250 OK`, the server is a Catch-All and SMTP verification won't work.

---

## 4. Open-Source OSINT Scrapers (Zero Limits)
You can run dedicated OSINT scrapers locally on your machine. Since they query public directories and PGP key servers, they have **no credit limits**.

### 1. theHarvester (Command-line)
`theHarvester` is an industry-standard penetration testing tool that gathers names, emails, IPs, and subdomains from public search engines.
* **Installation**: 
  ```bash
  pip install git+https://github.com/laramies/theHarvester.git
  ```
* **Run a search**:
  ```bash
  theHarvester -d stripe.com -b google,bing,pgp
  ```
  *(This scans Google, Bing, and PGP key directories for any public emails associated with `stripe.com`)*.

### 2. Phonebook.cz (Web Directory)
`Phonebook.cz` is a search engine containing billions of leaked/public emails, domains, and URLs.
* **Usage**: Go to **[Phonebook.cz](https://phonebook.cz/)**, enter any company domain (e.g. `stripe.com`), and select **"emails"** to view a massive indexed list of emails for that company.

### 3. Hunter.io / Snov.io Pattern Lookup (Unlimited Free)
You don't need credits to search company email *patterns*. Both Hunter.io and Tomba.io allow you to check the pattern for a domain (e.g. `{first_initial}{last}`) for free, which you can then combine with the SMTP verification script above to check emails in bulk.
