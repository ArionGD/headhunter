from django.contrib import admin
from .models import Lead, Interaction

class InteractionInline(admin.TabularInline):
    model = Interaction
    extra = 1

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'organization', 'location', 'source', 'status', 'created_at')
    list_filter = ('status', 'source', 'location')
    search_fields = ('name', 'organization', 'email', 'title', 'location')
    list_editable = ('status',)
    inlines = [InteractionInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'title', 'organization', 'linkedin_url')
        }),
        ('Contact Info', {
            'fields': ('email', 'phone', 'location')
        }),
        ('Classification & Status', {
            'fields': ('source', 'status')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )

@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ('lead', 'interaction_type', 'timestamp')
    list_filter = ('interaction_type', 'timestamp')
    search_fields = ('lead__name', 'content')
