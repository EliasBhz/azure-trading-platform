from typing import Protocol


class KillSwitchSource(Protocol):
    """Where the kill switch state is read from.

    It is a protocol rather than a boolean setting so that the production
    implementation can read Key Vault or App Configuration on every cycle. A
    kill switch baked into the container image at build time would require a
    redeployment to trip, which defeats its purpose.
    """

    def is_engaged(self) -> bool: ...


class StaticKillSwitch:
    """A kill switch fixed at construction time.

    Used locally and in tests. In Azure it is replaced by a source that reads
    the current value at each cycle.
    """

    def __init__(self, engaged: bool) -> None:
        self._engaged = engaged

    def is_engaged(self) -> bool:
        return self._engaged
