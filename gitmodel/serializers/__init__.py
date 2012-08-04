BUILTIN_SERIALIZERS = {
    "xml"    : "gitmodel.serializers.xml_serializer",
    "python" : "gitmodel.serializers.python",
    "json"   : "gitmodel.serializers.json",
}

def get_serializer_module(config, format):
    serializer_modules = BUILTIN_SERIALIZERS.copy()
    serializer_modules.update(config.get('SERIALIZER_MODULES', {}))
    if format not in serializer_modules.keys():
        raise ValueError("Invalid serializer format: {}".format(format))
    mod = __import__(serializer_modules[format], globals(), locals(), ['Serializer'], -1)
    return mod


def serialize(obj, format, **options):
    config = obj._meta.config
    serializer = get_serializer_module(config, format).Serializer()
    return serializer.serialize(obj, **options)

def deserialize(model, data, format, **options):
    config = model._meta.config
    deserializer = get_serializer_module(config, format).Deserializer(model, **options)
    return deserializer.deserialize(data)
