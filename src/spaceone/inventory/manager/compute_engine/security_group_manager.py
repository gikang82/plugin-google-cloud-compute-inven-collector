from itertools import product
import logging

from spaceone.core.manager import BaseManager
from spaceone.inventory.model.security_group import SecurityGroup

_LOGGER = logging.getLogger(__name__)


class SecurityGroupManager(BaseManager):

    def __init__(self):
        pass

    def get_security_group_rules_info(self, instance, firewalls):
        '''
        "data.security_group_rules" = [
                    {
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
                        direction = StringType(choices=("inboud", "outbound"))
                        port = StringType(serialize_when_none=False)
                        action = StringType(choices=('allow', 'deny'))
                    }
                ],
        '''

        sg_rules = []
        inst_svc_accounts = self._get_svc_account_infos(instance)
        inst_network_info = self._get_instance_network_info(instance)

        for firewall in firewalls:
            if firewall.get('network', '') in inst_network_info:
                for fire_wall_target_tag in firewall.get('targetTags', []):
                    if fire_wall_target_tag in self._get_tag_item_list(instance) \
                            or 'allow-all-instance' in fire_wall_target_tag:
                        protocol_ports_list = self.get_allowed_or_denied_info(firewall)
                        # skipping, seems to have bug protocol_ports_list => [{'protocol': ['all'], 'port': '0-65535'}]
                        #self.append_security_group(protocol_ports_list, firewall, sg_rules)

            elif "targetServiceAccounts" in firewall:
                for firewall_target_service_account in firewall.get('targetServiceAccounts', []):
                    if firewall_target_service_account in inst_svc_accounts:
                        protocol_ports_list = self.get_allowed_or_denied_info(firewall)
                        self.append_security_group(protocol_ports_list, firewall, sg_rules)

            elif "targetTags" not in firewall and "targetServiceAccounts" not in firewall:
                pass

        return sg_rules

    def append_security_group(self, protocol_ports_list, firewall, sg_rules):
        try:
            for protocol_ports in protocol_ports_list:
                sg_dict = self._get_sg_dict(protocol_ports, firewall)
                if 'port' in protocol_ports:
                    sg_dict.update({'port': protocol_ports.get('port')})

                sg_list = (dict(zip(sg_dict, x)) for x in product(*sg_dict.values()))

                for sg_single in sg_list:
                    min_port, max_port = self._port_min_and_max(sg_single)

                    if min_port is not None:
                        sg_single.update({'port_range_min': min_port})
                    if max_port is not None:
                        sg_single.update({'port_range_max': max_port})

                    remote_cidr = sg_single.get('remote_cidr', '')
                    remote_id = sg_single.get('remote_id', '')

                    sg_single.update({
                        'priority': firewall.get('priority', 0),
                        'direction': 'inbound' if 'INGRESS' == firewall.get('direction', '') else 'outbound',
                        'description': firewall.get('description', ''),
                        'action': 'allow' if 'allowed' in firewall else 'deny',
                        'security_group_name': firewall.get('name', ''),
                        'security_group_id': firewall.get('id', ''),
                        'remote': remote_cidr if remote_cidr != '' else remote_id
                    })

                    sg_rules.append(SecurityGroup(sg_single, strict=False))

        except Exception as e:
            _LOGGER.error(f'[append_security_group] {e}', exc_info=True)

    def get_allowed_or_denied_info(self, firewall):
        if 'allowed' in firewall:
            return self._get_proto_in_format('allowed', firewall)
        else:
            return self._get_proto_in_format('denied', firewall)

    @staticmethod
    def _get_sg_dict(protocol_ports, firewall):
        remote_cidr = firewall.get('sourceRanges', [])
        remote_id = firewall.get('sourceTags', [])
        sg_dict = {'protocol': protocol_ports.get('protocol')}

        if len(remote_cidr) > 0:
            sg_dict.update({'remote_cidr': remote_cidr})
        if len(remote_id) > 0:
            sg_dict.update({'remote_id': remote_id})

        return sg_dict


    @staticmethod
    def _port_min_and_max(sg_single):
        port = sg_single.get('port', None)
        if port is not None:
            striped_port = port.replace(' ', '')
            port_split = striped_port.split('-')
            if len(port_split) > 1:
                return int(port_split[0]), int(port_split[1])
            else:
                return int(port_split[0]), int(port_split[0])
        else:
            return None, None

    @staticmethod
    def _get_instance_network_info(instance):
        inst_network_interfaces = instance.get('networkInterfaces', [])
        return [d.get('network') for d in inst_network_interfaces if d.get('network', '') != '']

    @staticmethod
    def _get_svc_account_infos(instance):
        svc_accounts = instance.get('serviceAccounts', [])
        return [d.get('email') for d in svc_accounts if d.get('email', '') != '']

    @staticmethod
    def _get_tag_item_list(instance):
        inst_tags = instance.get('tags', {})
        return inst_tags.get('items', [])

    @staticmethod
    def _get_proto_in_format(flag, firewall):
        protocol_port_list = []
        for proto in firewall.get(flag, []):
            protocol = proto.get('IPProtocol', [])
            ports = proto.get('ports', None)
            item = {'protocol': protocol if isinstance(protocol, list) else [protocol]}
            if protocol == 'all':
                item.update({'port': '0-65535'})
            if ports is not None:
                item.update({'port': ports})
            protocol_port_list.append(item)
        return protocol_port_list
