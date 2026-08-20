from django.db import models
from core.models import Lead

class UserEmailConfig(models.Model):
    owner_username = models.CharField(max_length=150, db_index=True, help_text="Username of account owning this email configuration")
    sender_name = models.CharField(max_length=255, help_text="Display name for outgoing emails (e.g. SEA Movement Team)")
    sender_email = models.EmailField(help_text="Organization email address")
    
    smtp_host = models.CharField(max_length=255, default='smtp.gmail.com', help_text="SMTP Host address")
    smtp_port = models.IntegerField(default=587, help_text="SMTP Port (e.g. 587 for TLS, 465 for SSL)")
    smtp_use_tls = models.BooleanField(default=True, help_text="Use TLS connection")
    smtp_username = models.CharField(max_length=255, help_text="SMTP Authentication Username (usually email address)")
    smtp_app_password = models.CharField(max_length=255, help_text="16-character App Password or SMTP password")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.sender_name} <{self.sender_email}> ({self.owner_username})"

class EmailTemplate(models.Model):
    owner_username = models.CharField(max_length=150, db_index=True)
    title = models.CharField(max_length=255, help_text="Internal template name (e.g. Partnership Intro)")
    subject = models.CharField(max_length=255, help_text="Email subject line supporting merge tags like {{ lead.name }}")
    body_template = models.TextField(help_text="Email body template supporting {{ lead.name }}, {{ lead.organization }}, {{ sender_name }}")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.owner_username})"

class OutreachLog(models.Model):
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='outreach_logs')
    owner_username = models.CharField(max_length=150, db_index=True)
    sender_email = models.EmailField()
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent', db_index=True)
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Email to {self.recipient_email} - {self.get_status_display()} ({self.sent_at.strftime('%Y-%m-%d %H:%M')})"
