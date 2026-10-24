"""Inference boundary; disabled until an actual runtime/tool protocol is integrated."""
from typing import Protocol


class GemmaRuntime(Protocol):
    def explain(self, comparison, tools): ...


class UnconfiguredGemmaRuntime:
    model_id = None

    def explain(self, comparison, tools):
        return dict(status='ai_unavailable', model_id=None, input_revision=comparison['input_revision'],
                    candidate_explanations=[], error={'code':'gemma_not_configured',
                    'message':'No genuine Gemma runtime has been integrated. Deterministic comparisons and checklists remain available.',
                    'retryable':False})
