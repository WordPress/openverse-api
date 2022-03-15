import abc
import logging

from catalog.api.utils.oauth2_helper import get_token_info
from django_redis import get_redis_connection
from rest_framework.throttling import SimpleRateThrottle


log = logging.getLogger(__name__)


class ThrottleExemption:
    def __init__(self, throttle_class, request):
        self.throttle_class = throttle_class
        self.request = request

    @abc.abstractmethod
    def is_exempt(self) -> bool:
        ...


class ExemptionAwareThrottle(SimpleRateThrottle):
    """
    An throttle exemption aware base throttle.

    Classes in ``exemption_classes`` are evaluated for each
    request. If any of them detect an exempted request then
    the request will not be throttled.
    """

    exemption_classes = []

    def allow_request(self, request, view):
        for exemption_class in self.exemption_classes:
            if exemption_class(self, request).is_exempt():
                return True

        return super().allow_request(request, view)


class InternalNetworkExemption(ThrottleExemption):
    redis_set_name = "ip-whitelist"

    def is_exempt(self):
        ip = self.throttle_class.get_ident(self.request)
        redis = get_redis_connection("default", write=False)
        return redis.sismember(self.redis_set_name, ip)


class ApiKeyExemption(ThrottleExemption):
    redis_set_name = "client-id-allowlist"

    def is_exempt(self):
        client_id, _, _ = get_token_info(str(self.request.auth))
        redis = get_redis_connection("default")
        return redis.sismember(self.redis_set_name, client_id)


class AnonRateThrottle(ExemptionAwareThrottle):
    """
    Limits the rate of API calls that may be made by a anonymous users.

    The IP address of the request will be used as the unique cache key.
    """

    scope = "anon"
    exemption_classes = [InternalNetworkExemption, ApiKeyExemption]

    def get_cache_key(self, request, view):
        # Do not throttle requests with a valid access token.
        if request.auth:
            client_id, _, verified = get_token_info(str(request.auth))
            if client_id and verified:
                return None

        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class PostRequestThrottler(AnonRateThrottle):
    rate = "30/day"


class BurstRateThrottle(AnonRateThrottle):
    scope = "anon_burst"


class SustainedRateThrottle(AnonRateThrottle):
    scope = "anon_sustained"


class TenPerDay(AnonRateThrottle):
    rate = "10/day"


class OneThousandPerMinute(AnonRateThrottle):
    rate = "1000/min"


class OnePerSecond(AnonRateThrottle):
    rate = "1/second"


class OAuth2IdThrottleRate(ExemptionAwareThrottle):
    """
    Limits the rate of API calls that may be made by a given user's Oauth2
    client ID. Can be configured to apply to either standard or enhanced
    API keys.
    """

    scope = "oauth2_client_credentials"
    applies_to_rate_limit_model = "standard"
    exemption_classes = [InternalNetworkExemption, ApiKeyExemption]

    def get_cache_key(self, request, view):
        # Find the client ID associated with the access token.
        auth = str(request.auth)
        client_id, rate_limit_model, verified = get_token_info(auth)
        if client_id and rate_limit_model == self.applies_to_rate_limit_model:
            ident = client_id
        else:
            # Don't throttle invalid tokens; leave that to the anonymous
            # throttlers. Don't throttle enhanced rate limit tokens either.
            return None

        return self.cache_format % {"scope": self.scope, "ident": ident}


class OAuth2IdThrottleSustainedRate(OAuth2IdThrottleRate):
    applies_to_rate_limit_model = "standard"
    scope = "oauth2_client_credentials_sustained"


class OAuth2IdThrottleBurstRate(OAuth2IdThrottleRate):
    applies_to_rate_limit_model = "standard"
    scope = "oauth2_client_credentials_burst"


class EnhancedOAuth2IdThrottleSustainedRate(OAuth2IdThrottleRate):
    applies_to_rate_limit_model = "enhanced"
    scope = "enhanced_oauth2_client_credentials_sustained"


class EnhancedOAuth2IdThrottleBurstRate(OAuth2IdThrottleRate):
    applies_to_rate_limit_model = "enhanced"
    scope = "enhanced_oauth2_client_credentials_burst"
