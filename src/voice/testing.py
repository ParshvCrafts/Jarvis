"""
Voice Command Testing Suite for JARVIS.

Provides comprehensive testing for:
- Wake word detection accuracy
- Speech-to-text accuracy
- End-to-end response time
- Voice pipeline reliability
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


@dataclass
class TestCase:
    """A voice command test case."""
    name: str
    command: str
    category: str
    expected_intent: str = ""
    expected_keywords: List[str] = field(default_factory=list)
    timeout: float = 30.0
    requires_hardware: bool = False


@dataclass
class TestResult:
    """Result of a single test."""
    test_case: TestCase
    success: bool
    transcription: str = ""
    response: str = ""
    wake_word_time: float = 0.0
    stt_time: float = 0.0
    llm_time: float = 0.0
    tts_time: float = 0.0
    total_time: float = 0.0
    error: str = ""
    timestamp: float = field(default_factory=time.time)
    
    @property
    def metrics(self) -> Dict[str, float]:
        return {
            "wake_word_time": self.wake_word_time,
            "stt_time": self.stt_time,
            "llm_time": self.llm_time,
            "tts_time": self.tts_time,
            "total_time": self.total_time,
        }


@dataclass
class TestSuiteResult:
    """Result of a complete test suite run."""
    total_tests: int
    passed: int
    failed: int
    skipped: int
    results: List[TestResult]
    start_time: float
    end_time: float
    
    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.passed / self.total_tests
    
    @property
    def avg_response_time(self) -> float:
        times = [r.total_time for r in self.results if r.success and r.total_time > 0]
        return sum(times) / len(times) if times else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "pass_rate": self.pass_rate,
            "avg_response_time": self.avg_response_time,
            "duration": self.end_time - self.start_time,
            "results": [
                {
                    "name": r.test_case.name,
                    "category": r.test_case.category,
                    "success": r.success,
                    "transcription": r.transcription,
                    "metrics": r.metrics,
                    "error": r.error,
                }
                for r in self.results
            ],
        }


# Default test cases
DEFAULT_TEST_CASES = [
    # Simple commands
    TestCase(
        name="greeting",
        command="Hello",
        category="simple",
        expected_intent="greeting",
    ),
    TestCase(
        name="time_query",
        command="What time is it?",
        category="simple",
        expected_intent="question",
        expected_keywords=["time", "clock"],
    ),
    TestCase(
        name="date_query",
        command="What's today's date?",
        category="simple",
        expected_intent="question",
        expected_keywords=["date", "today"],
    ),
    
    # Research commands
    TestCase(
        name="web_search",
        command="Search for Python tutorials",
        category="research",
        expected_intent="research",
        expected_keywords=["search", "python"],
    ),
    TestCase(
        name="definition",
        command="What is machine learning?",
        category="research",
        expected_intent="research",
        expected_keywords=["machine learning", "AI", "algorithm"],
    ),
    
    # System commands
    TestCase(
        name="open_app",
        command="Open Chrome",
        category="system",
        expected_intent="system",
        expected_keywords=["chrome", "browser", "open"],
    ),
    TestCase(
        name="screenshot",
        command="Take a screenshot",
        category="system",
        expected_intent="system",
        expected_keywords=["screenshot", "capture"],
    ),
    
    # IoT commands
    TestCase(
        name="light_on",
        command="Turn on the lights",
        category="iot",
        expected_intent="iot",
        expected_keywords=["light", "on"],
        requires_hardware=True,
    ),
    TestCase(
        name="light_off",
        command="Turn off the lights",
        category="iot",
        expected_intent="iot",
        expected_keywords=["light", "off"],
        requires_hardware=True,
    ),
    TestCase(
        name="door_unlock",
        command="Unlock the front door",
        category="iot",
        expected_intent="iot",
        expected_keywords=["unlock", "door"],
        requires_hardware=True,
    ),
    
    # Coding commands
    TestCase(
        name="code_generation",
        command="Write a Python function to sort a list",
        category="coding",
        expected_intent="coding",
        expected_keywords=["def", "sort", "list"],
    ),
    TestCase(
        name="git_status",
        command="Git status",
        category="coding",
        expected_intent="coding",
        expected_keywords=["git", "status"],
    ),
    
    # Multi-step commands
    TestCase(
        name="research_summarize",
        command="Research quantum computing and give me a summary",
        category="complex",
        expected_intent="research",
        timeout=60.0,
    ),
]


class VoiceTestRunner:
    """
    Runs voice command tests.
    
    Can run tests in:
    - Manual mode: User speaks commands
    - Simulated mode: Uses pre-recorded audio or text input
    """
    
    def __init__(
        self,
        test_cases: Optional[List[TestCase]] = None,
        data_dir: Optional[Path] = None,
        include_hardware_tests: bool = False,
    ):
        self.test_cases = test_cases or DEFAULT_TEST_CASES
        self.data_dir = data_dir or Path("data/tests")
        self.include_hardware_tests = include_hardware_tests
        
        self._results: List[TestResult] = []
    
    def _filter_tests(self, categories: Optional[List[str]] = None) -> List[TestCase]:
        """Filter test cases by category and hardware requirements."""
        tests = self.test_cases
        
        if not self.include_hardware_tests:
            tests = [t for t in tests if not t.requires_hardware]
        
        if categories:
            tests = [t for t in tests if t.category in categories]
        
        return tests
    
    def run_manual_test(
        self,
        test_case: TestCase,
        process_command: Callable[[str], str],
    ) -> TestResult:
        """
        Run a single test with manual voice input.
        
        Args:
            test_case: Test case to run.
            process_command: Function to process command and return response.
            
        Returns:
            TestResult with timing and accuracy metrics.
        """
        print(f"\n{'=' * 50}")
        print(f"Test: {test_case.name}")
        print(f"Category: {test_case.category}")
        print(f"{'=' * 50}")
        print(f"\nPlease say: \"{test_case.command}\"")
        print("Press Enter when ready, then speak...")
        input()
        
        start_time = time.time()
        
        try:
            # Record and transcribe
            transcription = self._record_and_transcribe()
            stt_time = time.time() - start_time
            
            if not transcription:
                return TestResult(
                    test_case=test_case,
                    success=False,
                    error="No transcription",
                    stt_time=stt_time,
                )
            
            print(f"Transcribed: \"{transcription}\"")
            
            # Process command
            llm_start = time.time()
            response = process_command(transcription)
            llm_time = time.time() - llm_start
            
            total_time = time.time() - start_time
            
            # Check success
            success = self._evaluate_result(test_case, transcription, response)
            
            return TestResult(
                test_case=test_case,
                success=success,
                transcription=transcription,
                response=response,
                stt_time=stt_time,
                llm_time=llm_time,
                total_time=total_time,
            )
            
        except Exception as e:
            return TestResult(
                test_case=test_case,
                success=False,
                error=str(e),
                total_time=time.time() - start_time,
            )
    
    def run_text_test(
        self,
        test_case: TestCase,
        process_command: Callable[[str], str],
    ) -> TestResult:
        """
        Run a test using text input (simulated voice).
        
        Args:
            test_case: Test case to run.
            process_command: Function to process command.
            
        Returns:
            TestResult.
        """
        start_time = time.time()
        
        try:
            # Use the command text directly
            transcription = test_case.command
            
            # Process command
            llm_start = time.time()
            response = process_command(transcription)
            llm_time = time.time() - llm_start
            
            total_time = time.time() - start_time
            
            # Check success
            success = self._evaluate_result(test_case, transcription, response)
            
            return TestResult(
                test_case=test_case,
                success=success,
                transcription=transcription,
                response=response,
                llm_time=llm_time,
                total_time=total_time,
            )
            
        except Exception as e:
            return TestResult(
                test_case=test_case,
                success=False,
                error=str(e),
                total_time=time.time() - start_time,
            )
    
    def _record_and_transcribe(self, duration: float = 5.0) -> str:
        """Record audio and transcribe."""
        if not SOUNDDEVICE_AVAILABLE or not NUMPY_AVAILABLE:
            return ""
        
        try:
            from .stt_enhanced import EnhancedSpeechToText
            
            sample_rate = 16000
            print("Recording...")
            
            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype=np.float32,
            )
            sd.wait()
            
            print("Transcribing...")
            
            stt = EnhancedSpeechToText()
            result = stt.transcribe(recording.flatten(), sample_rate)
            
            return result.text if not result.is_empty else ""
            
        except Exception as e:
            logger.error(f"Recording/transcription failed: {e}")
            return ""
    
    def _evaluate_result(
        self,
        test_case: TestCase,
        transcription: str,
        response: str,
    ) -> bool:
        """Evaluate if test passed."""
        # Check if transcription is similar to expected command
        command_words = set(test_case.command.lower().split())
        trans_words = set(transcription.lower().split())
        
        # At least 50% word overlap
        overlap = len(command_words & trans_words)
        if overlap < len(command_words) * 0.5:
            return False
        
        # Check for expected keywords in response
        if test_case.expected_keywords:
            response_lower = response.lower()
            found_keywords = sum(
                1 for kw in test_case.expected_keywords
                if kw.lower() in response_lower
            )
            if found_keywords == 0:
                return False
        
        # Check response is not empty or error
        if not response or "error" in response.lower():
            return False
        
        return True
    
    def run_suite(
        self,
        process_command: Callable[[str], str],
        categories: Optional[List[str]] = None,
        mode: str = "text",
    ) -> TestSuiteResult:
        """
        Run a complete test suite.
        
        Args:
            process_command: Function to process commands.
            categories: Categories to test (None = all).
            mode: "text" for simulated, "manual" for voice input.
            
        Returns:
            TestSuiteResult with all results.
        """
        tests = self._filter_tests(categories)
        
        print(f"\n{'=' * 60}")
        print("JARVIS VOICE COMMAND TEST SUITE")
        print(f"{'=' * 60}")
        print(f"Tests to run: {len(tests)}")
        print(f"Mode: {mode}")
        print(f"Categories: {categories or 'all'}")
        print(f"{'=' * 60}\n")
        
        start_time = time.time()
        results = []
        passed = 0
        failed = 0
        skipped = 0
        
        for i, test_case in enumerate(tests, 1):
            print(f"\n[{i}/{len(tests)}] Running: {test_case.name}")
            
            try:
                if mode == "manual":
                    result = self.run_manual_test(test_case, process_command)
                else:
                    result = self.run_text_test(test_case, process_command)
                
                results.append(result)
                
                if result.success:
                    passed += 1
                    print(f"  ✓ PASSED ({result.total_time:.2f}s)")
                else:
                    failed += 1
                    print(f"  ✗ FAILED: {result.error or 'Evaluation failed'}")
                    
            except Exception as e:
                skipped += 1
                print(f"  ⊘ SKIPPED: {e}")
        
        end_time = time.time()
        
        suite_result = TestSuiteResult(
            total_tests=len(tests),
            passed=passed,
            failed=failed,
            skipped=skipped,
            results=results,
            start_time=start_time,
            end_time=end_time,
        )
        
        # Print summary
        print(f"\n{'=' * 60}")
        print("TEST SUITE RESULTS")
        print(f"{'=' * 60}")
        print(f"Total:   {suite_result.total_tests}")
        print(f"Passed:  {suite_result.passed} ({suite_result.pass_rate:.1%})")
        print(f"Failed:  {suite_result.failed}")
        print(f"Skipped: {suite_result.skipped}")
        print(f"Duration: {suite_result.end_time - suite_result.start_time:.1f}s")
        print(f"Avg Response Time: {suite_result.avg_response_time:.2f}s")
        print(f"{'=' * 60}\n")
        
        # Save results
        self._save_results(suite_result)
        
        return suite_result
    
    def _save_results(self, result: TestSuiteResult) -> None:
        """Save test results to file."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.data_dir / f"test_results_{timestamp}.json"
        
        try:
            with open(path, "w") as f:
                json.dump(result.to_dict(), f, indent=2)
            print(f"Results saved to: {path}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")


class STTAccuracyTester:
    """Tests speech-to-text accuracy."""
    
    def __init__(self):
        self.test_phrases = [
            "Hello, how are you today?",
            "The quick brown fox jumps over the lazy dog.",
            "Turn on the living room lights.",
            "What's the weather like in Seattle?",
            "Set a reminder for tomorrow at 3 PM.",
            "Play some relaxing music.",
            "Search for Italian restaurants nearby.",
            "Send a message to John saying I'll be late.",
        ]
    
    def calculate_wer(self, reference: str, hypothesis: str) -> float:
        """
        Calculate Word Error Rate.
        
        Args:
            reference: Expected text.
            hypothesis: Transcribed text.
            
        Returns:
            WER as a float (0.0 = perfect, 1.0 = all wrong).
        """
        ref_words = reference.lower().split()
        hyp_words = hypothesis.lower().split()
        
        # Simple Levenshtein distance
        m, n = len(ref_words), len(hyp_words)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if ref_words[i - 1] == hyp_words[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(
                        dp[i - 1][j],      # deletion
                        dp[i][j - 1],      # insertion
                        dp[i - 1][j - 1],  # substitution
                    )
        
        return dp[m][n] / m if m > 0 else 0.0
    
    def run_accuracy_test(self) -> Dict[str, Any]:
        """
        Run STT accuracy test.
        
        Returns:
            Dict with accuracy metrics.
        """
        if not SOUNDDEVICE_AVAILABLE or not NUMPY_AVAILABLE:
            return {"error": "Audio libraries not available"}
        
        print("\n" + "=" * 50)
        print("STT ACCURACY TEST")
        print("=" * 50)
        print("\nYou will be asked to read several phrases.")
        print("Speak clearly and at a normal pace.\n")
        
        results = []
        
        try:
            from .stt_enhanced import EnhancedSpeechToText
            stt = EnhancedSpeechToText()
        except ImportError:
            return {"error": "STT not available"}
        
        for i, phrase in enumerate(self.test_phrases, 1):
            print(f"\n[{i}/{len(self.test_phrases)}]")
            print(f"Please say: \"{phrase}\"")
            print("Press Enter when ready...")
            input()
            
            # Record
            sample_rate = 16000
            duration = max(3.0, len(phrase.split()) * 0.5)
            
            print("Recording...")
            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype=np.float32,
            )
            sd.wait()
            
            # Transcribe
            result = stt.transcribe(recording.flatten(), sample_rate)
            transcription = result.text if not result.is_empty else ""
            
            # Calculate WER
            wer = self.calculate_wer(phrase, transcription)
            
            results.append({
                "reference": phrase,
                "hypothesis": transcription,
                "wer": wer,
                "confidence": result.confidence,
            })
            
            print(f"Transcribed: \"{transcription}\"")
            print(f"WER: {wer:.2%}")
        
        # Calculate overall metrics
        avg_wer = sum(r["wer"] for r in results) / len(results)
        avg_confidence = sum(r["confidence"] for r in results) / len(results)
        
        print("\n" + "=" * 50)
        print("RESULTS")
        print("=" * 50)
        print(f"Average WER: {avg_wer:.2%}")
        print(f"Average Confidence: {avg_confidence:.2%}")
        print(f"Accuracy: {(1 - avg_wer):.2%}")
        
        return {
            "results": results,
            "avg_wer": avg_wer,
            "avg_confidence": avg_confidence,
            "accuracy": 1 - avg_wer,
        }


# Convenience functions

def run_voice_tests(
    process_command: Callable[[str], str],
    categories: Optional[List[str]] = None,
    mode: str = "text",
) -> TestSuiteResult:
    """Run voice command test suite."""
    runner = VoiceTestRunner()
    return runner.run_suite(process_command, categories, mode)


def run_stt_accuracy_test() -> Dict[str, Any]:
    """Run STT accuracy test."""
    tester = STTAccuracyTester()
    return tester.run_accuracy_test()
