def superuser_context(request):
    """
    Context processor to ensure is_superuser and is_admin are always reliably
    available in all templates, including for existing sessions.
    """
    if not hasattr(request, "session"):
        return {"is_superuser": False, "is_admin": False}
        
    user_id = request.session.get("user_id", "")
    user_role = request.session.get("user_role", "")
    is_admin = request.session.get("is_admin", False)
    
    is_super = (user_id == "admin" or user_role == "superuser" or is_admin is True)
    
    # Auto-heal session in case session was created in earlier builds
    if user_id == "admin":
        request.session["is_admin"] = True
        request.session["user_role"] = "superuser"
        
    return {
        "is_superuser": is_super,
        "is_admin": is_super,
        "current_user_id": user_id,
        "current_user_role": "superuser" if is_super else "user"
    }