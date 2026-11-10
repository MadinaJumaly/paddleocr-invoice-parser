from django.contrib import admin

from .models import Profile, Recognition


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "organization")
    search_fields = ("user__username", "phone", "organization")


@admin.register(Recognition)
class RecognitionAdmin(admin.ModelAdmin):
    list_display = ("original_name", "user", "status", "language", "created_at", "finished_at")
    list_filter = ("status", "language", "created_at")
    search_fields = ("original_name", "user__username")
    readonly_fields = ("tables", "created_at", "finished_at")
