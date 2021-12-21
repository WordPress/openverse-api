from unittest.mock import MagicMock, patch

import pytest


def _patch_redis():
    def redis_mget(keys, *_, **__):
        """
        Patch for ``redis.mget`` used by ``validate_images`` to use validity
        information from the cache
        """
        return [None] * len(keys)

    mock_conn = MagicMock()
    mock_conn.mget = MagicMock(side_effect=redis_mget)
    return patch("django_redis.get_redis_connection", return_value=mock_conn)


def _path_grequests():
    def grequests_map(reqs, *_, **__):
        """
        Patch for ``grequests.map`` used by ``validate_images`` to filter
        and remove dead links
        """
        responses = []
        for idx in range(len(list(reqs))):
            mocked_res = MagicMock()
            mocked_res.status_code = 200 if idx % 10 != 0 else 404
            responses.append(mocked_res)
        return responses

    return patch("grequests.map", side_effect=grequests_map)


@pytest.mark.django_db
def test_dead_link_filtering(client):
    _patch_redis().start()
    mocked_map = _path_grequests().start()

    path = "/v1/images/"
    query_params = {"q": "*", "page_size": 100}

    # Make a request that does not filter dead links...
    res_with_dead_links = client.get(
        path,
        query_params | {"filter_dead": False},
    )
    # ...and ensure that our patched function was not called
    mocked_map.assert_not_called()

    # Make a request that filters dead links...
    res_without_dead_links = client.get(
        path,
        query_params | {"filter_dead": True},
    )
    # ...and ensure that our patched function was called
    mocked_map.assert_called()

    assert res_with_dead_links.status_code == 200
    assert res_without_dead_links.status_code == 200

    data_with_dead_links = res_with_dead_links.json()
    data_without_dead_links = res_without_dead_links.json()

    res_1_ids = set(result["id"] for result in data_with_dead_links["results"])
    res_2_ids = set(result["id"] for result in data_without_dead_links["results"])
    assert bool(res_1_ids - res_2_ids)
