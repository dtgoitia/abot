# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import asyncio
from collections import defaultdict
import logging
import pprint
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
import weakref

import aiohttp

from abot.bot import Backend, BotObject, Channel, Entity, Event, MessageEvent

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
    """Represents a Telegram conversation.

    A TelegramChannel represents one of the following concepts in Telegram:
      - Telegram channel
      - Telegram conversation (where the TelegramChannel is a TelegramUser)
      - Telegram group
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._telegram_backend._register_user(self._data)

    async def say(self, text: str) -> str:
        for line in text.splitlines():
            await self._telegram_backend.say
        
    # TODO: model conversation ID, group ID, channel ID


class TelegramEntity(TelegramObject, Entity):
    async def tell(self, text: str):
        pass

    @property
    def username(self):
        return self._data.get('username')

    @property
    def id(self):
        return self._data.get('id')

    def __repr__(self):
        cls = self.__class__.__name__
        userid = self.id
        username = self.username
        return f'<{cls} {username}#{userid}>'

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.id == other.id:
            return True
        return False


class TelegramEvent(TelegramObject, Event):
    _data_type = ''

    @property
    def sender(self) -> Optional[TelegramEntity]:
        pass

    # TODO: necessary?
    @property
    def channel(self) -> TelegramChannel:
        """Return the channel user to send the TelegramEvent."""
        if hasattr(self, '_channel'):
            self._channel: TelegramChannel
            return self._channel
        raise ValueError('Channel is not set')

    # TODO: necessary?
    @channel.setter
    def channel(self, channel: TelegramChannel):
        if hasattr(self, '_channel'):
            raise ValueError(f'Channel {self._channel} is in place, cannot replace with {channel}')
        self._channel = channel

    # TODO: necessary?
    async def reply(self, text: str, to: str = None):
        if to is None:
            to = f"@{self.sender.username}"
        return await self._channel.say(f"{to}: {text}")

    # TODO: update as needed
    def __repr__(self):
        cls = self.__class__.__name__
        return f"<{cls} #{self._data['type']}>"


class TelegramMessageEvent(TelegramEvent, MessageEvent):
    """Telegram message event data

    Message from a user in a 1 to 1 conversation with the bot:
    {'message': {'chat': {'first_name': 'David',
                          'id': 185639288,
                          'type': 'private',
                          'username': 'david'},
                 'date': 1560196082,
                 'from': {'first_name': 'David',
                          'id': 185639288,
                          'is_bot': False,
                          'language_code': 'en',
                          'username': 'david'},
                 'message_id': 42,
                 'text': 'asd'},
     'update_id': 218871170}

    Message from a user in a group where the bot is admin:
    {'message': {'chat': {'all_members_are_administrators': False,
                          'id': -362869152,
                          'title': 'test_group',
                          'type': 'group'},
                 'date': 1560317091,
                 'from': {'first_name': 'David',
                          'id': 185639288,
                          'is_bot': False,
                          'language_code': 'en',
                          'username': 'david'},
                 'message_id': 48,
                 'text': 'now the bot is admin as well'},
     'update_id': 218871177}]}
    """
    _data_type = 'chat-message'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_data = self._data.get('message').get('from')

        self._telegram_backend._register_user(user_data)

    # TODO: adapt this to Telegram use case
    @property
    def sender(self) -> Optional[TelegramEntity]:
        sender = self._data.get('message', {}).get('from').get('username')
        entity = self._telegram_backend._get_entity(sender)
        return entity

    @property
    def text(self) -> str:
        return self._data.get('message', {}).get('text')

    @property

    def channel(self) -> TelegramChannel:
        import ipdb; ipdb.set_trace()
        return self._data.get('message', {}).get('chat').get('id')

    @property
    def message_id(self) -> str:
        """Unique message identifier inside a given TelegramChannel."""
        import ipdb; ipdb.set_trace()
        return self._data.get('message', {}).get('message_id')
        # TODO: consider if it is necessary to create a really unique ID. At the
        # moment, message_id is only unique within a given channel (chat). Is it
        # necessary to request IDs which are unique

    def __repr__(self):
        cls = self.__class__.__name__
        chatid = self.message_id
        sender = self.sender  # TODO: the __repr__ of this sender looks ugly because it's not adapted to Telegram yet
        msg = self.text
        return f'<{cls}#{chatid} {sender} "{msg}">'


class TelegramNewChatMember(TelegramEvent):
    """Message received when the bot was added to the channel
     {'message': {'chat': {'all_members_are_administrators': True,
                           'id': -362869152,
                           'title': 'test_group',
                           'type': 'group'},
                  'date': 1560316178,
                  'from': {'first_name': 'David',
                           'id': 185639288,
                           'is_bot': False,
                           'language_code': 'en',
                           'username': 'david'},
                  'message_id': 47,
                  'new_chat_member': {'first_name': 'dtg',
                                      'id': 849011351,
                                      'is_bot': True,
                                      'username': 'dtg_bot'},
                  'new_chat_members': [{'first_name': 'dtg',
                                        'id': 849011351,
                                        'is_bot': True,
                                        'username': 'dtg_bot'}],
                  'new_chat_participant': {'first_name': 'dtg',
                                           'id': 849011351,
                                           'is_bot': True,
                                           'username': 'dtg_bot'}},
    """
    pass


class TelegramChannelPost(TelegramEvent):
    """Update emited by the Telegram Bot API when a user posts a message into a channel.
    {'channel_post': {'chat': {'id': -1001390499227,
                               'title': 'test_channel',
                               'type': 'channel'},
                      'date': 1560316939,
                      'message_id': 5,
                      'text': 'hey!'},
     'update_id': 218871176}
    """
    pass


class TelegramCommand(TelegramMessageEvent):
    _data_type = 'chat-command'

    # TODO: adapt this to Telegram use case
    @property
    def sender(self) -> Optional[TelegramEntity]:
        return self._telegram_backend._get_entity(self._data.get('username'))

    def __repr__(self):
        cls = self.__class__.__name__
        sender = self.sender
        return f'<{cls} {sender}>'


def map_update_to_event(update: dict, backend: 'TelegramBackend') -> Optional[TelegramEvent]:
    if 'message' not in update:
        return None
    message = update['message']
    if 'entities' in message and has_bot_command(message['entities']):
        # event = TelegramCommandEvent(update, backend)
        pass
    else:
        event = TelegramMessageEvent(update, backend)
    # else:
    #     event = TelegramEvent(update, backend)  # type: ignore
    return event


def has_bot_command(entities: List[dict]) -> bool:
    """Return true if there is any ``bot_command`` entity type."""
    for entity in entities:
        if entity['type'] == 'bot_command':
            return True
    else:
        return False


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
        self.telegram_users = defaultdict(dict)
        self.telegram_entites = weakref.WeakValueDictionary()

    def configure(self, *, token=None):
        if token:
            self.base_url = f"https://api.telegram.org/bot{token}"

    async def initialize(self):
        self.aio_session = aiohttp.ClientSession()
        if self.base_url:
            self._token_is_valid = await self.test_bot_token()

    async def consume(self) -> AsyncGenerator['TelegramEvent', None]:
        # TODO: check the format of the log and ensure it consistent with the
        # rest of the logs, also ensure it contains TelegramBackend somewhere
        if self._token_is_valid is False:
            logger.info(f"Bot token is not valid")
            return

        logger.info(f"Bot token is valid")
        logger.info(f"Consuming...")
        async for update in self._next_update():
            event = map_update_to_event(update, self)
            if event:
                yield event

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

    async def _next_update(self) -> AsyncGenerator[dict, None]:
        """Fetch available updates and yield them one by one."""
        while (True):
            updates = await self._get_updates()
            if updates:
                for update in updates:
                    yield update

    async def _get_updates(self) -> Optional[dict]:
        """Returns a list of updates.

        Example:
        """
        url = self._create_url(self._GET_UPDATES)
        body = {
            'offset': self._updates_offset,
            # 'limit': self._updates_limit,  # TODO: add support for limit
            'timeout': self._updates_timeout,
            # 'allowed_updates': self._allowed_updates,  # TODO: add support for selective updates
        }
        response = await self._api_post(url, body)
        if response['ok'] and 'result' in response:
            updates = response['result']
            if len(updates) > 0:
                last_update_id = updates[-1]['update_id']
                self._updates_offset = last_update_id + 1
            return updates
        # TODO: test a situation when there are no new results:
        # send the latest update ID on the request, and you should not get any new update back
        asyncio.sleep(1)
        return None

    def _register_user(self, user_data) -> Optional[TelegramEntity]:
        """User data structure:
        {'first_name': 'David',
        'id': 185639288,
        'is_bot': False,
        'language_code': 'en',
        'username': 'david'}
        """
        user_id = None
        update_dict: Dict[str, Any] = {}
        if not user_data:
            return None
        if 'id' in user_data:
            user_id = user_data['id']
            update_dict['id'] = user_id
        if 'first_name' in user_data:
            update_dict['first_name'] = user_data['first_name']
        if 'username' in user_data:
            update_dict['username'] = user_data['username']

        self.telegram_users[user_id].update(update_dict)
        # TODO: is this complete?

    def _get_entity(self, id_or_name: str) -> Optional[TelegramEntity]:
        # TODO: adapt to Telegram case
        user_data = self._get_user_data(id_or_name)
        if not user_data:
            logger.info(f'Information for user {id_or_name} not available')
            return None
        user_id = user_data['id']
        entity = self.telegram_entites.get(user_id)
        if entity:
            return entity
        entity = TelegramEntity(user_data, self)
        self.telegram_entites[user_id] = entity
        return entity

    def _get_user_data(self, id_or_name):  # TODO: are return type
        # TODO: adapt to Telegram case
        for id, user_data in self.telegram_users.items():
            if id_or_name == id:
                data = {'id': id}
                data.update(user_data)
                return data
            elif id_or_name == user_data.get('username'):
                data = {'id': id}
                data.update(user_data)
                return data
