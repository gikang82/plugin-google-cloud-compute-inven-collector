from schematics import Model
from schematics.types import ModelType, ListType, StringType
from spaceone.inventory.model import OS, GoogleCloud, Hardware, SecurityGroup, Compute, LoadBalancer, VPC, Subnet, \
    AutoScaler, NIC, Disk, ServerMetadata, StackDriver


class ReferenceModel(Model):
    class Option:
        serialize_when_none = False
    resource_id = StringType(required=False, serialize_when_none=False)
    external_link = StringType(required=False, serialize_when_none=False)


class ServerData(Model):
    os = ModelType(OS)
    google_cloud = ModelType(GoogleCloud)
    hardware = ModelType(Hardware)
    compute = ModelType(Compute)
    load_balancers = ListType(ModelType(LoadBalancer))
    security_group = ListType(ModelType(SecurityGroup))
    vpc = ModelType(VPC)
    subnet = ModelType(Subnet)
    auto_scaler = ModelType(AutoScaler, serialize_when_none=False)
    stackdriver = ModelType(StackDriver)


class Server(Model):
    name = StringType()
    server_type = StringType(default='VM')
    os_type = StringType(choices=('LINUX', 'WINDOWS'))
    provider = StringType(default='google_cloud')
    primary_ip_address = StringType()
    ip_addresses = ListType(StringType())
    region_code = StringType()
    region_type = StringType(default='GOOGLE_CLOUD')
    nics = ListType(ModelType(NIC))
    disks = ListType(ModelType(Disk))
    data = ModelType(ServerData)
    _metadata = ModelType(ServerMetadata, serialized_name='metadata')
    reference = ModelType(ReferenceModel)

