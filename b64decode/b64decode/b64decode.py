#!/usr/bin/env python3

#   Copyright 2014-present PUNCH Cyber Analytics Group
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

Decode base64 encoded payloads

"""

import base64

from stoq.plugins import WorkerPlugin
from stoq import ExtractedPayload, Payload, Request, WorkerResponse


class B64Decode(WorkerPlugin):
    async def scan(self, payload: Payload, request: Request) -> WorkerResponse:
        decoded_content = base64.b64decode(payload.content)
        extracted = [ExtractedPayload(decoded_content)]
        return WorkerResponse(extracted=extracted)
