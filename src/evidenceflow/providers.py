from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .models import Assessment, Citation, EvidenceCase, Risk


class ProviderError(RuntimeError):
    pass


class TransientProviderError(ProviderError):
    pass


class AnalysisProvider(Protocol):
    def analyze(self, case: EvidenceCase) -> Assessment: ...


@dataclass
class KeywordProvider:
    """Deterministic local provider used for demos and regression evals."""

    def analyze(self, case: EvidenceCase) -> Assessment:
        joined = "\n".join(source.text for source in case.sources).lower()
        if any(
            word in joined for word in ("credential leak", "remote code", "critical")
        ):
            risk = Risk.CRITICAL
        elif any(word in joined for word in ("failed", "exposed", "unauthorized")):
            risk = Risk.HIGH
        elif any(word in joined for word in ("warning", "stale", "degraded")):
            risk = Risk.MEDIUM
        else:
            risk = Risk.LOW
        source = case.sources[0]
        quote = source.text.splitlines()[0][:240]
        return Assessment(
            risk=risk,
            summary=f"Evidence classified as {risk.value} risk.",
            labels=("synthetic-eval",),
            citations=(Citation(source_id=source.source_id, quote=quote),),
            confidence=0.80,
        )


@dataclass
class OpenAICompatibleProvider:
    base_url: str
    model: str
    api_key: str = "local"
    timeout_seconds: float = 45.0
    schema_repair_attempts: int = 1
    max_tokens: int = 1200
    disable_thinking: bool = False
    assessment_validator: Callable[[EvidenceCase, Assessment], None] | None = None

    def analyze(self, case: EvidenceCase) -> Assessment:
        sources = [{"source_id": s.source_id, "text": s.text} for s in case.sources]
        prompt = (
            "Analyze this evidence. Return only one JSON object matching this exact "
            'shape: {"risk":"low|medium|high|critical",'
            '"summary":"...","labels":["..."],'
            '"citations":[{"source_id":"...","quote":"..."}],'
            '"confidence":0.0}. Every citation must use the keys source_id and '
            "quote. quote must be copied exactly from the referenced source. "
            "Do not rename, add, or omit fields.\n"
            + json.dumps({"title": case.title, "sources": sources})
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an evidence classification component. Follow the JSON "
                    "contract exactly; never return Markdown. Do not claim legal or "
                    "regulatory compliance, certification, complete security, or the "
                    "absence of vulnerabilities from repository or scanner evidence."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        content = self._complete(messages)
        for attempt in range(self.schema_repair_attempts + 1):
            try:
                assessment = self._parse_assessment(content)
                if self.assessment_validator is not None:
                    self.assessment_validator(case, assessment)
                return assessment
            except (ProviderError, ValueError) as exc:
                if attempt == self.schema_repair_attempts:
                    if isinstance(exc, ProviderError):
                        raise
                    raise ProviderError(
                        "provider returned prohibited assurance semantics"
                    ) from exc
                messages.extend(
                    [
                        {"role": "assistant", "content": content},
                        {
                            "role": "user",
                            "content": (
                                "The response violated the required JSON or assurance "
                                "contract. Return a corrected object only. Every "
                                "citation must contain exactly source_id and an exact "
                                "quote. Describe only the bounded evidence; do not use "
                                "compliance, compliant, certification, certified, "
                                "fully secure, or no-vulnerabilities claims or labels."
                            ),
                        },
                    ]
                )
                content = self._complete(messages)
        raise AssertionError("schema repair loop ended without a result")

    def _complete(self, messages: list[dict[str, str]]) -> str:
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        if self.disable_thinking:
            body["think"] = False
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in {408, 429} and exc.code < 500:
                raise ProviderError(
                    f"provider rejected the request: HTTP {exc.code}"
                ) from exc
            raise TransientProviderError(
                f"transient provider error: HTTP {exc.code}"
            ) from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise TransientProviderError(str(exc)) from exc
        try:
            return str(payload["choices"][0]["message"]["content"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(
                "provider response did not contain message content"
            ) from exc

    @staticmethod
    def _parse_assessment(content: str) -> Assessment:
        try:
            parsed = json.loads(content)
            return Assessment(
                risk=Risk(parsed["risk"]),
                summary=str(parsed["summary"]),
                labels=tuple(str(label) for label in parsed.get("labels", [])),
                citations=tuple(
                    Citation(source_id=item["source_id"], quote=item["quote"])
                    for item in parsed["citations"]
                ),
                confidence=float(parsed["confidence"]),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderError("provider returned an invalid assessment") from exc
