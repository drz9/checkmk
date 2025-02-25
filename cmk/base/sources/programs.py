#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Dict, Optional

import cmk.utils.paths
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.translations import TranslationOptions
from cmk.utils.type_defs import HostAddress, HostName, SourceType

from cmk.core_helpers import FetcherType, ProgramFetcher
from cmk.core_helpers.agent import AgentFileCache, AgentFileCacheFactory, AgentSummarizerDefault

import cmk.base.config as config
import cmk.base.core_config as core_config
from cmk.base.config import HostConfig

from .agent import AgentSource


class ProgramSource(AgentSource):
    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        id_: str,
        main_data_source: bool,
        cmdline: str,
        stdin: Optional[str],
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
    ) -> None:
        super().__init__(
            host_config,
            ipaddress,
            source_type=SourceType.HOST,
            fetcher_type=FetcherType.PROGRAM,
            description=ProgramSource._make_description(
                cmdline,
                stdin,
            ),
            id_=id_,
            main_data_source=main_data_source,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
        )
        self.cmdline = cmdline
        self.stdin = stdin

    @staticmethod
    def special_agent(
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        main_data_source: bool = False,
        special_agent_id: str,
        params: Dict,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
    ) -> "SpecialAgentSource":
        return SpecialAgentSource(
            host_config,
            ipaddress,
            main_data_source=main_data_source,
            special_agent_id=special_agent_id,
            params=params,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
        )

    @staticmethod
    def ds(
        host_config: HostConfig,
        ipaddress: HostAddress,
        *,
        main_data_source: bool = False,
        template: str,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
    ) -> "DSProgramSource":
        return DSProgramSource(
            host_config,
            ipaddress,
            main_data_source=main_data_source,
            template=template,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
        )

    def _make_file_cache(self) -> AgentFileCache:
        return AgentFileCacheFactory(
            self.host_config.hostname,
            base_path=self.file_cache_base_path,
            simulation=self.simulation_mode,
            max_age=self.file_cache_max_age,
        ).make()

    def _make_fetcher(self) -> ProgramFetcher:
        return ProgramFetcher(
            cmdline=self.cmdline,
            stdin=self.stdin,
            is_cmc=config.is_cmc(),
        )

    def _make_summarizer(self) -> AgentSummarizerDefault:
        return AgentSummarizerDefault(self.exit_spec)

    @staticmethod
    def _make_description(cmdline, stdin):
        response = ["Program: %s" % cmdline]
        if stdin:
            response.extend(["  Program stdin:", stdin])
        return "\n".join(response)


class DSProgramSource(ProgramSource):
    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        main_data_source: bool = False,
        template: str,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
    ) -> None:
        super().__init__(
            host_config,
            ipaddress,
            id_="agent",
            main_data_source=main_data_source,
            cmdline=DSProgramSource._translate(
                template,
                host_config,
                ipaddress,
            ),
            stdin=None,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
        )

    @staticmethod
    def _translate(
        cmd: str,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
    ) -> str:
        return DSProgramSource._translate_host_macros(
            DSProgramSource._translate_legacy_macros(cmd, host_config.hostname, ipaddress),
            host_config,
        )

    @staticmethod
    def _translate_legacy_macros(
        cmd: str,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
    ) -> str:
        # Make "legacy" translation. The users should use the $...$ macros in future
        return replace_macros_in_str(
            cmd,
            {
                "<IP>": ipaddress or "",
                "<HOST>": hostname,
            },
        )

    @staticmethod
    def _translate_host_macros(cmd: str, host_config: HostConfig) -> str:
        config_cache = config.get_config_cache()
        attrs = core_config.get_host_attributes(host_config.hostname, config_cache)
        if host_config.is_cluster:
            parents_list = core_config.get_cluster_nodes_for_config(
                config_cache,
                host_config,
            )
            attrs.setdefault("alias", "cluster of %s" % ", ".join(parents_list))
            attrs.update(
                core_config.get_cluster_attributes(
                    config_cache,
                    host_config,
                    parents_list,
                )
            )

        macros = core_config.get_host_macros_from_attributes(host_config.hostname, attrs)
        return core_config.replace_macros(cmd, macros)


class SpecialAgentSource(ProgramSource):
    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        main_data_source: bool = False,
        special_agent_id: str,
        params: Dict,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
    ) -> None:
        super().__init__(
            host_config,
            ipaddress,
            id_="special_%s" % special_agent_id,
            main_data_source=main_data_source,
            cmdline=SpecialAgentSource._make_cmdline(
                host_config.hostname,
                ipaddress,
                special_agent_id,
                params,
            ),
            stdin=SpecialAgentSource._make_stdin(
                host_config.hostname,
                ipaddress,
                special_agent_id,
                params,
            ),
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
        )
        self.special_agent_id = special_agent_id
        self.special_agent_plugin_file_name = "agent_%s" % special_agent_id

    @staticmethod
    def _make_cmdline(
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        special_agent_id: str,
        params: Dict,
    ) -> str:
        path = SpecialAgentSource._make_source_path(special_agent_id)
        args = SpecialAgentSource._make_source_args(
            hostname,
            ipaddress,
            special_agent_id,
            params,
        )
        return "%s %s" % (path, args)

    @staticmethod
    def _make_stdin(
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        special_agent_id: str,
        params: Dict,
    ) -> Optional[str]:
        info_func = config.special_agent_info[special_agent_id]
        # TODO: We call a user supplied function here.
        # If this crashes during config generation, it can get quite ugly.
        # We should really wrap this and implement proper sanitation and exception handling.
        # Deal with this when modernizing the API (CMK-3812).
        agent_configuration = info_func(params, hostname, ipaddress)
        return getattr(agent_configuration, "stdin", None)

    @staticmethod
    def _make_source_path(special_agent_id: str) -> Path:
        file_name = "agent_%s" % special_agent_id
        local_path = cmk.utils.paths.local_agents_dir / "special" / file_name
        if local_path.exists():
            return local_path
        return Path(cmk.utils.paths.agents_dir) / "special" / file_name

    @staticmethod
    def _make_source_args(
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        special_agent_id: str,
        params: Dict,
    ) -> str:
        info_func = config.special_agent_info[special_agent_id]
        # TODO: CMK-3812 (see above)
        agent_configuration = info_func(params, hostname, ipaddress)
        return core_config.commandline_arguments(hostname, None, agent_configuration)
