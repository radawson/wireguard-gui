class WireguardGuiError(Exception):
    """Base application error."""


class CommandExecutionError(WireguardGuiError):
    """Raised when a shell command returns a non-zero exit code."""

    def __init__(self, command: str, returncode: int, stderr: str = ""):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        detail = stderr.strip() or "unknown error"
        super().__init__(f"Command failed ({returncode}): {command} - {detail}")


class EntityNotFoundError(WireguardGuiError):
    """Raised when a model cannot be found."""


class ValidationError(WireguardGuiError):
    """Raised when input validation fails."""
