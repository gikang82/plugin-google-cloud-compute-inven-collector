import time
import logging
import json

from spaceone.core.service import *
from spaceone.inventory.manager.collector_manager import CollectorManager
from spaceone.inventory.model.resource import CloudServiceTypeResourceResponse, RegionResourceResponse, ErrorResourceResponse

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

SUPPORTED_RESOURCE_TYPE = ['inventory.Server', 'inventory.Region', 'inventory.ErrorResource']
NUMBER_OF_CONCURRENT = 20
SUPPORTED_FEATURES = ['garbage_collection']
SUPPORTED_SCHEDULES = ['hours']

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
            'supported_resource_type': SUPPORTED_RESOURCE_TYPE,
            'supported_features': SUPPORTED_FEATURES,
            'supported_schedules': SUPPORTED_SCHEDULES
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

        _LOGGER.debug(f'############## Start Collecting Sequence ##################')
        resource_regions = []
        collected_region_code = []

        # Returns cloud service type
        try:
            for cloud_service_type in self.collector_manager.list_cloud_service_types():
                yield CloudServiceTypeResourceResponse({
                    'resource': cloud_service_type
                })
        except Exception as e:
            _LOGGER.error(f'[list_resources] yield cloud service type => {e}', exc_info=True)
            yield self.generate_error_response(e, "inventory.CloudServiceType")

        # ServerResourceResponse/ErrorResourceResponse type will return
        try:
            compute_vm_resources = self.collector_manager.list_resources(params)
            _LOGGER.debug(f'[list_resources] compute_vm_resources => {compute_vm_resources}')
            # Returns cloud resources
            for resource in compute_vm_resources:
                # Check if resource type is ServerResourceResponse
                if resource.resource_type == 'inventory.Server':
                    collected_region = self.collector_manager.get_region_from_result(resource)
                    if collected_region and collected_region.region_code not in collected_region_code:
                        resource_regions.append(collected_region)
                        collected_region_code.append(collected_region.region_code)

                yield resource

        except Exception as e:
            _LOGGER.error(f'[list_resources] get collected_region => {e}', exc_info=True)
            yield self.generate_error_response(e, "inventory.Region")

        # Returns cloud region type
        try:
            for resource_region in resource_regions:
                yield RegionResourceResponse({
                    'resource': resource_region
                })
        except Exception as e:
            _LOGGER.error(f'[list_resources] => yield region {e}', exc_info=True)
            yield self.generate_error_response(e, "inventory.Region")

        _LOGGER.debug(f'############## TOTAL FINISHED {time.time() - start_time} Sec ##################')

    def set_params_for_zones(self, params, all_regions):
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
            for region in all_regions:
                for zone in region.get('zones', []):
                    match_zones.append({'zone': zone.split('/')[-1], 'region': region['name']})

        return match_zones

    @staticmethod
    def generate_error_response(e, resource_type):
        if type(e) is dict:
            error_resource_response = ErrorResourceResponse({
                'message': json.dumps(e),
                'resource': {'resource_type': resource_type}
            })
        else:
            error_resource_response = ErrorResourceResponse({
                'message': str(e),
                'resource': {'resource_type': resource_type}
            })

        return error_resource_response

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
