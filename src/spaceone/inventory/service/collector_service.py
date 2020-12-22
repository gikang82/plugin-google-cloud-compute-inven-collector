import time
import logging
from spaceone.core.service import *
from spaceone.inventory.manager.collector_manager import CollectorManager

_LOGGER = logging.getLogger(__name__)

FILTER_FORMAT = [
    {
        'key': 'project_id',
        'name': 'Project ID',
        'type': 'str',
        'resource_type': 'SERVER',
        'search_key': 'identity.Project.project_id',
        'change_rules': [{
            'resource_key': 'data.compute.instance_id',
            'change_key': 'instance_id'
        }, {
            'resource_key': 'data.compute.region',
            'change_key': 'region_name'
        }]
    }, {
        'key': 'collection_info.service_accounts',
        'name': 'Service Account ID',
        'type': 'str',
        'resource_type': 'SERVER',
        'search_key': 'identity.ServiceAccount.service_account_id',
        'change_rules': [{
            'resource_key': 'data.compute.instance_id',
            'change_key': 'instance_id'
        }, {
            'resource_key': 'data.compute.region',
            'change_key': 'region_name'
        }]
    }, {
        'key': 'server_id',
        'name': 'Server ID',
        'type': 'list',
        'resource_type': 'SERVER',
        'search_key': 'inventory.Server.server_id',
        'change_rules': [{
            'resource_key': 'data.compute.instance_id',
            'change_key': 'instance_id'
        }, {
            'resource_key': 'data.compute.region',
            'change_key': 'region_name'
        }]
    }, {
        'key': 'instance_id',
        'name': 'Instance ID',
        'type': 'list',
        'resource_type': 'CUSTOM'
    },
    {
        'key': 'region_name',
        'name': 'Region',
        'type': 'list',
        'resource_type': 'CUSTOM'
    }
]

SUPPORTED_RESOURCE_TYPE = ['inventory.Server', 'inventory.Region']
NUMBER_OF_CONCURRENT = 20


@authentication_handler
class CollectorService(BaseService):
    def __init__(self, metadata):
        super().__init__(metadata)
        self.collector_manager: CollectorManager = self.locator.get_manager('CollectorManager')

    @transaction
    @check_required(['options'])
    def init(self, params):
        """ init plugin by options
        """
        capability = {
            'filter_format': FILTER_FORMAT,
            'supported_resource_type': SUPPORTED_RESOURCE_TYPE
            }
        return {'metadata': capability}

    @transaction
    @check_required(['options', 'secret_data'])
    def verify(self, params):
        """ verify options capability
        Args:
            params
              - options
              - secret_data: may be empty dictionary

        Returns:

        Raises:
             ERROR_VERIFY_FAILED:
        """
        manager = self.locator.get_manager('CollectorManager')
        secret_data = params['secret_data']
        options = params.get('options', {})
        active = manager.verify(options, secret_data)
        return {}

    @transaction
    @check_required(['options', 'secret_data', 'filter'])
    def list_resources(self, params):
        """ Get quick list of resources
        Args:
            params:
                - options
                - secret_data
                - filter

        Returns: list of resources
        """

        start_time = time.time()
        all_regions = self.collector_manager.list_regions(params['secret_data'])

        resource_regions = []
        collected_region_code = []

        server_resource_format = {'resource_type': 'inventory.Server',
                                  'match_rules': {'1': ['reference.resource_id']}}
        region_resource_format = {'resource_type': 'inventory.Region',
                                  'match_rules': {'1': ['region_code', 'provider']}}
        cloud_service_type_resource_format = {'resource_type': 'inventory.CloudServiceType',
                                              'match_rules': {'1': ['name', 'group', 'provider']}}

        for cloud_service_type in self.collector_manager.list_cloud_service_types():
            yield cloud_service_type, cloud_service_type_resource_format

        # parameter setting for multi threading
        mt_params = self.set_params_for_zones(params, all_regions)

        # TODO: parallel collecting instances through multi threading
        target_params = []
        is_instance = False
        for params in mt_params:
            _instances = self.collector_manager.list_instances_only(params)

            if _instances:
                params.update({
                    'instances':  _instances
                })

                target_params.append(params)
                is_instance = True

        if is_instance:
            global_resources = self.collector_manager.get_global_resources(params['secret_data'], all_regions)

            resources = []
            for params in target_params:
                params.update({
                    'resources': global_resources
                })

                resources.extend(self.collector_manager.list_resources(params))

            for resource in resources:
                collected_region = self.collector_manager.get_region_from_result(resource)

                if collected_region and collected_region.region_code not in collected_region_code:
                    resource_regions.append(collected_region)
                    collected_region_code.append(collected_region.region_code)

                yield resource, server_resource_format

            for resource_region in resource_regions:
                yield resource_region, region_resource_format

        print(f'############## TOTAL FINISHED {time.time() - start_time} Sec ##################')

    def set_params_for_zones(self, params, all_regions):
        # print("[ SET Params for ZONES ]")
        params_for_zones = []

        (query, instance_ids, filter_region_name) = self._check_query(params['filter'])
        target_zones = self.get_all_zones(params.get('secret_data', ''), filter_region_name, all_regions)

        for target_zone in target_zones:
            params_for_zones.append({
                'zone_info': target_zone,
                'query': query,
                'secret_data': params['secret_data'],
                'instance_ids': instance_ids,
            })

        return params_for_zones

    def get_all_zones(self, secret_data, filter_region_name, all_regions):
        """ Find all zone name
        Args:
            secret_data: secret data
            filter_region_name (list): list of region_name if wanted

        Returns: list of zones
        """
        match_zones = []

        if 'region_name' in secret_data:
            match_zones = self.match_zones_from_region(all_regions, secret_data['region_name'])

        if filter_region_name:
            for _region in filter_region_name:
                match_zones = self.match_zones_from_region(all_regions, _region)

        if not match_zones:
            # print(f'region count = {len(all_regions)}')
            for region in all_regions:
                for zone in region.get('zones', []):
                    match_zones.append({'zone': zone.split('/')[-1], 'region': region['name']})

        return match_zones

    @staticmethod
    def match_zones_from_region(all_regions, region):
        match_zones = []

        for _region in all_regions:
            if _region['name'] == region:
                for _zone in _region.get('zones', []):
                    match_zones.append({'region': region, 'zone': _zone.split('/')[-1]})

        return match_zones

    @staticmethod
    def get_full_resource_name(project_id, resource_type, resource):
        return f'https://www.googleapis.com/compute/v1/projects/{project_id}/{resource_type}/{resource}'

    @staticmethod
    def _check_query(query):
        """
        Args:
            query (dict): example
                  {
                      'instance_id': ['i-123', 'i-2222', ...]
                      'instance_type': 'm4.xlarge',
                      'region_name': ['aaaa']
                  }
        If there is regiona_name in query, this indicates searching only these regions
        """

        instance_ids = []
        filters = []
        region_name = []
        for key, value in query.items():
            if key == 'instance_id' and isinstance(value, list):
                instance_ids = value

            elif key == 'region_name' and isinstance(value, list):
                region_name.extend(value)

            else:
                if not isinstance(value, list):
                    value = [value]

                if value:
                    filters.append({'Name': key, 'Values': value})

        return filters, instance_ids, region_name
