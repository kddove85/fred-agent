"""
AI Economic Assistant Test Suite
Tests tool usage, accuracy, analysis quality, and adherence to system prompt
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
import re


@dataclass
class TestScore:
    """Scoring for a single test"""
    tool_usage: int  # max 25
    data_accuracy: int  # max 25
    analysis_quality: int  # max 25
    communication: int  # max 15
    prompt_adherence: int  # max 10

    @property
    def total(self) -> int:
        return (self.tool_usage + self.data_accuracy +
                self.analysis_quality + self.communication +
                self.prompt_adherence)

    @property
    def grade(self) -> str:
        if self.total >= 90:
            return "A (Excellent)"
        elif self.total >= 80:
            return "B (Good)"
        elif self.total >= 70:
            return "C (Adequate)"
        elif self.total >= 60:
            return "D (Poor)"
        else:
            return "F (Failed)"


@dataclass
class TestResult:
    """Complete test result"""
    test_name: str
    prompt: str
    response: str
    tool_calls: List[Dict]
    score: TestScore
    strengths: List[str]
    weaknesses: List[str]
    critical_issues: List[str]
    timestamp: str

    def to_dict(self):
        return {
            **asdict(self),
            'score': asdict(self.score),
            'total_score': self.score.total,
            'grade': self.score.grade
        }


class AIAssistantEvaluator:
    """Evaluates AI assistant responses against rubric"""

    def __init__(self):
        self.results: List[TestResult] = []

    async def run_test(
            self,
            test_name: str,
            prompt: str,
            ai_function,  # Your function that calls the AI
            expected_tools: List[str] = None,
            expected_data_points: List[str] = None
    ) -> TestResult:
        """
        Run a single test and evaluate the response

        Args:
            test_name: Name of the test
            prompt: The prompt to send to AI
            ai_function: Async function that takes prompt and returns (response, tool_calls)
            expected_tools: List of tool names expected to be called
            expected_data_points: List of data points expected in response
        """
        print(f"\n{'=' * 80}")
        print(f"Running Test: {test_name}")
        print(f"{'=' * 80}")
        print(f"Prompt: {prompt}\n")

        # Get AI response
        response, tool_calls = await ai_function(prompt)

        print(f"Response length: {len(response)} characters")
        print(f"Tools called: {[tool.get('name', 'unknown') for tool in tool_calls]}\n")

        # Evaluate
        score = self._evaluate_response(
            response,
            tool_calls,
            expected_tools,
            expected_data_points
        )

        strengths, weaknesses, critical_issues = self._identify_issues(
            response,
            tool_calls,
            score
        )

        result = TestResult(
            test_name=test_name,
            prompt=prompt,
            response=response,
            tool_calls=tool_calls,
            score=score,
            strengths=strengths,
            weaknesses=weaknesses,
            critical_issues=critical_issues,
            timestamp=datetime.now().isoformat()
        )

        self.results.append(result)
        self._print_result(result)

        return result

    def _evaluate_response(
            self,
            response: str,
            tool_calls: List[Dict],
            expected_tools: List[str],
            expected_data_points: List[str]
    ) -> TestScore:
        """Evaluate response against rubric"""

        # Category 1: Tool Usage (25 points)
        tool_usage = self._score_tool_usage(tool_calls, expected_tools)

        # Category 2: Data Accuracy & Citations (25 points)
        data_accuracy = self._score_data_accuracy(response, tool_calls, expected_data_points)

        # Category 3: Analysis Quality (25 points)
        analysis_quality = self._score_analysis_quality(response)

        # Category 4: Communication (15 points)
        communication = self._score_communication(response)

        # Category 5: Prompt Adherence (10 points)
        prompt_adherence = self._score_prompt_adherence(response, tool_calls)

        return TestScore(
            tool_usage=tool_usage,
            data_accuracy=data_accuracy,
            analysis_quality=analysis_quality,
            communication=communication,
            prompt_adherence=prompt_adherence
        )

    def _score_tool_usage(self, tool_calls: List[Dict], expected_tools: List[str]) -> int:
        """Score tool usage (max 25 points)"""
        score = 0

        # 1.1 Appropriate Tool Selection (10 points)
        if not expected_tools:
            score += 7
        else:
            tools_called = [tool.get('name', '') for tool in tool_calls]
            expected_called = sum(1 for tool in expected_tools if tool in tools_called)
            if expected_called == len(expected_tools):
                score += 10
            elif expected_called >= len(expected_tools) * 0.7:
                score += 7
            elif expected_called >= len(expected_tools) * 0.5:
                score += 5
            else:
                score += 2

        # 1.2 Tool Call Efficiency (5 points)
        num_calls = len(tool_calls)
        if num_calls == 0:
            score += 0
        elif num_calls <= 5:
            score += 5
        elif num_calls <= 10:
            score += 4
        else:
            score += 2

        # 1.3 Multi-Tool Coordination (10 points) - FIXED
        unique_tools = len(set(tool.get('name', '') for tool in tool_calls))
        if unique_tools >= 2:
            # Check for FRED data tools (fixed to check actual tool names)
            has_fred_data = any(
                'series' in tool.get('name', '').lower() or
                'fred' in tool.get('name', '').lower()
                for tool in tool_calls
            )
            # Check for news tools
            has_news = any(
                'news' in tool.get('name', '').lower() or
                'article' in tool.get('name', '').lower()
                for tool in tool_calls
            )

            if has_fred_data and has_news:
                score += 10  # ✅ Now properly detects FRED + news
            elif unique_tools >= 2:
                score += 7
            else:
                score += 4
        elif unique_tools == 1:
            score += 3
        else:
            score += 0

        return min(score, 25)

    def _score_data_accuracy(
            self,
            response: str,
            tool_calls: List[Dict],
            expected_data_points: List[str]
    ) -> int:
        """Score data accuracy and citations (max 25 points)"""
        score = 0

        # 2.1 Factual Accuracy (10 points)
        # Check if uses tools vs training data
        if tool_calls:
            score += 10  # Used tools for current data
        else:
            # Check if claims to have current data without tools
            if any(word in response.lower() for word in ['current', 'latest', 'today', 'now']):
                score += 2  # Red flag: claims current data without tools
            else:
                score += 5  # At least honest about limitations

        # 2.2 Source Attribution (10 points)
        citation_patterns = [
            r'according to (?:fred|bls|bea|federal reserve)',
            r'fred data (?:as of|from)',
            r'(?:source|data from):\s*(?:fred|bls|bea)',
            r'(?:primary|secondary)\s*(?:source)?',
        ]

        citations_found = sum(
            1 for pattern in citation_patterns
            if re.search(pattern, response.lower())
        )

        if citations_found >= 3:
            score += 10
        elif citations_found >= 2:
            score += 7
        elif citations_found >= 1:
            score += 4
        else:
            score += 0

        # 2.3 Data Presentation (5 points)
        # Check for specific numbers, dates, percentages
        has_percentages = bool(re.search(r'\d+\.?\d*%', response))
        has_dates = bool(re.search(
            r'\d{4}|\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
            response.lower()))
        has_specific_numbers = bool(re.search(r'\d+\.?\d+', response))

        specificity = sum([has_percentages, has_dates, has_specific_numbers])

        if specificity == 3:
            score += 5
        elif specificity == 2:
            score += 4
        elif specificity == 1:
            score += 2
        else:
            score += 0

        return min(score, 25)

    def _score_analysis_quality(self, response: str) -> int:
        """Score analysis quality (max 25 points)"""
        score = 0
        response_lower = response.lower()

        # 3.1 Trend Identification (10 points)
        trend_indicators = [
            'trend', 'rising', 'falling', 'increasing', 'decreasing',
            'upward', 'downward', 'stable', 'declining', 'growing'
        ]

        has_trend_words = sum(1 for word in trend_indicators if word in response_lower)
        has_direction = any(word in response_lower for word in ['up', 'down', 'rising', 'falling', 'stable'])
        has_magnitude = any(
            word in response_lower for word in ['sharply', 'gradually', 'slightly', 'significantly', 'moderately'])

        if has_trend_words >= 3 and has_direction and has_magnitude:
            score += 10
        elif has_trend_words >= 2 and has_direction:
            score += 7
        elif has_trend_words >= 1:
            score += 4
        else:
            score += 0

        # 3.2 Synthesis & Context (10 points)
        synthesis_indicators = [
            'based on', 'combined with', 'together with', 'indicates',
            'suggests', 'context', 'because', 'due to', 'as a result'
        ]

        synthesis_count = sum(1 for phrase in synthesis_indicators if phrase in response_lower)

        if synthesis_count >= 4:
            score += 10
        elif synthesis_count >= 3:
            score += 7
        elif synthesis_count >= 2:
            score += 5
        else:
            score += 2

        # 3.3 Predictive Reasoning (5 points)
        has_prediction = any(
            word in response_lower for word in ['outlook', 'forecast', 'predict', 'expect', 'likely', 'next'])
        has_confidence = any(
            word in response_lower for word in ['confidence', 'uncertain', 'likely', 'probably', 'may', 'could'])
        has_caveat = any(
            word in response_lower for word in ['however', 'although', 'caveat', 'limitation', 'uncertain', 'risk'])

        prediction_score = sum([has_prediction, has_confidence, has_caveat])

        if prediction_score == 3:
            score += 5
        elif prediction_score == 2:
            score += 4
        elif prediction_score == 1:
            score += 2
        else:
            score += 0

        return min(score, 25)

    def _score_communication(self, response: str) -> int:
        """Score communication quality (max 15 points)"""
        score = 0

        # 4.1 Clarity & Organization (5 points)
        # Basic checks for structure
        has_paragraphs = response.count('\n\n') >= 1
        reasonable_length = 200 <= len(response) <= 3000

        if has_paragraphs and reasonable_length:
            score += 5
        elif has_paragraphs or reasonable_length:
            score += 3
        else:
            score += 1

        # 4.2 Appropriate Detail Level (5 points)
        word_count = len(response.split())

        if 150 <= word_count <= 500:
            score += 5  # Sweet spot
        elif 100 <= word_count <= 700:
            score += 4
        elif 50 <= word_count <= 1000:
            score += 3
        else:
            score += 1  # Too short or too long

        # 4.3 Actionable Insights (5 points)
        actionable_indicators = [
            'suggest', 'recommend', 'monitor', 'watch', 'consider',
            'should', 'could', 'next steps', 'follow up', 'key factors'
        ]

        actionable_count = sum(1 for phrase in actionable_indicators if phrase in response.lower())

        if actionable_count >= 3:
            score += 5
        elif actionable_count >= 2:
            score += 4
        elif actionable_count >= 1:
            score += 2
        else:
            score += 0

        return min(score, 15)

    def _score_prompt_adherence(self, response: str, tool_calls: List[Dict]) -> int:
        """Score adherence to system prompt (max 10 points)"""
        score = 0
        response_lower = response.lower()

        # 5.1 Follows Instructions (5 points)
        uses_tools_for_current = len(tool_calls) > 0
        acknowledges_uncertainty = any(
            word in response_lower for word in ['uncertain', 'may', 'could', 'likely', 'confidence'])
        professional_tone = not any(word in response_lower for word in ['lol', 'omg', 'wtf', '😀', '😊'])

        instruction_score = sum([uses_tools_for_current, acknowledges_uncertainty, professional_tone])
        score += min(instruction_score * 2, 5)  # Max 5 points

        # 5.2 Proactive Helpfulness (5 points)
        proactive_indicators = [
            'would you like', 'i can also', 'additionally',
            'you might also', 'consider', 'i suggest', 'related'
        ]

        proactive_count = sum(1 for phrase in proactive_indicators if phrase in response_lower)

        if proactive_count >= 2:
            score += 5
        elif proactive_count >= 1:
            score += 3
        else:
            score += 1

        return min(score, 10)

    def _identify_issues(
            self,
            response: str,
            tool_calls: List[Dict],
            score: TestScore
    ) -> Tuple[List[str], List[str], List[str]]:
        """Identify strengths, weaknesses, and critical issues"""
        strengths = []
        weaknesses = []
        critical_issues = []

        # Check for strengths
        if score.tool_usage >= 20:
            strengths.append("Excellent tool usage and coordination")
        if score.data_accuracy >= 20:
            strengths.append("Strong data accuracy and citation practices")
        if score.analysis_quality >= 20:
            strengths.append("High-quality analysis with good trend identification")
        if score.communication >= 12:
            strengths.append("Clear and well-organized communication")

        # Check for weaknesses
        if score.tool_usage < 15:
            weaknesses.append("Poor tool selection or inefficient usage")
        if score.data_accuracy < 15:
            weaknesses.append("Weak citations or missing specific data points")
        if score.analysis_quality < 15:
            weaknesses.append("Superficial analysis lacking depth or context")
        if score.communication < 10:
            weaknesses.append("Communication could be clearer or better organized")
        if score.prompt_adherence < 6:
            weaknesses.append("Not following system prompt guidelines")

        # Check for critical issues (red flags)
        response_lower = response.lower()

        # Red flag: Claims current data without tools
        if not tool_calls and any(word in response_lower for word in ['current', 'latest', 'now', 'today']):
            critical_issues.append("⚠️ CRITICAL: Claims current data without using tools")

        # Red flag: No citations for factual claims
        has_numbers = bool(re.search(r'\d+\.?\d*%', response))
        has_citations = bool(re.search(r'according to|source|fred|bls', response_lower))
        if has_numbers and not has_citations:
            critical_issues.append("⚠️ CRITICAL: Provides data without source attribution")

        # Red flag: Confident predictions without caveats
        has_prediction = any(word in response_lower for word in ['will', 'forecast', 'predict'])
        has_caveat = any(word in response_lower for word in ['uncertain', 'may', 'could', 'however', 'risk'])
        if has_prediction and not has_caveat:
            critical_issues.append("⚠️ WARNING: Makes predictions without acknowledging uncertainty")

        # Red flag: Uses only training data for current questions
        if 'cutoff' in response_lower and not tool_calls:
            critical_issues.append("⚠️ CRITICAL: Mentions knowledge cutoff instead of using tools")

        return strengths, weaknesses, critical_issues

    def _print_result(self, result: TestResult):
        """Print formatted test result"""
        print(f"\n{'=' * 80}")
        print(f"TEST RESULTS: {result.test_name}")
        print(f"{'=' * 80}")
        print(f"\nSCORES:")
        print(f"  Tool Usage:         {result.score.tool_usage:2d} / 25")
        print(f"  Data Accuracy:      {result.score.data_accuracy:2d} / 25")
        print(f"  Analysis Quality:   {result.score.analysis_quality:2d} / 25")
        print(f"  Communication:      {result.score.communication:2d} / 15")
        print(f"  Prompt Adherence:   {result.score.prompt_adherence:2d} / 10")
        print(f"  " + "-" * 40)
        print(f"  TOTAL:              {result.score.total:2d} / 100")
        print(f"  GRADE:              {result.score.grade}")

        if result.strengths:
            print(f"\n✅ STRENGTHS:")
            for strength in result.strengths:
                print(f"  • {strength}")

        if result.weaknesses:
            print(f"\n⚠️  WEAKNESSES:")
            for weakness in result.weaknesses:
                print(f"  • {weakness}")

        if result.critical_issues:
            print(f"\n🚨 CRITICAL ISSUES:")
            for issue in result.critical_issues:
                print(f"  • {issue}")

        print(f"\n{'=' * 80}\n")

    def generate_report(self, filename: str = "test_report.json"):
        """Generate comprehensive test report"""
        report = {
            'test_run_date': datetime.now().isoformat(),
            'total_tests': len(self.results),
            'average_score': sum(r.score.total for r in self.results) / len(self.results) if self.results else 0,
            'tests': [result.to_dict() for result in self.results]
        }

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n📊 Test report saved to: {filename}")

        # Print summary
        print(f"\n{'=' * 80}")
        print("TEST SUITE SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total Tests Run: {report['total_tests']}")
        print(f"Average Score: {report['average_score']:.1f} / 100")

        if self.results:
            best = max(self.results, key=lambda r: r.score.total)
            worst = min(self.results, key=lambda r: r.score.total)

            print(f"\nBest Performance: {best.test_name} ({best.score.total}/100)")
            print(f"Worst Performance: {worst.test_name} ({worst.score.total}/100)")

        print(f"{'=' * 80}\n")


# ============================================================================
# TEST SUITE
# ============================================================================

async def mock_ai_function(prompt: str) -> Tuple[str, List[Dict]]:
    """
    Calls your actual FRED client agent and returns response + tool calls
    """
    from fred_client import AgenticMCPClient
    import sys

    # Initialize client
    client = AgenticMCPClient()

    # Connect to MCP server (same as main)
    server_script = "mcp_server.py"
    command = f"python {server_script}"
    await client.connect_to_mcp_server(command)

    # Create conversation history with the prompt
    conversation_history = [{"role": "user", "content": prompt}]

    # Run agent with tracking
    response, tool_calls = await client.run_agentic_loop_with_tracking(conversation_history)

    # Cleanup
    await client.close()

    return response, tool_calls



async def run_test_suite():
    """Run the complete test suite"""

    evaluator = AIAssistantEvaluator()

    # Test 1: Basic Inflation Query
    await evaluator.run_test(
        test_name="Test 1: Basic Inflation Check",
        prompt="What's happening with inflation right now? Pull the latest CPI data from FRED and check recent economic news articles.",
        ai_function=mock_ai_function,
        expected_tools=['MCP_FRED:get_series_observations', 'get_economic_articles_for_analysis'],
        expected_data_points=['CPI', 'percentage', 'trend']
    )

    # Test 2: Unemployment Trend
    await evaluator.run_test(
        test_name="Test 2: Unemployment Trend Analysis",
        prompt="Analyze the unemployment trend over the past 6 months. What do recent news articles say about the labor market?",
        ai_function=mock_ai_function,
        expected_tools=['MCP_FRED:get_series_observations', 'get_economic_articles_for_analysis']
    )

    # Test 3: Multi-Indicator Analysis
    await evaluator.run_test(
        test_name="Test 3: Economic Snapshot",
        prompt="Give me an economic snapshot: what's happening with GDP growth, inflation, and unemployment? Include both data and recent news.",
        ai_function=mock_ai_function,
        expected_tools=['MCP_FRED:get_series_observations', 'get_economic_articles_for_analysis']
    )

    # Test 4: Prediction with Confidence
    await evaluator.run_test(
        test_name="Test 4: Interest Rate Outlook",
        prompt="Based on current trends and recent economic news, what's your outlook for interest rates over the next quarter? Provide confidence level.",
        ai_function=mock_ai_function,
        expected_tools=['MCP_FRED:get_series_observations', 'get_economic_articles_for_analysis']
    )

    # Test 5: Official Sources Only
    await evaluator.run_test(
        test_name="Test 5: Fed Announcements",
        prompt="What has the Federal Reserve announced recently? Only check official sources.",
        ai_function=mock_ai_function,
        expected_tools=['get_primary_source_economic_news']
    )

    # Generate final report
    evaluator.generate_report('ai_assistant_test_report.json')

    return evaluator


if __name__ == "__main__":
    print("🧪 Starting AI Economic Assistant Test Suite")
    print("=" * 80)

    # Run tests
    evaluator = asyncio.run(run_test_suite())

    print("\n✅ Test suite completed!")
    print(f"Check 'ai_assistant_test_report.json' for detailed results")