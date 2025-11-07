"""
Enhanced error handling utilities for the backend
Provides detailed error responses and logging
"""

from typing import Optional, Dict, Any
from enum import Enum
import logging
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Error categories for classification"""
    NETWORK = "network"
    VALIDATION = "validation"
    FILE_SYSTEM = "file_system"
    PERMISSION = "permission"
    AI_MODEL = "ai_model"
    STORAGE = "storage"
    DATABASE = "database"
    UNKNOWN = "unknown"


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DetailedError:
    """Represents a detailed error with context"""

    def __init__(
        self,
        title: str,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        technical_details: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestions: Optional[list[str]] = None
    ):
        self.title = title
        self.message = message
        self.category = category
        self.severity = severity
        self.technical_details = technical_details
        self.context = context or {}
        self.suggestions = suggestions or []
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "title": self.title,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "technical_details": self.technical_details,
            "context": self.context,
            "suggestions": self.suggestions,
            "timestamp": self.timestamp.isoformat()
        }


def create_error_response(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None
) -> DetailedError:
    """
    Create a detailed error response from an exception

    Args:
        exception: The exception that occurred
        context: Additional context information

    Returns:
        DetailedError object with categorized information
    """
    error_message = str(exception)
    error_type = type(exception).__name__
    context = context or {}

    # File system errors
    if isinstance(exception, FileNotFoundError):
        return DetailedError(
            title="File Not Found",
            message=f"The requested file could not be found: {error_message}",
            category=ErrorCategory.FILE_SYSTEM,
            severity=ErrorSeverity.ERROR,
            technical_details=f"{error_type}: {error_message}",
            context=context,
            suggestions=[
                "Verify the file path is correct",
                "Check if the file was moved or deleted",
                "Ensure proper file permissions"
            ]
        )

    # Permission errors
    if isinstance(exception, PermissionError):
        return DetailedError(
            title="Permission Denied",
            message="You do not have permission to perform this operation.",
            category=ErrorCategory.PERMISSION,
            severity=ErrorSeverity.ERROR,
            technical_details=f"{error_type}: {error_message}",
            context=context,
            suggestions=[
                "Check file and directory permissions",
                "Ensure the application has the necessary access rights",
                "Contact your system administrator"
            ]
        )

    # Validation errors
    if error_type in ["ValueError", "ValidationError"]:
        return DetailedError(
            title="Invalid Input",
            message=f"The provided input is invalid: {error_message}",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            technical_details=f"{error_type}: {error_message}",
            context=context,
            suggestions=[
                "Check your input values",
                "Ensure all required fields are provided",
                "Verify data types match expected formats"
            ]
        )

    # Database errors
    if "database" in error_message.lower() or "sql" in error_message.lower():
        return DetailedError(
            title="Database Error",
            message="A database error occurred. Please try again.",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.CRITICAL,
            technical_details=f"{error_type}: {error_message}",
            context=context,
            suggestions=[
                "Retry the operation",
                "Check database connectivity",
                "Contact support if the issue persists"
            ]
        )

    # AI/Model errors
    if "model" in error_message.lower() or "ollama" in error_message.lower():
        return DetailedError(
            title="AI Processing Error",
            message="The AI model encountered an error during processing.",
            category=ErrorCategory.AI_MODEL,
            severity=ErrorSeverity.ERROR,
            technical_details=f"{error_type}: {error_message}",
            context=context,
            suggestions=[
                "Ensure Ollama is running",
                "Check if the required model is downloaded",
                "Verify network connectivity to the AI service"
            ]
        )

    # Storage errors
    if "storage" in error_message.lower() or "upload" in error_message.lower():
        return DetailedError(
            title="Storage Error",
            message="Failed to access storage. Please check your configuration.",
            category=ErrorCategory.STORAGE,
            severity=ErrorSeverity.ERROR,
            technical_details=f"{error_type}: {error_message}",
            context=context,
            suggestions=[
                "Verify storage credentials",
                "Check network connectivity",
                "Ensure sufficient storage space"
            ]
        )

    # Generic error
    return DetailedError(
        title="An Error Occurred",
        message=error_message or "An unexpected error occurred.",
        category=ErrorCategory.UNKNOWN,
        severity=ErrorSeverity.ERROR,
        technical_details=f"{error_type}: {error_message}\n\nTraceback:\n{traceback.format_exc()}",
        context=context,
        suggestions=[
            "Try the operation again",
            "Check the application logs",
            "Report this issue if it persists"
        ]
    )


def log_detailed_error(error: DetailedError, logger_instance: logging.Logger = None):
    """
    Log a detailed error with appropriate severity

    Args:
        error: The DetailedError to log
        logger_instance: Optional logger instance to use
    """
    log = logger_instance or logger

    log_message = f"{error.title}: {error.message}"
    if error.context:
        log_message += f" | Context: {error.context}"

    if error.severity == ErrorSeverity.CRITICAL:
        log.critical(log_message)
        if error.technical_details:
            log.critical(f"Technical details: {error.technical_details}")
    elif error.severity == ErrorSeverity.ERROR:
        log.error(log_message)
        if error.technical_details:
            log.error(f"Technical details: {error.technical_details}")
    elif error.severity == ErrorSeverity.WARNING:
        log.warning(log_message)
    else:
        log.info(log_message)
