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

Decode ROT47 encoded content

"""

from stoq.plugins import StoqDecoderPlugin


class Rot47Decoder(StoqDecoderPlugin):

    def __init__(self):
        super().__init__()

    def activate(self, stoq):
        self.stoq = stoq

        super().activate()

    def decode(self, payload, **kwargs):
        """
        ROT47 decode content from provided payload

        :param bytes payload: Payload to be decoded
        :param **kwargs kwargs: Additional attributes (unused)

        :returns: ROT47 decoded content
        :rtype: list of tuples

        """

        try:
            byte_content = self.to_bytearray(payload)
            content_length = len(byte_content)

            for index in range(content_length):

                ord_value = byte_content[index]

                if ord_value >= 33 and ord_value <= 126:
                    new_value = (33 + ((ord_value + 14) % 94))
                    byte_content[index] = new_value
                else:
                    message = "Value out of range for ROT47, offset {}".format(index)
                    self.stoq.log.warn(message)

            # Define the metadata we want to return
            meta = {}
            meta['size'] = content_length

            # Return the results as a list of tuples
            return [(meta, bytes(byte_content))]

        except Exception as err:
            self.stoq.log.error("Unable to ROT47 payload: {}".format(str(err)))
            return None