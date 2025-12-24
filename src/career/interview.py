"""
Interview Prep Mode for JARVIS.

Practice technical interviews with AI assistance:
- Data Structures & Algorithms (LeetCode-style)
- Machine Learning Concepts
- Behavioral Questions (STAR method)
- System Design (Basic)
"""

import json
import random
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class QuestionType(Enum):
    CODING = "coding"
    ML_CONCEPT = "ml_concept"
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system_design"


class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class InterviewQuestion:
    id: Optional[int] = None
    type: QuestionType = QuestionType.CODING
    difficulty: Difficulty = Difficulty.MEDIUM
    title: str = ""
    question: str = ""
    hints: List[str] = field(default_factory=list)
    solution: str = ""
    explanation: str = ""
    tags: List[str] = field(default_factory=list)
    times_practiced: int = 0
    last_practiced: Optional[datetime] = None
    best_rating: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "difficulty": self.difficulty.value,
            "title": self.title,
            "question": self.question,
            "hints": json.dumps(self.hints),
            "solution": self.solution,
            "explanation": self.explanation,
            "tags": json.dumps(self.tags),
            "times_practiced": self.times_practiced,
            "last_practiced": self.last_practiced.isoformat() if self.last_practiced else None,
            "best_rating": self.best_rating,
        }
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "InterviewQuestion":
        return cls(
            id=row["id"],
            type=QuestionType(row["type"]),
            difficulty=Difficulty(row["difficulty"]),
            title=row["title"],
            question=row["question"],
            hints=json.loads(row["hints"]) if row["hints"] else [],
            solution=row["solution"] or "",
            explanation=row["explanation"] or "",
            tags=json.loads(row["tags"]) if row["tags"] else [],
            times_practiced=row["times_practiced"] or 0,
            last_practiced=datetime.fromisoformat(row["last_practiced"]) if row["last_practiced"] else None,
            best_rating=row["best_rating"],
        )


@dataclass
class InterviewSession:
    id: Optional[int] = None
    date: datetime = field(default_factory=datetime.now)
    type: QuestionType = QuestionType.CODING
    questions_attempted: int = 0
    questions_correct: int = 0
    duration_minutes: int = 0
    notes: str = ""
    
    @property
    def score(self) -> float:
        if self.questions_attempted == 0:
            return 0.0
        return (self.questions_correct / self.questions_attempted) * 100


class InterviewPrep:
    """Interview preparation system with question bank and progress tracking."""
    
    def __init__(self, data_dir: str = "data", default_difficulty: str = "medium"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "interview_prep.db"
        self.default_difficulty = Difficulty(default_difficulty)
        
        self._current_question: Optional[InterviewQuestion] = None
        self._current_hint_index: int = 0
        self._session_start: Optional[datetime] = None
        
        self._init_db()
        self._load_default_questions()
        logger.info("Interview Prep initialized")
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    title TEXT NOT NULL,
                    question TEXT NOT NULL,
                    hints TEXT,
                    solution TEXT,
                    explanation TEXT,
                    tags TEXT,
                    times_practiced INTEGER DEFAULT 0,
                    last_practiced TEXT,
                    best_rating INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    type TEXT NOT NULL,
                    questions_attempted INTEGER DEFAULT 0,
                    questions_correct INTEGER DEFAULT 0,
                    duration_minutes INTEGER DEFAULT 0,
                    notes TEXT
                )
            """)
            conn.commit()
    
    def _load_default_questions(self):
        """Load default questions if database is empty."""
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
            if count > 0:
                return
        
        questions = self._get_default_questions()
        for q in questions:
            self._add_question_to_db(q)
        logger.info(f"Loaded {len(questions)} default interview questions")
    
    def _add_question_to_db(self, q: InterviewQuestion):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO questions (type, difficulty, title, question, hints, solution, explanation, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (q.type.value, q.difficulty.value, q.title, q.question,
                  json.dumps(q.hints), q.solution, q.explanation, json.dumps(q.tags)))
            conn.commit()
    
    def get_random_question(
        self,
        qtype: Optional[QuestionType] = None,
        difficulty: Optional[Difficulty] = None,
    ) -> Optional[InterviewQuestion]:
        """Get a random question, optionally filtered by type and difficulty."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM questions WHERE 1=1"
            params = []
            
            if qtype:
                query += " AND type = ?"
                params.append(qtype.value)
            if difficulty:
                query += " AND difficulty = ?"
                params.append(difficulty.value)
            
            query += " ORDER BY RANDOM() LIMIT 1"
            row = conn.execute(query, params).fetchone()
            
            if row:
                self._current_question = InterviewQuestion.from_row(row)
                self._current_hint_index = 0
                return self._current_question
        return None
    
    def get_coding_question(self, difficulty: Optional[str] = None) -> str:
        """Get a coding question."""
        diff = Difficulty(difficulty) if difficulty else self.default_difficulty
        q = self.get_random_question(QuestionType.CODING, diff)
        if q:
            return self._format_question(q)
        return "No coding questions available."
    
    def get_ml_question(self) -> str:
        """Get an ML concept question."""
        q = self.get_random_question(QuestionType.ML_CONCEPT)
        if q:
            return self._format_question(q)
        return "No ML questions available."
    
    def get_behavioral_question(self) -> str:
        """Get a behavioral question."""
        q = self.get_random_question(QuestionType.BEHAVIORAL)
        if q:
            return self._format_question(q)
        return "No behavioral questions available."
    
    def get_system_design_question(self) -> str:
        """Get a system design question."""
        q = self.get_random_question(QuestionType.SYSTEM_DESIGN)
        if q:
            return self._format_question(q)
        return "No system design questions available."
    
    def _format_question(self, q: InterviewQuestion) -> str:
        diff_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
        emoji = diff_emoji.get(q.difficulty.value, "⚪")
        
        return f"""📝 **{q.title}** {emoji} {q.difficulty.value.title()}

{q.question}

💡 Say "hint" if you need help, or "solution" when ready."""
    
    def get_hint(self) -> str:
        """Get the next hint for the current question."""
        if not self._current_question:
            return "No active question. Start with 'coding question' or 'ML question'."
        
        hints = self._current_question.hints
        if not hints:
            return "No hints available for this question."
        
        if self._current_hint_index >= len(hints):
            return "No more hints available. Try 'solution' to see the answer."
        
        hint = hints[self._current_hint_index]
        self._current_hint_index += 1
        remaining = len(hints) - self._current_hint_index
        
        return f"💡 Hint {self._current_hint_index}/{len(hints)}: {hint}\n\n({remaining} hints remaining)"
    
    def get_solution(self) -> str:
        """Get the solution for the current question."""
        if not self._current_question:
            return "No active question."
        
        q = self._current_question
        self._mark_practiced(q.id)
        
        result = f"✅ **Solution for: {q.title}**\n\n"
        if q.solution:
            result += f"```python\n{q.solution}\n```\n\n"
        if q.explanation:
            result += f"📖 **Explanation:** {q.explanation}"
        
        return result
    
    def _mark_practiced(self, question_id: int):
        """Mark a question as practiced."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE questions 
                SET times_practiced = times_practiced + 1, last_practiced = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), question_id))
            conn.commit()
    
    def rate_answer(self, rating: int) -> str:
        """Rate your answer (1-5)."""
        if not self._current_question:
            return "No active question to rate."
        
        rating = max(1, min(5, rating))
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE questions 
                SET best_rating = MAX(COALESCE(best_rating, 0), ?)
                WHERE id = ?
            """, (rating, self._current_question.id))
            conn.commit()
        
        feedback = {
            1: "Keep practicing! You'll get better.",
            2: "Good effort! Review the solution.",
            3: "Solid attempt! A bit more practice needed.",
            4: "Great job! Almost perfect.",
            5: "Excellent! You've mastered this one!",
        }
        
        return f"⭐ Rated {rating}/5. {feedback[rating]}"
    
    def get_stats(self) -> str:
        """Get interview practice statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            total = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
            practiced = conn.execute("SELECT COUNT(*) FROM questions WHERE times_practiced > 0").fetchone()[0]
            
            by_type = conn.execute("""
                SELECT type, COUNT(*) as total, 
                       SUM(CASE WHEN times_practiced > 0 THEN 1 ELSE 0 END) as practiced
                FROM questions GROUP BY type
            """).fetchall()
            
            by_difficulty = conn.execute("""
                SELECT difficulty, COUNT(*) as total,
                       SUM(CASE WHEN times_practiced > 0 THEN 1 ELSE 0 END) as practiced
                FROM questions GROUP BY difficulty
            """).fetchall()
        
        lines = ["📊 **Interview Practice Stats**\n"]
        lines.append(f"Total Questions: {total}")
        lines.append(f"Practiced: {practiced} ({practiced*100//total if total else 0}%)\n")
        
        lines.append("**By Type:**")
        for row in by_type:
            lines.append(f"  • {row['type']}: {row['practiced']}/{row['total']}")
        
        lines.append("\n**By Difficulty:**")
        for row in by_difficulty:
            lines.append(f"  • {row['difficulty']}: {row['practiced']}/{row['total']}")
        
        return "\n".join(lines)
    
    def start_mock_interview(self, qtype: str = "coding", duration: int = 30) -> str:
        """Start a timed mock interview session."""
        self._session_start = datetime.now()
        
        type_map = {
            "coding": QuestionType.CODING,
            "ml": QuestionType.ML_CONCEPT,
            "behavioral": QuestionType.BEHAVIORAL,
            "system": QuestionType.SYSTEM_DESIGN,
        }
        
        qt = type_map.get(qtype.lower(), QuestionType.CODING)
        q = self.get_random_question(qt)
        
        if not q:
            return f"No {qtype} questions available."
        
        return f"""🎯 **Mock Interview Started!**
Type: {qtype.title()}
Duration: {duration} minutes

{self._format_question(q)}

⏱️ Timer started. Good luck!"""
    
    def _get_default_questions(self) -> List[InterviewQuestion]:
        """Return default question bank."""
        return [
            # Coding - Easy
            InterviewQuestion(
                type=QuestionType.CODING, difficulty=Difficulty.EASY,
                title="Two Sum",
                question="Given an array of integers nums and an integer target, return indices of the two numbers that add up to target.",
                hints=["Use a hash map", "Store complement as you iterate", "Check if complement exists"],
                solution="def twoSum(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        if target - num in seen:\n            return [seen[target - num], i]\n        seen[num] = i",
                explanation="Hash map for O(1) lookup. Time: O(n), Space: O(n)",
                tags=["arrays", "hash_map"]
            ),
            InterviewQuestion(
                type=QuestionType.CODING, difficulty=Difficulty.EASY,
                title="Valid Parentheses",
                question="Given a string containing '(', ')', '{', '}', '[' and ']', determine if the input string is valid.",
                hints=["Use a stack", "Push opening brackets", "Pop and compare for closing"],
                solution="def isValid(s):\n    stack = []\n    mapping = {')': '(', '}': '{', ']': '['}\n    for char in s:\n        if char in mapping:\n            if not stack or stack.pop() != mapping[char]:\n                return False\n        else:\n            stack.append(char)\n    return len(stack) == 0",
                explanation="Stack-based matching. Time: O(n), Space: O(n)",
                tags=["stack", "strings"]
            ),
            InterviewQuestion(
                type=QuestionType.CODING, difficulty=Difficulty.EASY,
                title="Maximum Subarray",
                question="Find the contiguous subarray with the largest sum.",
                hints=["Kadane's algorithm", "Track current and max sum", "Reset current if negative"],
                solution="def maxSubArray(nums):\n    max_sum = curr_sum = nums[0]\n    for num in nums[1:]:\n        curr_sum = max(num, curr_sum + num)\n        max_sum = max(max_sum, curr_sum)\n    return max_sum",
                explanation="Kadane's algorithm. Time: O(n), Space: O(1)",
                tags=["arrays", "dynamic_programming"]
            ),
            # Coding - Medium
            InterviewQuestion(
                type=QuestionType.CODING, difficulty=Difficulty.MEDIUM,
                title="Longest Substring Without Repeating",
                question="Find the length of the longest substring without repeating characters.",
                hints=["Sliding window", "Use a set to track chars", "Shrink window on duplicate"],
                solution="def lengthOfLongestSubstring(s):\n    chars = set()\n    left = max_len = 0\n    for right in range(len(s)):\n        while s[right] in chars:\n            chars.remove(s[left])\n            left += 1\n        chars.add(s[right])\n        max_len = max(max_len, right - left + 1)\n    return max_len",
                explanation="Sliding window with set. Time: O(n), Space: O(min(m,n))",
                tags=["sliding_window", "strings"]
            ),
            InterviewQuestion(
                type=QuestionType.CODING, difficulty=Difficulty.MEDIUM,
                title="3Sum",
                question="Find all unique triplets that sum to zero.",
                hints=["Sort first", "Fix one, two-pointer for rest", "Skip duplicates"],
                solution="def threeSum(nums):\n    nums.sort()\n    result = []\n    for i in range(len(nums)-2):\n        if i > 0 and nums[i] == nums[i-1]: continue\n        l, r = i+1, len(nums)-1\n        while l < r:\n            s = nums[i] + nums[l] + nums[r]\n            if s < 0: l += 1\n            elif s > 0: r -= 1\n            else:\n                result.append([nums[i], nums[l], nums[r]])\n                while l < r and nums[l] == nums[l+1]: l += 1\n                while l < r and nums[r] == nums[r-1]: r -= 1\n                l += 1; r -= 1\n    return result",
                explanation="Sort + two pointers. Time: O(n²), Space: O(1)",
                tags=["two_pointers", "sorting"]
            ),
            InterviewQuestion(
                type=QuestionType.CODING, difficulty=Difficulty.MEDIUM,
                title="Number of Islands",
                question="Count the number of islands in a 2D grid of '1's (land) and '0's (water).",
                hints=["DFS/BFS from each land cell", "Mark visited cells", "Count DFS starts"],
                solution="def numIslands(grid):\n    def dfs(i, j):\n        if i < 0 or i >= len(grid) or j < 0 or j >= len(grid[0]) or grid[i][j] != '1':\n            return\n        grid[i][j] = '0'\n        dfs(i+1, j); dfs(i-1, j); dfs(i, j+1); dfs(i, j-1)\n    count = 0\n    for i in range(len(grid)):\n        for j in range(len(grid[0])):\n            if grid[i][j] == '1':\n                dfs(i, j)\n                count += 1\n    return count",
                explanation="DFS flood fill. Time: O(m*n), Space: O(m*n)",
                tags=["dfs", "matrix"]
            ),
            InterviewQuestion(
                type=QuestionType.CODING, difficulty=Difficulty.MEDIUM,
                title="Coin Change",
                question="Find minimum coins needed to make up an amount.",
                hints=["Dynamic programming", "dp[i] = min coins for amount i", "Try each coin"],
                solution="def coinChange(coins, amount):\n    dp = [float('inf')] * (amount + 1)\n    dp[0] = 0\n    for i in range(1, amount + 1):\n        for coin in coins:\n            if coin <= i:\n                dp[i] = min(dp[i], dp[i - coin] + 1)\n    return dp[amount] if dp[amount] != float('inf') else -1",
                explanation="Bottom-up DP. Time: O(amount * coins), Space: O(amount)",
                tags=["dynamic_programming"]
            ),
            # Coding - Hard
            InterviewQuestion(
                type=QuestionType.CODING, difficulty=Difficulty.HARD,
                title="Trapping Rain Water",
                question="Given elevation map, compute how much water it can trap after raining.",
                hints=["Water level = min(left_max, right_max)", "Two pointers approach", "Track max heights"],
                solution="def trap(height):\n    if not height: return 0\n    l, r = 0, len(height) - 1\n    l_max, r_max = height[l], height[r]\n    water = 0\n    while l < r:\n        if l_max < r_max:\n            l += 1\n            l_max = max(l_max, height[l])\n            water += l_max - height[l]\n        else:\n            r -= 1\n            r_max = max(r_max, height[r])\n            water += r_max - height[r]\n    return water",
                explanation="Two pointers. Time: O(n), Space: O(1)",
                tags=["two_pointers", "arrays"]
            ),
            InterviewQuestion(
                type=QuestionType.CODING, difficulty=Difficulty.HARD,
                title="Merge K Sorted Lists",
                question="Merge k sorted linked lists into one sorted list.",
                hints=["Use a min-heap", "Add heads to heap", "Pop min, add next"],
                solution="import heapq\ndef mergeKLists(lists):\n    heap = []\n    for i, lst in enumerate(lists):\n        if lst: heapq.heappush(heap, (lst.val, i, lst))\n    dummy = curr = ListNode(0)\n    while heap:\n        val, i, node = heapq.heappop(heap)\n        curr.next = node\n        curr = curr.next\n        if node.next:\n            heapq.heappush(heap, (node.next.val, i, node.next))\n    return dummy.next",
                explanation="Min-heap. Time: O(N log k), Space: O(k)",
                tags=["heap", "linked_list"]
            ),
            # ML Concepts
            InterviewQuestion(
                type=QuestionType.ML_CONCEPT, difficulty=Difficulty.MEDIUM,
                title="Bias-Variance Tradeoff",
                question="Explain the bias-variance tradeoff in machine learning.",
                hints=["Bias = underfitting", "Variance = overfitting", "Total error = bias² + variance"],
                solution="Bias: Error from simplistic assumptions (underfitting). Variance: Sensitivity to training data (overfitting). Simple models have high bias, low variance. Complex models have low bias, high variance. Goal: minimize total error.",
                explanation="Fundamental concept for model selection and tuning.",
                tags=["fundamentals", "model_selection"]
            ),
            InterviewQuestion(
                type=QuestionType.ML_CONCEPT, difficulty=Difficulty.MEDIUM,
                title="Handling Imbalanced Data",
                question="How would you handle imbalanced data in classification?",
                hints=["Resampling techniques", "Class weights", "Different metrics"],
                solution="1. Oversampling (SMOTE), 2. Undersampling, 3. Class weights, 4. Use F1/AUC instead of accuracy, 5. Ensemble methods, 6. Anomaly detection approach",
                explanation="Common in fraud detection, disease diagnosis.",
                tags=["classification", "preprocessing"]
            ),
            InterviewQuestion(
                type=QuestionType.ML_CONCEPT, difficulty=Difficulty.EASY,
                title="Overfitting Prevention",
                question="What techniques prevent overfitting?",
                hints=["Regularization", "Cross-validation", "More data"],
                solution="1. Regularization (L1/L2), 2. Cross-validation, 3. Early stopping, 4. Dropout, 5. Data augmentation, 6. Simpler model, 7. Ensemble methods",
                explanation="Essential for building generalizable models.",
                tags=["fundamentals", "regularization"]
            ),
            InterviewQuestion(
                type=QuestionType.ML_CONCEPT, difficulty=Difficulty.MEDIUM,
                title="Random Forest vs Gradient Boosting",
                question="Compare Random Forest and Gradient Boosting.",
                hints=["Parallel vs sequential", "Variance vs bias reduction", "Training time"],
                solution="RF: Parallel trees, reduces variance, faster, less tuning. GB: Sequential trees, reduces bias, slower, needs tuning but often better performance. Use RF for quick baseline, GB for best performance.",
                explanation="Both are powerful ensemble methods with different strengths.",
                tags=["ensemble", "model_selection"]
            ),
            InterviewQuestion(
                type=QuestionType.ML_CONCEPT, difficulty=Difficulty.HARD,
                title="Attention Mechanism",
                question="Explain the attention mechanism in Transformers.",
                hints=["Query, Key, Value", "Scaled dot-product", "Self-attention"],
                solution="Attention(Q,K,V) = softmax(QK^T/√d_k)V. Self-attention: each position attends to all positions. Multi-head: multiple attention heads learn different relationships. Enables parallelization and captures long-range dependencies.",
                explanation="Foundation of modern NLP (BERT, GPT).",
                tags=["deep_learning", "transformers"]
            ),
            InterviewQuestion(
                type=QuestionType.ML_CONCEPT, difficulty=Difficulty.MEDIUM,
                title="Precision vs Recall",
                question="Explain precision and recall. When prioritize each?",
                hints=["FP vs FN", "Business context matters", "F1 for balance"],
                solution="Precision = TP/(TP+FP), Recall = TP/(TP+FN). Prioritize precision when FP costly (spam filter). Prioritize recall when FN costly (disease detection). F1 = harmonic mean for balance.",
                explanation="Critical for choosing the right metric.",
                tags=["evaluation", "metrics"]
            ),
            # Behavioral
            InterviewQuestion(
                type=QuestionType.BEHAVIORAL, difficulty=Difficulty.MEDIUM,
                title="Tell Me About Yourself",
                question="Tell me about yourself and why you're interested in this role.",
                hints=["Present → Past → Future", "Keep relevant", "2-3 minutes"],
                solution="Structure: 1. Current status (student at UC Berkeley), 2. What sparked interest, 3. Relevant projects/experience, 4. Why this role/company, 5. What you hope to learn/contribute.",
                explanation="Often the first question - make a strong impression.",
                tags=["introduction", "common"]
            ),
            InterviewQuestion(
                type=QuestionType.BEHAVIORAL, difficulty=Difficulty.MEDIUM,
                title="Challenging Project",
                question="Tell me about a challenging project. How did you overcome difficulties?",
                hints=["Use STAR method", "Focus on YOUR actions", "Quantify results"],
                solution="STAR: Situation (context), Task (your responsibility), Action (what YOU did), Result (outcome + learnings). Be specific, show problem-solving, mention what you learned.",
                explanation="Shows problem-solving and resilience.",
                tags=["problem_solving", "star_method"]
            ),
            InterviewQuestion(
                type=QuestionType.BEHAVIORAL, difficulty=Difficulty.MEDIUM,
                title="Team Conflict",
                question="Describe a time you had a conflict with a team member.",
                hints=["Show emotional intelligence", "Focus on resolution", "What you learned"],
                solution="1. Describe situation briefly, 2. Explain your approach (listened, understood their view), 3. How you resolved it (compromise, communication), 4. Positive outcome, 5. What you learned.",
                explanation="Shows interpersonal skills and maturity.",
                tags=["teamwork", "conflict_resolution"]
            ),
            InterviewQuestion(
                type=QuestionType.BEHAVIORAL, difficulty=Difficulty.EASY,
                title="Why This Company",
                question="Why do you want to work at our company?",
                hints=["Research the company", "Connect to your interests", "Be specific"],
                solution="1. Company-specific reasons (mission, products, culture), 2. Role alignment with your skills/interests, 3. Growth opportunity, 4. How you can contribute. Avoid generic answers.",
                explanation="Shows genuine interest and research.",
                tags=["motivation", "common"]
            ),
            InterviewQuestion(
                type=QuestionType.BEHAVIORAL, difficulty=Difficulty.MEDIUM,
                title="Failure Experience",
                question="Tell me about a time you failed. What did you learn?",
                hints=["Choose a real failure", "Focus on learning", "Show growth"],
                solution="1. Describe the failure honestly, 2. Take responsibility (no blame), 3. What you learned, 4. How you've applied that learning since. Show self-awareness and growth mindset.",
                explanation="Shows self-awareness and ability to learn.",
                tags=["self_awareness", "growth"]
            ),
            # System Design
            InterviewQuestion(
                type=QuestionType.SYSTEM_DESIGN, difficulty=Difficulty.MEDIUM,
                title="Design a Recommendation System",
                question="Design a movie recommendation system like Netflix.",
                hints=["Content-based vs collaborative", "Cold start problem", "Scalability"],
                solution="1. Requirements (scale, latency), 2. Approaches: Content-based (item features), Collaborative filtering (user-item matrix), Hybrid. 3. Architecture: Data pipeline, Feature store, Model serving, A/B testing. 4. Handle cold start with popular items.",
                explanation="Common ML system design question.",
                tags=["ml_systems", "recommendations"]
            ),
            InterviewQuestion(
                type=QuestionType.SYSTEM_DESIGN, difficulty=Difficulty.MEDIUM,
                title="Design a Fraud Detection System",
                question="Design a real-time fraud detection system for payments.",
                hints=["Real-time vs batch", "Feature engineering", "Handling imbalance"],
                solution="1. Requirements: Low latency, high recall. 2. Features: Transaction amount, location, time, user history. 3. Model: Ensemble (rules + ML). 4. Architecture: Stream processing, feature store, model serving. 5. Handle imbalance, minimize false positives.",
                explanation="Combines ML and systems thinking.",
                tags=["ml_systems", "real_time"]
            ),
            InterviewQuestion(
                type=QuestionType.SYSTEM_DESIGN, difficulty=Difficulty.HARD,
                title="Design ML Training Pipeline",
                question="Design a scalable ML training pipeline.",
                hints=["Data ingestion", "Feature engineering", "Model training", "Deployment"],
                solution="1. Data: Collection, validation, versioning. 2. Features: Feature store, transformation pipeline. 3. Training: Distributed training, hyperparameter tuning, experiment tracking. 4. Deployment: Model registry, A/B testing, monitoring. Tools: Airflow, MLflow, Kubeflow.",
                explanation="MLOps and infrastructure knowledge.",
                tags=["mlops", "infrastructure"]
            ),
        ]
