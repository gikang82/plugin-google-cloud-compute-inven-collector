from spaceone.core.manager import BaseManager
from spaceone.inventory.model.stackdriver import StackDriver, StackDriverFilters


class StackDriverManager(BaseManager):

    def __init__(self):
        pass

    def get_stackdriver_info(self, instance_name):
        '''
        cloudwatch_data = {
                       'type': 'gce_instance',
                       'filters': [{
                           'key': 'resource.labels.instance_id',
                           'value': '1873022307818018997'
                       }]
                   }
        '''

        stackdriver_data = {
            'type': 'gce_instance',
            'filters': self.get_filters(instance_name)
        }

        return StackDriver(stackdriver_data, strict=False)

    @staticmethod
    def get_filters(instance_name):
        '''
        "filters": [
            {
                "key": "resource.labels.instance_id",
                "value": instacne_name
            }
        ]
        '''

        filter = {
            'key': 'resource.labels.instance_name',
            'value': instance_name
        }

        return [StackDriverFilters(filter, strict=False)]