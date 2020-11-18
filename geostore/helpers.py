from django.db import transaction


def execute_async_func(async_func, args=()):
    """ Celery worker can be out of transaction, and raise DoesNotExist """
    async_func.delay(*args) if not transaction.get_connection().in_atomic_block else transaction.on_commit(
        lambda: async_func.delay(*args))
