"""
Unit Tests for Configuration Validation

Tests for the enhanced configuration system.
Run with: pytest backend/tests/test_config_validated.py -v
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))



from app.config import (
    Config,
    ConfigValidationResult,
    validate_on_startup,
)


class TestConfigValidationResult:
    """Test ConfigValidationResult class"""
    
    def test_empty_result_is_valid(self):
        """Empty result should be valid"""
        result = ConfigValidationResult()
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_result_with_errors_is_invalid(self):
        """Result with errors should be invalid"""
        result = ConfigValidationResult()
        result.add_error("Test error")
        assert result.is_valid is False
        assert len(result.errors) == 1
    
    def test_result_with_warnings_is_valid(self):
        """Result with only warnings should still be valid"""
        result = ConfigValidationResult()
        result.add_warning("Test warning")
        assert result.is_valid is True
        assert len(result.warnings) == 1
    
    def test_to_dict(self):
        """Test serialization"""
        result = ConfigValidationResult()
        result.add_error("Error 1")
        result.add_warning("Warning 1")
        result.add_info("Info 1")
        
        d = result.to_dict()
        assert d["is_valid"] is False
        assert d["error_count"] == 1
        assert d["warning_count"] == 1
        assert "Error 1" in d["errors"]
        assert "Warning 1" in d["warnings"]
        assert "Info 1" in d["info"]


class TestConfigValidation:
    """Test configuration validation methods"""
    
    def test_validate_returns_list_for_backward_compatibility(self):
        """validate() should return a list for backward compatibility"""
        errors = Config.validate()
        assert isinstance(errors, list)
    
    def test_validate_comprehensive_returns_result(self):
        """validate_comprehensive() should return ConfigValidationResult"""
        result = Config.validate_comprehensive()
        assert isinstance(result, ConfigValidationResult)
    
    def test_missing_llm_api_key_detected(self):
        """Should detect missing LLM_API_KEY"""
        with patch.dict(os.environ, {'LLM_API_KEY': '', 'ZEP_API_KEY': 'test_key'}):
            from importlib import reload
            import app.config as config_module
            reload(config_module)
            
            result = config_module.Config.validate_comprehensive()
            
            has_llm_error = any('LLM_API_KEY' in e for e in result.errors)
            assert has_llm_error, "Should detect missing LLM_API_KEY"
    
    def test_missing_zep_api_key_detected(self):
        """Should detect missing ZEP_API_KEY"""
        with patch.dict(os.environ, {'LLM_API_KEY': 'test_key', 'ZEP_API_KEY': ''}):
            from importlib import reload
            import app.config as config_module
            reload(config_module)
            
            result = config_module.Config.validate_comprehensive()
            
            has_zep_error = any('ZEP_API_KEY' in e for e in result.errors)
            assert has_zep_error, "Should detect missing ZEP_API_KEY"
    
    def test_placeholder_api_key_detected(self):
        """Should detect placeholder API keys"""
        with patch.dict(os.environ, {
            'LLM_API_KEY': 'your_api_key_here',
            'ZEP_API_KEY': 'test_key'
        }):
            from importlib import reload
            import app.config as config_module
            reload(config_module)
            
            result = config_module.Config.validate_comprehensive()
            
            has_placeholder_error = any('示例值' in e or 'placeholder' in e.lower() for e in result.errors)
            assert has_placeholder_error, "Should detect placeholder API key"


class TestURLValidation:
    """Test URL validation"""
    
    def test_valid_url_passes(self):
        """Valid URLs should pass validation"""
        with patch.dict(os.environ, {
            'LLM_API_KEY': 'test_key_12345',
            'ZEP_API_KEY': 'test_key_12345',
            'LLM_BASE_URL': 'https://api.openai.com/v1'
        }):
            from importlib import reload
            import app.config as config_module
            reload(config_module)
            
            result = config_module.Config.validate_comprehensive()
            
            url_in_info = any('LLM_BASE_URL' in i for i in result.info)
            assert url_in_info or len(result.errors) == 0
    
    def test_invalid_url_scheme_detected(self):
        """Invalid URL scheme should be detected"""
        with patch.dict(os.environ, {
            'LLM_API_KEY': 'test_key_12345',
            'ZEP_API_KEY': 'test_key_12345',
            'LLM_BASE_URL': 'ftp://invalid.com'
        }):
            from importlib import reload
            import app.config as config_module
            reload(config_module)
            
            result = config_module.Config.validate_comprehensive()
            
            has_url_error = any('LLM_BASE_URL' in e and ('协议' in e or 'scheme' in e.lower()) for e in result.errors)
            assert has_url_error, "Should detect invalid URL scheme"
    
    def test_url_without_scheme_detected(self):
        """URL without scheme should be detected"""
        with patch.dict(os.environ, {
            'LLM_API_KEY': 'test_key_12345',
            'ZEP_API_KEY': 'test_key_12345',
            'LLM_BASE_URL': 'api.openai.com/v1'  
        }):
            from importlib import reload
            import app.config as config_module
            reload(config_module)
            
            result = config_module.Config.validate_comprehensive()
            
            has_url_error = any('LLM_BASE_URL' in e for e in result.errors)
            assert has_url_error, "Should detect URL without scheme"


class TestNumericValidation:
    """Test numeric range validation"""
    
    def test_zero_max_rounds_detected(self):
        """Zero max rounds should be detected"""
        with patch.dict(os.environ, {
            'LLM_API_KEY': 'test_key_12345',
            'ZEP_API_KEY': 'test_key_12345',
            'OASIS_DEFAULT_MAX_ROUNDS': '0'
        }):
            from importlib import reload
            import app.config as config_module
            reload(config_module)
            
            result = config_module.Config.validate_comprehensive()
            
            has_rounds_error = any('OASIS_DEFAULT_MAX_ROUNDS' in e for e in result.errors)
            assert has_rounds_error, "Should detect zero max rounds"
    
    def test_negative_max_rounds_detected(self):
        """Negative max rounds should be detected"""
        with patch.dict(os.environ, {
            'LLM_API_KEY': 'test_key_12345',
            'ZEP_API_KEY': 'test_key_12345',
            'OASIS_DEFAULT_MAX_ROUNDS': '-10'
        }):
            from importlib import reload
            import app.config as config_module
            reload(config_module)
            
            result = config_module.Config.validate_comprehensive()
            
            has_rounds_error = any('OASIS_DEFAULT_MAX_ROUNDS' in e for e in result.errors)
            assert has_rounds_error, "Should detect negative max rounds"
    
    def test_large_max_rounds_warns(self):
        """Large max rounds should trigger warning"""
        with patch.dict(os.environ, {
            'LLM_API_KEY': 'test_key_12345',
            'ZEP_API_KEY': 'test_key_12345',
            'OASIS_DEFAULT_MAX_ROUNDS': '2000'
        }):
            from importlib import reload
            import app.config as config_module
            reload(config_module)
            
            result = config_module.Config.validate_comprehensive()
            
            has_rounds_warning = any('OASIS_DEFAULT_MAX_ROUNDS' in w for w in result.warnings)
            assert has_rounds_warning, "Should warn about large max rounds"


class TestDirectoryValidation:
    """Test directory validation"""
    
    def test_directory_created_if_not_exists(self):
        """Should create directory if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            upload_dir = os.path.join(tmpdir, 'new_uploads')
            
            with patch.dict(os.environ, {
                'LLM_API_KEY': 'test_key_12345',
                'ZEP_API_KEY': 'test_key_12345',
            }):
                with patch.object(Config, 'UPLOAD_FOLDER', upload_dir):
                    result = Config.validate_comprehensive()
                    
                   


class TestConfigSummary:
    """Test configuration summary"""
    
    def test_get_config_summary(self):
        """Should return configuration summary without sensitive data"""
        summary = Config.get_config_summary()
        
        assert 'llm' in summary
        assert 'zep' in summary
        assert 'simulation' in summary
        assert 'debug' in summary
        
        summary_str = str(summary)
        assert 'api_key' not in summary_str.lower()
        assert 'secret' not in summary_str.lower()


class TestStartupValidation:
    """Test startup validation function"""
    
    def test_validate_on_startup_returns_bool(self):
        """validate_on_startup should return boolean"""
        with patch.dict(os.environ, {
            'LLM_API_KEY': 'test_key_12345',
            'ZEP_API_KEY': 'test_key_12345',
        }):
            from importlib import reload
            import app.config as config_module
            reload(config_module)
            
            result = validate_on_startup()
            assert isinstance(result, bool)


class TestDebugMode:
    """Test debug mode detection"""
    
    def test_debug_mode_warning(self):
        """Debug mode should trigger warning"""
        with patch.dict(os.environ, {
            'LLM_API_KEY': 'test_key_12345',
            'ZEP_API_KEY': 'test_key_12345',
            'FLASK_DEBUG': 'True'
        }):
            from importlib import reload
            import app.config as config_module
            reload(config_module)
            
            result = config_module.Config.validate_comprehensive()
            
            has_debug_warning = any('DEBUG' in w or 'debug' in w for w in result.warnings)
            assert has_debug_warning, "Should warn about debug mode"


class TestConfigConsistency:
    """Test configuration consistency checks"""
    
    def test_valid_model_name_passes(self):
        """Valid model names should pass"""
        with patch.dict(os.environ, {
            'LLM_API_KEY': 'test_key_12345',
            'ZEP_API_KEY': 'test_key_12345',
            'LLM_MODEL_NAME': 'gpt-4o-mini'
        }):
            from importlib import reload
            import app.config as config_module
            reload(config_module)
            
            result = config_module.Config.validate_comprehensive()
            
            has_model_info = any('LLM_MODEL_NAME' in i for i in result.info)
            assert has_model_info, "Should show valid model name in info"
    
    def test_unusual_model_name_warns(self):
        """Unusual model names should trigger warning"""
        with patch.dict(os.environ, {
            'LLM_API_KEY': 'test_key_12345',
            'ZEP_API_KEY': 'test_key_12345',
            'LLM_MODEL_NAME': 'UNUSUAL_MODEL_FORMAT'
        }):
            from importlib import reload
            import app.config as config_module
            reload(config_module)
            
            result = config_module.Config.validate_comprehensive()
            
            has_model_warning = any('LLM_MODEL_NAME' in w for w in result.warnings)
            assert has_model_warning, "Should warn about unusual model name format"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])