"""调试嘉宾提取正则表达式."""

import re

# 测试用例
test_cases = [
    ("邀请历史学家王明来作客，与他对谈冷战时期的外交政策。", "历史学家王明"),
    ("邀请张三来聊聊", "张三"),
    ("邀请了李四来做客", "李四"),
    ("邀请王五作客", "王五"),
    ("邀请著名学者赵六来作客", "著名学者赵六"),
]

# 方案3: 更精确的分词匹配
pattern3 = r"邀请[了]?\s*([^，。\n\s]+(?:\s+[^，。\n\s]+){0,5})\s+(?:来|作|为|做客|作客)"

# 方案4: 排除"来"字的匹配
pattern4 = r"邀请[了]?\s*((?:[^，。\n\s]+\s+)*[^，。\n\s来]+)(?:\s*(?:来|作|为|做客|作客))"

# 方案5: 使用 split 方式

def extract_guest_v5(description: str) -> str:
    """使用字符串分割提取嘉宾."""
    import re
    # 找到"邀请"后的内容，直到"来"或"作客"等词
    match = re.search(r"邀请[了]?\s*(.+?)(?:\s+来|\s+作客|\s+做客|\s+作|，|。)", description)
    if match:
        return match.group(1).strip()
    return ""

print("=" * 60)
print("方案3: 精确匹配")
print("=" * 60)
for desc, expected in test_cases:
    matches = re.findall(pattern3, desc)
    result = matches[0] if matches else ""
    status = "✅" if result == expected else "❌"
    print(f"{status} '{desc}'")
    print(f"   结果: '{result}' | 期望: '{expected}'")

print("\n" + "=" * 60)
print("方案4: 排除来字")
print("=" * 60)
for desc, expected in test_cases:
    matches = re.findall(pattern4, desc)
    result = matches[0].strip() if matches else ""
    status = "✅" if result == expected else "❌"
    print(f"{status} '{desc}'")
    print(f"   结果: '{result}' | 期望: '{expected}'")

print("\n" + "=" * 60)
print("方案5: 字符串分割")
print("=" * 60)
for desc, expected in test_cases:
    result = extract_guest_v5(desc)
    status = "✅" if result == expected else "❌"
    print(f"{status} '{desc}'")
    print(f"   结果: '{result}' | 期望: '{expected}'")
