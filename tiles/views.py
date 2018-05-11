import mercantile

from django.views.generic import View
from django.contrib.gis.gdal.envelope import Envelope

from django.db.models import Count, Value, F

from .funcs import ST_Intersects, ST_Transform, ST_MakeEnvelope, ST_AsMvtGeom, ST_AsMVT
from ..models import Layer, Feature

class MVTView(View):
    query = """WITH bbox AS (
        SELECT ST_MakeEnvelope({0}, {1}, {2} ,{3}, 3857) AS geom
    )
    ============================================
        SELECT  id,
                properties,
                ST_AsMvtGeom(
                    ST_Transform(terra_feature.geom,3857),
                    bbox.geom,
                    4096,
                    256,
                    true
                ) AS geom

        FROM terra_feature, bbox
        WHERE ST_Intersects(ST_Transform(terra_feature.geom,3857), bbox.geom)
                AND layer_id={4}
    ===============================

    SELECT {4} AS id, count(*) AS count, ST_AsMVT(tilegeom, 'name', 4096, 'geom') AS mvt
    FROM tilegeom"""
        # .format(xmin, ymin, xmax, ymax, self.layer_pk)
        # return Feature.objects.raw(query)[0]

    def get_tile(self):
        bounds = mercantile.bounds(self.x, self.y, self.z)
        xmin, ymin = mercantile.xy(bounds.west, bounds.south)
        xmax, ymax = mercantile.xy(bounds.east, bounds.north)

        bbox = Envelope(xmin, ymin, xmax, ymax)
        
        a = Layer.objects.get(pk=self.layer_pk).features.annotate(
                bbox=ST_MakeEnvelope(xmin, ymin, xmax, ymax, 3857)
            ).annotate(
                intersect=ST_Intersects(
                            ST_Transform('geom', 3857),
                            'bbox'
                        ),
            ).filter(
                intersect=True
            ).annotate(
                geometry=ST_AsMvtGeom(
                    ST_Transform('geom', 3857),
                    'bbox',
                    4096,
                    256,
                    True
                )
            ) .aggregate(
                count=Count('*'),
                mvt=ST_AsMVT(
                    'subquery',
                    Value('name'),
                    4096,
                    )
            )
        print(a.query)
        



        # features = Layer.objects.get(pk=self.layer_pk).features.filter(
        #     ST_Intersects(
        #         ST_Transform(
        #             geom,
        #             3857
        #         ),
        #         bbox
        #     )
        # )





    def get(self, request, layer_pk, z, x, y):
        self.layer_pk = layer_pk
        self.z = z
        self.x = x
        self.y = y

        self.get_tile()
        return
