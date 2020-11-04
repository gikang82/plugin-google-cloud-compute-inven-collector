from schematics import Model
from schematics.types import ListType, StringType, DateTimeType, DictType


class Compute(Model):
    keypair = StringType(default="")
    public_ip_address = StringType()
    az = StringType()
    instance_id = StringType()
    instance_name = StringType(default='')
    instance_state = StringType(choices=('PROVISIONING', 'STAGING', 'RUNNING', 'STOPPING', 'REPAIRING', 'SUSPENDING', 'SUSPENDED', 'TERMINATED'))
    instance_type = StringType()
    account = StringType()
    image = StringType()
    launched_at = DateTimeType()
    security_groups = ListType(StringType, default=[])
    tags = DictType(StringType, default={})
