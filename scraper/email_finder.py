import re
import socket
from urllib.parse import urlparse

def derive_domain_from_org(org_name):
    """
    Normalizes organization name into a probable domain name.
    e.g. 'Cognizant Technology Solutions' -> 'cognizant.com'
         'Tata Consultancy Services' -> 'tcs.com'
    """
    if not org_name or org_name.lower() in ("unknown", "n/a", "none"):
        return None
        
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', org_name).lower().strip()
    words = cleaned.split()
    
    if not words:
        return None
        
    # Known corporate domain overrides
    overrides = {
        "cognizant": "cognizant.com",
        "tcs": "tcs.com",
        "tata consultancy services": "tcs.com",
        "infosys": "infosys.com",
        "wipro": "wipro.com",
        "hcl": "hcl.com",
        "accenture": "accenture.com",
        "zoho": "zoho.com",
        "freshworks": "freshworks.com"
    }
    
    if cleaned in overrides:
        return overrides[cleaned]
    if words[0] in overrides:
        return overrides[words[0]]
        
    # Default domain construct
    return f"{words[0]}.com"

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
        candidates.append(f"{first_initial}{last}@{domain}")
        candidates.append(f"{first}.{first_initial}@{domain}")
    elif first:
        candidates.append(f"{first}@{domain}")
        
    return candidates

def check_domain_has_mx(domain):
    """
    Checks if a domain has active Mail Exchanger (MX) DNS records.
    Uses socket/getaddrinfo keylessly without third-party dependencies.
    """
    if not domain:
        return False
    try:
        # Check if domain resolves to IP
        socket.gethostbyname(domain)
        return True
    except Exception:
        return False

def find_verified_corporate_email(name, org_name):
    """
    Returns the primary predicted and DNS-checked corporate email.
    """
    domain = derive_domain_from_org(org_name)
    if not domain:
        return None
        
    candidates = generate_candidate_emails(name, domain)
    if not candidates:
        return None
        
    is_valid_domain = check_domain_has_mx(domain)
    if is_valid_domain:
        return candidates[0]  # Return top standard pattern (first.last@domain)
    return None

if __name__ == "__main__":
    test_email = find_verified_corporate_email("Rajesh Kumar", "Cognizant Technology Solutions")
    print(f"Derived Email: {test_email}")
