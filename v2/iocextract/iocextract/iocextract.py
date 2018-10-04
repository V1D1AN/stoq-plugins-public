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

Extract and normalize Indicators of Compromise (IOC) from payloads

"""

from configparser import ConfigParser
from typing import Dict, Optional
import re
import os
import time
import requests
import socket
from urllib.parse import urlsplit
from ipaddress import ip_address, ip_network

from stoq import (
    Payload, RequestMeta, WorkerResponse,
    DispatcherResponse, ExtractedPayload, PayloadMeta)
from stoq.plugins import WorkerPlugin


class IOCExtract(WorkerPlugin):
    """
    IOCExtract

    """

    def __init__(self, config: ConfigParser,
                 plugin_opts: Optional[Dict]) -> None:
        super().__init__(config, plugin_opts)

        self.whitelist_file = [e.strip() for e in config.get('options', 'whitelist_file').split(',')]
        self.auto_update = config.get('options', 'auto_update')
        self.update_interval = config.get('options', 'update_interval')
        self.iana_url = config.get('options', 'iana_url')
        self.iana_tld_file = config.get('options', 'iana_tld_file')
        iana_tlds = self.__parse_iana()

        # Helper regexes
        self.helpers = {}
        self.helpers['dot'] = r"(?:\.|\[\.\]|\<\.\>|\{\.\}|\(\.\)|\<DOT\>|\[DOT\]|\{DOT\}|\(DOT\))"
        self.helpers['at'] = r"(?:@|\[@\]|\<@\>|\{@\}|\(@\)|\<AT\>|\[AT\]|\{AT\}|\(AT\))"
        self.helpers['http'] = r"\b(?:H(?:XX|TT)P|MEOW):\/\/"
        self.helpers['https'] = r"\b(?:H(?:XX|TT)PS|MEOWS):\/\/"
        self.helpers['tld'] = self.helpers['dot'] + r"(?:%s)\b" % iana_tlds
        self.helpers['host'] = r"\b(?:[A-Z0-9\-]+%s){0,4}" % self.helpers['dot']
        self.helpers['domain'] = r"[A-Z0-9\-]{2,50}" + self.helpers['tld']
        self.helpers['fqdn'] = "{0}{1}".format(self.helpers['host'],
                                               self.helpers['domain'])

        # Simple normalizers, post-processing
        # key=regex_name, value=replacement value
        # re.sub(regex_name, replacement)
        self.normalizers = {
            'dot': '.',
            'at': '@',
            'http': 'http://',
            'https': 'https://',
            'tld': lambda m: m.group(0).lower(),
            'domain': lambda m: m.group(0).lower(),
            'fqdn': lambda m: m.group(0).lower()
        }

        # Data-type regexes
        self.ioctypes = {}
        self.ioctypes['md5'] = r"\b[A-F0-9]{32}\b"
        self.ioctypes['sha1'] = r"\b[A-F0-9]{40}\b"
        self.ioctypes['sha256'] = r"\b[A-F0-9]{64}\b"
        self.ioctypes['sha512'] = r"\b[A-F0-9]{128}\b"
        self.ioctypes['ipv4'] = r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)%s){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)" % self.helpers['dot']
        self.ioctypes['ipv6'] = r"(?:(?:(?:\b|::)(?:(?:[\dA-F]{1,4}(?::|::)){1,7})(?:[\dA-F]{1,4}))(?:(?:(?:\.\d{1,3})?){3})(?:::|\b))|(?:[\dA-F]{1,4}::)|(?:::[\dA-F]{1,4}(?:(?:(?:\.\d{1,3})?){3}))"
        self.ioctypes['mac_address'] = r"\b(?i)(?:[0-9A-F]{2}[:-]){5}(?:[0-9A-F]{2})\b"
        self.ioctypes['email'] = "{0}{1}{2}".format(r"\b[A-Z0-9\.\_\%\+\-]+",
                                                    self.helpers['at'],
                                                    self.helpers['fqdn'])
        self.ioctypes['domain'] = self.helpers['fqdn']
        self.ioctypes['url'] = "(?:{0}|{1})(?:{2}|{3}|{4}){5}".format(self.helpers['http'],
                                                          self.helpers['https'],
                                                          self.helpers['fqdn'],
                                                          self.ioctypes['ipv4'],
                                                          self.ioctypes['ipv6'],
                                                          r"(?:[\:\/][A-Z0-9\/\:\+\%\.\_\-\=\~\&\\#\?]*){0,1}")

        # Compile regexes for faster repeat usage
        self.compiled_re = {}
        self.whitelist_patterns = {}
        for ioc in self.ioctypes:
            self.whitelist_patterns[ioc] = set()
            self.compiled_re[ioc] = re.compile(self.ioctypes[ioc],
                                               re.IGNORECASE)

        self.__load_whitelist()

    def read(self, payload, normalize=True, ioctype='all', **kwargs):
        """
        Extract IOC's out of a payload

        :param bytes payload: Content to be analyzed for IOC's
        :param bool normalize: Define whether the extracted IOC's should
                               be normalized
        :param bytes ioctype: Type of IOC to extract. Valid options are:
                              all (default), md5, sha1, sha256, ipv4, ipv6,
                              mac_address, email, domain, uri

        :returns: IOC's extracted from payload
        :rtype: dict

        """
    def scan(
            self,
            payload: Payload,
            request_meta: RequestMeta,
    ) -> WorkerResponse:

        normalize = True
        ioctype = 'all'
        results = {}

        if ioctype == 'all':
            for ioc in self.compiled_re:
                if self.compiled_re[ioc]:
                    matches = self.compiled_re[ioc].findall(payload.content.decode())
                    if matches:
                        results[ioc] = list(set(matches))
        elif self.compiled_re[ioctype]:
            matches = self.compiled_re[ioctype].findall(payload.content.decode())
            if matches:
                results[ioctype] = list(set(matches))

        if 'ipv6' in results:
            results['ipv6'] = [address for address in results['ipv6']
                               if self.__validate_ipv6(address)]
            if not results['ipv6']:
                results.pop('ipv6')

        if normalize:
            results = self.__normalize(results)

        return WorkerResponse(results)

    def __normalize(self, parsed_results):
        """
        Normalize, e.g., replace '[DOT]' with '.' for return value

        """

        normalized_results = {}
        for indicator_type in parsed_results:
            normalized_results[indicator_type] = set()
            for indicator in parsed_results[indicator_type]:
                for normalizer in self.normalizers:
                    indicator = re.sub(self.helpers[normalizer],
                                       self.normalizers[normalizer],
                                       indicator,
                                       flags=re.IGNORECASE)
                if self.__check_whitelist(indicator, indicator_type):
                    normalized_results[indicator_type].add(indicator)
            normalized_results[indicator_type] = list(normalized_results[indicator_type])

        return normalized_results

    def __validate_ipv6(self, address):
        """
        Validate whether a result is a valid ipv6 address

        """
        try:
            socket.inet_pton(socket.AF_INET6, address)
            return True
        except socket.error:
            return False

    def __load_whitelist(self):
        for whitelist_file in self.whitelist_file:
            if not os.path.isfile(whitelist_file):
                print("Invalid whitelist file...skipping {}".format(whitelist_file))
                continue

            with open(whitelist_file) as content:
                for line in content.readlines():
                    if line.startswith("#") or len(line) < 3:
                        continue

                    try:
                        indicator_type, pattern = line.split(':', 1)
                    except:
                        print("Invalid line in whitelist: {}".format(line))
                        continue

                    try:
                        self.whitelist_patterns[indicator_type].add(pattern.strip())
                    except KeyError:
                        print("Unknown indicator type: {}".format(indicator_type))

    def __check_whitelist(self, indicator, indicator_type):

        # Set to False so we can use only domain: in the whitelist_file
        is_url = False

        # Define the default netmask for the ip version
        netmasks = {'ipv4': '32',
                    'ipv6': '128'}

        try:

            if indicator_type == 'url':
                indicator_type = 'domain'
                is_url = True

            for pattern in self.whitelist_patterns[indicator_type]:
                # Extracted IOC is an IPv4/6 address
                if indicator_type in ['ipv4', 'ipv6']:
                    pattern_has_netmask = False
                    indicator_has_netmask = False

                    if len(pattern.split('/')) > 1:
                        pattern_has_netmask = True

                    if len(indicator.split('/')) > 1:
                        indicator_has_netmask = True

                    if pattern_has_netmask:
                        pattern_ip = ip_network("{}".format(pattern))
                    else:
                        pattern_ip = ip_network("{}/{}".format(pattern, netmasks[indicator_type]))

                    if indicator_has_netmask:
                        indicator_ip = ip_network(indicator)
                    else:
                        indicator_ip = ip_address(indicator)

                    if indicator_ip in pattern_ip:
                        return False

                elif indicator_type == 'domain':
                    if is_url:
                        indicator_domain = ".{0.netloc}".format(urlsplit(indicator))
                    else:
                        indicator_domain = ".{}".format(indicator)

                    if indicator_domain.endswith(pattern) or indicator == pattern:
                        return False

                elif indicator_type in ['mac_address', 'email', 'md5',
                                        'sha1', 'sha256', 'sha512']:
                    if indicator == pattern:
                        return False

        except KeyError:
            print("Unknown indicator type: {}".format(indicator_type))
            return False
        except Exception as err:
            print("Unable to handle indicator/pattern: {}".format(str(err)))
            return False

        return True

    def __parse_iana(self, update=False):
        # Our TLD file is not defined in the config file, let's set a default
        if not hasattr(self, 'iana_tld_file'):
            self.iana_tld_file = "plugins/iocextract/tlds-alpha-by-domain.txt"

        # Make sure we validate the entire path
        self.iana_tld_file = os.path.abspath(self.iana_tld_file)

        # Read TLD list from file for building regex
        if not os.path.isfile(self.iana_tld_file):
            print("IANA TLD File does not exist")
            update = True
        else:
            # Yes, I know this is a silly way of doing it. However, I hate datetime
            # and this is in protest.
            tld_age = int(int(time.time() - os.path.getmtime(self.iana_tld_file)) / 86400)
            if os.path.getsize(self.iana_tld_file) == 0:
                print("IANA TLD file is empty")
                update = True
            elif tld_age >= int(self.update_interval):
                print("IANA TLD file is {} days old".format(tld_age))
                update = True

        if update and self.auto_update:
            self.__download_iana()

        try:
            with open(self.iana_tld_file) as f:
                iana_tlds = "|".join(f.read().splitlines()[1:])
        except Exception as err:
            print("Unable to open IANA TLD File: {}".format(err))
            iana_tlds = None

        return iana_tlds

    def __download_iana(self):
        print("Downloading latest IANA TLD file from {}".format(self.iana_url))
        content = requests.get(self.iana_url).content
        if content:
            path = os.path.dirname(self.iana_tld_file)
            filename = os.path.basename(self.iana_tld_file)
            with open(f'{path}/{filename}', 'w') as outfile:
                outfile.write(content.decode())
        else:
            print("No content received from {}".format(self.iana_url))
