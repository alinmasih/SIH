"""
Custom exception hierarchy for the forensics platform.

All platform-specific exceptions inherit from ForensicsPlatformException.
"""


class ForensicsPlatformException(Exception):
    """Base exception for all platform errors"""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


class ConfigurationError(ForensicsPlatformException):
    """Configuration-related errors"""
    pass


class ValidationError(ForensicsPlatformException):
    """Input validation errors"""
    pass


class PermissionError(ForensicsPlatformException):
    """Permission/privilege errors"""
    pass


class SafetyError(ForensicsPlatformException):
    """Safety check failures - prevents dangerous operations"""
    pass


class ForensicsError(ForensicsPlatformException):
    """Forensic operation failures"""
    pass


class EvidenceIntegrityError(ForensicsError):
    """Evidence integrity verification failed"""
    pass


class CarvingError(ForensicsError):
    """File carving operation failures"""
    pass


class SanitizationError(ForensicsPlatformException):
    """Sanitization operation failures"""
    pass


class DeviceAccessError(SanitizationError):
    """Device access failures"""
    pass


class VerificationError(SanitizationError):
    """Sanitization verification failures"""
    pass


class DatabaseError(ForensicsPlatformException):
    """Database operation failures"""
    pass


class ExternalToolError(ForensicsPlatformException):
    """External tool execution failures"""
    pass


class AuditError(ForensicsPlatformException):
    """Audit logging failures"""
    pass


class ReportGenerationError(ForensicsPlatformException):
    """Report generation failures"""
    pass
