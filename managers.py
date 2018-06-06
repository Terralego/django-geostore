from django.contrib.auth.base_user import BaseUserManager
from django.db.models import F, Q, QuerySet


class TerraUserManager(BaseUserManager):

    def _create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self._create_user(email, password, **extra_fields)


class FeatureQuerySet(QuerySet):

    def for_date(self, date_from, date_to):
        date_from = date_from.replace(year=1970)
        date_to = date_to.replace(year=1970)

        return self.filter(
            (
                (
                    Q(from_date__lte=F('to_date'))
                    & (
                        Q(from_date__lte=date_from, to_date__gte=date_from, )
                        | Q(from_date__lte=date_to, to_date__gte=date_to, )
                    )
                )
                | (
                    Q(to_date__lt=F('from_date'))
                    & (
                        Q(from_date__lte=date_from)
                        | Q(from_date__lte=date_to)
                        | Q(to_date__gte=date_to)
                        | Q(to_date__gte=date_from)
                    )
                )
            )
        )

    def intersects(self, geometry):
        return self.filter(
            geom__intersects=geometry
        )
