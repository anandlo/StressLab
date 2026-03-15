import json
import socket
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

EVENT_PORT = 9999


class EventMarker:
    """Sends UDP event markers for synchronization with data_recorder.py."""

    def __init__(self, host: str = "127.0.0.1", port: int = EVENT_PORT):
        self.host = host
        self.port = port
        self._sock: socket.socket | None = None

    def connect(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.info("Event marker UDP socket ready on %s:%d", self.host, self.port)
        except OSError as e:
            logger.warning("Could not create event marker socket: %s", e)
            self._sock = None

    def send(self, event_type: str, data: dict | None = None):
        if self._sock is None:
            return
        payload = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            **(data or {}),
        }
        try:
            msg = json.dumps(payload).encode("utf-8")
            self._sock.sendto(msg, (self.host, self.port))
        except OSError:
            pass

    def trial_start(self, trial_id: str, paradigm: str, difficulty: int):
        self.send("trial_start", {"trial_id": trial_id, "paradigm": paradigm,
                                   "difficulty": difficulty})

    def trial_end(self, trial_id: str, correct: bool, response_time_ms: float):
        self.send("trial_end", {"trial_id": trial_id, "correct": correct,
                                 "response_time_ms": response_time_ms})

    def block_start(self, block: int):
        self.send("block_start", {"block": block})

    def block_end(self, block: int):
        self.send("block_end", {"block": block})

    def session_start(self, participant_id: str):
        self.send("session_start", {"participant_id": participant_id})

    def session_end(self, participant_id: str):
        self.send("session_end", {"participant_id": participant_id})

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None
