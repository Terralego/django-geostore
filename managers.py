from django.db.models import F, Q, QuerySet


class FeatureQuerySet(QuerySet):

    def for_date(self, date_from, date_to):
        date_from = date_from.replace(year=1970)
        date_to = date_to.replace(year=1970)

        return self.filter(
            (
                (
                    Q(from_date__lte=F('to_date'))
                    & (
                        Q(from_date__lte=date_from, to_date__gte=date_from, )
                        | Q(from_date__lte=date_to, to_date__gte=date_to, )
                    )
                )
                | (
                    Q(to_date__lt=F('from_date'))
                    & (
                        Q(from_date__lte=date_from)
                        | Q(from_date__lte=date_to)
                        | Q(to_date__gte=date_to)
                        | Q(to_date__gte=date_from)
                    )
                )
            )
        )

    def intersects(self, geometry):
        return self.filter(
            geom__intersects=geometry
        )
