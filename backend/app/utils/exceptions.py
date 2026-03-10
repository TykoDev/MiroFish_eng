"""
MiroFish Custom Exceptions

This module provides a hierarchy of custom exceptions for better error handling,
debugging, and API responses throughout the MiroFish application.

Usage:
    from app.utils.exceptions import (
        MiroFishError,
        OntologyGenerationError,
        GraphBuildError,
        ProfileGenerationError,
        SimulationError,
        ConfigurationError,
        ValidationError,
        ExternalAPIError,
    )
"""

from typing import Optional, Dict, Any, List
from enum import Enum


class ErrorSeverity(str, Enum):
    """Error severity levels for logging and monitoring"""
    LOW = "low"           # Minor issues, can be retried
    MEDIUM = "medium"     # Significant issues, may need attention
    HIGH = "high"         # Critical issues, immediate attention needed
    CRITICAL = "critical" # System-level failures


class MiroFishError(Exception):
    """
    Base exception class for all MiroFish errors.
    
    Provides:
    - Error code for programmatic handling
    - Severity level for monitoring
    - Optional details dictionary for context
    - User-friendly message vs technical message separation
    """
    
    # Default values for subclasses
    error_code: str = "MIROFISH_ERROR"
    http_status: int = 500
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a MiroFish error.
        
        Args:
            message: Technical error message (for logs and debugging)
            details: Additional context dictionary
            user_message: User-friendly message (for API responses)
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.user_message = user_message or message
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API response"""
        result = {
            "error": True,
            "error_code": self.error_code,
            "message": self.user_message,
            "severity": self.severity.value,
        }
        if self.details:
            result["details"] = self.details
        if self.cause:
            result["cause"] = str(self.cause)
        return result
    
    def __str__(self) -> str:
        if self.details:
            return f"[{self.error_code}] {self.message} - Details: {self.details}"
        return f"[{self.error_code}] {self.message}"


# ============================================================
# Configuration Errors
# ============================================================

class ConfigurationError(MiroFishError):
    """Base class for configuration-related errors"""
    error_code = "CONFIG_ERROR"
    http_status = 500
    severity = ErrorSeverity.HIGH


class MissingConfigError(ConfigurationError):
    """Required configuration is missing"""
    error_code = "CONFIG_MISSING"
    
    def __init__(self, config_name: str, **kwargs):
        # Remove any conflicting kwargs
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"Required configuration '{config_name}' is not set"
        super().__init__(
            message=message,
            user_message=f"System configuration missing: {config_name}",
            details={"config_name": config_name},
            **kwargs
        )


class InvalidConfigError(ConfigurationError):
    """Configuration value is invalid"""
    error_code = "CONFIG_INVALID"
    
    def __init__(self, config_name: str, value: Any, reason: str, **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"Configuration '{config_name}' has invalid value: {reason}"
        super().__init__(
            message=message,
            user_message=f"Configuration '{config_name}' is invalid: {reason}",
            details={"config_name": config_name, "value": str(value), "reason": reason},
            **kwargs
        )


# ============================================================
# Ontology Errors
# ============================================================

class OntologyError(MiroFishError):
    """Base class for ontology-related errors"""
    error_code = "ONTOLOGY_ERROR"
    http_status = 500
    severity = ErrorSeverity.MEDIUM


class OntologyGenerationError(OntologyError):
    """Failed to generate ontology from documents"""
    error_code = "ONTOLOGY_GENERATION_FAILED"
    
    def __init__(self, message: str = "Failed to generate ontology", **kwargs):
        kwargs.pop('user_message', None)
        super().__init__(
            message=message,
            user_message="Ontology generation failed. Please check document content.",
            **kwargs
        )


class OntologyValidationError(OntologyError):
    """Generated ontology fails validation"""
    error_code = "ONTOLOGY_VALIDATION_FAILED"
    http_status = 400
    
    def __init__(self, errors: List[str], **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"Ontology validation failed: {errors}"
        super().__init__(
            message=message,
            user_message="Generated ontology definition does not meet specifications",
            details={"validation_errors": errors},
            **kwargs
        )


# ============================================================
# Graph Errors
# ============================================================

class GraphError(MiroFishError):
    """Base class for graph-related errors"""
    error_code = "GRAPH_ERROR"
    http_status = 500
    severity = ErrorSeverity.MEDIUM


class GraphBuildError(GraphError):
    """Failed to build knowledge graph"""
    error_code = "GRAPH_BUILD_FAILED"
    
    def __init__(self, graph_id: Optional[str] = None, **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"Failed to build graph: {graph_id or 'unknown'}"
        super().__init__(
            message=message,
            user_message="Graph build failed. Please try again later.",
            details={"graph_id": graph_id},
            **kwargs
        )


class GraphConnectionError(GraphError):
    """Failed to connect to graph database (Zep)"""
    error_code = "GRAPH_CONNECTION_FAILED"
    severity = ErrorSeverity.HIGH
    
    def __init__(self, **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        super().__init__(
            message="Failed to connect to Zep graph database",
            user_message="Cannot connect to graph database. Please check network connection.",
            **kwargs
        )


class GraphQueryError(GraphError):
    """Failed to query graph"""
    error_code = "GRAPH_QUERY_FAILED"
    
    def __init__(self, query: str = "", **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"Graph query failed: {query[:100]}..."
        super().__init__(
            message=message,
            user_message="Graph query failed",
            **kwargs
        )


# ============================================================
# Profile/Agent Errors
# ============================================================

class ProfileError(MiroFishError):
    """Base class for agent profile errors"""
    error_code = "PROFILE_ERROR"
    http_status = 500
    severity = ErrorSeverity.MEDIUM


class ProfileGenerationError(ProfileError):
    """Failed to generate agent profile"""
    error_code = "PROFILE_GENERATION_FAILED"
    
    def __init__(self, entity_name: str = "", **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"Failed to generate profile for entity: {entity_name}"
        super().__init__(
            message=message,
            user_message=f"Agent profile generation failed: {entity_name}",
            details={"entity_name": entity_name},
            **kwargs
        )


class ProfileValidationError(ProfileError):
    """Profile validation failed"""
    error_code = "PROFILE_VALIDATION_FAILED"
    http_status = 400
    
    def __init__(self, entity_name: str, errors: List[str], **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"Profile validation failed for {entity_name}: {errors}"
        super().__init__(
            message=message,
            user_message=f"Agent profile validation failed: {entity_name}",
            details={"entity_name": entity_name, "errors": errors},
            **kwargs
        )


# ============================================================
# Simulation Errors
# ============================================================

class SimulationError(MiroFishError):
    """Base class for simulation errors"""
    error_code = "SIMULATION_ERROR"
    http_status = 500
    severity = ErrorSeverity.MEDIUM


class SimulationInitError(SimulationError):
    """Failed to initialize simulation"""
    error_code = "SIMULATION_INIT_FAILED"
    
    def __init__(self, simulation_id: str = "", **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"Failed to initialize simulation: {simulation_id}"
        super().__init__(
            message=message,
            user_message="Simulation initialization failed",
            details={"simulation_id": simulation_id},
            **kwargs
        )


class SimulationRunError(SimulationError):
    """Error during simulation execution"""
    error_code = "SIMULATION_RUN_FAILED"
    
    def __init__(self, simulation_id: str, round_num: int = 0, **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"Simulation {simulation_id} failed at round {round_num}"
        super().__init__(
            message=message,
            user_message="Error occurred during simulation execution",
            details={"simulation_id": simulation_id, "round": round_num},
            **kwargs
        )


class IPCError(SimulationError):
    """Inter-process communication error"""
    error_code = "IPC_ERROR"
    
    def __init__(self, command: str = "", **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"IPC command failed: {command}"
        super().__init__(
            message=message,
            user_message="Inter-process communication error",
            details={"command": command},
            **kwargs
        )


# ============================================================
# External API Errors
# ============================================================

class ExternalAPIError(MiroFishError):
    """Base class for external API errors"""
    error_code = "EXTERNAL_API_ERROR"
    http_status = 502
    severity = ErrorSeverity.HIGH


class LLMError(ExternalAPIError):
    """LLM API call failed"""
    error_code = "LLM_ERROR"
    
    def __init__(self, provider: str = "", operation: str = "", **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"LLM API call failed: {provider} - {operation}"
        super().__init__(
            message=message,
            user_message="AI model call failed. Please try again later.",
            details={"provider": provider, "operation": operation},
            **kwargs
        )


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded"""
    error_code = "LLM_RATE_LIMIT"
    http_status = 429
    
    def __init__(self, **kwargs):
        # Don't pass provider/operation to parent, handle directly
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        # Call grandparent directly
        ExternalAPIError.__init__(
            self,
            message="LLM rate limit exceeded",
            user_message="AI model rate limit exceeded. Please try again later.",
            details={"rate_limited": True},
            **kwargs
        )


class ZepError(ExternalAPIError):
    """Zep API call failed"""
    error_code = "ZEP_ERROR"
    
    def __init__(self, operation: str = "", **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"Zep API call failed: {operation}"
        super().__init__(
            message=message,
            user_message="Graph service call failed",
            details={"operation": operation},
            **kwargs
        )


# ============================================================
# Validation Errors
# ============================================================

class ValidationError(MiroFishError):
    """Base class for validation errors"""
    error_code = "VALIDATION_ERROR"
    http_status = 400
    severity = ErrorSeverity.LOW


class FileValidationError(ValidationError):
    """Invalid file upload"""
    error_code = "FILE_VALIDATION_ERROR"
    
    def __init__(self, filename: str, reason: str, **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"File validation failed for '{filename}': {reason}"
        super().__init__(
            message=message,
            user_message=f"File validation failed: {reason}",
            details={"filename": filename, "reason": reason},
            **kwargs
        )


class ParameterValidationError(ValidationError):
    """Invalid request parameter"""
    error_code = "PARAMETER_VALIDATION_ERROR"
    
    def __init__(self, param_name: str, value: Any, expected: str, **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"Invalid parameter '{param_name}': expected {expected}, got {type(value).__name__}"
        super().__init__(
            message=message,
            user_message=f"Invalid parameter: {param_name}",
            details={"param_name": param_name, "value": str(value), "expected": expected},
            **kwargs
        )


# ============================================================
# Not Found Errors
# ============================================================

class NotFoundError(MiroFishError):
    """Resource not found"""
    error_code = "NOT_FOUND"
    http_status = 404
    severity = ErrorSeverity.LOW
    
    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        kwargs.pop('message', None)
        kwargs.pop('user_message', None)
        kwargs.pop('details', None)
        message = f"{resource_type} not found: {resource_id}"
        super().__init__(
            message=message,
            user_message=f"{resource_type} not found: {resource_id}",
            details={"resource_type": resource_type, "resource_id": resource_id},
            **kwargs
        )


class ProjectNotFoundError(NotFoundError):
    """Project not found"""
    error_code = "PROJECT_NOT_FOUND"
    
    def __init__(self, project_id: str, **kwargs):
        super().__init__("Project", project_id, **kwargs)


class SimulationNotFoundError(NotFoundError):
    """Simulation not found"""
    error_code = "SIMULATION_NOT_FOUND"
    
    def __init__(self, simulation_id: str, **kwargs):
        super().__init__("Simulation", simulation_id, **kwargs)


class ReportNotFoundError(NotFoundError):
    """Report not found"""
    error_code = "REPORT_NOT_FOUND"
    
    def __init__(self, report_id: str, **kwargs):
        super().__init__("Report", report_id, **kwargs)
