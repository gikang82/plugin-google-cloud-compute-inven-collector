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
from pprint import pprint
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

    def list_regions(self, secret_data):
        if self.gcp_connector is None:
            self.set_connector(secret_data)

        return self.gcp_connector.list_regions()

    def list_zones(self, secret_data):
        if self.gcp_connector is None:
            self.set_connector(secret_data)

        return self.gcp_connector.list_zones()

    def list_instances_only(self, params):
        instance_filter = {'zone': params['zone_info']['zone']}

        if len(params.get('instance_ids', [])) > 0:
            instance_filter.update({'filter': [{'key': 'id', 'values': params['instance_ids']}]})

        return self.gcp_connector.list_instances(**instance_filter)

    def get_instance(self, zone_info, instance, global_resources):
        zone = zone_info['zone']

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
        instance_group = self.gcp_connector.list_instance_group_managers(zone=zone)
        self.gcp_connector.set_instance_into_instance_group_managers(instance_group, zone=zone)

        # Get Machine Types
        instance_types = self.gcp_connector.list_machine_types(zone=zone)

        # Autoscaling group list
        auto_scaler = self.gcp_connector.list_auto_scalers(zone=zone)

        # disks
        disks = self.gcp_connector.list_disk(zone=zone)
        # TODO: if distro has additional requirement with os_distros for future
        # disk_types = self.gcp_connector.list_disk_types(zone=zone)

        # call_up all the managers
        vm_instance_manager: VMInstanceManager = VMInstanceManager()
        auto_scaler_manager: AutoScalerManager = AutoScalerManager()
        lb_manager: LoadBalancerManager = LoadBalancerManager()
        disk_manager: DiskManager = DiskManager()
        nic_manager: NICManager = NICManager()
        vpc_manager: VPCManager = VPCManager()
        security_group_manager: SecurityGroupManager = SecurityGroupManager()
        stackdriver_manager: StackDriverManager = StackDriverManager()
        meta_manager: MetadataManager = MetadataManager()

        server_data = vm_instance_manager.get_server_info(instance, instance_types, disks, zone_info, public_images)
        auto_scaler_vo = auto_scaler_manager.get_auto_scaler_info(instance, instance_group, auto_scaler)
        load_balancer_vos = lb_manager.get_load_balancer_info(instance, instance_group, backend_svcs, url_maps, target_pools, forwarding_rules)
        disk_vos = disk_manager.get_disk_info(instance, disks)
        vpc_vo, subnet_vo = vpc_manager.get_vpc_info(instance, vpcs, subnets)
        nic_vos = nic_manager.get_nic_info(instance, subnet_vo)
        security_group_vos = security_group_manager.get_security_group_rules_info(instance, firewalls)
        security_groups = [d.get('security_group_name') for d in security_group_vos if d.get('security_group_name', '') != '']
        
        server_data.update({
            'nics': nic_vos,
            'disks': disk_vos,
        })

        server_data['data']['compute']['security_groups'] = security_groups
        server_data['data'].update({
            'load_balancers': load_balancer_vos,
            'security_group': security_group_vos,
            'auto_scaler': auto_scaler_vo,
            'vpc': vpc_vo,
            'subnet': subnet_vo,
            'stackdriver': stackdriver_manager.get_stackdriver_info(instance.get('id', ''))
        })

        server_data.update({
            '_metadata': meta_manager.get_metadata(),
            'reference': ReferenceModel({
                'resource_id': server_data['data']['google_cloud']['self_link'],
                'external_link': f"https://console.cloud.google.com/compute/instancesDetail/zones/{zone}/instances/{server_data['name']}?project={server_data['data']['compute']['account']}"
            })
        })

        return Server(server_data, strict=False)

    def list_resources(self, params):
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

        print(f"START LIST Resources {params['zone_info']['zone']}")
        start_time = time.time()

        # try:
        secret_data = params.get('secret_data', {})

        zone_info = params.get('zone_info')
        self._set_project_id_to_zone_info(zone_info, secret_data.get('project_id', ''))

        instances = params.get('instances', [])
        global_resources = params['resources']

        resources = [self.get_instance(zone_info, instance, global_resources) for instance in instances]
        print(f'   [{params["zone_info"]["zone"]}] Finished {time.time() - start_time} Seconds')
        return resources

        # except Exception as e:
        #     print(f'[ERROR: {params["zone_info"]["zone"]}] : {e}')
        #     return []

    def list_subnets(self, params):
        # print(f"[START] LIST Subnet {params['region']}")
        return self.gcp_connector.list_subnets(region=params['region'])

    def list_forwarding_rules(self, params):
        # print(f"LIST Forwarding Rules START.. {params['region']}")
        return self.gcp_connector.list_forwarding_rules(region=params['region'])

    def list_target_pools(self, params):
        return self.gcp_connector.list_target_pools(region=params['region'])

    def list_region_url_maps(self, params):
        return self.gcp_connector.list_region_url_maps(region=params['region'])

    def list_region_backend_svcs(self, params):
        return self.gcp_connector.list_region_backend_svcs(region=params['region'])

    def list_public_images(self):

        public_images = {}
        public_image_list = [
            {'key': 'centos', 'value': 'centos-cloud'},
            {'key': 'coreos', 'value': 'coreos-cloud'},
            {'key': 'debian', 'value': 'debian-cloud'},
            {'key': 'google', 'value': 'google-containers'},
            {'key': 'opensuse', 'value': 'opensuse-cloud'},
            {'key': 'rhel', 'value': 'rhel-cloud'},
            {'key': 'suse', 'value': 'suse-cloud'},
            {'key': 'ubuntu', 'value': 'ubuntu-os-cloud'},
            {'key': 'windows', 'value': 'windows-cloud'}
        ]

        for public_image in public_image_list:
            image_list = self.gcp_connector.list_public_images(project=public_image.get('value'), orderBy='creationTimestamp desc')
            public_images[public_image.get('key')] = image_list
        return public_images

    def get_global_resources(self, secret_data, regions):
        # print("[ GET zone independent resources ]")
        if self.gcp_connector is None:
            self.set_connector(secret_data)

        # Global sources within project_id
        url_maps = self.gcp_connector.list_url_maps()
        images = self.gcp_connector.list_images()
        public_images = self.list_public_images()

        vpcs = self.gcp_connector.list_vpcs()
        fire_walls = self.gcp_connector.list_firewalls()
        backend_svcs = self.gcp_connector.list_backend_svcs()

        # Regional Sources with region parameter
        subnets = []
        forwarding_rules = []
        target_pools = []

        for region_param in self.generate_region_params(regions):
            subnets.extend(self.list_subnets(region_param))
            forwarding_rules.extend(self.list_forwarding_rules(region_param))
            target_pools.extend(self.list_target_pools(region_param))
            url_maps.extend(self.list_region_url_maps(region_param))
            backend_svcs.extend(self.list_region_backend_svcs(region_param))

        # Generate Thread Pool for collecting Subnets
        # with concurrent.futures.ThreadPoolExecutor(max_workers=NUMBER_OF_CONCURRENT) as executor:
        #     future_executors = []
        #     for mt_param in mt_params:
        #         future_executors.append(executor.submit(self.list_subnets, mt_param))
        #
        #     for future in concurrent.futures.as_completed(future_executors):
        #         for result in future.result():
        #             subnets.append(result)

        # Generate Thread Pool for collecting Forwarding Rules
        # with concurrent.futures.ThreadPoolExecutor(max_workers=NUMBER_OF_CONCURRENT) as executor:
        #     future_executors = []
        #     for mt_param in mt_params:
        #         future_executors.append(executor.submit(self.list_forwarding_rules, mt_param))
        #
        #     for future in concurrent.futures.as_completed(future_executors):
        #         for result in future.result():
        #             forwarding_rules.append(result)

        # print("====== END of zone independent resources")

        return {
            'public_images': public_images,
            'images': images,
            'vpcs': vpcs,
            'subnets': subnets,
            'fire_walls': fire_walls,
            'forwarding_rules': forwarding_rules,
            'target_pools': target_pools,
            'url_maps': url_maps,
            'backend_svcs': backend_svcs
        }


    def generate_region_params(self, regions):
        return list(map(lambda region: {'region': region['name']}, regions))

    @staticmethod
    def _set_project_id_to_zone_info(zone_info, project_id):
        if project_id != '':
            zone_info.update({'project_id': project_id})

    @staticmethod
    def get_region_from_result(result):
        REGION_INFO = {
            'asia-east1': {'name': 'Taiwan (Changhua County)', 'tags': {'latitude': '43.8345', 'longitude': '2.1972'}},
            'asia-east2': {'name': 'Hong Kong', 'tags': {'latitude': '43.8345', 'longitude': '2.1972'}},
            'asia-northeast1': {'name': 'Japan (Tokyo)', 'tags': {'latitude': '43.8345', 'longitude': '2.1972'}},
            'asia-northeast2': {'name': 'Japan (Osaka)'},
            'asia-northeast3': {'name': 'South Korea (Seoul)'},
            'asia-south1': {'name': 'India (Mumbai)'},
            'asia-southeast1': {'name': 'Singapore (Jurong West)'},
            'asia-southeast2': {'name': 'Indonesia (Jakarta)'},
            'australia-southeast1': {'name': 'Australia (Sydney)'},
            'europe-north1': {'name': 'Finland (Hamina)'},
            'europe-west1': {'name': 'Belgium (St. Ghislain)'},
            'europe-west2': {'name': 'England, UK (London)'},
            'europe-west3': {'name': 'Germany (Frankfurt)'},
            'europe-west4': {'name': 'Netherlands (Eemshaven)'},
            'europe-west6': {'name': 'Switzerland (Zürich)'},
            'northamerica-northeast1': {'name': 'Canada (Montréal, Québec)'},
            'southamerica-east1': {'name': 'Brazil (Osasco, São Paulo)'},
            'us-central1': {'name': 'USA (Council Bluffs, Iowa,)'},
            'us-east1': {'name': 'US, South Carolina (Moncks Corner)'},
            'us-east4': {'name': 'US, Northern Virginia (Ashburn)'},
            'us-west1': {'name': 'US, Oregon (The Dalles, )'},
            'us-west2': {'name': 'Los Angeles, California, USA'},
            'us-west3': {'name': 'Salt Lake City, Utah, USA'},
            'us-west4': {'name': 'Las Vegas, Nevada, USA'},
        }

        match_region_info = REGION_INFO.get(result.get('region_code'))

        if match_region_info is not None:
            region_info = match_region_info.copy()
            region_info.update({
                'region_code': result.get('region_code')
            })

            return Region(region_info, strict=False)

        return None

