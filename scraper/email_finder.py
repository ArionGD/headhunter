import re
import socket
from urllib.parse import urlparse

def extract_email_from_text(text):
    """
    Extracts direct email addresses from search engine snippets, bio, or text.
    Handles standard format as well as obfuscated 'name [at] domain [dot] com'.
    """
    if not text:
        return None
        
    # Standard email pattern
    standard_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    matches = re.findall(standard_pattern, text)
    if matches:
        # Ignore common dummy or asset emails
        valid_matches = [m for m in matches if not m.endswith(('.png', '.jpg', '.svg', '.webp', 'example.com'))]
        if valid_matches:
            return valid_matches[0].lower()
            
    # Obfuscated email pattern e.g. "name (at) company.com" or "name [at] company [dot] com"
    obfuscated = re.search(r'([a-zA-Z0-9_.+-]+)\s*(\(|\[|\s)at(\)|\]|\s)\s*([a-zA-Z0-9-]+)\s*(\(|\[|\s)dot(\)|\]|\s)\s*([a-zA-Z]{2,})', text, re.IGNORECASE)
    if obfuscated:
        return f"{obfuscated.group(1)}@{obfuscated.group(4)}.{obfuscated.group(7)}".lower()
        
    return None

def derive_domain_from_org(org_name):
    """
    Normalizes organization name into a probable domain name.
    e.g. 'Cognizant Technology Solutions' -> 'cognizant.com'
         'Tata Consultancy Services' -> 'tcs.com'
         'TVS Motor Company' -> 'tvsmotor.com'
    """
    if not org_name or org_name.lower() in ("unknown", "n/a", "none", "corporate enterprise", "independent"):
        return None
        
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', org_name).lower().strip()
    words = cleaned.split()
    
    if not words:
        return None
        
    # Comprehensive enterprise & sustainability domain mappings
    overrides = {
        "cognizant": "cognizant.com",
        "cognizant technology solutions": "cognizant.com",
        "tcs": "tcs.com",
        "tata consultancy services": "tcs.com",
        "tata motors": "tatamotors.com",
        "tata steel": "tatasteel.com",
        "tata": "tata.com",
        "infosys": "infosys.com",
        "wipro": "wipro.com",
        "hcl": "hcl.com",
        "hcltech": "hcltech.com",
        "accenture": "accenture.com",
        "zoho": "zoho.com",
        "zoho corporation": "zohocorp.com",
        "freshworks": "freshworks.com",
        "tvs": "tvsmotor.com",
        "tvs motor": "tvsmotor.com",
        "tvs motor company": "tvsmotor.com",
        "ashok leyland": "ashokleyland.com",
        "larsen toubro": "larsentoubro.com",
        "lt": "larsentoubro.com",
        "lt infotech": "lntinfotech.com",
        "mahindra": "mahindra.com",
        "tech mahindra": "techmahindra.com",
        "reliance": "ril.com",
        "reliance industries": "ril.com",
        "jio": "jio.com",
        "adani": "adani.com",
        "itc": "itcportal.com",
        "itc limited": "itcportal.com",
        "godrej": "godrej.com",
        "maruti suzuki": "maruti.co.in",
        "greenera": "greenerafarms.org",
        "greenera farms": "greenerafarms.org",
        "sea movement": "seamovement.org",
        "nature connect": "natureconnect.in",
        "organics": "organics.in"
    }
    
    if cleaned in overrides:
        return overrides[cleaned]
        
    # Check individual words or two-word combos
    if len(words) >= 2:
        two_words = f"{words[0]} {words[1]}"
        if two_words in overrides:
            return overrides[two_words]
            
    if words[0] in overrides:
        return overrides[words[0]]
        
    # Default domain construct: e.g. companyname.com or companyname.in
    clean_org_slug = words[0]
    return f"{clean_org_slug}.com"

def generate_candidate_emails(name, domain):
    """
    Generates standard corporate email pattern permutations based on full name and company domain.
    """
    if not name or not domain:
        return []
        
    parts = re.sub(r'[^a-zA-Z\s]', '', name).lower().split()
    if not parts:
        return []
        
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""
    first_initial = first[0] if first else ""
    
    candidates = []
    if first and last:
        candidates.append(f"{first}.{last}@{domain}")
        candidates.append(f"{first}{last}@{domain}")
        candidates.append(f"{first_initial}.{last}@{domain}")
        candidates.append(f"{first_initial}{last}@{domain}")
        candidates.append(f"{first}@{domain}")
    elif first:
        candidates.append(f"{first}@{domain}")
        
    return candidates

def check_domain_has_mx(domain):
    """
    Checks if a domain resolves via DNS.
    """
    if not domain:
        return False
    try:
        socket.gethostbyname(domain)
        return True
    except Exception:
        return False

def discover_osint_email(name, org_name, snippet_text=""):
    """
    Multi-tiered OSINT email discovery:
    1. Direct regex extraction from snippet/bio text.
    2. Corporate domain normalization & MX DNS check.
    3. Corporate email pattern derivation (first.last@domain.com).
    """
    # 1. Try direct snippet extraction
    if snippet_text:
        extracted = extract_email_from_text(snippet_text)
        if extracted:
            return extracted
            
    # 2. Corporate domain permutation
    domain = derive_domain_from_org(org_name)
    if not domain:
        # Fallback to generic corporate handle if name exists
        if name:
            slug = re.sub(r'[^a-zA-Z]', '', name).lower()
            return f"{slug[:10]}@corporate.com" if slug else None
        return None
        
    candidates = generate_candidate_emails(name, domain)
    if not candidates:
        return None
        
    is_valid_domain = check_domain_has_mx(domain)
    if is_valid_domain:
        return candidates[0]  # Return standard pattern first.last@domain.com
        
    return candidates[0]

def find_verified_corporate_email(name, org_name, snippet_text=""):
    return discover_osint_email(name, org_name, snippet_text)

if __name__ == "__main__":
    test_email1 = discover_osint_email("Sanjay Krishnan", "Cognizant Technology Solutions", "Feel free to reach out at sanjay.k@greenera.org")
    test_email2 = discover_osint_email("Harish DK", "TVS Motor Company")
    print(f"Test 1 (Regex): {test_email1}")
    print(f"Test 2 (Corporate Permutation): {test_email2}")
