"""
A/B Testing - Generate 2+ video variants and compare performance metrics.
"""

import os
import time
import json
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from loguru import logger
from app.services import task as tm
from app.utils import utils


@dataclass
class ABTestVariant:
    variant_id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    variant_name: str = ""
    params_override: Dict = field(default_factory=dict)
    task_id: str = ""
    video_urls: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, generating, completed, failed
    error_message: str = ""
    metrics: Dict = field(default_factory=dict)  # duration, file_size, etc.
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0


@dataclass
class ABTest:
    test_id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    name: str = ""
    base_params: Dict = field(default_factory=dict)
    variants: List[ABTestVariant] = field(default_factory=list)
    winner: str = ""  # variant_id of winner
    status: str = "pending"  # pending, running, completed, failed
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0


class ABTestManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tests: Dict[str, ABTest] = {}
                    cls._instance._results_dir = os.path.join(utils.storage_dir(), "ab_tests")
                    os.makedirs(cls._instance._results_dir, exist_ok=True)
        return cls._instance

    def create_test(self, name: str, base_params: Dict,
                    variants_config: List[Dict]) -> ABTest:
        """Create an A/B test with multiple variants

        variants_config example:
        [
            {"name": "Azure TTS", "params_override": {"voice_name": "en-US-JennyNeural-Female"}},
            {"name": "Chatterbox", "params_override": {"voice_name": "chatterbox:default:Default Voice-Neutral"}},
        ]
        """
        test = ABTest(name=name, base_params=base_params)
        for vc in variants_config:
            variant = ABTestVariant(
                variant_name=vc["name"],
                params_override=vc.get("params_override", {})
            )
            test.variants.append(variant)

        self._tests[test.test_id] = test
        logger.info(f"A/B test created: {test.test_id} - '{name}' with {len(test.variants)} variants")
        return test

    def run_test(self, test_id: str) -> bool:
        """Run all variants of an A/B test"""
        test = self._tests.get(test_id)
        if not test:
            logger.error(f"A/B test not found: {test_id}")
            return False

        test.status = "running"
        threads = []

        for variant in test.variants:
            thread = threading.Thread(
                target=self._run_variant,
                args=(test, variant),
                daemon=True
            )
            thread.start()
            threads.append(thread)

        for t in threads:
            t.join()

        self._evaluate_winner(test)
        test.status = "completed"
        test.completed_at = time.time()
        self._save_test(test)
        logger.success(f"A/B test completed: {test_id} - Winner: {test.winner}")
        return True

    def _run_variant(self, test: ABTest, variant: ABTestVariant):
        """Run a single variant"""
        variant.status = "generating"
        try:
            from app.models.schema import VideoParams

            # Merge base params with variant overrides
            merged = {**test.base_params, **variant.params_override}
            params = VideoParams(**merged)

            result = tm.start(task_id=variant.task_id, params=params)
            if result and "videos" in result:
                variant.status = "completed"
                variant.video_urls = result["videos"]
                variant.metrics = {
                    "video_count": len(result["videos"]),
                    "audio_file": result.get("audio_file", ""),
                    "audio_duration": result.get("audio_duration", 0),
                    "file_size": os.path.getsize(result["videos"][0]) if result["videos"] else 0,
                }
                variant.completed_at = time.time()
            else:
                variant.status = "failed"
                variant.error_message = "No videos generated"
        except Exception as e:
            variant.status = "failed"
            variant.error_message = str(e)
            logger.error(f"A/B variant failed: {variant.variant_name} - {e}")

    def _evaluate_winner(self, test: ABTest):
        """Determine winning variant based on metrics"""
        completed = [v for v in test.variants if v.status == "completed"]
        if not completed:
            test.winner = ""
            return

        # Score each variant
        best_variant = None
        best_score = -1

        for v in completed:
            score = 0
            # Higher file size = better quality (up to a point)
            score += min(v.metrics.get("file_size", 0) / 1_000_000, 10)
            # Lower duration variance from target = better
            score += 5  # Base score for completion
            # More videos = more options
            score += v.metrics.get("video_count", 0) * 2

            if score > best_score:
                best_score = score
                best_variant = v

        test.winner = best_variant.variant_id if best_variant else ""
        logger.info(f"A/B test '{test.name}' - Winner: {best_variant.variant_name if best_variant else 'None'} (score: {best_score:.1f})")

    def get_test(self, test_id: str) -> Optional[Dict]:
        test = self._tests.get(test_id)
        if test:
            return self._test_to_dict(test)
        return None

    def get_all_tests(self) -> List[Dict]:
        return [self._test_to_dict(t) for t in self._tests.values()]

    def get_test_results(self, test_id: str) -> Optional[Dict]:
        test = self._tests.get(test_id)
        if not test or test.status != "completed":
            return None

        return {
            "test_id": test.test_id,
            "name": test.name,
            "status": test.status,
            "winner": test.winner,
            "winner_name": next((v.variant_name for v in test.variants if v.variant_id == test.winner), ""),
            "variants": [
                {
                    "variant_id": v.variant_id,
                    "name": v.variant_name,
                    "status": v.status,
                    "video_urls": v.video_urls,
                    "metrics": v.metrics,
                    "error_message": v.error_message,
                }
                for v in test.variants
            ],
        }

    def _save_test(self, test: ABTest):
        path = os.path.join(self._results_dir, f"{test.test_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._test_to_dict(test), f, ensure_ascii=False, indent=2, default=str)

    def _test_to_dict(self, test: ABTest) -> Dict:
        return {
            "test_id": test.test_id,
            "name": test.name,
            "status": test.status,
            "winner": test.winner,
            "variants": [self._variant_to_dict(v) for v in test.variants],
            "base_params": test.base_params,
            "created_at": test.created_at,
            "completed_at": test.completed_at,
        }

    def _variant_to_dict(self, v: ABTestVariant) -> Dict:
        return {
            "variant_id": v.variant_id,
            "variant_name": v.variant_name,
            "params_override": v.params_override,
            "task_id": v.task_id,
            "status": v.status,
            "video_urls": v.video_urls,
            "metrics": v.metrics,
            "error_message": v.error_message,
        }


ab_test_manager = ABTestManager()
