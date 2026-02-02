
class AppBaseException(Exception):
    """Base exception for the application."""
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error

class ConfigurationError(AppBaseException):
    """Raised when there is a configuration issue."""
    pass

class ProviderError(AppBaseException):
    """Base exception for chat provider errors."""
    pass

class ProviderConnectionError(ProviderError):
    """Raised when there are connectivity issues with the provider."""
    pass

class ProviderAuthenticationError(ProviderError):
    """Raised when authentication with the provider fails."""
    pass

class ProviderMessageError(ProviderError):
    """Raised when sending or receiving a message fails."""
    pass

class ProviderTransientError(ProviderError):
    """Raised for temporary errors that might succeed on retry."""
    pass
