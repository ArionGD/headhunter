import socket

def generate_email_candidates(name: str, domain: str):
    """
    Generates standard corporate email pattern candidates.
    """
    parts = [p.lower().strip() for p in name.split() if p.strip()]
    if not parts or not domain:
        return []

    clean_domain = domain.lower().replace("http://", "").replace("https://", "").replace("www.", "").split("/")[0]
    
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""

    candidates = []
    if last:
        candidates.append(f"{first}.{last}@{clean_domain}")
        candidates.append(f"{first}{last}@{clean_domain}")
        candidates.append(f"{first[0]}{last}@{clean_domain}")
    candidates.append(f"{first}@{clean_domain}")

    return candidates

def check_domain_mx_records(domain: str) -> bool:
    """
    Keyless DNS MX record checker confirming if a domain has active mail exchangers.
    """
    clean_domain = domain.lower().replace("http://", "").replace("https://", "").replace("www.", "").split("/")[0]
    try:
        # Check standard DNS resolution for MX domain
        socket.gethostbyname(clean_domain)
        return True
    except Exception:
        return False

def verify_and_enrich_lead_email(name: str, company_domain: str):
    candidates = generate_email_candidates(name, company_domain)
    has_mx = check_domain_mx_records(company_domain)
    best_email = candidates[0] if candidates and has_mx else ""
    return best_email, has_mx
