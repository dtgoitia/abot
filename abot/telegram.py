# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import asyncio
import json
import logging
import pprint
import ssl
from typing import Dict, List, Optional, Union

import aiohttp
import certifi  # TODO: needed?

from abot.bot import Backend, BotObject, Channel

logger = logging.getLogger('abot.telegram')


class TelegramObject(BotObject):
    """Telegram specific objects."""

    def __init__(self, data, telegram_backend: 'TelegramBackend'):
        self._data = data
        self._telegram_backend = telegram_backend

    @property
    def backend(self):
        return self._telegram_backend


class TelegramChannel(TelegramObject, Channel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._telegram_backend._register_user(self._data)


class TelegramBackend(Backend):
    """Official Telegram Bot API methods."""

    _GET_ME = 'getMe'
    _SEND_MESSAGE = 'sendMessage'
    _GET_UPDATES = 'getUpdates'

    def __init__(self):
        self.aio_session = None
        self._updates_offset: int = None
        # Production long polling timeout set to 297 seconds because aiohttp's
        # default request timeout is 5min:
        # https://docs.aiohttp.org/en/stable/client_quickstart.html#timeouts
        self._updates_timeout: int = 297
        # TODO: remove timeout=0 (short-polling), only for testing purposes
        self._updates_timeout = 0

    def configure(self, *, token=None):
        if token:
            self.base_url = f"https://api.telegram.org/bot{token}"

    async def initialize(self):
        self.aio_session = aiohttp.ClientSession()
        if self.base_url:
            self._token_is_valid = await self.test_bot_token()

    async def consume(self):
        # TODO: remember this method is an async generator, which means it needs to yield stuff asynchronously
        logger.info(f"Consuming...")
        response = await self._get_updates()
        # TODO: find how to pass the update (response) to each event handler to respond to commands, etc.
        yield None

    async def send_message(self, chat_id: Union[int, str], text: str) -> dict:
        """Send a text message to chat_id.

        Source: https://core.telegram.org/bots/api#sendmessage

        :param chat_id: Unique identifier for the target chat or username of the target channel
        :param text: Text of the message to be sent
        """
        url = self._create_url(self._SEND_MESSAGE)
        body = {
            'chat_id': chat_id,
            'text': text,
        }
        result = await self._api_post(url, body)
        # TODO: how to know if the returned message is valid
        return result['data']

    async def test_bot_token(self) -> bool:
        """Return true if the token is accepted by the Telegram Bot API, otherwise return false.

        https://core.telegram.org/bots/api#getme
        """
        url = self._create_url(self._GET_ME)
        response = await self._api_get(url)
        if response['ok']:
            logger.info(f"Connected to Telegram Bot API as @{response['result']['username']}")
            return True
        logger.info(f"Telegram Bot API: provided token is not valid")
        return False

    async def _api_get(self, url: str) -> dict:
        async with self.aio_session.get(url) as resp:
            logger.debug(f'Request: {url}')
            response = await resp.json()
            logger.debug(f'Response: {pprint.pformat(response)}')
        if response['ok'] is False:
            logger.error(f"telegram api: error {response['error_code']}. {response['description']}")
        return response

    async def _api_post(self, url: str, body: dict) -> dict:
        async with self.aio_session.post(url, json=body) as resp:
            logger.debug(f'Request: {url} - {body}')
            response = await resp.json()
            logger.debug(f'Response: {pprint.pformat(response)}')
        if response['ok'] is False:
            logger.error(f"telegram api: error {response['error_code']}. {response['description']}")
        return response

    def _create_url(self, method_name: str = None):
        if method_name:
            return f'{self.base_url}/{method_name}'

    def _generate_body(self, chat_id: str, text):
        # TODO: not implemented yet
        raise Exception('not implemented yet')
        pass

    async def _get_updates(self):
        if self._token_is_valid is False:
            return
        url = self._create_url(self._GET_UPDATES)
        body = {
            'offset': self._updates_offset,
            # 'limit': self._updates_limit,  # TODO: add support for limit
            'timeout': self._updates_timeout,
            # 'allowed_updates': self._allowed_updates,  # TODO: add support for selective updates
        }
        response = await self._api_post(url, body)
        if response['ok'] and response['result']:
            self.last_update_id = response['result'][-1]['update_id']
            # TODO: handle a situation when there are no new results:
            # send the latest update ID on the request, and you should not get any new update back


            import ipdb; ipdb.set_trace()


        # TODO: store latest received update ID
        return result


# class BaseBot:
#     """
#     Base class for bot. It's raw bot.
#     """
#     def __init__(self, token: str):
#         """
#         Instructions how to get Bot token is found here: https://core.telegram.org/bots#3-how-do-i-create-a-bot

#         :param token: token from @BotFather
#         :type token: :obj:`str`
#         """
#         self.__token = token

#         # Asyncio loop instance
#         self.loop = asyncio.get_event_loop()

#         # aiohttp main session
#         ssl_context = ssl.create_default_context(cafile=certifi.where())
#         connector = aiohttp.TCPConnector(ssl=ssl_context, loop=self.loop)

#         self.session = aiohttp.ClientSession(connector=connector, loop=self.loop, json_serialize=json.dumps)

#     async def close(self):
#         """
#         Close all client sessions
#         """
#         await self.session.close()

#     async def request(self, method: str, data: Optional[Dict] = None,
#                       **kwargs) -> Union[List, Dict, bool]:
#         """Make an request to Telegram Bot API.

#         Docs: https://core.telegram.org/bots/api#making-requests

#         :param method: API method
#         :type method: :obj:`str`
#         :param data: request parameters
#         :type data: :obj:`dict`
#         :return: result
#         :rtype: Union[List, Dict]
#         :raise: :obj:`aiogram.exceptions.TelegramApiError`
#         """
#         # TODO: what is exactly 'data' parameter
#         # TODO: what is 'api'
#         return await self._make_request(self.session, self.__token, method, **kwargs)

#     async def make_request(self, session, token, method, data=None, **kwargs):
#         url = self._create_url(method_name=method)  # TODO: move to TelegramBackend

#         req = compose_data(data, files)
#         async with session.post(url, data=req, **kwargs) as response:
#             return check_result(method, response.content_type, response.status, await response.text())
