import inspect
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from meru.base import Action, StateNode
from meru.exceptions import HandlerException
from meru.sockets import PushSocket, SubscriberSocket
from meru.state import get_state, update_state


def action_handler(cls, method):
    """A decorator used to mark action handlers.

    It is intended to be used inside of classes deriving from :py:class:`MeruProcess`.
    """
    action, required_parameters = _inspect_action_handler_args(method)
    handler = MeruProcess.ActionHandler(action, required_parameters)
    cls._ACTION_HANDLERS[action] = handler
    return method


class MeruProcess:
    @dataclass
    class ActionHandler:
        method: Any
        args: List[Any]

    _ACTION_HANDLERS: Dict[Any, ActionHandler] = {}

    def __init__(self):
        self._push_socket: Optional[PushSocket] = None
        self._subscriber_socket: Optional[SubscriberSocket] = None

    @property
    def push_socket(self) -> PushSocket:
        if self._push_socket is None:
            raise RuntimeError(
                "The process has to be running for the push socket to be available"
            )
        return self._push_socket

    @property
    def subscriber_socket(self) -> SubscriberSocket:
        if self._subscriber_socket is None:
            raise RuntimeError(
                "The process has to be running for the subscriber socket to be available"
            )
        return self._subscriber_socket

    async def push(self, action: Action):
        """Pushes an action to the broker."""
        await self.push_socket.push(action)

    async def run(self):
        """Starts the process"""
        self._push_socket = PushSocket()
        self._subscriber_socket = SubscriberSocket()

        while True:
            async for action in self._subscriber_socket.receive_action():
                async for response in self.handle_action(action):
                    if response is not None:
                        await self.push(action)

    async def handle_action(self, action: Action):
        """Handles one incoming action.

        This method can be overriden to add fuctionality.
        """
        action_cls = action.__class__
        handler = self._ACTION_HANDLERS.get(action_cls, None)

        await update_state(action)

        if not handler:
            return

        states_to_inject = [get_state(cls) for cls in handler.args]

        if inspect.isasyncgenfunction(handler.method):
            async for action in handler.method(self, action, *states_to_inject):
                yield action
        else:
            yield await handler.method(self, action, *states_to_inject)

    async def initialize(self):
        """Override this method to add initialization code."""


def _inspect_action_handler_args(func: callable):
    """Like :py:func:`meru.introspection.inspect_action_handler_args`, but for methods."""
    raise NotImplementedError()
