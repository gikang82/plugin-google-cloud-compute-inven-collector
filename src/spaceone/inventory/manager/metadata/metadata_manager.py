from spaceone.core.manager import BaseManager
from spaceone.inventory.model.metadata.metadata import ServerMetadata
from spaceone.inventory.model.metadata.metadata_dynamic_layout import ItemDynamicLayout, TableDynamicLayout, \
    ListDynamicLayout
from spaceone.inventory.model.metadata.metadata_dynamic_field import TextDyField, EnumDyField, ListDyField, \
    DateTimeDyField

google_cloud_instance = ItemDynamicLayout.set_fields('VM Instance', fields=[
    TextDyField.data_source('Account', 'data.compute.account'),
    TextDyField.data_source('Instance ID', 'data.compute.instance_id'),
    TextDyField.data_source('Instance Name', 'data.compute.instance_name'),
    EnumDyField.data_source('Instance State', 'data.compute.instance_state', default_state={
        'safe': ['RUNNING'],
        'warning': ['STAGING', 'PROVISIONING', 'REPAIRING', 'STOPPING', 'SUSPENDING'],
        'disable': [],
        'alert': ['SUSPENDED', 'TERMINATED']
    }),
    EnumDyField.data_source('Preemptible', 'data.google_cloud.scheduling.preemptible', default_badge={
        'indigo.500': ['true'], 'coral.600': ['false']
    }),
    TextDyField.data_source('Instance Type', 'data.compute.instance_type'),
    TextDyField.data_source('Image', 'data.compute.image'),
    TextDyField.data_source('Region', 'region_code'),
    TextDyField.data_source('Availability Zone', 'data.compute.az'),
    TextDyField.data_source('Reservation Affinity', 'data.google_cloud.reservation_affinity'),
    TextDyField.data_source('Self link', 'data.google_cloud.self_link'),
    EnumDyField.data_source('Deletion Protection', 'data.google_cloud.deletion_protection', default_badge={
        'indigo.500': ['true'], 'coral.600': ['false']
    }),
    TextDyField.data_source('Public IP', 'data.compute.public_ip_address'),
    ListDyField.data_source('IP Addresses', 'ip_addresses',
                            default_badge={'type': 'outline', 'delimiter': '<br>'}),
    ListDyField.data_source('Affected Rules', 'data.compute.security_groups',
                            default_badge={'type': 'outline', 'delimiter': '<br>'}),

    DateTimeDyField.data_source('Launched At', 'data.compute.launched_at'),
])

google_cloud_vpc = ItemDynamicLayout.set_fields('VPC', fields=[
    TextDyField.data_source('VPC ID', 'data.vpc.vpc_id'),
    TextDyField.data_source('VPC Name', 'data.vpc.vpc_name'),
    TextDyField.data_source('Subnet ID', 'data.subnet.subnet_id'),
    TextDyField.data_source('Subnet Name', 'data.subnet.subnet_name'),
])

auto_scaler_group = ItemDynamicLayout.set_fields('Auto Scaler', fields=[
    TextDyField.data_source('Auto Scaler', 'data.auto_scaler.name'),
    TextDyField.data_source('Auto Scaler ID', 'data.auto_scaler.id'),
    TextDyField.data_source('Instance Group Name', 'data.auto_scaler.instance_group.name'),
    TextDyField.data_source('Instance Template Name', 'data.auto_scaler.instance_group.instance_template_name'),
])

compute_engine = ListDynamicLayout.set_layouts('Compute Engine', layouts=[google_cloud_instance, google_cloud_vpc, auto_scaler_group])

disk = TableDynamicLayout.set_fields('Disk', root_path='disks', fields=[
    TextDyField.data_source('Index', 'device_index'),
    TextDyField.data_source('Name', 'tags.disk_name'),
    TextDyField.data_source('Size(GB)', 'size'),
    TextDyField.data_source('Disk ID', 'tags.disk_id'),
    EnumDyField.data_source('Disk Type', 'tags.disk_type', default_outline_badge=['local-ssd', 'pd-balanced', 'pd-ssd', 'pd-standard']),
    TextDyField.data_source('Read IOPS', 'tags.read_iops'),
    TextDyField.data_source('Write IOPS', 'tags.write_iops'),
    TextDyField.data_source('Read Throughput(MB/s)', 'tags.read_throughput'),
    TextDyField.data_source('Write Throughput(MB/s)', 'tags.write_throughput'),
    EnumDyField.data_source('Encrypted', 'tags.encrypted', default_badge={
        'indigo.500': ['true'], 'coral.600': ['false']
    }),
])

nic = TableDynamicLayout.set_fields('NIC', root_path='nics', fields=[
    TextDyField.data_source('Index', 'device_index'),
    ListDyField.data_source('IP Addresses', 'ip_addresses', options={'delimiter': '<br>'}),
    TextDyField.data_source('CIDR', 'cidr'),
    TextDyField.data_source('Public IP', 'public_ip_address')
])

security_group = TableDynamicLayout.set_fields('Firewalls', root_path='data.security_group', fields=[
    EnumDyField.data_source('Direction', 'direction', default_badge={
        'indigo.500': ['inbound'], 'coral.600': ['outbound']
    }),
    TextDyField.data_source('Priority', 'priority'),
    EnumDyField.data_source('Action', 'action', default_badge={
        'indigo.500': ['allow'], 'coral.600': ['deny']
    }),
    TextDyField.data_source('Name', 'security_group_name'),
    EnumDyField.data_source('Protocol', 'protocol', default_outline_badge=['all', 'tcp', 'udp', 'icmp']),
    TextDyField.data_source('Port Rage', 'port'),
    TextDyField.data_source('Remote', 'remote'),
    TextDyField.data_source('Description', 'description'),
])

lb = TableDynamicLayout.set_fields('LB', root_path='data.load_balancers', fields=[
    TextDyField.data_source('Name', 'name'),
    # TextDyField.data_source('DNS', 'dns'),
    EnumDyField.data_source('Type', 'type', default_badge={
        'primary': ['HTTP', 'HTTPS'], 'indigo.500': ['TCP'], 'coral.600': ['UDP']
    }),
    ListDyField.data_source('Protocol', 'protocol', options={'delimiter': '<br>'}),
    ListDyField.data_source('Port', 'port', options={'delimiter': '<br>'}),
    EnumDyField.data_source('Scheme', 'scheme', default_badge={
        'indigo.500': ['EXTERNAL'], 'coral.600': ['INTERNAL']
    }),
])

labels = TableDynamicLayout.set_fields('Google Cloud Labels', root_path='data.google_cloud.labels', fields=[
    TextDyField.data_source('Key', 'key'),
    TextDyField.data_source('Value', 'value'),
])

metadata = ServerMetadata.set_layouts([compute_engine, labels, disk, nic, security_group, lb])


class MetadataManager(BaseManager):

    def __init__(self):
        self.metadata = metadata

    def get_metadata(self):
        return self.metadata
