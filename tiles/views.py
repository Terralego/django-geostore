import mercantile
from django.db.models import F
from django.http import HttpResponse, HttpResponseNotFound
from django.views.generic import View

from ..models import Feature, Layer
from .funcs import ST_AsMvtGeom, ST_MakeEnvelope, ST_Transform


class MVTView(View):
    def get_tile(self):
        bounds = mercantile.bounds(self.x, self.y, self.z)
        xmin, ymin = mercantile.xy(bounds.west, bounds.south)
        xmax, ymax = mercantile.xy(bounds.east, bounds.north)

        layer_query = Layer.objects.get(pk=self.layer_pk).features.annotate(
                bbox=ST_MakeEnvelope(xmin, ymin, xmax, ymax, 3857),
                geom3857=ST_Transform('geom', 3857)
            ).filter(
                bbox__intersects=F('geom3857')
            ).annotate(
                geometry=ST_AsMvtGeom(
                    F('geom3857'),
                    'bbox',
                    4096,
                    256,
                    True
                )
            )

        mvt_query = Feature.objects.raw(
            f'''
            WITH tilegeom as ({layer_query.query})
            SELECT {self.layer_pk} AS id, count(*) AS count,
                   ST_AsMVT(tilegeom, 'name', 4096, 'geometry') AS mvt
            FROM tilegeom
            '''
        )

        return mvt_query[0]

    def get(self, request, layer_pk, z, x, y):
        self.layer_pk = layer_pk
        self.z = z
        self.x = x
        self.y = y

        qs = self.get_tile()
        if qs.count > 0:
            return HttpResponse(
                        qs.mvt,
                        content_type="application/vnd.mapbox-vector-tile"
                        )
        else:
            return HttpResponseNotFound()
