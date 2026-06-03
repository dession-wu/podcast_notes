"""测试 DeepSeek API 连接."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from services.llm_service import LLMService
from config.settings import LLMProvider
from utils import configure_logging

configure_logging('INFO')

print('正在测试 DeepSeek API 连接...')
print('Base URL: https://api.deepseek.com')
print('Model: deepseek-chat')
print()

try:
    llm = LLMService(provider=LLMProvider.OPENAI)
    print('LLMService 初始化成功')
    
    print('正在发送测试请求...')
    response = llm.generate(
        prompt='你好，请用一句话介绍你自己',
        system_prompt='你是一个友好的助手',
        temperature=0.7,
    )
    print('API 调用成功')
    print(f'响应: {response[:100]}...')
    
except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()
