import logging
from core.models import UserActivityLog, UserMetaTracker
from core.turso_sync import push_activity_log_to_turso, push_user_meta_to_turso

logger = logging.getLogger(__name__)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    return ip

def record_user_activity(request, action, description, target_lead=None):
    """
    Records an activity log and updates the user's last_seen & last_action metadata.
    Mirrors all updates to Turso Cloud.
    """
    user_id = request.session.get("user_id", "admin") if (request and hasattr(request, "session")) else "admin"
    role = request.session.get("user_role", "superuser" if user_id == "admin" else "user") if (request and hasattr(request, "session")) else "superuser"
    ip = get_client_ip(request) if request else "127.0.0.1"
    user_agent = request.META.get('HTTP_USER_AGENT', 'Web App')[:250] if (request and hasattr(request, "META")) else "Web App"


    target_id = target_lead.id if target_lead else None
    target_name = target_lead.name if target_lead else None

    # 1. Create UserActivityLog in DB
    try:
        log_entry = UserActivityLog.objects.create(
            user_id=user_id,
            action=action,
            description=description,
            target_lead_id=target_id,
            target_lead_name=target_name,
            ip_address=ip
        )
        push_activity_log_to_turso(log_entry)
    except Exception as e:
        logger.error(f"Error creating UserActivityLog: {e}")

    # 2. Update or Create UserMetaTracker
    try:
        meta, _ = UserMetaTracker.objects.get_or_create(
            user_id=user_id,
            defaults={
                'role': role,
                'display_name': user_id.replace('_', ' ').title(),
                'last_ip': ip,
                'last_device': user_agent,
                'last_action': description
            }
        )
        meta.role = role
        meta.last_ip = ip
        meta.last_device = user_agent
        meta.last_action = description
        meta.save()
        push_user_meta_to_turso(meta)
    except Exception as e:
        logger.error(f"Error updating UserMetaTracker: {e}")

def update_user_last_seen(request):
    """Quick update of last seen on page visits without spamming activity log"""
    user_id = request.session.get("user_id")
    if not user_id:
        return
    role = request.session.get("user_role", "superuser" if user_id == "admin" else "user")
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', 'Web App')[:250]

    try:
        meta, _ = UserMetaTracker.objects.get_or_create(
            user_id=user_id,
            defaults={
                'role': role,
                'display_name': user_id.replace('_', ' ').title(),
                'last_ip': ip,
                'last_device': user_agent,
                'last_action': 'Navigating Control Panel'
            }
        )
        meta.role = role
        meta.last_ip = ip
        meta.last_device = user_agent
        meta.save()
        push_user_meta_to_turso(meta)
    except Exception as e:
        pass