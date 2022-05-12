from drf_yasg import openapi

from catalog.api.docs.media_docs import (
    MediaComplain,
    MediaDetail,
    MediaRelated,
    MediaSearch,
    MediaStats,
    fields_to_md,
    refer_sample,
)
from catalog.api.examples import (
    audio_complain_201_example,
    audio_complain_curl,
    audio_detail_200_example,
    audio_detail_404_example,
    audio_detail_curl,
    audio_related_200_example,
    audio_related_404_example,
    audio_related_curl,
    audio_search_200_example,
    audio_search_400_example,
    audio_search_list_curl,
    audio_stats_200_example,
    audio_stats_curl,
)
from catalog.api.serializers.error_serializers import (
    InputErrorSerializer,
    NotFoundErrorSerializer,
)
from catalog.api.serializers.provider_serializers import ProviderSerializer
from catalog.api.serializers.request.audio import (
    AudioReportSerializer,
    AudioSearchRequestSerializer,
)
from catalog.api.serializers.request.media import MediaThumbnailRequestSerializer
from catalog.api.serializers.response.audio import (
    AudioSearchSerializer,
    AudioSerializer,
)


class AudioSearch(MediaSearch):
    desc = f"""
audio_search is an API endpoint to search audio files using a query string.

By using this endpoint, you can obtain search results based on specified query and
optionally filter results by
{fields_to_md(AudioSearchRequestSerializer.fields_names)}.

{MediaSearch.desc}"""

    responses = {
        "200": openapi.Response(
            description="OK",
            examples=audio_search_200_example,
            schema=AudioSearchSerializer(many=True),
        ),
        "400": openapi.Response(
            description="Bad Request",
            examples=audio_search_400_example,
            schema=InputErrorSerializer,
        ),
    }

    code_examples = [
        {
            "lang": "Bash",
            "source": audio_search_list_curl,
        },
    ]

    swagger_setup = {
        "operation_id": "audio_search",
        "operation_description": desc,
        "query_serializer": AudioSearchRequestSerializer,
        "responses": responses,
        "code_examples": code_examples,
    }


class AudioStats(MediaStats):
    desc = f"""
audio_stats is an API endpoint to get a list of all content providers and their
respective number of audio files in the Openverse catalog.

{MediaStats.desc}"""

    responses = {
        "200": openapi.Response(
            description="OK",
            examples=audio_stats_200_example,
            schema=ProviderSerializer(many=True),
        )
    }

    code_examples = [
        {
            "lang": "Bash",
            "source": audio_stats_curl,
        },
    ]

    swagger_setup = {
        "operation_id": "audio_stats",
        "operation_description": desc,
        "responses": responses,
        "code_examples": code_examples,
    }


class AudioDetail(MediaDetail):
    desc = f"""
audio_detail is an API endpoint to get the details of a specified audio ID.

By using this endpoint, you can get audio details such as
{fields_to_md(AudioSerializer.Meta.fields)}.

{MediaDetail.desc}"""

    responses = {
        "200": openapi.Response(
            description="OK", examples=audio_detail_200_example, schema=AudioSerializer
        ),
        "404": openapi.Response(
            description="OK",
            examples=audio_detail_404_example,
            schema=NotFoundErrorSerializer,
        ),
    }

    code_examples = [
        {
            "lang": "Bash",
            "source": audio_detail_curl,
        },
    ]

    swagger_setup = {
        "operation_id": "audio_detail",
        "operation_description": desc,
        "responses": responses,
        "code_examples": code_examples,
    }


class AudioRelated(MediaRelated):
    desc = f"""
recommendations_audio_read is an API endpoint to get related audio files for a specified
audio ID.

By using this endpoint, you can get the details of related audio such as
{fields_to_md(AudioSerializer.Meta.fields)}.

{MediaRelated.desc}"""

    responses = {
        "200": openapi.Response(
            description="OK", examples=audio_related_200_example, schema=AudioSerializer
        ),
        "404": openapi.Response(
            description="Not Found",
            examples=audio_related_404_example,
            schema=NotFoundErrorSerializer,
        ),
    }

    code_examples = [
        {
            "lang": "Bash",
            "source": audio_related_curl,
        },
    ]

    swagger_setup = {
        "operation_id": "audio_related",
        "operation_description": desc,
        "responses": responses,
        "code_examples": code_examples,
    }


class AudioComplain(MediaComplain):
    desc = f"""
audio_report_create is an API endpoint to report an issue about a specified audio ID to
Openverse.

By using this endpoint, you can report an audio file if it infringes copyright, contains
mature or sensitive content and others.

{MediaComplain.desc}"""

    responses = {
        "201": openapi.Response(
            description="OK",
            examples=audio_complain_201_example,
            schema=AudioReportSerializer,
        )
    }

    code_examples = [
        {
            "lang": "Bash",
            "source": audio_complain_curl,
        }
    ]

    swagger_setup = {
        "operation_id": "audio_report",
        "operation_description": desc,
        "responses": responses,
        "code_examples": code_examples,
    }


class AudioThumbnail:
    desc = f"""
thumbnail is an API endpoint to retrieve the scaled down and compressed thumbnail
of the artwork of an audio track or its audio set.

{refer_sample}"""

    swagger_setup = {
        "operation_id": "audio_thumbnail",
        "operation_description": desc,
        "query_serializer": MediaThumbnailRequestSerializer,
    }
