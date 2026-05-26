class BrowserControllerError(Exception):
    """Base exception for browser controller failures."""


class BrowserSessionClosedError(BrowserControllerError):
    """Raised when a browser action is requested on a closed session."""


class BrowserRecoveryError(BrowserControllerError):
    """Raised when browser session recovery fails."""

