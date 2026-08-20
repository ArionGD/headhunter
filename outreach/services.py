import logging
from django.core.mail.backends.smtp import EmailBackend
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from core.models import Lead, Interaction
from .models import UserEmailConfig, OutreachLog, EmailTemplate

logger = logging.getLogger(__name__)

def get_smtp_connection(config: UserEmailConfig):
    """
    Creates a dynamic Django SMTP EmailBackend connection using the user's specific credentials.
    """
    return EmailBackend(
        host=config.smtp_host,
        port=config.smtp_port,
        username=config.smtp_username,
        password=config.smtp_app_password,
        use_tls=config.smtp_use_tls,
        fail_silently=False,
    )

def render_email_template(template_str: str, lead: Lead, config: UserEmailConfig) -> str:
    """
    Replaces merge tags in string with actual lead and user data.
    """
    if not template_str:
        return ""
    
    replacements = {
        '{{ lead.name }}': lead.name or "Colleague",
        '{{ lead.first_name }}': lead.name.split()[0] if lead.name else "Colleague",
        '{{ lead.organization }}': lead.organization or "your organization",
        '{{ lead.title }}': lead.title or "Professional",
        '{{ lead.location }}': lead.location or "",
        '{{ sender_name }}': config.sender_name or "Outreach Team",
        '{{ sender_email }}': config.sender_email or "",
    }
    
    result = template_str
    for key, value in replacements.items():
        result = result.replace(key, value)
    
    return result

def send_lead_email(config: UserEmailConfig, lead: Lead, subject: str, body_text: str):
    """
    Sends a personalized outreach email to a lead using the user's SMTP config.
    Logs OutreachLog, creates core.Interaction, and updates lead status to 'contacted'.
    """
    if not lead.email:
        raise ValueError(f"Lead '{lead.name}' does not have a valid email address.")
        
    connection = get_smtp_connection(config)
    from_email = f"{config.sender_name} <{config.sender_email}>"
    recipient_list = [lead.email]
    
    # Render final merge tags
    rendered_subject = render_email_template(subject, lead, config)
    rendered_body = render_email_template(body_text, lead, config)
    
    try:
        email = EmailMultiAlternatives(
            subject=rendered_subject,
            body=rendered_body,
            from_email=from_email,
            to=recipient_list,
            connection=connection
        )
        email.send()
        
        # Log successful outreach
        log = OutreachLog.objects.create(
            lead=lead,
            owner_username=config.owner_username,
            sender_email=config.sender_email,
            recipient_email=lead.email,
            subject=rendered_subject,
            body=rendered_body,
            status='sent'
        )
        
        # Log interaction in core CRM
        Interaction.objects.create(
            lead=lead,
            interaction_type='email',
            content=f"Sent email: '{rendered_subject}' via {config.sender_email}"
        )
        
        # Update lead status to 'contacted'
        if lead.status in ['discovered', 'vetted']:
            lead.status = 'contacted'
            lead.save(update_fields=['status', 'updated_at'])
            
        return log
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to send email to {lead.email}: {error_msg}")
        
        # Log failed outreach
        log = OutreachLog.objects.create(
            lead=lead,
            owner_username=config.owner_username,
            sender_email=config.sender_email,
            recipient_email=lead.email,
            subject=rendered_subject,
            body=rendered_body,
            status='failed',
            error_message=error_msg
        )
        raise e

def test_smtp_connection(config: UserEmailConfig) -> tuple[bool, str]:
    """
    Tests SMTP connection by opening connection and sending dummy test email to sender's address.
    """
    try:
        connection = get_smtp_connection(config)
        connection.open()
        
        # Send quick verification test email to sender's own inbox
        test_msg = EmailMultiAlternatives(
            subject="[Hunter.io] SMTP Credentials Connection Verification",
            body=f"Hello {config.sender_name},\n\nYour SMTP configuration ({config.smtp_host}:{config.smtp_port}) and App Password have been successfully verified!",
            from_email=f"{config.sender_name} <{config.sender_email}>",
            to=[config.sender_email],
            connection=connection
        )
        test_msg.send()
        connection.close()
        return True, "SMTP Connection & Test Email Dispatched Successfully!"
    except Exception as e:
        return False, f"SMTP Connection Failed: {str(e)}"

def get_or_create_default_templates(owner_username: str):
    """
    Ensures standard default templates exist for the given user account.
    """
    if not EmailTemplate.objects.filter(owner_username=owner_username).exists():
        EmailTemplate.objects.create(
            owner_username=owner_username,
            title="Partnership Introduction",
            subject="Exploring Collaboration with {{ lead.organization }} — SEA Movement",
            body_template="""Hi {{ lead.first_name }},

I noticed your impactful work as {{ lead.title }} at {{ lead.organization }}. 

We are currently building key partnerships for sustainable environment initiatives and regional sustainability projects. Given your background in {{ lead.location }}, I would love to connect for a quick 10-minute intro call this week.

Would you be open to exchanging a few ideas?

Best regards,
{{ sender_name }}
{{ sender_email }}""",
            is_default=True
        )
        
        EmailTemplate.objects.create(
            owner_username=owner_username,
            title="Follow-Up Outreach",
            subject="Re: Quick Question regarding {{ lead.organization }}",
            body_template="""Hi {{ lead.first_name }},

Following up on my previous note. I wanted to see if you had a moment to review our partnership proposal for {{ lead.organization }}.

Looking forward to hearing your thoughts.

Warm regards,
{{ sender_name }}""",
            is_default=False
        )
