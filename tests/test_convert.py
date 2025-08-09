"""
数据驱动的格式转换测试
使用JSONC案例文件测试Claude到OpenAI的API格式转换
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.claude_proxy.providers.openai import OpenAIProvider
from src.claude_proxy.models.claude import ClaudeMessagesRequest, ClaudeMessage
from src.claude_proxy.config import get_settings
from tests.conversion_runner import ConversionCaseLoader, ConversionTestValidator


class TestConvertCases:
    """基于数据驱动的格式转换测试"""
    
    # 预设的测试环境变量
    TEST_ENV_VARS = {
        'OPENAI_API_KEY': 'sk-test-key-12345',
        'OPENAI_BASE_URL': 'https://api.openai.com/v1',
        'CLAUDE_PROXY_BIG_MODEL': 'gpt-4o',
        'CLAUDE_PROXY_SMALL_MODEL': 'gpt-4o-mini',
        'CLAUDE_PROXY_LOG_LEVEL': 'INFO',
        'CLAUDE_PROXY_HOST': '0.0.0.0',
        'CLAUDE_PROXY_PORT': '8080',
    }
    
    @classmethod
    def setup_class(cls):
        """测试类初始化"""
        cls.loader = ConversionCaseLoader()
        cls.validator = ConversionTestValidator()
        cls.cases = cls.loader.load_all_cases()
        
        print(f"\n🧪 Loaded {len(cls.cases)} conversion test cases")
    
    @pytest.mark.parametrize("case", [
        pytest.param(case, id=f"{case.category}::{case.file_name}") 
        for case in ConversionCaseLoader().load_all_cases()
        if (case.test_config.get('test_request_conversion', True) 
            and case.claude_request 
            and case.expected_openai_request)
    ])
    def test_request_convert(self, case):
        """测试Claude请求到OpenAI请求的转换"""
        # 设置测试环境变量，可被case.env覆盖
        test_env = self.TEST_ENV_VARS.copy()
        if hasattr(case, 'env') and case.env:
            test_env.update(case.env)
        
        with patch.dict(os.environ, test_env, clear=False):
            # 清除缓存的设置并重新加载配置
            import src.claude_proxy.config as config_module
            config_module._settings = None
            settings = config_module.get_settings()
            
            # 创建OpenAI provider实例
            provider = OpenAIProvider(
                api_key="test-key",
                base_url="https://api.openai.com/v1",
                timeout=30
            )
            
            # 将Claude请求转换为Pydantic模型
            claude_request = ClaudeMessagesRequest(**case.claude_request)
            
            # 执行转换
            actual_openai_request = provider.convert_request(claude_request)
            
            # 验证转换结果
            is_valid, errors = self.validator.validate_request_conversion(
                case.claude_request,
                actual_openai_request,
                case.expected_openai_request
            )
            
            # 断言验证结果
            if not is_valid:
                error_msg = f"Request conversion failed for case '{case.file_name}':\n"
                for error in errors:
                    error_msg += f"  - {error}\n"
                error_msg += f"\nExpected: {case.expected_openai_request}\n"
                error_msg += f"Actual: {actual_openai_request}\n"
                error_msg += f"Case file: {case.file_path}"
                
                pytest.fail(error_msg)
    
    @pytest.mark.parametrize("case", [
        pytest.param(case, id=f"{case.category}::{case.file_name}")
        for case in ConversionCaseLoader().load_all_cases()
        if (case.test_config.get('test_response_conversion', True) 
            and case.openai_response 
            and case.expected_claude_response)
    ])
    def test_response_conversion(self, case):
        """测试OpenAI响应到Claude响应的转换"""
        # 设置测试环境变量，可被case.env覆盖
        test_env = self.TEST_ENV_VARS.copy()
        if hasattr(case, 'env') and case.env:
            test_env.update(case.env)
        
        with patch.dict(os.environ, test_env, clear=False):
            # 清除缓存的设置并重新加载配置
            import src.claude_proxy.config as config_module
            config_module._settings = None
            settings = config_module.get_settings()
            
            # 创建OpenAI provider实例
            provider = OpenAIProvider(
                api_key="test-key",
                base_url="https://api.openai.com/v1",
                timeout=30
            )
            
            # 创建原始Claude请求（如果有的话）
            claude_request = None
            if case.claude_request:
                claude_request = ClaudeMessagesRequest(**case.claude_request)
            
            # 执行响应转换
            actual_claude_response = provider.convert_response(
                case.openai_response,
                claude_request
            )
        
        # 验证转换结果
        is_valid, errors = self.validator.validate_response_conversion(
            case.openai_response,
            actual_claude_response.model_dump(),
            case.expected_claude_response
        )
        
        # 断言验证结果
        if not is_valid:
            error_msg = f"Response conversion failed for case '{case.file_name}':\n"
            for error in errors:
                error_msg += f"  - {error}\n"
            error_msg += f"\nExpected: {case.expected_claude_response}\n"
            error_msg += f"Actual: {actual_claude_response.model_dump()}\n"
            error_msg += f"Case file: {case.file_path}"
            
            pytest.fail(error_msg)
    
    @pytest.mark.parametrize("case", [
        pytest.param(case, id=f"{case.category}::{case.file_name}")
        for case in ConversionCaseLoader().load_all_cases()
        if (case.test_config.get('test_model_mapping', True) 
            and case.claude_request 
            and case.expected_openai_request)
    ])
    def test_model_mapping(self, case):
        """测试模型映射是否正确"""
        # 设置测试环境变量，可被case.env覆盖
        test_env = self.TEST_ENV_VARS.copy()
        if hasattr(case, 'env') and case.env:
            test_env.update(case.env)
        
        with patch.dict(os.environ, test_env, clear=False):
            # 清除缓存的设置并重新加载配置
            import src.claude_proxy.config as config_module
            config_module._settings = None
            
            from src.claude_proxy.config import map_claude_model
            
            claude_model = case.claude_request['model']
            expected_openai_model = case.expected_openai_request['model']
            actual_mapped_model = map_claude_model(claude_model)
        
        # 验证模型映射
        is_valid, errors = self.validator.validate_model_mapping(
            claude_model,
            actual_mapped_model, 
            expected_openai_model
        )
        
        if not is_valid:
            error_msg = f"Model mapping failed for case '{case.file_name}':\n"
            for error in errors:
                error_msg += f"  - {error}\n"
            error_msg += f"Case file: {case.file_path}"
            
            pytest.fail(error_msg)
    
    @pytest.mark.parametrize("case", [
        pytest.param(case, id=f"{case.category}::{case.file_name}")
        for case in ConversionCaseLoader().load_all_cases()
        if (case.test_config.get('test_streaming_conversion', False)
            and case.openai_streaming_response
            and case.expected_claude_streaming_response)
    ])
    def test_streaming_conversion(self, case):
        """测试流式响应转换"""
        # 这是一个更复杂的测试，需要模拟SSE流
        # 暂时标记为TODO，需要实现流式转换逻辑后再完成
        pytest.skip("Streaming conversion test not implemented yet")
    
    
    @classmethod
    def teardown_class(cls):
        """测试类清理"""
        print(f"\n✅ Completed testing {len(cls.cases)} conversion cases")


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v", "--tb=short"])