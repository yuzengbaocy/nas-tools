import re

from utils.functions import singleton
from utils.sqls import get_config_filter_rule, get_config_filter_group


@singleton
class FilterRule:

    _groups = []
    _rules = []

    def __init__(self):
        self.init_config()

    def init_config(self):
        self._groups = get_config_filter_group()
        self._rules = get_config_filter_rule()

    def get_rule_groups(self, groupid=None, default=False):
        """
        获取所有规则组
        """
        ret_groups = []
        for group in self._groups:
            group_info = {
                "id": group[0],
                "name": group[1],
                "default": group[2],
                "note": group[3]
            }
            if groupid and int(groupid) == int(group[0])\
                    or default and group[2] == "Y":
                return group_info
            ret_groups.append(group_info)
        if groupid or default:
            return {}
        return ret_groups

    def get_rule_infos(self):
        """
        获取所有的规则组及组内的规则
        """
        groups = self.get_rule_groups()
        for group in groups:
            group['rules'] = self.get_rules(group.get("id"))
        return groups

    def get_rules(self, groupid, ruleid=None):
        """
        获取过滤规则
        """
        if not groupid:
            return []
        ret_rules = []
        for rule in self._rules:
            rule_info = {
                "id": rule[0],
                "group": rule[1],
                "name": rule[2],
                "pri": rule[3],
                "include": rule[4].split("\n") if rule[4] else [],
                "exclude": rule[5].split("\n") if rule[5] else [],
                "size": rule[6],
                "note": rule[7]
            }
            if int(rule[1]) == int(groupid) \
                    and (not ruleid or int(ruleid) == rule[0]):
                ret_rules.append(rule_info)
        if ruleid:
            return ret_rules[0] if ret_rules else {}
        return ret_rules

    def check_rules(self, title, torrent_size, subtitle=None, rolegroup=None):
        """
        检查种子是否匹配站点过滤规则：排除规则、包含规则，优先规则
        :param title: 种子标题
        :param subtitle: 种子副标题
        :param torrent_size: 种子大小
        :param rolegroup: 规则组ID
        :return: 是否匹配，匹配的优先值，值越大越优先
        """
        if not title:
            return False, 0
        if subtitle:
            title = "%s %s" % (title, subtitle)
        if not rolegroup:
            rolegroup = self.get_rule_groups(default=True)
            if not rolegroup:
                return True, 0
        else:
            rolegroup = self.get_rule_groups(groupid=rolegroup)
        filters = self.get_rules(groupid=rolegroup.get("id"))
        # 命中优先级
        order_seq = 100
        # 当前规则组是否命中
        group_match = True
        for filter_info in filters:
            # 当前规则是否命中
            rule_match = True
            # 命中规则的序号
            order_seq -= 1
            # 必须包括的项
            includes = filter_info.get('include')
            if includes and rule_match:
                include_flag = True
                for include in includes:
                    if not include:
                        continue
                    if not re.search(r'%s' % include.strip(), title, re.IGNORECASE):
                        include_flag = False
                        break
                if not include_flag:
                    rule_match = False

            # 不能包含的项
            excludes = filter_info.get('exclude')
            if excludes and rule_match:
                exclude_flag = False
                exclude_count = 0
                for exclude in excludes:
                    if not exclude:
                        continue
                    exclude_count += 1
                    if not re.search(r'%s' % exclude.strip(), title, re.IGNORECASE):
                        exclude_flag = True
                if exclude_count > 0 and not exclude_flag:
                    rule_match = False
            # 大小
            sizes = filter_info.get('size')
            if sizes and rule_match:
                if sizes.find(',') != -1:
                    sizes = sizes.split(',')
                    if sizes[0].isdigit():
                        begin_size = int(sizes[0].strip())
                    else:
                        begin_size = 0
                    if sizes[1].isdigit():
                        end_size = int(sizes[1].strip())
                    else:
                        end_size = 0
                else:
                    begin_size = 0
                    if sizes.isdigit():
                        end_size = int(sizes.strip())
                    else:
                        end_size = 0
                if not begin_size * 1024 ** 3 <= int(torrent_size) <= end_size * 1024 ** 3:
                    rule_match = False

            if rule_match:
                return True, order_seq
            else:
                group_match = False
        if not group_match:
            return False, 0
        return True, order_seq