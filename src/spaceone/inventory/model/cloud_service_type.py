from schematics import Model
from schematics.types import ListType, StringType, DictType, BooleanType


class CloudServiceType(Model):
    name = StringType(default='Instance')
    provider = StringType(default='google_cloud')
    group = StringType(default='ComputeEngine')
    labels = ListType(StringType(), serialize_when_none=False, default=['Compute'])
    tags = DictType(StringType, serialize_when_none=False)
    is_primary = BooleanType(default=True)
    is_major = BooleanType(default=True)
    resource_type = StringType(default='inventory.Server')
