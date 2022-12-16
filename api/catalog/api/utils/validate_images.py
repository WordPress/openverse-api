import asyncio
import logging
import time

from django.conf import settings

import aiohttp
import django_redis
from asgiref.sync import async_to_sync
from decouple import config
from elasticsearch_dsl.response import Hit

from catalog.api.utils.dead_link_mask import get_query_mask, save_query_mask


parent_logger = logging.getLogger(__name__)


CACHE_PREFIX = "valid:"
HEADERS = {
    "User-Agent": settings.OUTBOUND_USER_AGENT_TEMPLATE.format(purpose="LinkValidation")
}


def _get_cached_statuses(redis, image_urls):
    cached_statuses = redis.mget([CACHE_PREFIX + url for url in image_urls])
    return [int(b.decode("utf-8")) if b is not None else None for b in cached_statuses]


def _get_expiry(status, default):
    return config(f"LINK_VALIDATION_CACHE_EXPIRY__{status}", default=default, cast=int)


async def _head(url: str, session: aiohttp.ClientSession) -> tuple[str, int]:
    try:
        async with session.head(url, allow_redirects=False) as response:
            return url, response.status
    except (aiohttp.ClientError, asyncio.TimeoutError) as exception:
        _log_validation_failure(exception)
        return url, -1


# https://stackoverflow.com/q/55259755
@async_to_sync
async def _make_head_requests(urls: list[str]) -> list[tuple[str, int]]:
    tasks = []
    timeout = aiohttp.ClientTimeout(total=2)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        tasks = [asyncio.ensure_future(_head(url, session)) for url in urls]
        responses = asyncio.gather(*tasks)
        await responses
    return responses.result()


def validate_images(
    query_hash: str, start_slice: int, results: list[Hit], image_urls: list[str]
) -> None:
    """
    Make sure images exist before we display them. Treat redirects as broken
    links since 99% of the time the redirect leads to a generic "not found"
    placeholder.

    Results are cached in redis and shared amongst all API servers in the
    cluster.
    """
    logger = parent_logger.getChild("validate_images")
    if not image_urls:
        logger.info("no image urls to validate")
        return

    logger.debug("starting validation")
    start_time = time.time()

    # Pull matching images from the cache.
    redis = django_redis.get_redis_connection("default")
    cached_statuses = _get_cached_statuses(redis, image_urls)
    logger.debug(f"len(cached_statuses)={len(cached_statuses)}")

    # Anything that isn't in the cache needs to be validated via HEAD request.
    to_verify = {}
    for idx, url in enumerate(image_urls):
        if cached_statuses[idx] is None:
            to_verify[url] = idx
    logger.debug(f"len(to_verify)={len(to_verify)}")

    verified = _make_head_requests(to_verify.keys())

    # Cache newly verified image statuses.
    to_cache = {CACHE_PREFIX + url: status for url, status in verified}

    pipe = redis.pipeline()
    if len(to_cache) > 0:
        pipe.mset(to_cache)

    for key, status in to_cache.items():
        if status == 200:
            logger.debug(f"healthy link key={key}")
        elif status == -1:
            logger.debug(f"no response from provider key={key}")
        else:
            logger.debug(f"broken link key={key}")

        expiry = settings.LINK_VALIDATION_CACHE_EXPIRY_CONFIGURATION[status]
        logger.debug(f"caching status={status} expiry={expiry}")
        pipe.expire(key, expiry)

    pipe.execute()

    # Merge newly verified results with cached statuses
    for idx, url in enumerate(to_verify):
        cache_idx = to_verify[url]
        cached_statuses[cache_idx] = verified[idx][1]

    # Create a new dead link mask
    new_mask = [1] * len(results)

    # Delete broken images from the search results response.
    for idx, _ in enumerate(cached_statuses):
        del_idx = len(cached_statuses) - idx - 1
        status = cached_statuses[del_idx]
        if status == 429 or status == 403:
            logger.warning(
                "Image validation failed due to rate limiting or blocking. "
                f"url={image_urls[idx]} "
                f"status={status} "
            )
        elif status != 200:
            logger.info(
                "Deleting broken image from results "
                f"id={results[del_idx]['identifier']} "
                f"status={status} "
            )
            # remove the result, mutating in place
            del results[del_idx]
            # update the result's position in the mask to indicate it is dead
            new_mask[del_idx] = 0

    # Merge and cache the new mask
    mask = get_query_mask(query_hash)
    if mask:
        # skip the leading part of the mask that represents results that come before
        # the results we've verified this time around. Overwrite everything after
        # with our new results validation mask.
        new_mask = mask[:start_slice] + new_mask
    save_query_mask(query_hash, new_mask)

    end_time = time.time()
    logger.debug(
        "end validation "
        f"end_time={end_time} "
        f"start_time={start_time} "
        f"delta={end_time - start_time} "
    )


def _log_validation_failure(exception):
    logger = parent_logger.getChild("_log_validation_failure")
    logger.warning(f"Failed to validate image! Reason: {exception}")
