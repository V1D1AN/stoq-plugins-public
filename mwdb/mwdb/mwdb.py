#!/usr/bin/env python3

#   Copyright 2014-2018 PUNCH Cyber Analytics Group
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

Send payload to Mwdb

"""


import requests
from time import sleep
from json import JSONDecodeError
from configparser import ConfigParser
from typing import Dict, Optional, Union, Tuple, List

from stoq.plugins import ArchiverPlugin
from stoq.helpers import StoqConfigParser, get_sha1
from stoq.exceptions import StoqPluginException
from stoq import Error, Payload, Request, ArchiverResponse

class Mwdb(ArchiverPlugin):
    def __init__(self, config: StoqConfigParser) -> None:
        super().__init__(config)

        self.mwdb_url = config.get('options', 'mwdb_url', fallback=None)
        if not self.mwdb_url:
            raise StoqPluginException("Mwdb URL was not provided")
        self.apikey = config.get('options', 'apikey', fallback=None)
        if not self.apikey:
            raise StoqPluginException("Mwdb API Key was not provided")

    async def archive(self, payload: Payload, request: Request) -> ArchiverResponse:
        """
        Send payloads to mwdb

        """

        errors: List[Error] = []
        url = f'{self.mwdb_url}/api/file'
        headers = {'Authorization': 'Bearer ' + self.apikey}
        filename = payload.results.payload_meta.extra_data.get('filename')
        if isinstance(filename, bytes):
            filename = filename.decode()
        files = {'file': (filename, payload.content)}
        response = requests.post(url, files=files, headers=headers)
        results = response.json()
