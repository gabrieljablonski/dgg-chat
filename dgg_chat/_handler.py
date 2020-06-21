import logging


class DGGChatEventHandler:
    def __init__(self):
        self._handlers = {}
        self._errors = []

    @property
    def errors(self):
        return self._errors

    def on(self, event, f):
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
            try:
                if args:
                    handler(*args)
                else:
                    handler()
            except Exception as e:
                self._errors.append(e)
