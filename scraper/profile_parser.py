import re

def calculate_nature_inclination(name="", title="", organization="", bio_text="", location=""):
    """
    Evaluates a prospect profile against sustainability and corporate parameters
    to calculate a Nature Inclination Score (0-100%) and matched interest reasons.
    """
    text = f"{name} {title} {organization} {bio_text} {location}".lower()
    
    high_weight_terms = {
        "permaculture": "Permaculture",
        "organic": "Organic Farming",
        "food forest": "Food Forest",
        "farmland": "Farmland",
        "heirloom": "Heirloom Seeds",
        "rainwater harvesting": "Rainwater Harvesting",
        "climate adaptation": "Climate Adaptation",
        "green asset": "Green Asset Investment",
        "impact investing": "Impact Investing",
        "home schooling": "Alternative Living / Home Schooling",
        "bio-organic": "Bio-Organics"
    }
    
    med_weight_terms = {
        "sustainability": "Sustainability",
        "esg": "ESG Practices",
        "csr": "Corporate Social Responsibility (CSR)",
        "solar": "Solar Energy",
        "kitchen gardening": "Kitchen Gardening",
        "agriculture": "Agriculture Interest",
        "trees": "Tree Plantation",
        "rural": "Rural Life",
        "healthy lifestyle": "Healthy Lifestyle",
        "values": "Ethics & Values",
        "eco": "Eco Initiatives",
        "nursery": "Plant Nursery"
    }
    
    seniority_terms = [
        "director", "vp", "vice president", "head", "partner", "senior", "lead", "architect", "manager"
    ]
    
    matched_reasons = []
    score = 55  # Base professional score
    
    # Check high weight terms (+15)
    for term, label in high_weight_terms.items():
        if term in text:
            score += 15
            matched_reasons.append(label)
            
    # Check medium weight terms (+10)
    for term, label in med_weight_terms.items():
        if term in text:
            score += 10
            matched_reasons.append(label)
            
    # Check seniority (+5)
    for s_term in seniority_terms:
        if s_term in text:
            score += 5
            matched_reasons.append("Senior Corporate Level")
            break
            
    # Cap score at 98% max
    score = min(score, 98)
    
    # Remove duplicate reasons while preserving order
    unique_reasons = list(dict.fromkeys(matched_reasons))
    reasons_str = ", ".join(unique_reasons) if unique_reasons else "Standard Corporate Match"
    
    return score, reasons_str

if __name__ == "__main__":
    test_score, test_reasons = calculate_nature_inclination(
        name="Sanjay Krishnan",
        title="VP Operations & ESG Lead",
        organization="Cognizant",
        bio_text="Passionate about permaculture, food forest development, and rainwater harvesting in Chennai.",
        location="Chennai"
    )
    print(f"Test Score: {test_score}% | Reasons: {test_reasons}")
