from dataclasses import dataclass
from io import StringIO
from unittest import mock
import smtplib

from django.core.management import call_command

import pytest
from fakeredis import FakeRedis

from test.factory.models.oauth2 import (
    OAuth2RegistrationFactory,
    OAuth2VerificationFactory,
    ThrottledApplicationFactory,
)

from catalog.api.models.oauth import (
    OAuth2Registration,
    OAuth2Verification,
    ThrottledApplication,
)


command_module_path = "catalog.management.commands.resendoauthverification"


@pytest.fixture(autouse=True)
def redis(monkeypatch) -> FakeRedis:
    fake_redis = FakeRedis()

    def get_redis_connection(*args, **kwargs):
        return fake_redis

    monkeypatch.setattr(
        f"{command_module_path}.get_redis_connection", get_redis_connection
    )

    yield fake_redis
    fake_redis.client().close()


@dataclass
class CapturedEmail:
    message: str
    recipient_list: list[str]


@pytest.fixture
def captured_emails(monkeypatch) -> list[CapturedEmail]:
    captured = []
    
    def send_mail(*args, **kwargs):
        captured.append(
            CapturedEmail(
                message=kwargs["message"],
                recipient_list=kwargs["recipient_list"],
            )
        )

    monkeypatch.setattr(
        f"{command_module_path}.send_mail", send_mail
    )

    yield captured


@pytest.fixture
def failed_emails(monkeypatch) -> list[CapturedEmail]:
    failed = []

    def send_mail(*args, **kwargs):
        failed.append(
            CapturedEmail(
                message=kwargs["message"],
                recipient_list=kwargs["recipient_list"],
            )
        )
        raise smtplib.SMTPAuthenticationError(1, "beep boop bad password")

    monkeypatch.setattr(
        f"{command_module_path}.send_mail", send_mail
    )

    yield failed


@dataclass
class OAuthGroup:
    registration: OAuth2Registration
    application: ThrottledApplication
    verification: OAuth2Verification


def cohesive_verification(email=None, verified=False) -> OAuthGroup:
    """
    Generate a registration, application, and verification.

    Optionally associate it with a specific email.
    """
    options = {}
    if email:
        options.update(email=email)

    registration = OAuth2RegistrationFactory.create(**options)

    application = ThrottledApplicationFactory.create(
        name=registration.name,
        verified=verified
    )

    verification = OAuth2VerificationFactory.create(
        email=registration.email, associated_application=application
    )

    return OAuthGroup(
        registration=registration, application=application, verification=verification
    )


@dataclass
class CleanableEmail:
    email: str
    keep_group: OAuthGroup
    clean_groups: list[OAuthGroup]


def make_cleanable_email():
    keep = cohesive_verification()
    clean = [
        cohesive_verification(
            email=keep.registration.email
        )
        for _ in range(10)
    ]

    return CleanableEmail(
        email=keep.registration.email,
        keep_group=keep,
        clean_groups=clean
    )


@pytest.fixture
def cleanable_email():
    return make_cleanable_email()


def is_group_captured(email: CapturedEmail, group: OAuthGroup) -> bool:
    return (
        group.verification.code in email.message and
        [group.registration.email] == email.recipient_list
    )


def count_captured_emails_for_group(
    captured_emails: list[CapturedEmail],
    oauth_group: OAuthGroup
) -> int:
    count = 0
    for email in captured_emails:
        if is_group_captured(email, oauth_group):
            count += 1
    
    return count
    


def assert_one_email_sent(
    captured_emails: list[CapturedEmail],
    oauth_group: OAuthGroup
):
    assert count_captured_emails_for_group(captured_emails, oauth_group) == 1

def assert_cleaned_and_sent(cleanable_email: CleanableEmail, captured_emails: list[CapturedEmail]):
    keep = cleanable_email.keep_group
    assert OAuth2Registration.objects.filter(pk=keep.registration.pk).exists() == True
    assert OAuth2Verification.objects.filter(pk=keep.verification.pk).exists() == True
    assert ThrottledApplication.objects.filter(pk=keep.application.pk).exists() == True

    for cleaned in cleanable_email.clean_groups:
        assert OAuth2Registration.objects.filter(pk=cleaned.registration.pk).exists() == False
        assert OAuth2Verification.objects.filter(pk=cleaned.verification.pk).exists() == False
        assert ThrottledApplication.objects.filter(pk=cleaned.application.pk).exists() == False

    assert_one_email_sent(captured_emails, keep)


def call_resendoauthverification(input_response="YES", **options):
    out = StringIO()
    err = StringIO()
    options.update(stdout=out, stderr=err)
    with mock.patch(f"{command_module_path}.get_input", return_value=input_response):
        call_command("resendoauthverification", **options)

    res = out.getvalue(), err.getvalue()
    print(res)

    return res


@pytest.mark.parametrize(
    "return_value",
    (
        None,
        "",
        "no"
        "NO",
        "yes",  # must be exactly YES
    )
)
def test_should_exit_if_wet_unconfirmed(return_value):
    with pytest.raises(SystemExit):
        call_resendoauthverification(input_response=return_value, dry_run=False)


@pytest.mark.django_db
def test_should_continue_if_wet_confirmed_with_YES(captured_emails, cleanable_email):
    call_resendoauthverification(input_response="YES", dry_run=False)
    assert_cleaned_and_sent(cleanable_email, captured_emails)


@pytest.mark.django_db
def test_should_clean_for_several_emails(captured_emails):
    cleanables = [
        make_cleanable_email() for _ in range(10)
    ]
    call_resendoauthverification(dry_run=False)
    for cleanable in cleanables:
        assert_cleaned_and_sent(cleanable, captured_emails)


@pytest.mark.django_db
def test_should_not_resend_for_already_sent(captured_emails):
    cleanables = [
        make_cleanable_email() for _ in range(10)
    ]
    call_resendoauthverification(dry_run=False)
    for cleanable in cleanables:
        assert_cleaned_and_sent(cleanable, captured_emails)
    call_resendoauthverification(dry_run=False)
    for cleanable in cleanables:
        assert_one_email_sent(captured_emails, cleanable.keep_group)


@pytest.mark.django_db
def test_should_not_count_email_as_sent_if_failed_and_rollback(failed_emails, cleanable_email, redis):
    call_resendoauthverification(dry_run=False)
    assert count_captured_emails_for_group(failed_emails, cleanable_email.keep_group) == 1

    keep = cleanable_email.keep_group
    assert OAuth2Registration.objects.filter(pk=keep.registration.pk).exists() == True
    assert OAuth2Verification.objects.filter(pk=keep.verification.pk).exists() == True
    assert ThrottledApplication.objects.filter(pk=keep.application.pk).exists() == True

    # Assert these all still exist
    for cleaned in cleanable_email.clean_groups:
        assert OAuth2Registration.objects.filter(pk=cleaned.registration.pk).exists() == True
        assert OAuth2Verification.objects.filter(pk=cleaned.verification.pk).exists() == True
        assert ThrottledApplication.objects.filter(pk=cleaned.application.pk).exists() == True

    assert redis.sismember("resendoauthverification:processed", keep.registration.email) == False


@pytest.mark.django_db
def test_should_not_delete_or_send_if_dry_run(cleanable_email, captured_emails, redis):
    call_resendoauthverification(dry_run=True)
    assert count_captured_emails_for_group(captured_emails, cleanable_email.keep_group) == 0

    keep = cleanable_email.keep_group
    assert OAuth2Registration.objects.filter(pk=keep.registration.pk).exists() == True
    assert OAuth2Verification.objects.filter(pk=keep.verification.pk).exists() == True
    assert ThrottledApplication.objects.filter(pk=keep.application.pk).exists() == True

    # Assert these all still exist (no clean up has happened)
    for cleaned in cleanable_email.clean_groups:
        assert OAuth2Registration.objects.filter(pk=cleaned.registration.pk).exists() == True
        assert OAuth2Verification.objects.filter(pk=cleaned.verification.pk).exists() == True
        assert ThrottledApplication.objects.filter(pk=cleaned.application.pk).exists() == True

    assert redis.sismember("resendoauthverification:processed", keep.registration.email) == False


@pytest.mark.django_db
def test_should_not_send_for_verified_emails(cleanable_email, captured_emails):
    verified = cohesive_verification(verified=True)

    call_resendoauthverification(dry_run=False)
    assert count_captured_emails_for_group(captured_emails, verified) == 0
    assert_cleaned_and_sent(cleanable_email, captured_emails)
