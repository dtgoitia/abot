# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

# import logging

# import asynctest as am
import pytest
# import ipdb
# import unittest.mock as mock

from abot.telegram import TelegramBackend
from tests.conftest import get_config


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


# TODO: test the send_message method

@pytest.mark.skip
@pytest.mark.integration
@pytest.mark.asyncio
async def test_backend_checks_token_on_initialize():
    token = get_config('TOKEN')
    backend = TelegramBackend()
    backend.configure(token=token)
    response = await backend.initialize()
    assert response  # TODO: finish this


@pytest.fixture
def token():
    """Get Telegram Bot API token from the configuration file or environment variable."""
    return get_config('TOKEN')


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backend_consume(token):
    # Calls with the right offset if has called before
    # token = get_config('TOKEN')
    backend = TelegramBackend()
    backend.configure(token=token)
    await backend.initialize()
    async for event in backend.consume():
        # TODO: find how to pass the update (response) to each event handler to
        #       respond to commands, etc.
        import ipdb; ipdb.set_trace()
        print(event)
    import ipdb; ipdb.set_trace()
    print('end of test')


# @pytest.mark.skip
# @pytest.mark.integration
# @pytest.mark.asyncio
# async def test_telegram_backend_integration():
#     token = get_config('TOKEN')
#     bot = Bot()
#     backend = TelegramBackend()
#     backend.configure(token=token)
#     bot.attach_backend(backend)

#     # await bot.run_forever()
