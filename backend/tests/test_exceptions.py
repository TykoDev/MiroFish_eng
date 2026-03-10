"""
Unit Tests for Custom Exceptions

Tests for the MiroFish exception hierarchy.
Run with: pytest backend/tests/test_exceptions.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils.exceptions import (
    MiroFishError,
    ErrorSeverity,
    # Configuration
    ConfigurationError,
    MissingConfigError,
    InvalidConfigError,
    # Ontology
    OntologyError,
    OntologyGenerationError,
    OntologyValidationError,
    # Graph
    GraphError,
    GraphBuildError,
    GraphConnectionError,
    GraphQueryError,
    # Profile
    ProfileError,
    ProfileGenerationError,
    ProfileValidationError,
    # Simulation
    SimulationError,
    SimulationInitError,
    SimulationRunError,
    IPCError,
    # External API
    ExternalAPIError,
    LLMError,
    LLMRateLimitError,
    ZepError,
    # Validation
    ValidationError,
    FileValidationError,
    ParameterValidationError,
    # Not Found
    NotFoundError,
    ProjectNotFoundError,
    SimulationNotFoundError,
    ReportNotFoundError,
)


class TestMiroFishErrorBase:
    """Test the base MiroFishError class"""
    
    def test_basic_error_creation(self):
        """Test basic error creation"""
        error = MiroFishError("Test error message")
        assert error.message == "Test error message"
        assert error.user_message == "Test error message"
        assert error.details == {}
        assert error.cause is None
    
    def test_error_with_all_params(self):
        """Test error with all parameters"""
        original_error = ValueError("original")
        error = MiroFishError(
            message="Technical message",
            details={"key": "value"},
            user_message="User friendly message",
            cause=original_error
        )
        assert error.message == "Technical message"
        assert error.user_message == "User friendly message"
        assert error.details == {"key": "value"}
        assert error.cause == original_error
    
    def test_to_dict(self):
        """Test error serialization"""
        error = MiroFishError(
            message="Test",
            details={"foo": "bar"},
            user_message="User message"
        )
        result = error.to_dict()
        
        assert result["error"] == True
        assert result["error_code"] == "MIROFISH_ERROR"
        assert result["message"] == "User message"
        assert result["severity"] == "medium"
        assert result["details"] == {"foo": "bar"}
    
    def test_str_representation(self):
        """Test string representation"""
        error = MiroFishError("Test message", details={"key": "value"})
        string_repr = str(error)
        
        assert "[MIROFISH_ERROR]" in string_repr
        assert "Test message" in string_repr
        assert "key" in string_repr


class TestConfigurationErrors:
    """Test configuration-related errors"""
    
    def test_missing_config_error(self):
        """Test MissingConfigError"""
        error = MissingConfigError("LLM_API_KEY")
        
        assert error.error_code == "CONFIG_MISSING"
        assert error.http_status == 500
        assert error.severity == ErrorSeverity.HIGH
        assert "LLM_API_KEY" in error.message
        assert "LLM_API_KEY" in error.details["config_name"]
    
    def test_invalid_config_error(self):
        """Test InvalidConfigError"""
        error = InvalidConfigError(
            config_name="PORT",
            value="abc",
            reason="must be a number"
        )
        
        assert error.error_code == "CONFIG_INVALID"
        assert "PORT" in error.message
        assert "must be a number" in error.message


class TestOntologyErrors:
    """Test ontology-related errors"""
    
    def test_ontology_generation_error(self):
        """Test OntologyGenerationError"""
        error = OntologyGenerationError()
        
        assert error.error_code == "ONTOLOGY_GENERATION_FAILED"
        assert error.http_status == 500
    
    def test_ontology_validation_error(self):
        """Test OntologyValidationError"""
        errors = ["Missing entity type", "Invalid edge definition"]
        error = OntologyValidationError(errors)
        
        assert error.error_code == "ONTOLOGY_VALIDATION_FAILED"
        assert error.http_status == 400 
        assert error.details["validation_errors"] == errors


class TestGraphErrors:
    """Test graph-related errors"""
    
    def test_graph_build_error(self):
        """Test GraphBuildError"""
        error = GraphBuildError(graph_id="graph_123")
        
        assert error.error_code == "GRAPH_BUILD_FAILED"
        assert "graph_123" in error.message
        assert error.details["graph_id"] == "graph_123"
    
    def test_graph_connection_error(self):
        """Test GraphConnectionError"""
        error = GraphConnectionError()
        
        assert error.error_code == "GRAPH_CONNECTION_FAILED"
        assert error.severity == ErrorSeverity.HIGH
    
    def test_graph_query_error(self):
        """Test GraphQueryError"""
        error = GraphQueryError(query="MATCH (n) RETURN n")
        
        assert error.error_code == "GRAPH_QUERY_FAILED"


class TestProfileErrors:
    """Test profile-related errors"""
    
    def test_profile_generation_error(self):
        """Test ProfileGenerationError"""
        error = ProfileGenerationError(entity_name="John Doe")
        
        assert error.error_code == "PROFILE_GENERATION_FAILED"
        assert "John Doe" in error.message
        assert error.details["entity_name"] == "John Doe"
    
    def test_profile_validation_error(self):
        """Test ProfileValidationError"""
        errors = ["bio is required", "age must be positive"]
        error = ProfileValidationError("Agent1", errors)
        
        assert error.error_code == "PROFILE_VALIDATION_FAILED"
        assert error.http_status == 400
        assert error.details["errors"] == errors


class TestSimulationErrors:
    """Test simulation-related errors"""
    
    def test_simulation_init_error(self):
        """Test SimulationInitError"""
        error = SimulationInitError(simulation_id="sim_abc123")
        
        assert error.error_code == "SIMULATION_INIT_FAILED"
        assert "sim_abc123" in error.message
    
    def test_simulation_run_error(self):
        """Test SimulationRunError"""
        error = SimulationRunError(simulation_id="sim_123", round_num=15)
        
        assert error.error_code == "SIMULATION_RUN_FAILED"
        assert error.details["round"] == 15
    
    def test_ipc_error(self):
        """Test IPCError"""
        error = IPCError(command="interview_agent")
        
        assert error.error_code == "IPC_ERROR"


class TestExternalAPIErrors:
    """Test external API errors"""
    
    def test_llm_error(self):
        """Test LLMError"""
        error = LLMError(provider="OpenAI", operation="chat_completion")
        
        assert error.error_code == "LLM_ERROR"
        assert error.http_status == 502
        assert error.severity == ErrorSeverity.HIGH
        assert error.details["provider"] == "OpenAI"
    
    def test_llm_rate_limit_error(self):
        """Test LLMRateLimitError"""
        error = LLMRateLimitError()
        
        assert error.error_code == "LLM_RATE_LIMIT"
        assert error.http_status == 429
    
    def test_zep_error(self):
        """Test ZepError"""
        error = ZepError(operation="search_graph")
        
        assert error.error_code == "ZEP_ERROR"


class TestValidationErrors:
    """Test validation errors"""
    
    def test_file_validation_error(self):
        """Test FileValidationError"""
        error = FileValidationError("test.pdf", "file too large")
        
        assert error.error_code == "FILE_VALIDATION_ERROR"
        assert error.http_status == 400
        assert error.severity == ErrorSeverity.LOW
    
    def test_parameter_validation_error(self):
        """Test ParameterValidationError"""
        error = ParameterValidationError("rounds", "abc", "integer")
        
        assert error.error_code == "PARAMETER_VALIDATION_ERROR"
        assert error.details["param_name"] == "rounds"


class TestNotFoundErrors:
    """Test not found errors"""
    
    def test_project_not_found(self):
        """Test ProjectNotFoundError"""
        error = ProjectNotFoundError("proj_123")
        
        assert error.error_code == "PROJECT_NOT_FOUND"
        assert error.http_status == 404
        assert error.details["resource_type"] == "Project"
    
    def test_simulation_not_found(self):
        """Test SimulationNotFoundError"""
        error = SimulationNotFoundError("sim_456")
        
        assert error.error_code == "SIMULATION_NOT_FOUND"
    
    def test_report_not_found(self):
        """Test ReportNotFoundError"""
        error = ReportNotFoundError("report_789")
        
        assert error.error_code == "REPORT_NOT_FOUND"


class TestErrorInheritance:
    """Test error inheritance hierarchy"""
    
    def test_ontology_error_inherits_from_base(self):
        """Verify ontology errors inherit from MiroFishError"""
        error = OntologyGenerationError()
        assert isinstance(error, MiroFishError)
        assert isinstance(error, OntologyError)
    
    def test_graph_error_inherits_from_base(self):
        """Verify graph errors inherit from MiroFishError"""
        error = GraphBuildError()
        assert isinstance(error, MiroFishError)
        assert isinstance(error, GraphError)
    
    def test_all_errors_can_be_caught_by_base(self):
        """Verify all errors can be caught by MiroFishError"""
        errors_to_test = [
            MissingConfigError("test"),
            OntologyGenerationError(),
            GraphBuildError(),
            ProfileGenerationError(),
            SimulationRunError("sim", 1),
            LLMError(),
            ProjectNotFoundError("test"),
        ]
        
        for error in errors_to_test:
            assert isinstance(error, MiroFishError), f"{type(error).__name__} should inherit from MiroFishError"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
