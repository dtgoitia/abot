# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from collections import Iterable, defaultdict

import asyncio
import contextvars
import inspect
import logging
import pprint
import re
import typing
from asyncio.events import AbstractEventLoop
from inspect import iscoroutinefunction
from typing import List, Optional

from abot.cli import CommandCollection, Group
from abot.util import iterator_merge

logger = logging.getLogger(__name__)


class Abort(Exception):
    pass


class Backend:
    def configure(self, **config):
        """Feed configuration to the Backend instance before initialization.

        This method can be useful to pass usernames or passwords to the Backend
        and store/handle them before the Bot initializates the Backend.
        """
        raise NotImplementedError

    async def initialize(self):
        """Execute one time operation which should run when the Backend starts."""
        raise NotImplementedError()

    async def consume(self):
        """Execute Backend logic.

        This method should be an async generator which yields Events, or any
        Event subtype.
        """
        raise NotImplementedError()

    def whoami(self) -> Optional['Entity']:
        """Return whatever Entity identify the current Backend instance.

        The Entity returned by this method will be used to identify the current
        Backend and match incoming Events and MessageEvents to the current
        Backend. Bear in mind that multiple Backends of the same type could be
        running at the same time. Thus, this Entity should be unique for
        each Backend instance.

        The idea is to leave up to the Bot author to decide which Entity is
        more convenient to identify the Backend.

        E.g.: if the Backend is using a given username to authenticate against
        Telegram, this method could return an Entity which represents this
        username.
        """
        raise NotImplementedError()

    def is_mentioned(self, message_event: 'MessageEvent') -> Optional[str]:
        whoami = self.whoami()
        if not whoami:
            return None
        username = whoami.username
        text = message_event.text
        if not (username and text):
            return None
        if len(text) < 2:
            return None
        pattern = r'^(@|!)?' + username + r'(([,:]|\s)|$)'
        logger.debug(f'Checking if `{text}` matches {pattern}')
        if re.match(pattern, text):
            return username
        return None


class BotObject:
    @property
    def bot(self) -> 'Bot':
        if hasattr(self, '_bot'):
            self._bot: 'Bot'
            return self._bot
        raise ValueError(f'Bot is not set in {self.__class__.__name__}')

    @bot.setter
    def bot(self, bot: 'Bot'):
        if hasattr(self, '_bot'):
            raise ValueError(f'Bot {self._bot} is in place, cannot replace with {bot}')
        self._bot = bot

    @property
    def backend(self) -> Backend:
        raise NotImplementedError()


class Channel(BotObject):
    @property
    async def entities(self) -> List['Entity']:  # TODO: consider to remove async keyword
        raise NotImplementedError()

    async def say(self, text: str):
        # Say something in the same channel as the message
        raise NotImplementedError()


class Entity(BotObject):
    """Anything that is not an Event or a Channel."""
    @property
    def id(self) -> str:
        raise NotImplementedError()

    @property
    def username(self) -> str:
        raise NotImplementedError()

    async def tell(self, text: str):
        # Say something to the sender
        raise NotImplementedError()


class Event(BotObject):
    """A particular occurrence that happens in a Channel.

    This occurrence may be related or not to a particular Entity which sends
    the event through a given Channel.

    E.g. of events:
        - User has joined the chat room.
        - User A sent a text message.
        - Chat room name has changed.
    """
    @property
    def sender(self) -> Optional[Entity]:
        # Return the entity that sent this, if any
        raise NotImplementedError()

    @property
    def channel(self) -> Channel:
        # Return the channel used to send the Event
        raise NotImplementedError()

    async def reply(self, text: str):
        # Reply to the message mentioning if possible
        raise NotImplementedError()


class MessageEvent(Event):
    @property
    def text(self) -> str:
        # Return the content of the message in plaintext
        raise NotImplementedError()


class _NoBackend(Backend):
    def configure(self, **config):
        pass

    async def initialize(self):
        pass

    async def consume(self):
        pass

    def whoami(self) -> Optional['Entity']:
        pass

    def __bool__(self):
        return False


_no_backend = _NoBackend()


class _NoBotObject(BotObject):
    @property
    def bot(self):
        return current_bot.get(None)

    @bot.setter
    def bot(self, bot: 'Bot'):
        if hasattr(self, '_bot'):
            raise ValueError(f'Bot {self._bot} is in place, cannot replace with {bot}')
        self._bot = bot

    backend = _no_backend

    def __bool__(self):
        return False


class _NoEntity(_NoBotObject, Entity):
    id = ''
    username = ''

    async def tell(self, text: str):
        print(text)


_no_entity = _NoEntity()


class _NoChannel(_NoBotObject, Channel):
    entities = [_no_entity]  # type: ignore

    async def say(self, text: str):
        print(text)


_no_channel = _NoChannel()


class _NoEvent(_NoBotObject, Event):
    sender = _no_entity
    channel = _no_channel

    async def reply(self, text: str):
        print(text)


_no_event = _NoEvent()


class _NoMessageEvent(_NoEvent, MessageEvent):
    text = ''


_no_message_event = _NoMessageEvent()

current_event = contextvars.ContextVar('current_event', default=_no_message_event)
current_bot: 'contextvars.ContextVar[Bot]' = contextvars.ContextVar('current_bot')


class Bot:
    def __init__(self):
        self.backends = {}
        self.event_handlers = defaultdict(set)
        self.message_handlers = set()
        self.forever_loop: asyncio.Future = None

    def attach_backend(self, backend: Backend):
        if backend in self.backends:
            raise ValueError(f'Backend {backend} is already attached to bot')
        iterator = self.backend_consume(backend)
        self.backends[backend] = iterator

    async def backend_consume(self, backend: 'Backend'):
        while True:
            try:
                async for event in backend.consume():
                    yield event
            except Abort as e:
                logger.exception(f'Backend {backend} decided to abort bot execution')
                raise e from None
            except Exception:
                logger.exception(f'Exception in {backend} handled. Trying to recover.')

    def attach_command_group(self, group: Group):
        self.message_handlers.add(group)

    async def _handle_message(self, message: MessageEvent):
        name = message.backend.is_mentioned(message)
        if not name:
            return
        logger.info(f'Executing command: {message.text}')
        cmd = CommandCollection(sources=self.message_handlers)
        asyncio.ensure_future(cmd.async_message(message))

    def add_event_handler(self, event_class_or_func=None, *, func=None):
        if iscoroutinefunction(event_class_or_func):
            func = event_class_or_func
            event_class = None
        else:
            event_class = event_class_or_func

        if event_class and not isinstance(event_class, Iterable):
            event_class = (event_class,)

        def wrapper(f):
            nonlocal event_class
            assert asyncio.iscoroutinefunction(f), \
                f'Handler for {event_class} needs to be coroutine ({f})'
            if event_class is None:
                event_class = extract_possible_argument_types(f)

            for ec in event_class:
                self.event_handlers[f].add(ec)
            return f

        if func is None:
            return wrapper
        else:
            wrapper(func)

    async def _handle_event(self, event: Event):
        # Same event can be handled multiple times, Messages only once
        if isinstance(event, MessageEvent):
            logger.debug(f'Handling message {event.text}')
            await self._handle_message(event)
        runs = 0
        for cls in inspect.getmro(event.__class__):
            for handler, handled_classes in self.event_handlers.items():
                if cls not in handled_classes:
                    continue
                asyncio.ensure_future(self.run_event(handler, event))
                runs += 1
        if not runs:
            logger.debug(f'No message handler for {event}')

    async def _run_forever(self):
        continue_running = True

        for backend in self.backends:
            await backend.initialize()

        backend_iterators = {i: None for i in self.backends.values()}

        while continue_running:
            try:
                async for event in iterator_merge(backend_iterators):
                    ce_token = current_event.set(event)
                    await self._handle_event(event=event)
                    current_event.reset(ce_token)
            except Abort as e:
                logger.info(f'Execution aborted by {e}')
                raise e from None
            except Exception as e:
                continue_running = await self.internal_exception_handler(e)

    async def run_forever(self):
        cbt = current_bot.set(self)
        self.forever_loop = self._run_forever()
        current_bot.reset(cbt)
        return await self.forever_loop

    async def internal_exception_handler(self, exception):
        logger.error('Internal exception handled', exc_info=exception)

        tb = exception.__traceback__
        while tb.tb_next:
            tb = tb.tb_next

        logger.error(f'Locals: {pprint.pformat(tb.tb_frame.f_locals)}')
        return True

    async def run_event(self, func, event):
        logger.debug(f'Starting handling {event} with <{func.__name__}>')
        try:
            await func(event)
        except Abort as exception:
            self.forever_loop.set_exception(exception)
            logger.exception(f'Handling {event} in <{func.__name__}> aborted, stopping run')
        except Exception as exception:
            await self.handle_bot_exception(func, event, exception)
        else:
            logger.debug(f'Finished handling {event} with <{func.__name__}>')

    async def handle_bot_exception(self, func, event, exception):
        logger.exception(f'Failed running {event} in {func}')
        # await event.say(f':boom:... Houston we found a problem: ```{exception}```')

    def start(self, event_loop: AbstractEventLoop = None):
        return asyncio.ensure_future(self.run_forever(), loop=event_loop)


def extract_possible_argument_types(func) -> Iterable:
    args = typing.get_type_hints(func)
    if len(args) != 1:
        raise AttributeError(f'Function {func} can only have one argument if using type hinting')
    type_hint = next(iter(args.values()))
    if type_hint.__class__.__name__ in ('_Union', '_GenericAlias'):
        return type_hint.__args__
    return type_hint,
