"""Document proofreading — LLM-powered grammar and spelling check."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from services.llm_service import LLMService
from utils import get_logger

logger = get_logger(__name__)


@dataclass
class ProofreadIssue:
    """A single proofreading issue."""
    line: int
    column: int
    original: str
    suggestion: str
    issue_type: str  # "grammar", "spelling", "punctuation"
    context: str
    accepted: bool | None = None  # None = pending, True = accepted, False = rejected


class Proofreader:
    """Proofreads Chinese text using LLM."""

    SYSTEM_PROMPT = """你是一位中文文档校对专家。请仔细阅读以下文本，找出其中的语法错误、错别字、标点符号错误。

对于每个错误，请按以下 JSON 格式输出：
{
  "issues": [
    {
      "line": 行号,
      "column": 列号,
      "original": "错误文本",
      "suggestion": "建议修改",
      "type": "grammar|spelling|punctuation",
      "context": "包含错误的上下文（30字左右）"
    }
  ]
}

要求：
- 只输出 JSON，不要其他解释
- 重点关注"的/地/得"误用、错别字、标点错误
- 忽略口语化表达（这是播客转录文本）
- 如果没有错误，输出 {"issues": []}"""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm = llm_service or LLMService()

    async def proofread(self, text: str) -> list[ProofreadIssue]:
        """Proofread text and return list of issues."""
        prompt = f"{self.SYSTEM_PROMPT}\n\n文本：\n{text}"
        
        try:
            response = await self.llm.generate(prompt)
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in proofreading response")
                return []
            
            data = json.loads(json_match.group())
            issues = []
            for item in data.get("issues", []):
                issues.append(ProofreadIssue(
                    line=item.get("line", 0),
                    column=item.get("column", 0),
                    original=item.get("original", ""),
                    suggestion=item.get("suggestion", ""),
                    issue_type=item.get("type", "grammar"),
                    context=item.get("context", ""),
                ))
            
            logger.info("Proofreading complete", issues_found=len(issues))
            return issues
        except Exception as e:
            logger.error("Proofreading failed", error=str(e))
            return []

    def apply_corrections(self, text: str, issues: list[ProofreadIssue]) -> str:
        """Apply all accepted corrections to text."""
        corrected = text
        # Sort by position (reverse) to avoid offset issues
        accepted = [i for i in issues if i.accepted is True]
        accepted.sort(key=lambda x: (x.line, x.column), reverse=True)
        
        for issue in accepted:
            corrected = corrected.replace(issue.original, issue.suggestion, 1)
        
        return corrected
