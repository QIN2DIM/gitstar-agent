# -*- coding: utf-8 -*-
# Time       : 2023/9/25 17:15
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
from __future__ import annotations

import json
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import apprise
from loguru import logger


def load_latest_log(path: Path, minutes: float = 45.0) -> List[str] | None:
    history = []
    with open(path, "r", encoding="utf8") as file:
        for line in file:
            data = json.loads(line)
            t = datetime.fromtimestamp(data["record"]["time"]["timestamp"])
            if datetime.now() - t < timedelta(minutes=minutes):
                history.append(data["text"])
    return history


def send_message(apprise_servers: List[str] | None = None, latest_log: List[str] | None = None):
    apprise_servers = apprise_servers or []

    _inline_textbox = ["运行日志".center(20, "-")]
    if latest_log and isinstance(latest_log, list):
        _inline_textbox += latest_log

    body = "\n".join(_inline_textbox)
    title = "GitStarReflector 运行报告"

    apobj = apprise.Apprise()
    apobj.add(apprise_servers)
    apobj.notify(body=body, title=title, body_format=apprise.common.NotifyFormat.MARKDOWN)
    logger.success("消息推送完毕", motive="NOTIFY")


def notify(serialize_log_path: Path, servers: List[str]):
    with suppress(Exception):
        latest_events = load_latest_log(path=serialize_log_path, minutes=45.0)
        send_message(apprise_servers=servers, latest_log=latest_events)
