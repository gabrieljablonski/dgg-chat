class StreamInfo:
    def __init__(
        self,
        started_at, ended_at, duration,
        viewers, game, host, live,
        preview, status_text
    ):
        self.started_at = started_at
        self.ended_at = ended_at
        self.duration = duration
        self.viewers = viewers
        self.game = game
        self.host = host
        self.live = live
        self.preview = preview
        self.status_text = status_text

    @classmethod
    def from_api_response(cls, response):
        return cls(**response)
