import mimetypes

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.html import format_html

import catalog.api.controllers.search_controller as search_controller
from catalog.api.models.base import OpenLedgerModel
from catalog.api.models.mixins import (
    ForeignIdentifierMixin,
    IdentifierMixin,
    MediaMixin,
)
from catalog.api.utils.attribution import get_attribution_text
from catalog.api.utils.licenses import get_license_url


PENDING = "pending_review"
MATURE_FILTERED = "mature_filtered"
DEINDEXED = "deindexed"
NO_ACTION = "no_action"

MATURE = "mature"
DMCA = "dmca"
OTHER = "other"


class AbstractMedia(
    IdentifierMixin, ForeignIdentifierMixin, MediaMixin, OpenLedgerModel
):
    """
    Generic model from which to inherit all media classes. This class stores
    information common to all media types indexed by Openverse.
    """

    watermarked = models.BooleanField(blank=True, null=True)

    license = models.CharField(
        max_length=50,
        help_text="The name of license for the media.",
    )
    license_version = models.CharField(
        max_length=25,
        blank=True,
        null=True,
        help_text="The version of the media license.",
    )

    source = models.CharField(
        max_length=80,
        blank=True,
        null=True,
        db_index=True,
        help_text="The source of the data, meaning a particular dataset. "
        "Source and provider can be different. Eg: the Google Open "
        "Images dataset is source=openimages, but provider=flickr.",
    )
    last_synced_with_source = models.DateTimeField(blank=True, null=True, db_index=True)
    removed_from_source = models.BooleanField(default=False)

    view_count = models.IntegerField(
        blank=True,
        null=True,
        default=0,
    )

    tags = models.JSONField(
        blank=True,
        null=True,
        help_text="Tags with detailed metadata, such as accuracy.",
    )
    tags_list = ArrayField(
        base_field=models.CharField(max_length=255),
        blank=True,
        null=True,
        help_text="List of tags names without detailed metadata.",
    )

    category = models.CharField(
        max_length=80,
        blank=True,
        null=True,
        db_index=True,
        help_text="The top-level classification of this media file.",
    )

    meta_data = models.JSONField(blank=True, null=True)

    @property
    def license_url(self):
        if self.meta_data and (url := self.meta_data.get("license_url")):
            return url
        else:
            return get_license_url(self.license.lower(), self.license_version)

    @property
    def attribution(self):
        """
        Get the plain-text English attribution for a media item. Refer to the frontend
        source code for an internationalised implementation.

        :return: the plain-text English-language attribution for a creative work
        """

        return get_attribution_text(
            self.title,
            self.creator,
            self.license.lower(),
            self.license_version,
            self.license_url,
        )

    class Meta:
        """
        Meta class for all media types indexed by Openverse. All concrete media
        classes should inherit their Meta class from this.
        """

        ordering = ["-created_on"]
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["foreign_identifier", "provider"],
                name="unique_provider_%(class)s",  # populated by concrete model
            ),
        ]


class AbstractMediaReport(models.Model):
    """
    Generic model from which to inherit all reported media classes. 'Reported'
    here refers to content reports such as mature, copyright-violating or
    deleted content.
    """

    BASE_URL = "https://search.creativecommons.org/"

    REPORT_CHOICES = [(MATURE, MATURE), (DMCA, DMCA), (OTHER, OTHER)]

    STATUS_CHOICES = [
        (PENDING, PENDING),
        (MATURE_FILTERED, MATURE_FILTERED),
        (DEINDEXED, DEINDEXED),
        (NO_ACTION, NO_ACTION),
    ]

    created_at = models.DateTimeField(auto_now_add=True)

    identifier = models.UUIDField(help_text="The ID for media to be reported.")
    reason = models.CharField(
        max_length=20,
        choices=REPORT_CHOICES,
        help_text="The reason to report media to Openverse.",
    )
    description = models.TextField(
        max_length=500,
        blank=True,
        null=True,
        help_text="The explanation on why media is being reported.",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)

    class Meta:
        abstract = True

    def url(self, media_type):
        url = f"{AbstractMediaReport.BASE_URL}" f"{media_type}/" f"{self.identifier}"
        return format_html(f"<a href={url}>{url}</a>")

    def save(self, *args, **kwargs):
        """
        Extend the ``save()`` functionality with Elastic Search integration to
        update records and refresh indices.

        Media marked as mature or deleted also leads to instantiation of their
        corresponding mature or deleted classes.

        Additional kwargs:
        index_name    : Name of ES index, eg. 'image'
        media_class   : Class of the media, eg. ``Image``
        mature_class  : Class that stores mature media, eg. ``MatureImage``
        deleted_class : Class that stores deleted media, eg. ``DeletedImage``
        """

        index_name = kwargs.pop("index_name")
        media_class = kwargs.pop("media_class")
        mature_class = kwargs.pop("mature_class")
        deleted_class = kwargs.pop("deleted_class")

        update_required = {MATURE_FILTERED, DEINDEXED}  # ES needs updating
        if self.status in update_required:
            es = search_controller.es
            try:
                media = media_class.objects.get(identifier=self.identifier)
            except media_class.DoesNotExist:
                super(AbstractMediaReport, self).save(*args, **kwargs)
                return
            es_id = media.id
            if self.status == MATURE_FILTERED:
                # Create an instance of the mature class for this media
                mature_class.objects.create(identifier=self.identifier)
                # Mark as 'mature' in Elastic Search
                es.update(index=index_name, id=es_id, body={"doc": {"mature": True}})
            elif self.status == DEINDEXED:
                # Delete from the API database, retaining the copy of the
                # metadata upstream in the catalog
                media.delete()
                # Create an instance of the deleted class for this media,
                # so that we don't reindex it later
                deleted_class.objects.create(identifier=self.identifier)
                # Remove from Elastic Search
                es.delete(index=index_name, id=es_id)
            es.indices.refresh(index=index_name)

        same_reports = self.__class__.objects.filter(
            identifier=self.identifier,
            status=PENDING,
        )
        if self.status != DEINDEXED:
            same_reports = same_reports.filter(reason=self.reason)
        same_reports.update(status=self.status)
        super(AbstractMediaReport, self).save(*args, **kwargs)


class AbstractDeletedMedia(OpenLedgerModel):
    """
    Generic model from which to inherit all deleted media classes. 'Deleted'
    here refers to media which has been deleted at the source.
    """

    identifier = models.UUIDField(
        unique=True, primary_key=True, help_text="The identifier of the deleted media."
    )

    class Meta:
        abstract = True


class AbstractMatureMedia(models.Model):
    """
    Generic model from which to inherit all mature media classes.
    """

    created_on = models.DateTimeField(auto_now_add=True)
    identifier = models.UUIDField(unique=True, primary_key=True)

    class Meta:
        abstract = True


class AbstractMediaList(OpenLedgerModel):
    """
    Generic model from which to inherit media lists. Each subclass should define
    its own `ManyToManyField` to point to a subclass of `AbstractMedia`.
    """

    title = models.CharField(max_length=2000, help_text="Display name")
    slug = models.CharField(
        max_length=200,
        help_text="A unique identifier used to make a friendly URL for "
        "downstream API consumers.",
        unique=True,
        db_index=True,
    )
    auth = models.CharField(
        max_length=64,
        help_text="A randomly generated string assigned upon list creation. "
        "Used to authenticate updates and deletions.",
    )

    class Meta:
        abstract = True


class AbstractAltFile:
    """
    This is not a Django model.

    This Python class serves as the schema for an alternative file. An alt file
    provides alternative qualities, formats and resolutions that are available
    from the provider that are not canonical.

    The schema of the class must correspond to that of the
    :py:class:`catalog.api.models.mixins.FileMixin` class.
    """

    def __init__(self, attrs):
        self.url = attrs.get("url")
        self.filesize = attrs.get("filesize")
        self.filetype = attrs.get("filetype")

    @property
    def size_in_mib(self):  # ~ MiB or mibibytes
        return self.filesize / 2**20

    @property
    def size_in_mb(self):  # ~ MB or megabytes
        return self.filesize / 1e6

    @property
    def mime_type(self):
        """
        Get the MIME type of the file inferred from the extension of the file.
        :return: the inferred MIME type of the file
        """

        return mimetypes.types_map[f".{self.filetype}"]
