#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
# pylint: disable=consider-using-in

from .temperature import check_temperature
from cmk.base.check_api import saveint, get_bytes_human_readable

from cmk.base.plugins.agent_based.utils.hp_proliant import MAP_TYPES_MEMORY

hp_proliant_status_map = {
    1: 'unknown',
    2: 'ok',
    3: 'degraded',
    4: 'failed',
    5: 'disabled',
}

hp_proliant_status2nagios_map = {
    'unknown': 3,
    'other': 3,
    'ok': 0,
    'degraded': 2,
    'failed': 2,
    'disabled': 1
}

hp_proliant_locale = {
    1: "other",
    2: "unknown",
    3: "system",
    4: "systemBoard",
    5: "ioBoard",
    6: "cpu",
    7: "memory",
    8: "storage",
    9: "removableMedia",
    10: "powerSupply",
    11: "ambient",
    12: "chassis",
    13: "bridgeCard",
    14: "managementBoard",
    15: "backplane",
    16: "networkSlot",
    17: "bladeSlot",
    18: "virtual",
}

#   .--da cntlr------------------------------------------------------------.
#   |                     _                    _   _                       |
#   |                  __| | __ _    ___ _ __ | |_| |_ __                  |
#   |                 / _` |/ _` |  / __| '_ \| __| | '__|                 |
#   |                | (_| | (_| | | (__| | | | |_| | |                    |
#   |                 \__,_|\__,_|  \___|_| |_|\__|_|_|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'

hp_proliant_da_cntlr_cond_map = {
    '1': (3, 'other'),
    '2': (0, 'ok'),
    '3': (1, 'degraded'),
    '4': (2, 'failed'),
}

hp_proliant_da_cntlr_role_map = {
    '1': 'other',
    '2': 'notDuplexed',
    '3': 'active',
    '4': 'backup',
}

hp_proliant_da_cntlr_state_map = {
    '1': (3, 'other'),
    '2': (0, 'ok'),
    '3': (2, 'generalFailure'),
    '4': (2, 'cableProblem'),
    '5': (2, 'poweredOff'),
}


def inventory_hp_proliant_da_cntlr(info):
    if info:
        return [(line[0], None) for line in info]


def check_hp_proliant_da_cntlr(item, params, info):
    for line in info:
        index, model, slot, cond, role, b_status, b_cond, serial = line
        if index == item:
            sum_state = 0
            output = []

            for val, label, map_ in [(cond, 'Condition', hp_proliant_da_cntlr_cond_map),
                                     (b_cond, 'Board-Condition', hp_proliant_da_cntlr_cond_map),
                                     (b_status, 'Board-Status', hp_proliant_da_cntlr_state_map)]:
                this_state = map_[val][0]
                state_txt = ''
                if this_state == 1:
                    state_txt = ' (!)'
                elif this_state == 2:
                    state_txt = ' (!!)'
                sum_state = max(sum_state, this_state)
                output.append('%s: %s%s' % (label, map_[val][1], state_txt))

            output.append('(Role: %s, Model: %s, Slot: %s, Serial: %s)' %
                          (hp_proliant_da_cntlr_role_map.get(role, 'unknown'), model, slot, serial))

            return (sum_state, ', '.join(output))
    return (3, "Controller not found in snmp data")


#.
#   .--cpu-----------------------------------------------------------------.
#   |                                                                      |
#   |                           ___ _ __  _   _                            |
#   |                          / __| '_ \| | | |                           |
#   |                         | (__| |_) | |_| |                           |
#   |                          \___| .__/ \__,_|                           |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'

hp_proliant_cpu_status_map = {1: "unknown", 2: "ok", 3: "degraded", 4: "failed", 5: "disabled"}
hp_proliant_cpu_status2nagios_map = {
    'unknown': 3,
    'ok': 0,
    'degraded': 2,
    'failed': 2,
    'disabled': 1
}


def inventory_hp_proliant_cpu(info):
    if len(info) > 0:
        return [(line[0], None) for line in info]


def check_hp_proliant_cpu(item, params, info):
    for line in info:
        if line[0] == item:
            index, slot, name, status = line
            snmp_status = hp_proliant_cpu_status_map[int(status)]
            status = hp_proliant_cpu_status2nagios_map[snmp_status]

            return (status,
                    'CPU%s "%s" in slot %s is in state "%s"' % (index, name, slot, snmp_status))
    return (3, "item not found in snmp data")


#.
#   .--fans----------------------------------------------------------------.
#   |                          __                                          |
#   |                         / _| __ _ _ __  ___                          |
#   |                        | |_ / _` | '_ \/ __|                         |
#   |                        |  _| (_| | | | \__ \                         |
#   |                        |_|  \__,_|_| |_|___/                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'

hp_proliant_fans_status_map = {1: 'other', 2: 'ok', 3: 'degraded', 4: 'failed'}
hp_proliant_speed_map = {1: 'other', 2: 'normal', 3: 'high'}
hp_proliant_fans_locale = {
    1: "other",
    2: "unknown",
    3: "system",
    4: "systemBoard",
    5: "ioBoard",
    6: "cpu",
    7: "memory",
    8: "storage",
    9: "removableMedia",
    10: "powerSupply",
    11: "ambient",
    12: "chassis",
    13: "bridgeCard",
}


def inventory_hp_proliant_fans(info):
    if len(info) > 0:
        items = []
        for line in [l for l in info if l[2] == '3']:
            label = 'other'
            if int(line[1]) in hp_proliant_fans_locale:
                label = hp_proliant_fans_locale[int(line[1])]
            items.append(("%s (%s)" % (line[0], label), None))
        return items


def check_hp_proliant_fans(item, params, info):
    for line in info:
        label = 'other'
        if len(line) > 1 and int(line[1]) in hp_proliant_fans_locale:
            label = hp_proliant_fans_locale[int(line[1])]

        if "%s (%s)" % (line[0], label) == item:
            index, _name, _present, speed, status, currentSpeed = line
            snmp_status = hp_proliant_fans_status_map[int(status)]
            status = hp_proliant_status2nagios_map[snmp_status]

            detailOutput = ''
            perfdata = []
            if currentSpeed != '':
                detailOutput = ', RPM: %s' % currentSpeed
                perfdata = [('temp', int(currentSpeed))]

            return (status, 'FAN Sensor %s "%s", Speed is %s, State is %s%s' %
                    (index, label, hp_proliant_speed_map[int(speed)], snmp_status, detailOutput),
                    perfdata)
    return (3, "item not found in snmp data")


#.
#   .--mem-----------------------------------------------------------------.
#   |                                                                      |
#   |                      _ __ ___   ___ _ __ ___                         |
#   |                     | '_ ` _ \ / _ \ '_ ` _ \                        |
#   |                     | | | | | |  __/ | | | | |                       |
#   |                     |_| |_| |_|\___|_| |_| |_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

hp_proliant_mem_status_map = {
    1: "other",
    2: "notPresent",
    3: "present",
    4: "good",
    5: "add",
    6: "upgrade",
    7: "missing",
    8: "doesNotMatch",
    9: "notSupported",
    10: "badConfig",
    11: "degraded",
    12: "spare",
    13: "partial",
}

hp_proliant_mem_status2nagios_map = {
    'n/a': 3,
    'other': 3,
    'notPresent': 3,
    'present': 1,
    'good': 0,
    'add': 1,
    'upgrade': 1,
    'missing': 2,
    'doesNotMatch': 2,
    'notSupported': 2,
    'badConfig': 2,
    'degraded': 2,
    'spare': 0,
    'partial': 1,
}

hp_proliant_mem_condition_status2nagios_map = {
    'other': 3,
    'ok': 0,
    'degraded': 2,
    'failed': 2,
    'degradedModuleIndexUnknown': 3
}

hp_proliant_mem_condition_map = {
    0: 'n/a',
    1: 'other',
    2: 'ok',
    3: 'degraded',
    4: 'degradedModuleIndexUnknown',
}


def inventory_hp_proliant_mem(info):
    if len(info) > 0:
        return [ (line[1], None) for line in info if line[2].isdigit() and \
                 int(line[2]) > 0 and int(line[4]) != 2 ]


def check_hp_proliant_mem(item, params, info):
    for line in info:
        if line[1] == item:
            # Note: mgmt_hp_proliant_mem provides exact 6 values;
            # hp_proliant provides 10 values because related inventory plugin
            # needs the last 4.
            board_index, module_index, module_size, module_type, \
            module_status, module_condition = line[:6]

            yield 0, f"Board: {board_index}"
            yield 0, f"Num: {module_index}"

            type_ = MAP_TYPES_MEMORY.get(module_type, f"unknown({module_type})")
            yield 0, f"Type: {type_}"

            module_size = get_bytes_human_readable(int(module_size) * 1024)
            yield 0, f"Size: {module_size}"

            snmp_status = 'n/a'
            if int(module_status) in hp_proliant_mem_status_map:
                snmp_status = hp_proliant_mem_status_map[int(module_status)]

            status_output = f"Status: {snmp_status}"
            yield hp_proliant_mem_status2nagios_map[snmp_status], status_output

            condition = 'n/a'
            if saveint(module_condition) in hp_proliant_mem_condition_map:
                condition = hp_proliant_mem_condition_map[saveint(module_condition)]
            condition_output = f"Condition: {condition}"
            yield hp_proliant_mem_condition_status2nagios_map[condition], condition_output


#.
#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def format_hp_proliant_name(line):
    return "%s (%s)" % (line[0], hp_proliant_locale[int(line[1])])


def inventory_hp_proliant_temp(info):
    for line in info:
        if line[-1] != "1":
            # other(1): Temperature could not be determined
            yield format_hp_proliant_name(line), {}


def check_hp_proliant_temp(item, params, info):
    for line in info:
        if format_hp_proliant_name(line) == item:
            value, threshold, status = line[2:]

            # This case means no threshold available and
            # the devices' web interface displays "N/A"
            if threshold == "-99" or threshold == "0":
                devlevels = None
            else:
                threshold = float(threshold)
                devlevels = (threshold, threshold)

            snmp_status = hp_proliant_status_map[int(status)]

            return check_temperature(float(value),
                                     params,
                                     "hp_proliant_temp_%s" % item,
                                     dev_levels=devlevels,
                                     dev_status=hp_proliant_status2nagios_map[snmp_status],
                                     dev_status_name="Unit: %s" % snmp_status)
    return 3, "item not found in snmp data"


#.
#   .--scan function-------------------------------------------------------.
#   |                           __                  _   _                  |
#   |    ___  ___ __ _ _ __    / _|_   _ _ __   ___| |_(_) ___  _ __       |
#   |   / __|/ __/ _` | '_ \  | |_| | | | '_ \ / __| __| |/ _ \| '_ \      |
#   |   \__ \ (_| (_| | | | | |  _| |_| | | | | (__| |_| | (_) | | | |     |
#   |   |___/\___\__,_|_| |_| |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def proliant_general_scan_function(oid):
    return ("8072.3.2.10" in oid(".1.3.6.1.2.1.1.2.0") or
            "232.9.4.10" in oid(".1.3.6.1.2.1.1.2.0") or
            (".1.3.6.1.4.1.311.1.1.3.1.2" in oid(".1.3.6.1.2.1.1.2.0") and
             oid(".1.3.6.1.4.1.232.11.1.3.0")))


def hp_proliant_scan_function(oid):
    return ("proliant" in oid(".1.3.6.1.4.1.232.2.2.4.2.0", "").lower() or
            "storeeasy" in oid(".1.3.6.1.4.1.232.2.2.4.2.0", "").lower())


#.
