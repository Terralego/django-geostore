Plugins
=======


Routing
--------

django-geostore-routing integrate a way to use your LineString layer as a routing one. It uses pgRouting as backend.

Install it with :

.. code-block:: bash

  pip install django-geostore-routing


and enable-it in your INSTALLED_APPS :


.. code-block:: bash

  INSTALLED_APPS = (
      ...
      'geostore',
      'geostore_routing',
      ...
  )


Full documentation : https://django-geostore-routing.readthedocs.io/

Repository : https://github.com/Terralego/django-geostore-routing
