from dataclasses import dataclass

from django.core.mail import send_mail
from django.db import transaction

from django_tqdm import BaseCommand
from django_redis import get_redis_connection

from catalog.api.models.oauth import OAuth2Verification, OAuth2Registration, ThrottledApplication

verification_msg_template = """
The Openverse API OAuth2 email verification process has recently been fixed.
We have detected that you attempted to register an application using this email.

To verify your Openverse API credentials, click on the following link:

{link}

If you believe you received this message in error, please disregard it.
"""

@dataclass
class Result:
    saved_application_name: str
    deleted_applications: int = 0

class Command(BaseCommand):
    help = "Resends verification emails for unverified Oauth applications."
    """
    This command is meant to be used a single time in production to remediate
    failed email sending. It puts a lock in Redis to prevent it from being run
    multiple times.

    If for some reason it needs to be run a second time, pass the --force flag
    to release the lock.
    """
    lock_name = 'resendoauthverification:lock'

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", help="Force running the command even if a lock already exists in redis", type=bool
        )

    @transaction.atomic
    def _handle_email(self, email):
        """
        1. Get all application IDs for the email
        2. Use the one with the lowest ID as the "original" attempt
        3. Delete the rest
        4. Delete OAuth2Registrations for the email not associated with the "original" application
        5. Delete OAuth2Verifications for the email not associated with the "original" application

        This ignores the fact that someone could have tried to register multiple unverified but distinct
        applications under the same email. This is unlikely given that none of the requests would have
        worked and that the "feature" isn't explicitly documented anyway.
        """
        application_ids = list(OAuth2Registration.objects.filter(
            email=email
        ).select_related('associated_application').order_by('id').values('pk'))

        application_to_verify = ThrottledApplication.objects.get(application_ids[0])

        deleted_applications = 0
        if len(application_ids) > 1:
            applications_to_delete_ids = application_ids[1:]
            ThrottledApplication.objects.filter(pk__in=applications_to_delete_ids).delete()
            OAuth2Registration.objects.filter(email=email).exclude(name=application_to_verify.name).delete()
            OAuth2Verification.objects.filter(email=email).exclude(associated_application=application_to_verify).delete()
            deleted_applications = len(applications_to_delete_ids)
        
        verification = OAuth2Verification.objects.get(associated_application=application_to_verify)
        token = verification.code
        link = request.build_absolute_uri(reverse("verify-email", [token]))
        verification_msg = verification_msg_template.format(
            link=link
        )
        send_mail(
            subject="Verify your API credentials",
            message=verification_msg,
            from_email=settings.EMAIL_SENDER,
            recipient_list=[verification.email],
            fail_silently=False,
        )

        return Result(
            saved_application_name=application_to_verify.name,
            deleted_applications=deleted_applications,
        )

    def handle(self, *args, **options):
        redis = get_redis_connection('default')

        if redis.exists(self.lock_name) and not options['force']:
            self.error("A lock already exists for the resend oauth verification command. Exiting.")
            return
        
        redis.set(self.lock_name, True)

        try:
            emails_with_verified_applications = OAuth2Verification.objects.filter(
                associated_application__verified=True
            ).values('email')
            emails_with_zero_verified_applications = list(OAuth2Verification.objects.exclude(
                email__in=emails_with_verified_applications
            ).values('email').distinct())

            count_to_process = len(emails_with_zero_verified_applications)
            results = []
            errored_emails = []

            with self.tqdm(total=count_to_process) as progress:
                for email in emails_with_zero_verified_applications:
                    try:
                        results.append(self._handle_email(email))
                    except BaseException as err:
                        errored_emails.append(email)
                        self.error(f"Unable to process {email}: " f"{err}")

                    progress.update(1)
        finally:
            redis.delete(self.lock_name)

        if errored_emails:
            joined = "\n".join(errored_emails)
            self.info(
                self.style.WARNING(
                    f"The following emails were unable to be processed.\n\n"
                    f"{joined}"
                    f"\n\nPlease check the output above for the error related to each email."
                )
            )

        formatted_results = "\n\n".join(
            (
                f"Application name: {result.saved_application_name}\n"
                f"Cleaned related application count: {result.deleted_applications}\n"
            ) for result in results
        )

        self.info(
            self.style.SUCCESS(
                f"The following applications had email verifications sent.\n\n"
                f"{formatted_results}"
            )
        )
