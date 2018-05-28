import factory

from terracommon.terra.models import TerraUser


class TerraUserFactory(factory.DjangoModelFactory):
    class Meta:
        model = TerraUser
    
    email = 'foo@bar.com'
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, **kwargs)