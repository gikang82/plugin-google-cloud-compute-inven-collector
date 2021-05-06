__all__ = ['CollectorManager']

import time
import logging
from spaceone.core.manager import BaseManager
from spaceone.inventory.connector import GoogleCloudComputeConnector
from spaceone.inventory.manager.compute_engine import VMInstanceManager, AutoScalerManager, LoadBalancerManager, \
    DiskManager, NICManager, VPCManager, SecurityGroupManager, StackDriverManager
from spaceone.inventory.manager.metadata.metadata_manager import MetadataManager
from spaceone.inventory.model.server import Server, ReferenceModel
from spaceone.inventory.model.region import Region
from spaceone.inventory.model.cloud_service_type import CloudServiceType

# from pprint import pprint
_LOGGER = logging.getLogger(__name__)
NUMBER_OF_CONCURRENT = 20


class CollectorManager(BaseManager):

    gcp_connector = None

    def __init__(self, transaction):
        super().__init__(transaction)

    def verify(self, options, secret_data):
        """ Check connection
        """
        self.gcp_connector = self.locator.get_connector('GoogleCloudComputeConnector')
        r = self.gcp_connector.verify(options, secret_data)
        # ACTIVE/UNKNOWN
        return r

    def set_connector(self, secret_data):
        self.gcp_connector: GoogleCloudComputeConnector = self.locator.get_connector('GoogleCloudComputeConnector')
        self.gcp_connector.get_connect(secret_data)

    def list_resources(self, params):
        resources = []
        '''
        params = {
            'zone_info': {
               'region': 'us-east-1,
               'zone': 'us-east-1a'
            },
            'query': query,
            'secret_data': 'secret_data',
            'instance_ids': [instance_id, instance_id, ...],
            'resources': {
                'url_maps': url_maps,
                'images': images,
                'vpcs': vpcs,
                'fire_walls': fire_walls,
                'subnets': subnets,
                'forwarding_rules': forwarding_rules,
            },
            'instances': [...]
        }
        '''

        print(f"START LIST Resources")
        start_time = time.time()
        secret_data = params.get('secret_data', {})
        global_resources = self.get_global_resources(secret_data)
        compute_vms = self.gcp_connector.list_instances()

        for compute_vm in compute_vms:

            zone, region = self._get_zone_and_region(compute_vm)
            zone_info = {'zone': zone, 'region': region, 'project_id': secret_data.get('project_id', '')}

            try:
                resources.append(self.get_instances(zone_info, compute_vm, global_resources))
            except Exception as e:
                print(f'[ERROR: {zone}] : {e}')

        print(f' Compute VMs Finished {time.time() - start_time} Seconds')
        return resources

    def get_global_resources(self, secret_data):
        # print("[ GET zone independent resources ]")
        if self.gcp_connector is None:
            self.set_connector(secret_data)

        instance_group = self.gcp_connector.list_instance_group_managers()
        self.gcp_connector.set_instance_into_instance_group_managers(instance_group)

        managed_state_less = [i.get('selfLink') for i in instance_group if
                              i.get('status', {}).get('stateful', {}).get('hasStatefulConfig') == False]
        instance_groups_instance = []

        for self_link in managed_state_less:
            _self_link = self_link[:self_link.find('/instanceGroupManagers/')]
            instance_group_name = self_link[self_link.rfind('/')+1:]

            val = _self_link[_self_link.find('/zones/') + 7:] if 'zones' in self_link \
                else _self_link[_self_link.find('/regions/') + 9:]

            try:
                instances = self.gcp_connector.get_instance_in_group('zone', val,
                                                                     instance_group_name) if 'zones' in self_link else \
                    self.gcp_connector.get_instance_in_group('region', val, instance_group_name)

                instance_groups_instance.extend(instances.get('items'))

            except Exception as e:
                print(e)

        return {
            'disk': self.gcp_connector.list_disks(),
            'auto_scaler': self.gcp_connector.list_autoscalers(),
            'instance_type': self.gcp_connector.list_machine_types(),
            'instance_group': instance_group,
            'public_images': self.gcp_connector.list_images(secret_data.get('project_id')),
            'vpcs': self.gcp_connector.list_vpcs(),
            'subnets': self.gcp_connector.list_subnetworks(),
            'fire_walls': self.gcp_connector.list_firewall(),
            'forwarding_rules': self.gcp_connector.list_forwarding_rules(),
            'target_pools': self.gcp_connector.list_target_pools(),
            'url_maps': self.gcp_connector.list_url_maps(),
            'backend_svcs':  self.gcp_connector.list_back_end_services(),
            'managed_stateless': [i.get('instance') for i in instance_groups_instance if 'instance' in i]
        }

    def get_instances(self, zone_info, instance, global_resources):
        # VPC
        vpcs = global_resources.get('vpcs', [])
        subnets = global_resources.get('subnets', [])

        # All Public Images
        public_images = global_resources.get('public_images', {})

        # URL Maps
        url_maps = global_resources.get('url_maps', [])
        backend_svcs = global_resources.get('backend_svcs', [])
        target_pools = global_resources.get('target_pools', [])
        # Forwarding Rules
        forwarding_rules = global_resources.get('forwarding_rules', [])

        # Security Group (Firewall)
        firewalls = global_resources.get('fire_walls', [])

        # Get Instance Groups
        instance_group = global_resources.get('instance_group', [])

        # Get Machine Types
        instance_types = global_resources.get('instance_type', [])

        # Autoscaling group list
        auto_scaler = global_resources.get('auto_scaler', [])

        instance_in_managed_instance_groups = global_resources.get('managed_stateless', [])

        # disks
        disks = global_resources.get('disk', [])
        # TODO: if distro has additional requirement with os_distros for future
        # disk_types = self.gcp_connector.list_disk_types(zone=zone)

        # call_up all the managers
        vm_instance_manager: VMInstanceManager = VMInstanceManager(self.gcp_connector)
        auto_scaler_manager: AutoScalerManager = AutoScalerManager()
        lb_manager: LoadBalancerManager = LoadBalancerManager()
        disk_manager: DiskManager = DiskManager()
        nic_manager: NICManager = NICManager()
        vpc_manager: VPCManager = VPCManager()
        security_group_manager: SecurityGroupManager = SecurityGroupManager()
        stackdriver_manager: StackDriverManager = StackDriverManager()
        meta_manager: MetadataManager = MetadataManager()

        server_data = vm_instance_manager.get_server_info(instance, instance_types, disks, zone_info, public_images, instance_in_managed_instance_groups)

        auto_scaler_vo = auto_scaler_manager.get_auto_scaler_info(instance, instance_group, auto_scaler)
        load_balancer_vos = lb_manager.get_load_balancer_info(instance, instance_group, backend_svcs, url_maps,
                                                              target_pools, forwarding_rules)
        disk_vos = disk_manager.get_disk_info(instance, disks)
        vpc_vo, subnet_vo = vpc_manager.get_vpc_info(instance, vpcs, subnets)
        nic_vos = nic_manager.get_nic_info(instance, subnet_vo)
        security_group_vos = security_group_manager.get_security_group_rules_info(instance, firewalls)
        security_groups = [d.get('security_group_name') for d in security_group_vos if
                           d.get('security_group_name', '') != '']

        google_cloud = server_data['data'].get('google_cloud', {})

        _google_cloud = google_cloud.to_primitive()
        labels = _google_cloud.get('labels', [])
        server_data.update({
            'nics': nic_vos,
            'disks': disk_vos,
        })
        _name = instance.get('name', '')
        server_data['data']['compute']['security_groups'] = security_groups
        server_data['data'].update({
            'load_balancers': load_balancer_vos,
            'security_group': security_group_vos,
            'auto_scaler': auto_scaler_vo,
            'vpc': vpc_vo,
            'subnet': subnet_vo,
            'stackdriver': stackdriver_manager.get_stackdriver_info(_name)
        })

        server_data.update({
            'name': _name,
            'tags': labels,
            '_metadata': meta_manager.get_metadata(),
            'reference': ReferenceModel({
                'resource_id': server_data['data']['google_cloud']['self_link'],
                'external_link': f"https://console.cloud.google.com/compute/instancesDetail/zones/{zone_info.get('zone')}/instances/{server_data['name']}?project={server_data['data']['compute']['account']}"
            })
        })

        return Server(server_data, strict=False)




    @staticmethod
    def list_cloud_service_types():
        cloud_service_type = {
            'tags': {
                'spaceone:icon': 'https://spaceone-custom-assets.s3.ap-northeast-2.amazonaws.com/console-assets/icons/cloud-services/google_cloud/Compute_Engine.svg',
            }
        }
        return [CloudServiceType(cloud_service_type, strict=False)]

    @staticmethod
    def _get_zone_and_region(instance):
        z = instance.get('zone', '')
        zone = z[z.rfind('/')+1:]
        region = zone[:-2] if zone != '' else ''
        return zone, region

    @staticmethod
    def get_region_from_result(result):
        REGION_INFO = {
            "asia-east1": {"name": "Taiwan (Changhua County)", "tags": {"latitude": "24.051196", "longitude": "120.516430"}},
            "asia-east2": {"name": "Hong Kong", "tags": {"latitude": "22.283289", "longitude": "114.155851"}},
            "asia-northeast1": {"name": "Japan (Tokyo)", "tags": {"latitude": "35.628391", "longitude": "139.417634"}},
            "asia-northeast2": {"name": "Japan (Osaka)", "tags": {"latitude": "34.705403", "longitude": "135.490119"}},
            "asia-northeast3": {"name": "South Korea (Seoul)", "tags": {"latitude": "37.499968", "longitude": "127.036376"}},
            "asia-south1": {"name": "India (Mumbai)", "tags": {"latitude": "19.164951", "longitude": "72.851765"}},
            "asia-southeast1": {"name": "Singapore (Jurong West)", "tags": {"latitude": "1.351376", "longitude": "103.709574"}},
            "asia-southeast2": {"name": "Indonesia (Jakarta)", "tags": {"latitude": "-6.227851", "longitude": "106.808169"}},
            "australia-southeast1": {"name": "Australia (Sydney)", "tags": {"latitude": "-33.733694", "longitude": "150.969840"}},
            "europe-north1": {"name": "Finland (Hamina)", "tags": {"latitude": "60.539504", "longitude": "27.113819"}},
            "europe-west1": {"name": "Belgium (St.Ghislain)", "tags": {"latitude": "50.471248", "longitude": "3.825493"}},
            "europe-west2": {"name": "England, UK (London)", "tags": {"latitude": "51.515998", "longitude": "-0.126918"}},
            "europe-west3": {"name": "Germany (Frankfurt)", "tags": {"latitude": "50.115963", "longitude": "8.669625"}},
            "europe-west4": {"name": "Netherlands (Eemshaven)", "tags": {"latitude": "53.427625", "longitude": "6.865703"}},
            "europe-west6": {"name": "Switzerland (Zürich)", "tags": {"latitude": "47.365663", "longitude": "8.524881"}},
            "northamerica-northeast1": {"name": "Canada, Québec (Montréal)", "tags": {"latitude": "45.501926", "longitude": "-73.570086"}},
            "southamerica-east1": {"name": "Brazil, São Paulo (Osasco)", "tags": {"latitude": "43.8345", "longitude": "2.1972"}},
            "us-central1": {"name": "US, Iowa (Council Bluffs)", "tags": {"latitude": "41.221419", "longitude": "-95.862676"}},
            "us-east1": {"name": "US, South Carolina (Moncks Corner)", "tags": {"latitude": "33.203394", "longitude": "-79.986329"}},
            "us-east4": {"name": "US, Northern Virginia (Ashburn)", "tags": {"latitude": "39.021075", "longitude": "-77.463569"}},
            "us-west1": {"name": "US, Oregon (The Dalles)", "tags": {"latitude": "45.631800", "longitude": "-121.200921"}},
            "us-west2": {"name": "US, California (Los Angeles)", "tags": {"latitude": "34.049329", "longitude": "-118.255265"}},
            "us-west3": {"name": "US, Utah (Salt Lake City)", "tags": {"latitude": "40.730109", "longitude": "-111.951386"}},
            "us-west4": {"name": "US, Nevada (Las Vegas)", "tags": {"latitude": "36.092498", "longitude": "-115.086073"}}
        }

        match_region_info = REGION_INFO.get(result.get('region_code'))

        if match_region_info is not None:
            region_info = match_region_info.copy()
            region_info.update({
                'region_code': result.get('region_code')
            })

            return Region(region_info, strict=False)

        return None
