# -*- coding: utf-8 -*-
# Time       : 2022/2/4 1:28
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gitstar_agent.action import GitstarAgent, Config, GitStarUser
from gitstar_agent.notify import notify
from gitstar_agent.utils import init_log

__all__ = ["GitstarAgent", "notify", "GitStarUser", "Config"]


@dataclass
class Project:
    at_dir = Path(__file__).parent
    logs = at_dir.joinpath("logs")


project = Project()

logger = init_log(
    error=project.logs.joinpath("error.log"),
    runtime=project.logs.joinpath("runtime.log"),
    serialize=project.logs.joinpath("serialize.log"),
)


async def execute():
    config = Config.from_env()

    user = GitStarUser.from_token(token=config.token)
    user.pages = config.work_pages

    if not user.is_limited():
        agent = user.spawn_agent()
        await agent.execute()

    notify(
        serialize_log_path=project.logs.joinpath("serialize.log"), servers=config.apprise_servers
    )
