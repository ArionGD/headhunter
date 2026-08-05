import os
import sys
import json
import argparse
import requests
from dotenv import load_dotenv

# Load environment variables from the project root .env if it exists
# Walk up directory tree to find .env
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(base_dir, ".env"))

def main():
    parser = argparse.ArgumentParser(description="Synchronize scraped leads to HeadHunt.io server.")
    parser.add_argument("file", help="Path to the JSON file containing leads")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/import-leads/", 
                        help="API Endpoint URL of the hosted HeadHunt.io server (default: http://127.0.0.1:8000/api/import-leads/)")
    parser.add_argument("--token", help="Upload secret token (defaults to UPLOAD_SECRET_KEY in .env)")
    
    args = parser.parse_args()
    
    # Resolve token
    token = args.token or os.environ.get("UPLOAD_SECRET_KEY")
    if not token:
        print("Error: UPLOAD_SECRET_KEY is not set in environment or provided via --token.", file=sys.stderr)
        sys.exit(1)
        
    # Read leads file
    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            leads_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
        
    if not isinstance(leads_data, list):
        print("Error: JSON root must be a list of lead objects.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Loaded {len(leads_data)} leads from '{args.file}'. Syncing to {args.url}...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(args.url, json=leads_data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("Successfully synchronized!")
            print(f" -> Created new leads: {result.get('created', 0)}")
            print(f" -> Updated existing leads: {result.get('updated', 0)}")
        else:
            try:
                err_detail = response.json().get("error", response.text)
            except Exception:
                err_detail = response.text
            print(f"Upload failed with HTTP {response.status_code}: {err_detail}", file=sys.stderr)
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
