import blinker
import enum

from functools import wraps
from fluvius.helper import when


class DomainSignal(enum.Enum):
    COMMAND_COMPLETED      = "signal_command_completed"
    COMMAND_READY          = "signal_command_ready"
    COMMAND_RECEIVED       = "signal_command_received"
    EVENT_COMMITED         = "signal_event_commited"
    MESSAGE_RECEIVED       = "signal_message_received"
    RESPONSE_RECEIVED      = "signal_response_received"
    TRANSACTION_COMMITTED  = "signal_transaction_committed"
    TRANSACTION_COMMITTING = "signal_transaction_committing"
    TRIGGER_RECONCILIATION = "signal_trigger_reconciliation"
    TRIGGER_REPLICATION    = "signal_trigger_replication"


def guarded_function(func, match_sender):
    ''' Note: This may causes confusion, since `signal.has_receivers_for` may return invalid values
        https://pythonhosted.org/blinker/#optimizing-signal-sending
    '''
    if match_sender is None:
        return func, blinker.base.ANY

    if callable(match_sender):
        @wraps(func)
        def wrapped_func(sender, **kwargs):
            if match_sender(sender):
                return func(sender, **kwargs)
        return wrapped_func, blinker.base.ANY

    if isinstance(match_sender, (tuple, list, set)):
        @wraps(func)
        def wrapped_func(sender, **kwargs):
            if sender in match_sender:
                return func(sender, **kwargs)
        return wrapped_func, blinker.base.ANY

    return func, match_sender


class DomainSignalManager(object):
    def register_signals(self):
        self.signal_transaction_committing = blinker.Signal()
        self.signal_transaction_committed = blinker.Signal()

        self.signal_command_ready = blinker.Signal()
        self.signal_command_completed = blinker.Signal()

        self.signal_message_received = blinker.Signal()
        self.signal_response_received = blinker.Signal()
        self.signal_command_received = blinker.Signal()
        self.signal_event_commited = blinker.Signal()

        self.signal_trigger_replication = blinker.Signal()
        self.signal_trigger_reconciliation = blinker.Signal()

        if not (subs := getattr(self, "_signal_subscriptions", None)):
            return

        def _connect(signal, func, match):
            channel = getattr(self, signal.value)
            wrapped_func, match_sender = guarded_function(func, match)
            channel.connect(wrapped_func, match_sender, weak=False)

        for signal_key, subscribers in subs.items():
            for handler, sender in subscribers:
                _connect(signal_key, handler, sender)

    @classmethod
    def subscribe(cls, signal, match=None):
        if not hasattr(cls, '_signal_subscriptions'):
            cls._signal_subscriptions = {}

        subs = cls._signal_subscriptions
        subs.setdefault(signal, tuple())

        def _decorator(func):
            ''' Delayed signal connection '''
            subs[signal] += ((func, match), )
            return func

        return _decorator

    async def publish(self, signal, sender, **kwargs):
        channel = getattr(self, signal.value)
        replies = channel.send(sender, **kwargs)
        return [await when(rep) for _, rep in replies]
