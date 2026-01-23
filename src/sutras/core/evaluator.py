"""Evaluation framework for Sutras skills."""

import asyncio
import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sutras.core.skill import Skill


@dataclass
class EvalResult:
    """Result of a single evaluation case."""

    name: str
    metrics: dict[str, float]
    passed: bool
    threshold: float | None = None
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalSummary:
    """Summary of evaluation run."""

    total: int
    passed: int
    failed: int
    metrics: dict[str, float]
    results: list[EvalResult]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def success(self) -> bool:
        """Check if evaluation passed threshold."""
        return self.failed == 0 and self.total > 0


class BaseEvaluator(ABC):
    """Base class for evaluators."""

    @abstractmethod
    def evaluate(
        self,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        ground_truth: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        """Evaluate a single case.

        Args:
            inputs: Input data
            outputs: Generated outputs
            ground_truth: Expected/reference outputs

        Returns:
            Dictionary of metric names to scores
        """
        pass

    @abstractmethod
    def get_metric_names(self) -> list[str]:
        """Get list of metric names this evaluator computes."""
        pass


class RagasEvaluator(BaseEvaluator):
    """Ragas-based evaluator for RAG applications (v0.4+ API)."""

    def __init__(
        self,
        metrics: list[str] | None = None,
        model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
    ):
        self.metrics = metrics or ["faithfulness", "answer_relevancy", "context_precision"]
        self.model = model
        self.embedding_model = embedding_model
        self._ragas_available = self._check_ragas()
        self._metric_instances: dict[str, Any] = {}

    def _check_ragas(self) -> bool:
        try:
            import ragas  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_metric_instances(self) -> dict[str, Any]:
        if self._metric_instances:
            return self._metric_instances

        from openai import AsyncOpenAI
        from ragas.embeddings.base import embedding_factory
        from ragas.llms import llm_factory
        from ragas.metrics.collections import AnswerRelevancy, ContextPrecision, Faithfulness

        client = AsyncOpenAI()
        llm = llm_factory(model=self.model, client=client)
        embeddings = embedding_factory(
            provider="openai", model=self.embedding_model, client=client
        )

        metric_map = {
            "faithfulness": Faithfulness(llm=llm),
            "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=embeddings),
            "context_precision": ContextPrecision(llm=llm),
        }

        self._metric_instances = {m: metric_map[m] for m in self.metrics if m in metric_map}
        return self._metric_instances

    async def _score_faithfulness(
        self, metric: Any, user_input: str, response: str, retrieved_contexts: list[str]
    ) -> float:
        result = await metric.ascore(
            user_input=user_input, response=response, retrieved_contexts=retrieved_contexts
        )
        return result.value

    async def _score_answer_relevancy(
        self, metric: Any, user_input: str, response: str
    ) -> float:
        result = await metric.ascore(user_input=user_input, response=response)
        return result.value

    async def _score_context_precision(
        self, metric: Any, user_input: str, reference: str, retrieved_contexts: list[str]
    ) -> float:
        result = await metric.ascore(
            user_input=user_input, reference=reference, retrieved_contexts=retrieved_contexts
        )
        return result.value

    def evaluate(
        self,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        ground_truth: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        if not self._ragas_available:
            raise ImportError("Ragas is not installed. Install with: pip install 'sutras[eval]'")

        metric_instances = self._get_metric_instances()

        user_input = inputs.get("question", "")
        response = outputs.get("answer", "")
        retrieved_contexts = inputs.get("contexts", [])
        reference = ground_truth.get("answer", "") if ground_truth else ""

        async def run_all_metrics() -> dict[str, float]:
            results = {}
            for name, metric in metric_instances.items():
                try:
                    if name == "faithfulness":
                        results[name] = await self._score_faithfulness(
                            metric, user_input, response, retrieved_contexts
                        )
                    elif name == "answer_relevancy":
                        results[name] = await self._score_answer_relevancy(
                            metric, user_input, response
                        )
                    elif name == "context_precision":
                        results[name] = await self._score_context_precision(
                            metric, user_input, reference, retrieved_contexts
                        )
                except Exception:
                    results[name] = 0.0
            return results

        try:
            return asyncio.run(run_all_metrics())
        except Exception:
            return {"error": 0.0}

    def get_metric_names(self) -> list[str]:
        return self.metrics


class CustomEvaluator(BaseEvaluator):
    """Custom evaluator using user-defined functions."""

    def __init__(self, eval_fn: Callable[..., dict[str, float]], metric_names: list[str]):
        """Initialize custom evaluator.

        Args:
            eval_fn: Function that takes (inputs, outputs, ground_truth) and returns metrics dict
            metric_names: List of metric names the function returns
        """
        self.eval_fn = eval_fn
        self.metric_names = metric_names

    def evaluate(
        self,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        ground_truth: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        """Evaluate using custom function."""
        try:
            return self.eval_fn(inputs, outputs, ground_truth)
        except Exception:
            return {"error": 0.0}

    def get_metric_names(self) -> list[str]:
        """Get list of custom metrics."""
        return self.metric_names


class DatasetManager:
    """Manages evaluation datasets."""

    def __init__(self, dataset_path: Path | None = None):
        """Initialize dataset manager.

        Args:
            dataset_path: Path to dataset file
        """
        self.dataset_path = dataset_path
        self._cache: list[dict[str, Any]] = []

    def load(self) -> list[dict[str, Any]]:
        """Load evaluation dataset.

        Returns:
            List of evaluation cases

        Raises:
            FileNotFoundError: If dataset doesn't exist
            ValueError: If dataset format is invalid
        """
        if self._cache:
            return self._cache

        if not self.dataset_path or not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found at {self.dataset_path}")

        with self.dataset_path.open() as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Dataset must be a JSON array of evaluation cases")

        self._cache = data
        return self._cache

    def validate(self, data: list[dict[str, Any]]) -> bool:
        """Validate dataset format.

        Args:
            data: Dataset to validate

        Returns:
            True if valid
        """
        if not isinstance(data, list):
            return False

        required_fields = {"inputs", "expected"}
        for case in data:
            if not all(field in case for field in required_fields):
                return False

        return True


class EvaluationHistory:
    """Tracks evaluation history."""

    def __init__(self, history_dir: Path):
        """Initialize history tracker.

        Args:
            history_dir: Directory to store history
        """
        self.history_dir = history_dir
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def save(self, summary: EvalSummary, skill_name: str) -> Path:
        """Save evaluation results to history.

        Args:
            summary: Evaluation summary
            skill_name: Name of evaluated skill

        Returns:
            Path to saved history file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{skill_name}_{timestamp}.json"
        filepath = self.history_dir / filename

        history_data = {
            "skill": skill_name,
            "timestamp": summary.timestamp,
            "total": summary.total,
            "passed": summary.passed,
            "failed": summary.failed,
            "metrics": summary.metrics,
            "results": [
                {
                    "name": r.name,
                    "metrics": r.metrics,
                    "passed": r.passed,
                    "threshold": r.threshold,
                    "message": r.message,
                    "metadata": r.metadata,
                }
                for r in summary.results
            ],
        }

        with filepath.open("w") as f:
            json.dump(history_data, f, indent=2)

        return filepath

    def list(self, skill_name: str | None = None) -> list[Path]:
        """List evaluation history files.

        Args:
            skill_name: Filter by skill name (optional)

        Returns:
            List of history file paths
        """
        if skill_name:
            pattern = f"{skill_name}_*.json"
        else:
            pattern = "*.json"

        return sorted(
            self.history_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def load(self, filepath: Path) -> dict[str, Any]:
        """Load evaluation history from file.

        Args:
            filepath: Path to history file

        Returns:
            History data
        """
        with filepath.open() as f:
            return json.load(f)


class Evaluator:
    """Main evaluator for Sutras skills."""

    def __init__(self, skill: Skill):
        """Initialize evaluator.

        Args:
            skill: The skill to evaluate
        """
        self.skill = skill
        self.dataset_manager = self._init_dataset_manager()
        self.history = self._init_history()
        self.evaluator_impl = self._init_evaluator()

    def _init_dataset_manager(self) -> DatasetManager | None:
        """Initialize dataset manager if dataset is configured."""
        if not self.skill.abi or not self.skill.abi.eval:
            return None

        dataset_path = self.skill.abi.eval.dataset
        if dataset_path:
            full_path = self.skill.path / dataset_path
            return DatasetManager(full_path)

        return None

    def _init_history(self) -> EvaluationHistory:
        """Initialize evaluation history tracker."""
        history_dir = self.skill.path / ".sutras" / "eval_history"
        return EvaluationHistory(history_dir)

    def _init_evaluator(self) -> BaseEvaluator:
        """Initialize the appropriate evaluator implementation."""
        if not self.skill.abi or not self.skill.abi.eval:
            raise ValueError("No evaluation configuration found in sutras.yaml")

        framework = self.skill.abi.eval.framework
        metrics = self.skill.abi.eval.metrics

        if framework == "ragas":
            return RagasEvaluator(metrics)
        else:
            raise ValueError(f"Unsupported evaluation framework: {framework}")

    def run(self, save_history: bool = True) -> EvalSummary:
        """Run evaluation on the skill.

        Args:
            save_history: Whether to save results to history

        Returns:
            Evaluation summary
        """
        if not self.dataset_manager:
            return EvalSummary(
                total=0,
                passed=0,
                failed=0,
                metrics={},
                results=[],
            )

        dataset = self.dataset_manager.load()
        results = []
        all_metrics: dict[str, list[float]] = {}

        for i, case in enumerate(dataset):
            result = self._evaluate_case(case, i)
            results.append(result)

            for metric_name, score in result.metrics.items():
                if metric_name not in all_metrics:
                    all_metrics[metric_name] = []
                all_metrics[metric_name].append(score)

        avg_metrics = {
            name: sum(scores) / len(scores) for name, scores in all_metrics.items() if scores
        }

        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed

        summary = EvalSummary(
            total=len(results),
            passed=passed,
            failed=failed,
            metrics=avg_metrics,
            results=results,
        )

        if save_history:
            self.history.save(summary, self.skill.name)

        return summary

    def _evaluate_case(self, case: dict[str, Any], index: int) -> EvalResult:
        """Evaluate a single case.

        Args:
            case: Evaluation case
            index: Case index

        Returns:
            Evaluation result
        """
        try:
            inputs = case.get("inputs", {})
            expected = case.get("expected", {})
            name = case.get("name", f"case_{index}")

            outputs = self._execute_skill(inputs)

            metrics = self.evaluator_impl.evaluate(
                inputs=inputs,
                outputs=outputs,
                ground_truth=expected,
            )

            threshold = self.skill.abi.eval.threshold if self.skill.abi.eval else None
            if threshold is not None:
                avg_score = sum(metrics.values()) / len(metrics) if metrics else 0.0
                passed = avg_score >= threshold
            else:
                passed = True

            return EvalResult(
                name=name,
                metrics=metrics,
                passed=passed,
                threshold=threshold,
                message="Evaluation completed",
                metadata=case.get("metadata", {}),
            )

        except Exception as e:
            return EvalResult(
                name=case.get("name", f"case_{index}"),
                metrics={"error": 0.0},
                passed=False,
                message=f"Evaluation error: {str(e)}",
            )

    def _execute_skill(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute the skill with given inputs.

        Args:
            inputs: Skill inputs

        Returns:
            Skill outputs
        """
        return {"answer": "Sample output", "contexts": inputs.get("contexts", [])}
