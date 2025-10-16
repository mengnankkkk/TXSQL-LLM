"""
LLM API客户端Python实现
支持OpenAI、本地模型和缓存机制
"""

import os
import json
import time
import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass
import requests
from functools import lru_cache


@dataclass
class GenerationConfig:
    """LLM生成配置"""
    model_name: str = "gpt-4"
    temperature: float = 0.3
    max_tokens: int = 2000
    num_candidates: int = 3
    use_few_shot: bool = True


@dataclass
class LLMResponse:
    """LLM响应"""
    candidates: List[str]
    raw_response: str
    success: bool
    error_message: str = ""
    latency_ms: float = 0.0


class LLMClient:
    """LLM客户端统一接口"""

    def __init__(self, provider: str = "openai", api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.cache = {}
        self.stats = {"hits": 0, "misses": 0, "total_calls": 0}

    def generate(self, prompt: str, config: GenerationConfig) -> LLMResponse:
        """生成SQL重写候选"""
        self.stats["total_calls"] += 1

        # 检查缓存
        cache_key = self._get_cache_key(prompt, config)
        if cache_key in self.cache:
            self.stats["hits"] += 1
            return self.cache[cache_key]

        self.stats["misses"] += 1

        # 调用API
        start_time = time.time()
        try:
            if self.provider == "openai":
                response = self._call_openai(prompt, config)
            elif self.provider == "local":
                response = self._call_local_model(prompt, config)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

            response.latency_ms = (time.time() - start_time) * 1000
            self.cache[cache_key] = response
            return response

        except Exception as e:
            return LLMResponse(
                candidates=[],
                raw_response="",
                success=False,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )

    def _call_openai(self, prompt: str, config: GenerationConfig) -> LLMResponse:
        """调用OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "n": config.num_candidates
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        response.raise_for_status()

        result = response.json()
        candidates = [
            choice["message"]["content"]
            for choice in result["choices"]
        ]

        # 提取SQL代码块
        candidates = [self._extract_sql(c) for c in candidates]

        return LLMResponse(
            candidates=candidates,
            raw_response=json.dumps(result),
            success=True
        )

    def _call_local_model(self, prompt: str, config: GenerationConfig) -> LLMResponse:
        """调用本地模型API"""
        endpoint = os.getenv("LOCAL_MODEL_ENDPOINT", "http://localhost:8000/generate")

        data = {
            "prompt": prompt,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "n": config.num_candidates
        }

        response = requests.post(endpoint, json=data, timeout=120)
        response.raise_for_status()

        result = response.json()
        candidates = result.get("candidates", [])

        return LLMResponse(
            candidates=candidates,
            raw_response=json.dumps(result),
            success=True
        )

    def _extract_sql(self, text: str) -> str:
        """从文本中提取SQL代码块"""
        # 寻找```sql ... ```代码块
        if "```sql" in text:
            start = text.find("```sql") + 6
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()

        # 寻找```...```代码块
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()

        # 没有代码块标记，返回整个文本
        return text.strip()

    def _get_cache_key(self, prompt: str, config: GenerationConfig) -> str:
        """生成缓存键"""
        key_str = f"{prompt}|{config.model_name}|{config.temperature}|{config.num_candidates}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0
        return {
            **self.stats,
            "hit_rate": hit_rate,
            "cache_size": len(self.cache)
        }

    def clear_cache(self):
        """清除缓存"""
        self.cache.clear()


if __name__ == "__main__":
    # 测试代码
    client = LLMClient(provider="openai")

    test_prompt = """
    Rewrite the following SQL query for better performance:

    SELECT * FROM orders WHERE order_id IN (SELECT order_id FROM order_items WHERE price > 100);
    """

    config = GenerationConfig(num_candidates=2)
    response = client.generate(test_prompt, config)

    if response.success:
        print(f"Generated {len(response.candidates)} candidates:")
        for i, candidate in enumerate(response.candidates, 1):
            print(f"\n--- Candidate {i} ---")
            print(candidate)
        print(f"\nLatency: {response.latency_ms:.2f}ms")
    else:
        print(f"Error: {response.error_message}")
