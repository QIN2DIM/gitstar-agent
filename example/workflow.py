# -*- coding: utf-8 -*-
# Time       : 2023/9/25 18:08
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
import asyncio
import os

import gitstar_agent

os.environ["GITSTAR_TOKEN"] = os.getenv("GITSTAR_TOKEN", "")
os.environ["APPRISE_TELEGRAM"] = os.getenv("APPRISE_TELEGRAM", "")

asyncio.run(gitstar_agent.execute())
