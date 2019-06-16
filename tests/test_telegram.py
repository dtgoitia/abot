# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

# import logging

import asynctest as am
import pytest

from abot.telegram import map_update_to_event, \
                          TelegramBackend, \
                          TelegramChannel, \
                          TelegramEntity, \
                          TelegramMessageEvent, \
                          TelegramUser
from tests.conftest import get_config


def create_async_generator(*, yield_value):
    """Return an async generator function that yields ``yield_value`` asynchronously."""
    async def f():
        yield yield_value
    return f


@pytest.fixture
def token():
    """Get Telegram Bot API token from the configuration file or environment variable."""
    return get_config('TOKEN')


@pytest.fixture
def backend(token):
    """Return an authenticated TelegramBackend instance."""
    backend = TelegramBackend()
    backend.configure(token=token)
    return backend


@pytest.fixture
def mocked_backend_token(mocker):
    """Patch to TelegramBackend to skip the token validation."""
    with am.patch('abot.telegram.TelegramBackend.test_bot_token', new=am.CoroutineMock()) as m:
        m.return_value = True
        yield m


@pytest.fixture
def mocked_backend_updates(mocker):
    """Patch to TelegramBackend to fake the updates long-polled from the Telegram Bot API."""
    with am.patch('abot.telegram.TelegramBackend._next_update', new=am.MagicMock()) as m:
        iterator = create_async_generator(yield_value='test fake update')
        m.side_effect = iterator
        yield m


@pytest.fixture
@pytest.mark.asyncio
async def mocked_initialized_backend(mocked_backend_token, mocked_backend_updates):
    """Return an initialized TelegramBackend instance."""
    backend = TelegramBackend()
    backend.configure(token=token)
    await backend.initialize()
    return backend


@pytest.fixture
def chat_message():
    """Update sample for a message from a user to a bot in an individual conversation."""
    return {'message': {'chat': {'first_name': 'David',
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


@pytest.fixture
def chat_command():
    """Update sample for a command from a user to group where the bot is admin."""
    return {'message': {'chat': {'first_name': 'David',
                                 'id': 185639288,
                                 'type': 'private',
                                 'username': 'david'},
                        'date': 1560489607,
                        'entities': [{'length': 3,
                                      'offset': 0,
                                      'type': 'bot_command'}],
                        'from': {'first_name': 'David',
                                 'id': 185639288,
                                 'is_bot': False,
                                 'language_code': 'en',
                                 'username': 'david'},
                        'message_id': 59,
                        'text': '/do something'},
            'update_id': 218871170}


@pytest.fixture
def group_message():
    """Update sample for a message from a user to group where the bot is admin."""
    return {'message': {'chat': {'all_members_are_administrators': False,
                                 'id': -362869152,
                                 'title': 'Test group',
                                 'type': 'group'},
                        'date': 1560489939,
                        'from': {'first_name': 'David',
                                 'id': 185639288,
                                 'is_bot': False,
                                 'language_code': 'en',
                                 'username': 'david'},
                        'message_id': 60,
                        'text': 'jey'},
            'update_id': 218871170}


@pytest.fixture
def group_command():
    """Update sample for a command from a user to group where the bot is admin."""
    return {'message': {'chat': {'all_members_are_administrators': False,
                                 'id': -362869152,
                                 'title': 'Test group',
                                 'type': 'group'},
                        'date': 1560490154,
                        'entities': [{'length': 3,
                                      'offset': 0,
                                      'type': 'bot_command'}],
                        'from': {'first_name': 'David',
                                 'id': 185639288,
                                 'is_bot': False,
                                 'language_code': 'en',
                                 'username': 'david'},
                        'message_id': 64,
                        'text': '/do something'},
            'update_id': 218871193}


# TelegramBackend =============================================================

@pytest.mark.skip
def test_telegram_configure_sets_base_url():
    # Ensure that if token is provided, base_url is set
    # Ensure that if token is not provided, base_url is not set
    pass


@pytest.mark.skip
@pytest.mark.asyncio
async def test_telegram_backend_token_is_valid():
    # If base url is provided, call test_bot_token
    #   if token is valid, nothing happens
    #   if token is invalid, what? raise exception?
    # If base url is not provided, do not call test_bot_token
    # both cases create a aiohttp session
    pass


@pytest.mark.skip
@pytest.mark.asyncio
async def test_telegram_backend_token_is_invalid():
    pass


@pytest.mark.skip
@pytest.mark.integration
@pytest.mark.asyncio
async def test_backend_checks_token_on_initialize():
    token = get_config('TOKEN')
    backend = TelegramBackend()
    backend.configure(token=token)
    response = await backend.initialize()
    assert response  # TODO: finish this


def test_not_supported_updates(backend):
    update = {'nonsense': 'blah'}
    event = map_update_to_event(update, backend)
    assert event is None


def test_map_chat_messages(chat_message, backend):
    update = chat_message
    event: TelegramMessageEvent = map_update_to_event(update, backend)

    sender: TelegramEntity = event.sender
    assert isinstance(sender, TelegramEntity)
    assert sender.id == 185639288
    assert sender.username == 'david'

    message_id = event.message_id
    assert isinstance(message_id, str)
    assert message_id == 42

    channel: TelegramChannel = event.channel
    assert isinstance(channel, TelegramChannel)
    # assert isinstance(channel, TelegramUser)  # TODO: implement
    assert channel.id == 185639288
    assert channel.name == 'david'


@pytest.mark.skip
def test_map_chat_command(chat_command, backend):
    update = chat_command
    event = map_update_to_event(update, backend)
    assert event is False


@pytest.mark.skip
def test_map_group_message(group_message, backend):
    update = group_message
    event = map_update_to_event(update, backend)
    assert event is False


@pytest.mark.skip
def test_map_group_command(group_command, backend):
    update = group_command
    event = map_update_to_event(update, backend)
    assert event is False


@pytest.mark.skip
@pytest.mark.asyncio
async def test_backend_consumes_chat_message(mocked_initialized_backend, chat_message):
    backend = mocked_initialized_backend
    backend._next_update.side_effect = create_async_generator(yield_value=chat_message)

    event: TelegramMessageEvent
    async for event in backend.consume():
        assert event.sender['id'] == 185639288
        assert event.sender['first_name'] == 'David'
        assert event.sender['username'] == 'david'
        # TODO: add more assertions


@pytest.mark.skip
@pytest.mark.integration
@pytest.mark.asyncio
async def test_backend_consume():
    token = get_config('TOKEN')
    backend = TelegramBackend()
    backend.configure(token=token)
    await backend.initialize()
    async for event in backend.consume():
        print(event)


# @pytest.mark.skip
# @pytest.mark.integration
# @pytest.mark.asyncio
# async def test_telegram_backend_integration():
#     token = get_config('TOKEN')
#     bot = Bot()
#     backend = TelegramBackend()
#     backend.configure(token=token)
#     bot.attach_backend(backend)

    # await bot.run_forever()
