from schematics import Model
from schematics.types import StringType, ModelType, ListType


class StackDriverFilters(Model):
    key = StringType()
    value = StringType()


class StackDriver(Model):
    class Option:
        serialize_when_none = False

    type = StringType()
    filters = ListType(ModelType(StackDriverFilters), default=[])
