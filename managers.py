from django.contrib.auth.base_user import BaseUserManager
from django.db.models import F, Manager, Q


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


class FeatureManager(Manager):

    def for_date(self, range_date):
        compare_date = range_date.replace(year=1970)

        return self.filter(
            (Q(from_date__gte=F('to_date'))
             & (Q(from_date__lte=compare_date)
             | Q(to_date__gte=compare_date)))
            | Q(from_date__lte=compare_date, to_date__gte=compare_date, )
        )
