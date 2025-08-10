"""
数据驱动的转换测试运行器
加载YAML测试案例文件并执行转换测试
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
import json


@dataclass
class ConversionTestCase:
    """转换测试案例数据类"""
    file_name: str
    description: str
    category: str
    tags: List[str]
    claude_request: Optional[Dict[str, Any]]
    expected_openai_request: Optional[Dict[str, Any]]
    openai_response: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    expected_claude_response: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    test_config: Optional[Dict[str, bool]] = None
    env: Optional[Dict[str, str]] = None
    file_path: str = ""


class ConversionCaseLoader:
    """测试案例加载器"""
    
    def __init__(self, cases_dir: str = "tests/unit/convert_cases"):
        self.cases_dir = Path(cases_dir)
        self.cases: List[ConversionTestCase] = []
    
    def load_all_cases(self) -> List[ConversionTestCase]:
        """加载所有测试案例"""
        self.cases.clear()
        
        if not self.cases_dir.exists():
            raise FileNotFoundError(f"Cases directory not found: {self.cases_dir}")
        
        # 递归查找所有JSONC文件
        jsonc_files = list(self.cases_dir.rglob("*.jsonc"))
        
        for jsonc_file in jsonc_files:
            try:
                case = self._load_case_file(jsonc_file)
                if case:
                    self.cases.append(case)
            except Exception as e:
                print(f"❌ Failed to load case file {jsonc_file}: {e}")
        
        print(f"✅ Loaded {len(self.cases)} conversion test cases")
        return self.cases
    
    def _load_case_file(self, file_path: Path) -> Optional[ConversionTestCase]:
        """加载单个案例文件 (支持JSONC格式)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 移除JSONC注释
            content = self._remove_jsonc_comments(content)
            data = json.loads(content)
            
            # 验证至少有一个必需字段组合
            has_request_test = 'claude_request' in data and 'expected_openai_request' in data
            has_response_test = 'openai_response' in data and 'expected_claude_response' in data
            
            if not (has_request_test or has_response_test):
                raise ValueError(f"Must have either (claude_request + expected_openai_request) or (openai_response + expected_claude_response)")
            
            # 推断category from file path
            category = file_path.parent.name
            file_name = file_path.stem  # 文件名不带扩展名
            
            # 处理model字段：当request和expected都不含model时，给它们添加默认值
            claude_request = data.get('claude_request')
            expected_openai_request = data.get('expected_openai_request')
            openai_response = data.get('openai_response')
            expected_claude_response = data.get('expected_claude_response')
            
            # 处理请求转换的model字段
            should_skip_model_mapping = False
            if claude_request and expected_openai_request:
                if 'model' not in claude_request and 'model' not in expected_openai_request:
                    # 两个都没有model，添加默认值，并标记不测试model映射
                    claude_request = claude_request.copy()
                    expected_openai_request = expected_openai_request.copy()
                    claude_request['model'] = 'claude-3-haiku-20240307'
                    expected_openai_request['model'] = 'gpt-4o-mini'
                    should_skip_model_mapping = True
            
            # 处理响应转换的model字段（跳过streaming响应的list格式）
            if (openai_response and expected_claude_response 
                and not isinstance(openai_response, list) 
                and not isinstance(expected_claude_response, list)):
                if 'model' not in openai_response and 'model' not in expected_claude_response:
                    # 两个都没有model，添加默认值
                    openai_response = openai_response.copy()
                    expected_claude_response = expected_claude_response.copy()
                    openai_response['model'] = 'gpt-4o-mini'
                    expected_claude_response['model'] = 'claude-3-haiku-20240307'
                    should_skip_model_mapping = True
            
            # 更新test_config
            test_config = data.get('test_config', {}).copy()
            if should_skip_model_mapping:
                test_config['test_model_mapping'] = False
            
            return ConversionTestCase(
                file_name=file_name,
                description=data.get('description', ''),
                category=category,
                tags=data.get('tags', []),
                claude_request=claude_request,
                expected_openai_request=expected_openai_request,
                openai_response=openai_response,
                expected_claude_response=expected_claude_response,
                test_config=test_config,
                env=data.get('env', {}),
                file_path=str(file_path)
            )
        except Exception as e:
            print(f"❌ Error loading {file_path}: {e}")
            return None
    
    def _remove_jsonc_comments(self, content: str) -> str:
        """移除JSONC中的注释"""
        # 移除单行注释 // ...
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        
        # 移除多行注释 /* ... */
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        return content
    
    def get_cases_by_category(self, category: str) -> List[ConversionTestCase]:
        """按类别筛选案例"""
        return [case for case in self.cases if case.category == category]
    
    def get_cases_by_tag(self, tag: str) -> List[ConversionTestCase]:
        """按标签筛选案例"""
        return [case for case in self.cases if tag in case.tags]


class ConversionTestValidator:
    """转换测试验证器"""
    
    @staticmethod
    def validate_request_conversion(
        claude_request: Dict[str, Any],
        actual_openai_request: Dict[str, Any], 
        expected_openai_request: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """验证请求转换是否正确"""
        errors = []
        
        # 验证模型映射
        if actual_openai_request.get('model') != expected_openai_request.get('model'):
            errors.append(f"Model mismatch: expected {expected_openai_request.get('model')}, got {actual_openai_request.get('model')}")
        
        # 验证消息数组
        actual_messages = actual_openai_request.get('messages', [])
        expected_messages = expected_openai_request.get('messages', [])
        
        if len(actual_messages) != len(expected_messages):
            errors.append(f"Messages count mismatch: expected {len(expected_messages)}, got {len(actual_messages)}")
        else:
            for i, (actual_msg, expected_msg) in enumerate(zip(actual_messages, expected_messages)):
                if actual_msg != expected_msg:
                    errors.append(f"Message {i} mismatch: expected {expected_msg}, got {actual_msg}")
        
        # 验证其他参数
        for key in ['max_tokens', 'stream']:
            if key in expected_openai_request:
                if actual_openai_request.get(key) != expected_openai_request.get(key):
                    errors.append(f"{key} mismatch: expected {expected_openai_request.get(key)}, got {actual_openai_request.get(key)}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_response_conversion(
        openai_response: Dict[str, Any],
        actual_claude_response: Dict[str, Any],
        expected_claude_response: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """验证响应转换是否正确"""
        errors = []
        
        # 验证基本字段
        basic_fields = ['id', 'type', 'role', 'model', 'stop_reason']
        for field in basic_fields:
            if field in expected_claude_response:
                if actual_claude_response.get(field) != expected_claude_response.get(field):
                    errors.append(f"{field} mismatch: expected {expected_claude_response.get(field)}, got {actual_claude_response.get(field)}")
        
        # 验证内容转换
        actual_content = actual_claude_response.get('content', [])
        expected_content = expected_claude_response.get('content', [])
        
        if len(actual_content) != len(expected_content):
            errors.append(f"Content blocks count mismatch: expected {len(expected_content)}, got {len(actual_content)}")
        else:
            # 验证每个内容块的详细内容
            for i, (actual_block, expected_block) in enumerate(zip(actual_content, expected_content)):
                if actual_block.get('type') != expected_block.get('type'):
                    errors.append(f"Content block {i} type mismatch: expected {expected_block.get('type')}, got {actual_block.get('type')}")
                
                if actual_block.get('type') == 'text':
                    if actual_block.get('text') != expected_block.get('text'):
                        errors.append(f"Content block {i} text mismatch: expected '{expected_block.get('text')}', got '{actual_block.get('text')}'")
        
        # 验证使用统计转换
        actual_usage = actual_claude_response.get('usage', {})
        expected_usage = expected_claude_response.get('usage', {})
        
        for key in ['input_tokens', 'output_tokens']:
            if key in expected_usage:
                if actual_usage.get(key) != expected_usage.get(key):
                    errors.append(f"Usage {key} mismatch: expected {expected_usage.get(key)}, got {actual_usage.get(key)}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_model_mapping(claude_model: str, actual_openai_model: str, expected_openai_model: str) -> Tuple[bool, List[str]]:
        """验证模型映射是否正确"""
        if actual_openai_model != expected_openai_model:
            return False, [f"Model mapping incorrect: {claude_model} should map to {expected_openai_model}, got {actual_openai_model}"]
        return True, []


def print_case_summary(cases: List[ConversionTestCase]):
    """打印案例汇总信息"""
    print(f"\n📊 Test Cases Summary:")
    print(f"Total cases: {len(cases)}")
    
    # 按类别统计
    categories = {}
    for case in cases:
        categories[case.category] = categories.get(case.category, 0) + 1
    
    print("Categories:")
    for category, count in categories.items():
        print(f"  - {category}: {count} cases")
    
    # 按标签统计
    all_tags = set()
    for case in cases:
        all_tags.update(case.tags)
    
    print(f"Tags: {', '.join(sorted(all_tags))}")


if __name__ == "__main__":
    # 演示用法
    loader = ConversionCaseLoader()
    cases = loader.load_all_cases()
    print_case_summary(cases)
    
    # 打印案例详情
    for case in cases:
        print(f"\n📝 {case.file_name}")
        print(f"   Category: {case.category}")
        print(f"   Description: {case.description}")
        print(f"   Tags: {', '.join(case.tags)}")
        print(f"   File: {case.file_path}")