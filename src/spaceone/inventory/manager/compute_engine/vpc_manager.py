from spaceone.core.manager import BaseManager
from spaceone.inventory.model.vpc import VPC
from spaceone.inventory.model.subnet import Subnet


class VPCManager(BaseManager):

    def __init__(self):
        pass

    def get_vpc_info(self, instance, vpcs, subnets):
        '''
        vpc_data = {
            "vpc_id": "",
            "vpc_name": "",
            "description": "",
            "self_link": ""
        }

        subnet_data = {
            "subnet_id": "",
            "subnet_name": "",
            "self_link": "",
            "gateway_address": "",
            "vpc" : VPC
            "cidr": ""
        }
        '''

        vpc_data = {}
        subnet_data = {}
        matched_subnet = self._get_matching_subnet(instance, subnets)
        matched_vpc = self.get_matching_vpc(matched_subnet, vpcs)

        if matched_vpc is not None:
            vpc_data.update({
                'vpc_id': matched_vpc.get('id', ''),
                'vpc_name': matched_vpc.get('name', ''),
                'description': matched_vpc.get('description', ''),
                'self_link': matched_vpc.get('selfLink', ''),
            })

        if matched_subnet is not None:
            subnet_data.update({
                'subnet_id': matched_subnet.get('id', ''),
                'cidr': matched_subnet.get('ipCidrRange', ''),
                'subnet_name': matched_subnet.get('name', ''),
                'gateway_address': matched_subnet.get('gatewayAddress', ''),
                'vpc': vpc_data,
                'self_link': matched_subnet.get('selfLink', '')
            })

        return VPC(vpc_data, strict=False), Subnet(subnet_data, strict=False)

    def get_matching_vpc(self, matched_subnet, vpcs):
        matching_vpc = None
        network = matched_subnet.get('selfLink', None)
        if network is not None:
            for vpc in vpcs:
                if network in vpc.get('subnetworks', []):
                    matching_vpc = vpc
                    break

        return matching_vpc

    @staticmethod
    def _get_matching_subnet(instance, subnets):
        subnet_data = None
        subnet_work_links =[]
        network_interfaces = instance.get('networkInterfaces', [])
        for network_interface in network_interfaces:
            subnet_work = network_interface.get('subnetwork', '')
            if subnet_work != '':
                subnet_work_links.append(subnet_work)

        for subnet in subnets:
            if subnet.get('selfLink', '') in subnet_work_links:
                subnet_data = subnet
                break

        return subnet_data

    @staticmethod
    def _get_network_str(subnet):
        network = subnet.get('network', '')
        return network[network.find('/projects/'):len(network)] if network != '' else None