#   Copyright 2014-2015 PUNCH Cyber Analytics Group
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
Overview
========

Scan content with ClamAV

"""

import time
import argparse
import threading

from stoq.plugins import WorkerPlugin
from stoq.helpers import StoqConfigParser
from stoq.exceptions import StoqPluginException
from stoq import Error, Payload, Request, WorkerResponse

class ClamAvScan(WorkerPlugin):

    def __init__(self, config: StoqConfigParser) -> None:
        super().__init__(config)
        self.rules = config.get('options', 'rules', fallback=None)
        if not self.rules:
            raise StoqPluginException("Capa rules was not provided")


    async def scan(self, payload: Payload, request: Request) -> WorkerResponse:
