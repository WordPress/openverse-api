from elasticsearch_dsl import Search

from catalog.api.controllers.elasticsearch.utils import (
    _exclude_filtered,
    _get_query_slice,
    _get_result_and_page_count,
    _post_process_results,
)


def related_media(uuid, index, filter_dead):
    """
    Given a UUID, find related search results.
    """
    search_client = Search(using="default", index=index)

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
