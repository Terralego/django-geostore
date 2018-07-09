import logging

from .helpers import GeometryDefiner

logger = logging.getLogger(__name__)


def set_geometry_from_options(feature_args, options):
    geometry_columns = {
        GeometryDefiner.LONGITUDE: options.get('longitude'),
        GeometryDefiner.LATITUDE: options.get('latitude')
    }
    geometry_columns_filtered = {k: v for k, v in geometry_columns.items()
                                 if v is not None}

    geometry = GeometryDefiner.get_geometry(
        column_names=geometry_columns_filtered,
        row=feature_args["properties"]
    )
    if geometry:
        feature_args['geom'] = geometry
    else:
        pk_properties = [(key, feature_args["properties"].get(key)) for key in
                         options.get('pk_properties')]
        logger.warning(f'can not define geometry for: {str(pk_properties)}')
