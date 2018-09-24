from django.db.models import QuerySet


class FeatureQuerySet(QuerySet):

    def intersects(self, geometry):
        return self.filter(
            geom__intersects=geometry
        )
