from dataclasses import dataclass

from catalog.api.models.oauth import OAuth2Registration, OAuth2Verification, ThrottledApplication

from test.factory.models.oauth2 import OAuth2RegistrationFactory, OAuth2VerificationFactory, ThrottledApplicationFactory


@dataclass
class OAuthGroup:
    registration: OAuth2Registration
    application: ThrottledApplication
    verification: OAuth2Verification


def cohesive_verification(email=None) -> OAuthGroup:
    """
    Generate a registration, application, and verification.

    Optionally associate it with a specific email.
    """
    options = {}
    if email:
        options.update(email=email)

    registration = OAuth2RegistrationFactory.create(**options)

    application = ThrottledApplicationFactory.create()

    verification = OAuth2VerificationFactory.create(
        email=registration.email,
        associated_application=application
    )

    return OAuthGroup(
        registration=registration,
        application=application,
        verification=verification
    )
