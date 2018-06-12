from rest_framework_jwt.utils import jwt_payload_handler

from terracommon.terra.serializers import TerraUserSerializer


def terra_payload_handler(user):
    """ Custom response payload handler.

    This function controlls the custom payload after login or token refresh.
    This data is returned through the web API.
    """
    payload = jwt_payload_handler(user)

    user_serializer = TerraUserSerializer(user)
    payload.update({
        'user': user_serializer.data
    })
    return payload
