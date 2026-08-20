from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from core.models import Lead
from .models import UserEmailConfig, EmailTemplate, OutreachLog
from .services import send_lead_email, test_smtp_connection, get_or_create_default_templates, render_email_template

def get_current_user_id(request):
    return request.session.get("user_id", "admin")

def outreach_settings_view(request):
    user_id = get_current_user_id(request)
    if not user_id:
        return redirect('login')
        
    config = UserEmailConfig.objects.filter(owner_username=user_id).first()
    get_or_create_default_templates(user_id)
    templates = EmailTemplate.objects.filter(owner_username=user_id).order_by('-created_at')
    logs = OutreachLog.objects.filter(owner_username=user_id).order_by('-sent_at')[:20]
    
    test_result = None
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'save_config':
            sender_name = request.POST.get('sender_name', '').strip()
            sender_email = request.POST.get('sender_email', '').strip()
            smtp_host = request.POST.get('smtp_host', 'smtp.gmail.com').strip()
            smtp_port = int(request.POST.get('smtp_port', 587))
            smtp_username = request.POST.get('smtp_username', '').strip()
            smtp_app_password = request.POST.get('smtp_app_password', '').strip()
            
            if not config:
                config = UserEmailConfig(owner_username=user_id)
                
            config.sender_name = sender_name
            config.sender_email = sender_email
            config.smtp_host = smtp_host
            config.smtp_port = smtp_port
            config.smtp_username = smtp_username
            if smtp_app_password:
                config.smtp_app_password = smtp_app_password
            config.save()
            
            return redirect('outreach_settings')
            
        elif action == 'test_connection':
            if config:
                success, msg = test_smtp_connection(config)
                test_result = {'success': success, 'message': msg}

    context = {
        'user_id': user_id,
        'config': config,
        'templates': templates,
        'logs': logs,
        'test_result': test_result,
    }
    return render(request, 'outreach/settings.html', context)

@require_POST
def create_template_view(request):
    user_id = get_current_user_id(request)
    if not user_id:
        return redirect('login')
        
    title = request.POST.get('title', '').strip()
    subject = request.POST.get('subject', '').strip()
    body_template = request.POST.get('body_template', '').strip()
    
    if title and subject and body_template:
        EmailTemplate.objects.create(
            owner_username=user_id,
            title=title,
            subject=subject,
            body_template=body_template
        )
    return redirect('outreach_settings')

def get_email_modal_view(request, lead_id):
    user_id = get_current_user_id(request)
    if not user_id:
        return HttpResponse("Unauthorized", status=401)
        
    lead = get_object_or_404(Lead, id=lead_id)
    config = UserEmailConfig.objects.filter(owner_username=user_id).first()
    get_or_create_default_templates(user_id)
    templates = EmailTemplate.objects.filter(owner_username=user_id)
    
    default_template = templates.filter(is_default=True).first() or templates.first()
    
    preview_subject = ""
    preview_body = ""
    if default_template and config:
        preview_subject = render_email_template(default_template.subject, lead, config)
        preview_body = render_email_template(default_template.body_template, lead, config)

    context = {
        'lead': lead,
        'config': config,
        'templates': templates,
        'default_template': default_template,
        'preview_subject': preview_subject,
        'preview_body': preview_body,
    }
    return render(request, 'outreach/email_modal.html', context)

@require_POST
def send_direct_email_api(request, lead_id):
    user_id = get_current_user_id(request)
    if not user_id:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
        
    lead = get_object_or_404(Lead, id=lead_id)
    config = UserEmailConfig.objects.filter(owner_username=user_id, is_active=True).first()
    
    if not config or not config.smtp_app_password:
        return JsonResponse({
            'success': False,
            'error': 'Please configure your Organization Email & App Password first in Settings > Outreach.'
        }, status=400)
        
    subject = request.POST.get('subject', '').strip()
    body = request.POST.get('body', '').strip()
    
    if not subject or not body:
        return JsonResponse({'success': False, 'error': 'Subject and Body cannot be empty.'}, status=400)
        
    try:
        log = send_lead_email(config, lead, subject, body)
        return JsonResponse({
            'success': True,
            'message': f"Email successfully dispatched to {lead.email}!",
            'lead_status': lead.get_status_display()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
