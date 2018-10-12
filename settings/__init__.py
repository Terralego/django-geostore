import os

MEDIA_ACCEL_REDIRECT = os.getenv('MEDIA_ACCEL_REDIRECT', default=False)

# Geometrical projection used internaly in database
# Note: Other projection than 4326 are not yet supported by some part of code
INTERNAL_GEOMETRY_SRID = 4326
