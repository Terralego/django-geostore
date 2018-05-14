from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth import models
from django.db.models import Manager

from .tiles.funcs import ST_Intersects, ST_Transform

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
    
    def intersects(self, geometry):
        return self.filter(
            geom__intersects=geometry
        )
