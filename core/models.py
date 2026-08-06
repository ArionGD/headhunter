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
        ('prospeo', 'Prospeo.io'),
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
    inclination_score = models.IntegerField(default=50, help_text="Estimated nature & sustainability inclination (0-100%)")
    inclination_reasons = models.TextField(blank=True, null=True, help_text="Matched keywords or interest indicators")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.organization or 'No Org'} ({self.get_status_display()})"

class Interaction(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=50) # e.g., 'email', 'call', 'note'
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.interaction_type.capitalize()} with {self.lead.name} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
