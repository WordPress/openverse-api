from __future__ import annotations

import json
import logging as log
import pprint
from itertools import accumulate
from math import ceil
from typing import List, Literal, Optional, Tuple, Union

from django.conf import settings
from django.core.cache import cache

from elasticsearch.exceptions import RequestError
from elasticsearch_dsl import Q, Search
from elasticsearch_dsl.response import Hit, Response

from catalog.api import models  # To prevent circular import
from catalog.api.serializers.media_serializers import MediaSearchRequestSerializer
from catalog.api.utils.dead_link_mask import get_query_hash, get_query_mask
from catalog.api.utils.validate_images import validate_images


ELASTICSEARCH_MAX_RESULT_WINDOW = 10000

FILTER_CACHE_TIMEOUT = 30
DEAD_LINK_RATIO = 1 / 2
THUMBNAIL = "thumbnail"
URL = "url"
PROVIDER = "provider"
DEEP_PAGINATION_ERROR = "Deep pagination is not allowed."
QUERY_SPECIAL_CHARACTER_ERROR = "Unescaped special characters are not allowed."


def _paginate_with_dead_link_mask(
    s: Search, page_size: int, page: int
) -> Tuple[int, int]:
    """
    Given a query, a page and page_size, return the start and end
    of the slice of results.

    :param s: The elasticsearch Search object
    :param page_size: How big the page should be.
    :param page: The page number.
    :return: Tuple of start and end.
    """
    query_hash = get_query_hash(s)
    query_mask = get_query_mask(query_hash)
    if not query_mask:
        start = 0
        end = ceil(page_size * page / (1 - DEAD_LINK_RATIO))
    elif page_size * (page - 1) > sum(query_mask):
        start = len(query_mask)
        end = ceil(page_size * page / (1 - DEAD_LINK_RATIO))
    else:
        accu_query_mask = list(accumulate(query_mask))
        start = 0
        if page > 1:
            try:
                start = accu_query_mask.index(page_size * (page - 1) + 1)
            except ValueError:
                start = accu_query_mask.index(page_size * (page - 1)) + 1
        if page_size * page > sum(query_mask):
            end = ceil(page_size * page / (1 - DEAD_LINK_RATIO))
        else:
            end = accu_query_mask.index(page_size * page) + 1
    return start, end


def _get_query_slice(
    s: Search, page_size: int, page: int, filter_dead: Optional[bool] = False
) -> Tuple[int, int]:
    """
    Select the start and end of the search results for this query.
    """
    if filter_dead:
        start_slice, end_slice = _paginate_with_dead_link_mask(s, page_size, page)
    else:
        # Paginate search query.
        start_slice = page_size * (page - 1)
        end_slice = page_size * page
    if start_slice + end_slice > ELASTICSEARCH_MAX_RESULT_WINDOW:
        raise ValueError(DEEP_PAGINATION_ERROR)
    return start_slice, end_slice


def _quote_escape(query_string: str) -> str:
    """
    If there are any unmatched quotes in the query supplied by the user, ignore
    them by escaping.

    :param query_string: the string in which to escape unbalanced quotes
    :return: the given string, if the quotes are balanced, the escaped string otherwise
    """

    num_quotes = query_string.count('"')
    if num_quotes % 2 == 1:
        return query_string.replace('"', '\\"')
    else:
        return query_string


def _post_process_results(
    s, start, end, page_size, search_results, filter_dead
) -> List[Hit]:
    """
    After fetching the search results from the back end, iterate through the
    results, perform image validation, and route certain thumbnails through our
    proxy.

    :param s: The Elasticsearch Search object.
    :param start: The start of the result slice.
    :param end: The end of the result slice.
    :param search_results: The Elasticsearch response object containing search
    results.
    :param filter_dead: Whether images should be validated.
    :return: List of results.
    """
    results = []
    to_validate = []
    for res in search_results:
        if hasattr(res.meta, "highlight"):
            res.fields_matched = dir(res.meta.highlight)
        to_validate.append(res.url)
        results.append(res)

    if filter_dead:
        query_hash = get_query_hash(s)
        validate_images(query_hash, start, results, to_validate)

        if len(results) < page_size:
            end += int(end / 2)
            if start + end > ELASTICSEARCH_MAX_RESULT_WINDOW:
                return results

            s = s[start:end]
            search_response = s.execute()

            return _post_process_results(
                s, start, end, page_size, search_response, filter_dead
            )
    return results[:page_size]


def _apply_filter(
    s: Search,
    query_ser: MediaSearchRequestSerializer,
    basis: Union[str, tuple[str, str]],
    behaviour: Literal["filter", "exclude"] = "filter",
) -> Search:
    """
    Parse and apply a filter from the search parameters serializer. The
    parameter key is assumed to have the same name as the corresponding
    Elasticsearch property. Each parameter value is assumed to be a comma
    separated list encoded as a string.

    :param s: the search query to issue to Elasticsearch
    :param query_ser: the ``MediaSearchRequestSerializer`` instance with search query
    :param basis: the name of the field in the serializer and Elasticsearch
    :param behaviour: whether to accept (``filter``) or reject (``exclude``) the hit
    :return: the modified search query
    """

    search_params = query_ser.data
    if isinstance(basis, tuple):
        ser_field, es_field = basis
    else:
        ser_field = es_field = basis
    if ser_field in search_params:
        filters = []
        for arg in search_params[ser_field].split(","):
            filters.append(Q("term", **{es_field: arg}))
        method = getattr(s, behaviour)  # can be ``s.filter`` or ``s.exclude``
        return method("bool", should=filters)
    else:
        return s


def _exclude_filtered(s: Search) -> Search:
    """
    Hide data sources from the catalog dynamically. This excludes providers with
    ``filter_content`` enabled from the search results.

    :param s: the search query to issue to Elasticsearch
    :return: the modified search query
    """

    filter_cache_key = "filtered_providers"
    filtered_providers = cache.get(key=filter_cache_key)
    if not filtered_providers:
        filtered_providers = models.ContentProvider.objects.filter(
            filter_content=True
        ).values("provider_identifier")
        cache.set(
            key=filter_cache_key,
            timeout=FILTER_CACHE_TIMEOUT,
            value=filtered_providers,
        )
    if len(filtered_providers) != 0:
        to_exclude = [f["provider_identifier"] for f in filtered_providers]
        s = s.exclude("terms", provider=to_exclude)
    return s


def search(
    query_ser: MediaSearchRequestSerializer,
    index: Literal["image", "audio"],
    ip: int,
) -> Tuple[List[Hit], int, int]:
    """
    Perform a ranked, paginated search based on the query and filters given in the
    search request.

    :param query_ser: the ``MediaSearchRequestSerializer`` instance with search query
    :param index: The Elasticsearch index to search (e.g. 'image')
    :param ip: the users' hashed IP to consistently route to the same ES shard
    :return: the list of search results with the page and result count
    """

    s = Search(index=index)
    search_params = query_ser.data

    rules: dict[Literal["filter", "exclude"], list[Union[str, tuple[str, str]]]] = {
        "filter": [
            "extension",
            "category",
            ("categories", "category"),
            "aspect_ratio",
            "size",
            "source",
            ("license", "license.keyword"),
            ("license_type", "license.keyword"),
        ],
        "exclude": [
            ("excluded_source", "source"),
        ],
    }
    for behaviour, bases in rules.items():
        for basis in bases:
            s = _apply_filter(s, query_ser, basis, behaviour)

    # Exclude mature content
    if not search_params["mature"]:
        s = s.exclude("term", mature=True)
    # Exclude sources with ``filter_content`` enabled
    s = _exclude_filtered(s)

    # Search either by generic multimatch or by "advanced search" with
    # individual field-level queries specified.

    search_fields = ["tags.name", "title", "description"]
    if "q" in search_params:
        query = _quote_escape(search_params["q"])
        s = s.query(
            "simple_query_string",
            query=query,
            fields=search_fields,
            default_operator="AND",
        )
        # Boost exact matches
        quotes_stripped = query.replace('"', "")
        exact_match_boost = Q(
            "simple_query_string",
            fields=["title"],
            query=f'"{quotes_stripped}"',
            boost=10000,
        )
        s.query = Q("bool", must=s.query, should=exact_match_boost)
    else:
        query_bases = ["creator", "title", ("tags", "tags.name")]
        for query_basis in query_bases:
            if isinstance(query_basis, tuple):
                ser_field, es_field = query_basis
            else:
                ser_field = es_field = query_basis
            if ser_field in search_params:
                value = _quote_escape(search_params[ser_field])
                s = s.query("simple_query_string", fields=[es_field], query=value)

    if settings.USE_RANK_FEATURES:
        feature_boost = {"standardized_popularity": 10000}
        rank_queries = []
        for field, boost in feature_boost.items():
            rank_queries.append(Q("rank_feature", field=field, boost=boost))
        s.query = Q("bool", must=s.query, should=rank_queries)

    # Use highlighting to determine which fields contribute to the selection of
    # top results.
    s = s.highlight(*search_fields)
    s = s.highlight_options(order="score")
    s.extra(track_scores=True)  # TODO: Remove this line as it has no effect

    # Route users to the same Elasticsearch worker node to reduce
    # pagination inconsistencies and increase cache hits.
    s = s.params(preference=str(ip), request_timeout=7)

    # Paginate
    start, end = _get_query_slice(
        s,
        search_params["page_size"],
        search_params["page"],
        search_params["filter_dead"],
    )
    s = s[start:end]

    try:
        if settings.VERBOSE_ES_RESPONSE:
            log.info(pprint.pprint(s.to_dict()))
        search_response = s.execute()
        log.info(
            f"query={json.dumps(s.to_dict())}," f" es_took_ms={search_response.took}"
        )
        if settings.VERBOSE_ES_RESPONSE:
            log.info(pprint.pprint(search_response.to_dict()))
    except RequestError as e:
        raise ValueError(e)

    results = _post_process_results(
        s,
        start,
        end,
        search_params["page_size"],
        search_response,
        search_params["filter_dead"],
    )

    result_count, page_count = _get_result_and_page_count(
        search_response, results, search_params["page_size"]
    )
    return results, page_count, result_count


def related_media(uuid, index, filter_dead):
    """
    Given a UUID, find related search results.
    """
    search_client = Search(index=index)

    # Convert UUID to sequential ID.
    item = search_client
    item = item.query("match", identifier=uuid)
    _id = item.execute().hits[0].id

    s = search_client
    s = s.query(
        "more_like_this",
        fields=["tags.name", "title", "creator"],
        like={"_index": index, "_id": _id},
        min_term_freq=1,
        max_query_terms=50,
    )
    # Never show mature content in recommendations.
    s = s.exclude("term", mature=True)
    s = _exclude_filtered(s)
    page_size = 10
    page = 1
    start, end = _get_query_slice(s, page_size, page, filter_dead)
    s = s[start:end]
    response = s.execute()
    results = _post_process_results(s, start, end, page_size, response, filter_dead)

    result_count, _ = _get_result_and_page_count(response, results, page_size)

    return results, result_count


def _get_result_and_page_count(
    response_obj: Response, results: List[Hit], page_size: int
) -> Tuple[int, int]:
    """
    Elasticsearch does not allow deep pagination of ranked queries.
    Adjust returned page count to reflect this.

    :param response_obj: The original Elasticsearch response object.
    :param results: The list of filtered result Hits.
    :return: Result and page count.
    """
    result_count = response_obj.hits.total.value
    natural_page_count = int(result_count / page_size)
    if natural_page_count % page_size != 0:
        natural_page_count += 1
    last_allowed_page = int((5000 + page_size / 2) / page_size)
    page_count = min(natural_page_count, last_allowed_page)
    if len(results) < page_size and page_count == 0:
        result_count = len(results)

    return result_count, page_count
