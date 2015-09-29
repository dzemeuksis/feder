from feder.cases.models import Case
from feder.institutions.factory import factory_institution
from feder.monitorings.factory import factory_monitoring


def factory_case(user):
        monitoring = factory_monitoring(user)
        institution = factory_institution(user)
        return Case.objects.create(name="blabla",
                                   monitoring=monitoring,
                                   institution=institution,
                                   user=user)
