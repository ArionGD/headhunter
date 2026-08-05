# Master Plan: Hybrid Lead Sourcing & Relationship Manager (HeadHunt.io)

This document outlines the transition of **HeadHunt.io** from a pure search engine prototype into a hybrid **Sourcing Engine & Relationship Manager (CRM)**. The system will leverage high-volume local scraping on your PC, secure database synchronization, and hosted relationship management.

---

## 🏗️ System Architecture

```mermaid
graph TD
    subgraph Local PC (High-Volume Sourcing)
        A[Reddit /r/Chennai Scraper] --> D[Local SQLite Cache]
        B[Google Maps Nursery Scraper] --> D
        C[OSINT/LinkedIn Scraper] --> D
        E[Local CLI Sync Tool] -->|Secure API HTTP POST| F[Hosted API Endpoint]
    end

    subgraph Hosted Server (PythonAnywhere / Render)
        F --> G[(Hosted SQLite DB)]
        H[Live APIs: Apollo, Snov, Prospeo] -.-> G
        I[Django Dashboard & CRM UI] --> G
    end
```

---

## 📅 Phased Implementation Plan

### Phase 1: Local Sourcing & Scraping Suite (PC-Side)
To bypass paid API credits, we will write lightweight scrapers that run locally on your PC and output clean, structured profiles.

1. **Reddit Sourcing Script:**
   * Queries `r/Chennai`, `r/bangalore`, and `r/TamilNadu` for keyword threads.
   * Extracts user handles, matching text fragments, and dates.
2. **Google Maps Nursery Scraper:**
   * Scrapes reviews from prominent plant nurseries along ECR/OMR (Chennai) and Bangalore.
   * Flags 5-star reviewers who indicate interest in agroforestry, gardening, or mango/timber cultivation.
3. **Local Cache Database:**
   * Consolidates all scraped profiles in a simple local SQLite file before pushing to the cloud.

---

### Phase 2: CRM Database Schema (Django-Side)
We will transition the Django app from model-less to model-backed. 

Modify `core/models.py` to define the following structures:

```python
from django.db import models

class Lead(models.Model):
    STATUS_CHOICES = [
        ('discovered', 'Discovered'),
        ('vetted', 'Vetted'),
        ('contacted', 'Contacted'),
        ('interested', 'Interested (Investor Opportunity)'),
        ('joined', 'Joined SEA Movement'),
        ('ignored', 'N/A / Wrong Fit'),
    ]
    
    SOURCE_CHOICES = [
        ('apollo', 'Apollo.io'),
        ('snov', 'Snov.io'),
        ('reddit', 'Reddit Scraper'),
        ('gmaps', 'Google Maps Nursery Reviews'),
        ('manual', 'Manual Entry'),
    ]

    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True, null=True)
    organization = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='discovered')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Interaction(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=50) # e.g., 'email', 'call', 'note'
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
```

---

### Phase 3: Secure Synchronization Pipeline
To securely transfer local data to the hosted web application:

1. **Authentication Token:**
   * Generate an `UPLOAD_SECRET_KEY` in the hosted app's `.env` configuration.
2. **API Endpoint (`/api/import-leads/`):**
   * Create a POST endpoint in Django that receives JSON payloads of leads, validates the token, and writes/upserts them to the database.
3. **Local Sync CLI Script:**
   * A command-line script (`sync_leads.py`) that packages new items from your local scraper databases and pushes them in chunks to the hosted app.

---

### Phase 4: Hybrid Dashboard UI
Upgrade the existing user interface to integrate both workflows:

1. **Data Source Toggle:**
   * Add a new option to the Source Selection: **"Local Database (Imported Leads)"**.
2. **Relationship Manager Panel:**
   * When displaying a lead card, add a **"Manage Relationship"** toggle.
   * Clicking this allows you to:
     * Change Lead status (e.g. from *Discovered* to *Contacted*).
     * Add notes and log interactions (e.g. *"Spoke on phone, interested in ECR plot"*).
3. **Pipeline Filtering:**
   * Allow filtering the dashboard by status (e.g. *"Show all Leads who are 'Interested'"*) to act as a proper CRM board.

---

## 🔒 Security & Optimization Measures
* **Token Protection:** Use HMAC headers or simple token authorization for the `/api/import-leads/` endpoint.
* **Bulk Import Handling:** Chunk uploads into packages of 50–100 records to prevent memory timeouts on PythonAnywhere's web workers.
* **Database Indexes:** Index `Lead` fields on `status`, `location`, and `email` for rapid searching.
