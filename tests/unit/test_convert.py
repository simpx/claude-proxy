"""
数据驱动的格式转换测试
使用JSONC案例文件测试Claude到OpenAI的API格式转换
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch
import asyncio

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.claude_proxy.providers.openai import OpenAIProvider
from src.claude_proxy.models.claude import ClaudeMessagesRequest
from .conversion_runner import ConversionCaseLoader, ConversionTestValidator


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
    def test_request_conversion(self, case):
        """测试Claude请求到OpenAI请求的转换"""
        # 设置测试环境变量，可被case.env覆盖
        test_env = self.TEST_ENV_VARS.copy()
        if hasattr(case, 'env') and case.env:
            test_env.update(case.env)
        
        with patch.dict(os.environ, test_env, clear=False):
            # 清除缓存的设置并重新加载配置
            import src.claude_proxy.config as config_module
            config_module._settings = None
            
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
            and case.expected_claude_response
            and not isinstance(case.openai_response, list))  # Exclude streaming (list format)
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
            and case.expected_openai_request
            and 'model' in case.claude_request
            and 'model' in case.expected_openai_request)
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
        if (case.openai_response 
            and case.expected_claude_response
            and isinstance(case.openai_response, list)  # Streaming is indicated by list format
            and isinstance(case.expected_claude_response, list))
    ])
    @pytest.mark.asyncio
    async def test_streaming_conversion(self, case):
        """测试流式响应转换"""
        # 设置测试环境变量，可被case.env覆盖
        test_env = self.TEST_ENV_VARS.copy()
        if hasattr(case, 'env') and case.env:
            test_env.update(case.env)
        
        with patch.dict(os.environ, test_env, clear=False):
            import src.claude_proxy.config as config_module
            config_module._settings = None
            
            mock_client = self._create_mock_streaming_client(case.openai_response)
            
            provider = OpenAIProvider(
                api_key="test-key",
                base_url="https://api.openai.com/v1", 
                timeout=30,
                client=mock_client
            )
            
            from src.claude_proxy.models.claude import ClaudeMessagesRequest
            if case.claude_request:
                claude_request_obj = ClaudeMessagesRequest(**case.claude_request)
            else:
                claude_request_obj = ClaudeMessagesRequest(
                    model="claude-3-haiku-20240307",
                    max_tokens=100,
                    messages=[{"role": "user", "content": "test"}]
                )
            
            actual_events = []
            async for sse_event in provider.stream_complete(claude_request_obj, "test-request-id"):
                event = self._parse_sse_event(sse_event)
                if event:
                    actual_events.append(event)
            
            self._validate_streaming_events(
                actual_events,
                case.expected_claude_response, 
                case.file_name,
                case.file_path
            )
    
    def _create_mock_streaming_client(self, openai_chunks):
        """创建模拟流式HTTP客户端"""
        import json
        from unittest.mock import AsyncMock, MagicMock
        
        sse_lines = []
        for chunk in openai_chunks:
            sse_lines.append(f"data: {json.dumps(chunk)}")
        sse_lines.append("data: [DONE]")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        async def mock_aiter_lines():
            for line in sse_lines:
                yield line
        
        mock_response.aiter_lines = mock_aiter_lines
        
        class MockStreamContext:
            def __init__(self, response):
                self.response = response
            
            async def __aenter__(self):
                return self.response
            
            async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
                return None
        
        mock_client = AsyncMock()
        
        def mock_stream(*_args, **_kwargs):
            return MockStreamContext(mock_response)
        
        mock_client.stream = mock_stream
        
        return mock_client
    
    def _parse_sse_event(self, sse_event_str):
        """解析provider返回的SSE事件字符串为JSON对象"""
        import json
        
        if not sse_event_str.strip():
            return None
        
        lines = sse_event_str.strip().split('\n')
        data_line = None
        
        for line in lines:
            if line.startswith('data: '):
                data_line = line[6:]
                break
        
        if data_line:
            try:
                return json.loads(data_line)
            except json.JSONDecodeError:
                return None
        
        return None
    
    def _validate_streaming_events(self, actual_events, expected_events, case_name, case_file):
        """验证流式事件序列"""
        if len(actual_events) != len(expected_events):
            pytest.fail(f"Streaming event count mismatch in '{case_name}': expected {len(expected_events)}, got {len(actual_events)}\nCase file: {case_file}")
        
        for i, (actual, expected) in enumerate(zip(actual_events, expected_events)):
            if actual.get("type") != expected.get("type"):
                pytest.fail(f"Event {i} type mismatch in '{case_name}': expected {expected.get('type')}, got {actual.get('type')}\nCase file: {case_file}")
            
            if actual["type"] == "content_block_start":
                actual_block = actual.get("content_block", {})
                expected_block = expected.get("content_block", {})
                
                if actual_block.get("type") != expected_block.get("type"):
                    pytest.fail(f"Event {i} content_block type mismatch in '{case_name}': expected {expected_block.get('type')}, got {actual_block.get('type')}\nCase file: {case_file}")
                
                if actual_block.get("text") != expected_block.get("text"):
                    pytest.fail(f"Event {i} content_block text mismatch in '{case_name}': expected '{expected_block.get('text')}', got '{actual_block.get('text')}'\nCase file: {case_file}")
            
            elif actual["type"] == "content_block_delta":
                actual_text = actual.get("delta", {}).get("text", "")
                expected_text = expected.get("delta", {}).get("text", "")
                if actual_text != expected_text:
                    pytest.fail(f"Event {i} delta text mismatch in '{case_name}': expected '{expected_text}', got '{actual_text}'\nCase file: {case_file}")
            
            elif actual["type"] == "message_delta":
                actual_stop_reason = actual.get("delta", {}).get("stop_reason")
                expected_stop_reason = expected.get("delta", {}).get("stop_reason") 
                if actual_stop_reason != expected_stop_reason:
                    pytest.fail(f"Event {i} stop_reason mismatch in '{case_name}': expected '{expected_stop_reason}', got '{actual_stop_reason}'\nCase file: {case_file}")
                
                actual_usage = actual.get("usage", {})
                expected_usage = expected.get("usage", {})
                if expected_usage.get("output_tokens") is not None:
                    actual_tokens = actual_usage.get("output_tokens")
                    expected_tokens = expected_usage.get("output_tokens")
                    if actual_tokens != expected_tokens:
                        pytest.fail(f"Event {i} output_tokens mismatch in '{case_name}': expected {expected_tokens}, got {actual_tokens}\nCase file: {case_file}")
            
            elif actual["type"] == "message_start":
                actual_msg = actual.get("message", {})
                expected_msg = expected.get("message", {})
                
                if expected_msg.get("model") and actual_msg.get("model") != expected_msg.get("model"):
                    pytest.fail(f"Event {i} model mismatch in '{case_name}': expected {expected_msg.get('model')}, got {actual_msg.get('model')}\nCase file: {case_file}")
                
                if actual_msg.get("role") != expected_msg.get("role"):
                    pytest.fail(f"Event {i} role mismatch in '{case_name}': expected {expected_msg.get('role')}, got {actual_msg.get('role')}\nCase file: {case_file}")
    
    @classmethod
    def teardown_class(cls):
        """测试类清理"""
        print(f"\n✅ Completed testing {len(cls.cases)} conversion cases")


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v", "--tb=short"])