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

    name = models.CharField(max_length=255, db_index=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    organization = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual', db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='discovered', db_index=True)
    inclination_score = models.IntegerField(default=50, db_index=True, help_text="Estimated nature & sustainability inclination (0-100%)")
    inclination_reasons = models.TextField(blank=True, null=True, help_text="Matched keywords or interest indicators")
    notes = models.TextField(blank=True, null=True)
    owner_username = models.CharField(max_length=150, default='admin', db_index=True, help_text="Username of account that owns this lead")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.organization or 'No Org'} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            from core.turso_sync import push_lead_to_turso
            push_lead_to_turso(self)
        except Exception:
            pass


class Interaction(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=50) # e.g., 'email', 'call', 'note'
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.interaction_type.capitalize()} with {self.lead.name} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class UserMetaTracker(models.Model):
    user_id = models.CharField(max_length=150, unique=True, db_index=True)
    role = models.CharField(max_length=50, default='user')
    display_name = models.CharField(max_length=150, blank=True, null=True)
    last_seen = models.DateTimeField(auto_now=True)
    last_ip = models.CharField(max_length=100, blank=True, null=True)
    last_device = models.CharField(max_length=255, blank=True, null=True)
    last_action = models.CharField(max_length=255, blank=True, null=True)

    def formatted_last_seen(self):
        if not self.last_seen:
            return "Never"
        from django.utils import timezone
        local_dt = timezone.localtime(self.last_seen)
        return f"Last seen {local_dt.strftime('%H:%Mhrs %d-%m-%y')}"

    def __str__(self):
        return f"{self.user_id} ({self.role}) - {self.formatted_last_seen()}"


class UserActivityLog(models.Model):
    user_id = models.CharField(max_length=150, db_index=True)
    action = models.CharField(max_length=100, db_index=True)
    description = models.TextField()
    target_lead_id = models.IntegerField(blank=True, null=True)
    target_lead_name = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.CharField(max_length=100, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def formatted_time(self):
        from django.utils import timezone
        local_dt = timezone.localtime(self.timestamp)
        return local_dt.strftime('%H:%Mhrs %d-%m-%y')

    def __str__(self):
        return f"[{self.formatted_time()}] {self.user_id}: {self.action} - {self.description[:40]}"


