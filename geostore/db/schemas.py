from geostore.models import ArrayObjectProperty, LayerSchemaProperty


def schema_to_schemamodel(layer, schema):
    required = schema.get('required', [])
    for key, value in schema.get("properties").items():
        title = layer.get_property_title(key)
        value.pop("title")
        prop_type = value.pop("type")

        fields = {
            'slug': key,
            'title': title,
            'prop_type': prop_type,
            'layer': layer
        }
        if key in required:
            fields['required'] = True

        array_object_property_list = []
        options = value.copy()
        if prop_type == "array":
            array_type = value['items']['type']
            fields['array_type'] = array_type
            if array_type == "object":
                required_array = value['items'].get("required", [])
                items_array = value.get('items')
                for sub_key, sub_value in items_array.get("properties").items():
                    sub_title = sub_value.pop("title")
                    sub_prop_type = sub_value.pop("type")
                    sub_options = sub_value
                    sub_fields = {
                        'slug': sub_key,
                        'title': sub_title,
                        'prop_type': sub_prop_type,
                        'options': sub_options,
                    }
                    if sub_key in required_array:
                        sub_fields['required'] = True
                    array_object_property_list.append(sub_fields)
                del options['items']
        fields['options'] = options
        layer_schema_property = LayerSchemaProperty.objects.create(**fields)
        for array_object_property in array_object_property_list:
            ArrayObjectProperty.objects.create(**array_object_property, array_property=layer_schema_property)
