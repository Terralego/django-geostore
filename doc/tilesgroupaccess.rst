Vector Tiles Group Access
=========================

Django-Geostore has a mecanism to authorize only some django's user Groups to access layer's on vector tiles.

This can be used to manage layer access through vector tiles.

Here we're going to describe how it works.


Where to add a group
--------------------

Each layer has a ManyToMany relationship to django's Group model, that authorized only users present is thoses groups
to have access to thoses layers through vector tiles.

You can add a group, with the normal django's ORM API:

.. code-block:: python

  from django.contrib.auth.models import Group
  from geostore.models import Layer
  g = Group.objects.first()
  l = Layer.objects.first()

  l.authorized_groups.add(g)


Then ?
------

Then, you can generate the autheticated URL by using a QueryString like above,
where user_groups are a list of user_groups names, and layergroup is the group of the layer:

.. code-block:: python
    from geostore.tokens import tiles_token_generator
    querystring = QueryDict(mutable=True)
    querystring.update(
    {
        "idb64": tiles_token_generator.token_idb64(
            user_groups, layergroup
        ),
        "token": tiles_token_generator.make_token(
            user_groups, layergroup
        ),
    }
    )

    tilejson_url = reverse("group-tilejson", args=(layergroup.slug,))
    authenticated_url = f"{tilejson_url}?{querystring.urlencode()}"


You'll have available an authenticated url, this will filter layers in tiles that are accessible to the authenticated user groups.

All authenticated informations will be provided by the authenticated tilejson, that will provide to frontend all authenticated urls.

Usually, mapbox needs only the tilejson, geostore will do all the remaining work.