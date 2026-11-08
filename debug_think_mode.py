"""实验：测试关闭 deepseek-v4-flash 思考模式的不同参数方式"""
import sys
sys.path.insert(0, ".")

from config import settings
from openai import OpenAI

client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

prompt = "请用一句话介绍你自己，不要思考，直接回答。"

variants = {
    "baseline(当前代码方式)": {},
    "thinking_false": {"extra_body": {"thinking": False}},
    "reasoning_effort_none": {"reasoning_effort": "none"},
}

for name, extra in variants.items():
    print(f"\n=== {name} ===")
    try:
        kwargs = dict(model=settings.openai_model, messages=[{"role": "user", "content": prompt}], temperature=0.7, **extra)
        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        rc = getattr(msg, "reasoning_content", None)
        print("finish_reason:", resp.choices[0].finish_reason)
        print("content len:", len(msg.content or ""))
        print("content head:", repr((msg.content or "")[:120]))
        print("reasoning len:", len(rc or ""))
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e)[:200])