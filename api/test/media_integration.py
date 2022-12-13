"""
Base test cases for all media types.
These are not tests and cannot be invoked.
"""

import json
from test.constants import API_URL

import requests


def search(fixture):
    """Returns results for test query."""
    assert fixture["result_count"] > 0


def search_by_category(media_path, category, fixture):
    response = requests.get(
        f"{API_URL}/v1/{media_path}?category={category}&filter_dead=False"
    )
    assert response.status_code == 200
    data = json.loads(response.text)
    assert data["result_count"] < fixture["result_count"]
    results = data["results"]
    # Make sure each result is from the specified category
    assert all(audio_item["category"] == category for audio_item in results)


def search_all_excluded(media_path, excluded_source):
    response = requests.get(
        f"{API_URL}/v1/{media_path}?q=test&excluded_source={','.join(excluded_source)}&filter_dead=False"
    )
    data = json.loads(response.text)
    assert data["result_count"] == 0


def search_source_and_excluded(media_path):
    response = requests.get(
        f"{API_URL}/v1/{media_path}?q=test&source=x&excluded_source=y&filter_dead=False"
    )
    assert response.status_code == 400


def search_quotes(media_path, q="test"):
    """Returns a response when quote matching is messed up."""
    response = requests.get(
        f'{API_URL}/v1/{media_path}?q="{q}&filter_dead=False', verify=False
    )
    assert response.status_code == 200


def search_quotes_exact(media_path, q):
    """Only returns exact matches for the given query"""
    url_format = f"{API_URL}/v1/{media_path}?q={{q}}&filter_dead=False"
    unquoted_response = requests.get(url_format.format(q=q), verify=False)
    assert unquoted_response.status_code == 200
    unquoted_result_count = unquoted_response.json()["result_count"]
    assert unquoted_result_count > 0

    quoted_response = requests.get(url_format.format(q=f'"{q}"'), verify=False)
    assert quoted_response.status_code == 200
    quoted_result_count = quoted_response.json()["result_count"]
    assert quoted_result_count > 0

    # The rationale here is that the unquoted results will match more records due
    # to the query being overall less strict. Quoting the query will make it more
    # strict causing it to return fewer results.
    # Above we check that the results are not 0 to confirm that we do still get results back.
    assert quoted_result_count < unquoted_result_count


def search_special_chars(media_path, q="test"):
    """Returns a response when query includes special characters."""
    response = requests.get(
        f"{API_URL}/v1/{media_path}?q={q}!&filter_dead=False", verify=False
    )
    assert response.status_code == 200


def search_consistency(
    media_path,
    n_pages,
):
    """
    Returns consistent, non-duplicate results in the first n pages.

    Elasticsearch sometimes reaches an inconsistent state, which causes search
    results to appear differently upon page refresh. This can also introduce
    image duplicates in subsequent pages. This test ensures that no duplicates
    appear in the first few pages of a search query.
    """

    searches = {
        requests.get(
            f"{API_URL}/v1/{media_path}?page={page}&filter_dead=False", verify=False
        )
        for page in range(1, n_pages)
    }

    results = set()
    for response in searches:
        parsed = json.loads(response.text)
        for result in parsed["results"]:
            media_id = result["id"]
            assert media_id not in results
            results.add(media_id)


def detail(media_type, fixture):
    test_id = fixture["results"][0]["id"]
    response = requests.get(f"{API_URL}/v1/{media_type}/{test_id}", verify=False)
    assert response.status_code == 200


def stats(media_type, count_key="media_count"):
    response = requests.get(f"{API_URL}/v1/{media_type}/stats", verify=False)
    parsed_response = json.loads(response.text)
    assert response.status_code == 200
    num_media = 0
    provider_count = 0
    for pair in parsed_response:
        media_count = pair[count_key]
        num_media += int(media_count)
        provider_count += 1
    assert num_media > 0
    assert provider_count > 0


def report(media_type, fixture):
    test_id = fixture["results"][0]["id"]
    response = requests.post(
        f"{API_URL}/v1/{media_type}/{test_id}/report/",
        {
            "reason": "mature",
            "description": "This item contains sensitive content",
        },
        verify=False,
    )
    assert response.status_code == 201
    data = json.loads(response.text)
    assert data["identifier"] == test_id


def license_filter_case_insensitivity(media_type):
    response = requests.get(
        f"{API_URL}/v1/{media_type}?license=bY&filter_dead=False", verify=False
    )
    parsed = json.loads(response.text)
    assert parsed["result_count"] > 0


def uuid_validation(media_type, identifier):
    response = requests.get(f"{API_URL}/v1/{media_type}/{identifier}", verify=False)
    assert response.status_code == 404


def related(fixture):
    related_url = fixture["results"][0]["related_url"]
    response = requests.get(related_url)
    assert response.status_code == 200
