from django.contrib import admin

from catalog.api.admin.site import openverse_admin
from catalog.api.models import (
    PENDING,
    Audio,
    AudioReport,
    ContentProvider,
    Image,
    ImageReport,
)
from catalog.api.models.media import AbstractDeletedMedia, AbstractMatureMedia


admin.site = openverse_admin
admin.sites.site = openverse_admin


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    search_fields = ("identifier",)


@admin.register(Audio)
class AudioAdmin(admin.ModelAdmin):
    search_fields = ("identifier",)


class MediaReportAdmin(admin.ModelAdmin):
    list_display = ("reason", "status", "description", "created_on")
    media_specific_list_display = ()
    list_filter = ("status", "reason")
    list_display_links = ("status",)
    search_fields = (
        "description",
        "media_obj_id",
    )
    autocomplete_fields = ("media_obj",)
    actions = None

    def get_list_display(self, request):
        return self.list_display + self.media_specific_list_display

    def get_exclude(self, request, obj=None):
        if request.path.endswith("/change/"):
            return ["media_obj"]

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        always_readonly = [
            "reason",
            "description",
            "media_obj_id",
            "created_on",
        ]
        if obj.status == PENDING:
            return always_readonly
        else:
            status_readonly = ["status"]
            status_readonly.extend(always_readonly)
            return status_readonly


@admin.register(ImageReport)
class ImageReportAdmin(MediaReportAdmin):
    media_specific_list_display = ("image_url",)


@admin.register(AudioReport)
class AudioReportAdmin(MediaReportAdmin):
    media_specific_list_display = ("audio_url",)


class MediaSubreportAdmin(admin.ModelAdmin):
    exclude = [
        "media_obj",
    ]
    search_fields = [
        "media_obj_id",
    ]
    readonly_fields = [
        "media_obj_id",
    ]

    def has_add_permission(self, *args, **kwargs):
        """Create ``_Report`` instances instead."""
        return False


for klass in [
    *AbstractMatureMedia.__subclasses__(),
    *AbstractDeletedMedia.__subclasses__(),
]:
    admin.site.register(klass, MediaSubreportAdmin)


@admin.register(ContentProvider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("provider_name", "provider_identifier", "media_type")
    search_fields = ("provider_name", "provider_identifier")
    exclude = ("notes",)
