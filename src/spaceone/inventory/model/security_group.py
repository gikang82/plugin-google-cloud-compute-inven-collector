from schematics import Model
from schematics.types import StringType, IntType


class SecurityGroup(Model):
    priority = IntType(serialize_when_none=False)
    protocol = StringType()
    remote = StringType()                                   # mimic
    remote_id = StringType(serialize_when_none=False)       # filter value
    remote_cidr = StringType(serialize_when_none=False)     # cidr
    security_group_name = StringType(default="")
    port_range_min = IntType(serialize_when_none=False)
    port_range_max = IntType(serialize_when_none=False)
    security_group_id = StringType()
    description = StringType(default="")
    direction = StringType(choices=("inbound", "outbound"))
    port = StringType(serialize_when_none=False)
    action = StringType(choices=('allow', 'deny'))
