# -*- coding: utf-8 -*-
# Time       : 2023/7/1 16:22
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
from __future__ import annotations

import asyncio
import os
import sys
from asyncio import create_task
from dataclasses import dataclass, field
from typing import Dict
from typing import List, Any

import httpx
from httpx import AsyncClient
from loguru import logger

from gitstar_agent.utils import from_dict_to_model


@dataclass(frozen=True)
class Config:
    """系统运行配置"""

    token: str = ""
    """
    Documentation: https://github.com/settings/tokens/new
    - tips: Need to enable <repo> and <user> permission
    """

    apprise_servers: List[str] = field(default_factory=list)
    """
    Documentation: https://github.com/caronc/apprise
    - Default: []
    """

    work_pages: int = 1
    """
    Task Queue Length
    - Default: 1
    - limit: work_pages ∈ [1, 7]
    """

    @classmethod
    def from_env(cls):
        apprise_servers = [os.environ[k] for k in os.environ if k.startswith("APPRISE_")]
        gitstar_token = os.getenv("GITSTAR_TOKEN", "")

        if not gitstar_token:
            logger.error("📛 GITSTAR_TOKEN 为空或填写错误")
            sys.exit()
        if not apprise_servers:
            logger.warning("🎃 APPRISE_SERVER 为空或填写错误，无法启动消息通知组件")

        return cls(token=gitstar_token, apprise_servers=apprise_servers)


@dataclass
class Repository:
    full_name: str


@dataclass
class GitStarUser:
    token: str

    _pages: int = field(default=int)

    def __post_init__(self):
        self._pages = self._pages or 1

    @classmethod
    def from_token(cls, token: str):
        return cls(token=token)

    @property
    def pages(self):
        return self._pages

    @pages.setter
    def pages(self, new_pages):
        self._pages = new_pages

    @property
    def headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.67",
            "Host": "gitstar.com.cn",
            "Origin": "https://gitstar.com.cn",
            "Referer": "https://gitstar.com.cn",
            "Authorization": f"token {self.token}",
        }

    def is_limited(self) -> bool | None:
        """检查账号是否被限制"""
        url = "https://gitstar.com.cn/api/check_limit"

        try:
            resp = httpx.get(url, headers=self.headers)
            datas = resp.json()
            limit = datas["result"]["limit"]
            logger.info("账号可访问状态解析成功", response=datas)
            if limit:
                logger.warning("账号访问受限，任务即将退出", limit=limit)
                return True
            return False
        except Exception as err:
            logger.warning("账号可访问状态解析失败，即将试运行样本任务", err=err)

    def spawn_agent(self):
        return GitstarAgent(user=self)


class GitstarAgent:
    def __init__(self, user: GitStarUser):
        self.user = user

        self.lock = asyncio.Lock()
        self.task_queue = asyncio.Queue()

    async def get_repos(self, page: int, client: AsyncClient):
        """生产链接"""
        url = "https://gitstar.com.cn/api/repos"
        payload = {"page": page, "type": 1}
        try:
            res = await client.post(url, json=payload)
            datas = res.json()
            repos: List[Dict[str, Any]] = datas["result"]["datas"]
            for repo_ in repos:
                self.task_queue.put_nowait(from_dict_to_model(Repository, repo_))
            logger.info("🔗获取分页数据", page=page, response=datas)
        except Exception as err:
            logger.exception(err)
            logger.error("📛分页获取失败", missed_page=page, err=str(err))

    async def upload_star(self, repo: Repository, client: AsyncClient):
        """消费链接"""
        url = "https://gitstar.com.cn/api/upload_star"
        payload = {"full_name": repo.full_name, "type": 1}
        try:
            res = await client.post(url, json=payload)
            status = res.json()
            # Account access is restricted and all to-do tasks will pop up immediately
            if not status.get("result") and status.get("code", "").startswith("4"):
                async with self.lock:
                    while not self.task_queue.empty():
                        self.task_queue.get_nowait()
                    raise RuntimeError(f"账号受限 - cause={status.get('msg')}")
            logger.success(
                f"🌟点赞成功", remain=self.task_queue.qsize(), full_name=repo.full_name, status=status
            )
        except RuntimeError as err:
            logger.error("📛点赞失败", full_name=repo.full_name, err=str(err))
        except Exception as err:
            logger.exception(err)

    async def _adapter(self, client: AsyncClient):
        while not self.task_queue.empty():
            context = self.task_queue.get_nowait()
            if isinstance(context, int):
                await self.get_repos(page=context, client=client)
            else:
                await self.upload_star(repo=context, client=client)
            self.task_queue.task_done()

    async def execute(self):
        if task_ids := list(range(1, self.user.pages + 1)):
            for task_id in task_ids:
                self.task_queue.put_nowait(task_id)
        max_queue_size = self.task_queue.qsize()

        async with AsyncClient(headers=self.user.headers) as client:
            task_list = [create_task(self._adapter(client)) for _ in range(min(max_queue_size, 32))]
            await asyncio.wait(task_list)
