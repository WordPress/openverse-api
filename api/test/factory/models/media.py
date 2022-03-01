import factory
from uuid import uuid4
from factory.django import DjangoModelFactory
from test.factory.faker import Faker

from catalog.api.licenses import LICENSES
from catalog.api.models.media import AbstractMedia


class MediaFactory(DjangoModelFactory):
    """Base factory for models that extend from the AbstractMedia class."""
    class Meta:
        abstract = True

    identifier = factory.sequence(lambda _: uuid4())

    foreign_identifier = factory.sequence(lambda _: uuid4())
    """The foreign identifier isn't necessarily a UUID but for test purposes it's fine if it looks like one"""

    license = Faker("random_element", elements=[l[0] for l in LICENSES])

    foreign_landing_url = Faker("url")
    


class IdentifierFactory(factory.SubFactory):
    """
    A factory for creating a related model and returning the UUID.
    
    Distinct from the `SubFactory` in that this creates the related model but
    uses a specific attribute from it for the resulting value instead of the
    related model itself.
    """

    def evaluate(self, instance, step, extra):
        model = super().evaluate(instance, step, extra)
        return model.identifier
