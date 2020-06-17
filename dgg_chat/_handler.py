import logging


class DGGChatHandler:
    def __init__(self, chat=None):
        self._chat = chat
        self._handlers = {}

    @property
    def chat(self):
        return self._chat

    def on(self, f, event):
        self._handlers.setdefault(event, set()).add(f)
        return f

    def handle_event(self, event, *args):
        if event not in self._handlers:
            logging.debug(f"event type `{event}` not handled")
            return

        handlers = self._handlers.get(event)

        if not handlers:
            logging.debug(
                f"no handler registered for event type `{event}`"
            )
            return

        for handler in handlers:
            if args:
                handler(*args)
            else:
                handler()
