from django.contrib.gis.db.models import GeometryField
from django.contrib.gis.geos import Polygon
from django.db.models.functions import Cast

from . import EPSG_3857
from .funcs import ST_Extent, ST_Transform


class SIGTools(object):
    """
    This class collects all the sig functions  to use in TileVect, GeomConfig
    """

    @classmethod
    def get_extent_of_layer(cls, layer):
        """
        Outputs length of the smaller size of the features' bbox
        Returns 0 if the bbox is a Point
        """

        min_extent_features = float(0)

        # output might be a Point if single Point feature
        query = cls.get_bbox_layer(layer)

        if isinstance(query['extent'], Polygon):
            x1 = query['extent'].coords[0][0][0]
            x2 = query['extent'].coords[0][2][0]
            y1 = query['extent'].coords[0][0][1]
            y2 = query['extent'].coords[0][2][1]

            min_extent_features = min(float(abs(x2 - x1)), float(abs(y2 - y1)))

        return min_extent_features

    @classmethod
    def get_bbox_layer(cls, layer):
        """
        Method giving the bbox of a layer,
        under the form of a Polygon (if > 0)
        OUTPUT query # Polygon (bbox) with 'extent' attribute
        """
        features = layer.features.all()

        query = features.annotate(
            geom3857=Cast(ST_Transform('geom', EPSG_3857),
                          GeometryField(srid=EPSG_3857))
        ).aggregate(
            extent=Cast(ST_Extent('geom3857'), GeometryField(srid=0))
        )

        return query
