"""
Multi-Agent Coordinator for the intelligent intake system.
Coordinates between specialized agents to enhance question selection and analysis.
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.models.intake import QuestionSelectionResult
from app.services.question_selector import QuestionSelector
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


@dataclass
class AgentRecommendation:
    """Recommendation from a specialized agent."""

    agent_name: str
    question_ids: List[str]
    confidence_scores: Dict[str, float]
    reasoning: str
    domain_expertise: List[str]
    priority: int = 1


@dataclass
class AgentConsensus:
    """Consensus result from multiple agents."""

    selected_questions: List[str]
    agent_votes: Dict[str, List[str]]
    confidence_matrix: Dict[str, Dict[str, float]]
    consensus_score: float
    final_reasoning: str


class MultiAgentCoordinator:
    """
    Coordinates multiple specialized agents for enhanced question selection.

    This coordinator works with:
    - BusinessAnalyst Agent: Business requirements and stakeholders
    - TechnicalArchitect Agent: Architecture and technical decisions
    - ComplianceExpert Agent: Regulatory and security requirements
    - IndustryExpert Agent: Sector-specific knowledge
    - PerformanceEngineer Agent: NFRs and performance requirements
    """

    def __init__(self, question_selector: QuestionSelector):
        self.question_selector = question_selector
        self.agents = {}
        self.agent_endpoints = {
            "business_analyst": "http://localhost:8001",
            "technical_architect": "http://localhost:8002",
            "compliance_expert": "http://localhost:8003",
            "industry_expert": "http://localhost:8004",
            "performance_engineer": "http://localhost:8005",
        }
        self.orchestrator_endpoint = "http://localhost:8006"

        # Configuration
        self.max_concurrent_agents = 3
        self.consensus_threshold = 0.7
        self.confidence_threshold = 0.6

    async def enhanced_question_selection(
        self, intake_text: str, session_context: Optional[Dict] = None
    ) -> QuestionSelectionResult:
        """
        Enhanced question selection using multiple specialized agents.

        Args:
            intake_text: Original intake text from client
            session_context: Additional context from previous interactions

        Returns:
            Enhanced QuestionSelectionResult with agent recommendations
        """
        try:
            # 1. Get baseline selection from existing selector
            baseline_result = await self.question_selector.select_questions(intake_text)

            # 2. Analyze intake text to determine relevant agents
            relevant_agents = await self._identify_relevant_agents(intake_text)

            # 3. Get recommendations from each relevant agent
            agent_recommendations = await self._gather_agent_recommendations(
                intake_text, relevant_agents, session_context
            )

            # 4. Build consensus from agent recommendations
            consensus = await self._build_consensus(baseline_result, agent_recommendations)

            # 5. Merge with baseline and apply final selection logic
            enhanced_selection = await self._merge_selections(baseline_result, consensus)

            # 6. Add agent metadata to selection
            enhanced_selection.selection_metadata.update(
                {
                    "multi_agent_enabled": True,
                    "relevant_agents": relevant_agents,
                    "agent_consensus_score": consensus.consensus_score,
                    "agent_recommendations_count": len(agent_recommendations),
                    "enhanced_by": "multi_agent_coordinator",
                }
            )

            logger.info(f"Enhanced selection with {len(relevant_agents)} agents")
            logger.info(f"Consensus score: {consensus.consensus_score}")

            return enhanced_selection

        except Exception as e:
            logger.error(f"Error in enhanced selection: {str(e)}")
            # Fallback to baseline selection
            return baseline_result

    async def _identify_relevant_agents(self, intake_text: str) -> List[str]:
        """
        Identify which agents are most relevant for the given intake text.

        Args:
            intake_text: Client's project description

        Returns:
            List of relevant agent names
        """
        relevant_agents = []

        # Simple keyword-based agent relevance (could be enhanced with ML)
        text_lower = intake_text.lower()

        # Business Analyst - always relevant for business context
        relevant_agents.append("business_analyst")

        # Technical Architect - if technical terms mentioned
        tech_keywords = ["api", "database", "architecture", "microservices", "cloud", "integration"]
        if any(keyword in text_lower for keyword in tech_keywords):
            relevant_agents.append("technical_architect")

        # Compliance Expert - if compliance/security mentioned
        compliance_keywords = ["compliance", "security", "gdpr", "lgpd", "regulation", "audit"]
        if any(keyword in text_lower for keyword in compliance_keywords):
            relevant_agents.append("compliance_expert")

        # Industry Expert - if specific industry mentioned
        industry_keywords = ["healthcare", "finance", "ecommerce", "education", "government"]
        if any(keyword in text_lower for keyword in industry_keywords):
            relevant_agents.append("industry_expert")

        # Performance Engineer - if performance/scale mentioned
        perf_keywords = ["performance", "scale", "users", "load", "concurrent", "throughput"]
        if any(keyword in text_lower for keyword in perf_keywords):
            relevant_agents.append("performance_engineer")

        # Ensure we have at least 2 agents and at most max_concurrent_agents
        if len(relevant_agents) < 2:
            relevant_agents.append("technical_architect")

        return relevant_agents[: self.max_concurrent_agents]

    async def _gather_agent_recommendations(
        self, intake_text: str, agent_names: List[str], context: Optional[Dict] = None
    ) -> List[AgentRecommendation]:
        """
        Gather recommendations from multiple agents concurrently.

        Args:
            intake_text: Client's project description
            agent_names: List of agent names to consult
            context: Session context

        Returns:
            List of agent recommendations
        """
        recommendations = []

        # Create tasks for concurrent agent consultation
        tasks = []
        for agent_name in agent_names:
            task = self._consult_agent(agent_name, intake_text, context)
            tasks.append(task)

        # Execute concurrently with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=30.0
            )

            # Process results
            for i, result in enumerate(results):
                if isinstance(result, AgentRecommendation):
                    recommendations.append(result)
                else:
                    logger.warning(f"Agent {agent_names[i]} failed: {result}")

        except asyncio.TimeoutError:
            logger.warning("Agent consultation timeout")

        return recommendations

    async def _consult_agent(
        self, agent_name: str, intake_text: str, context: Optional[Dict] = None
    ) -> AgentRecommendation:
        """
        Consult a single specialized agent.

        Args:
            agent_name: Name of the agent to consult
            intake_text: Client's project description
            context: Session context

        Returns:
            Agent recommendation
        """
        try:
            # In a real implementation, this would make HTTP calls to agent endpoints
            # For now, we'll simulate agent behavior based on their expertise

            if agent_name == "business_analyst":
                return await self._simulate_business_analyst(intake_text)
            elif agent_name == "technical_architect":
                return await self._simulate_technical_architect(intake_text)
            elif agent_name == "compliance_expert":
                return await self._simulate_compliance_expert(intake_text)
            elif agent_name == "industry_expert":
                return await self._simulate_industry_expert(intake_text)
            elif agent_name == "performance_engineer":
                return await self._simulate_performance_engineer(intake_text)
            else:
                raise ValueError(f"Unknown agent: {agent_name}")

        except Exception as e:
            logger.error(f"Error consulting {agent_name}: {str(e)}")
            # Return empty recommendation
            return AgentRecommendation(
                agent_name=agent_name,
                question_ids=[],
                confidence_scores={},
                reasoning=f"Agent consultation failed: {str(e)}",
                domain_expertise=[],
                priority=5,
            )

    async def _simulate_business_analyst(self, intake_text: str) -> AgentRecommendation:
        """Simulate BusinessAnalyst agent behavior."""

        # Focus on business-stage questions
        business_questions = [q.id for q in self.question_selector.catalog if q.stage == "business"]

        # Prioritize key business questions
        priority_questions = []

        # Always recommend project type and budget questions
        priority_questions.extend(["B001", "B004", "B002"])  # Type, Budget, Problem

        # Add stakeholder and success metrics
        priority_questions.extend(["B006", "B007"])  # Stakeholders, Success metrics

        # Industry and compliance if relevant
        text_lower = intake_text.lower()
        if any(word in text_lower for word in ["healthcare", "finance", "government"]):
            priority_questions.append("B008")  # Compliance requirements

        # Filter to existing questions and limit to 5
        selected_ids = [qid for qid in priority_questions if qid in business_questions][:5]

        confidence_scores = {qid: 0.9 for qid in selected_ids}

        return AgentRecommendation(
            agent_name="business_analyst",
            question_ids=selected_ids,
            confidence_scores=confidence_scores,
            reasoning="Focused on business objectives, stakeholders, and strategic alignment",
            domain_expertise=["business_requirements", "stakeholder_analysis", "roi_analysis"],
            priority=1,
        )

    async def _simulate_technical_architect(self, intake_text: str) -> AgentRecommendation:
        """Simulate TechnicalArchitect agent behavior."""

        # Focus on technical and functional questions
        tech_questions = [
            q.id for q in self.question_selector.catalog if q.stage in ["technical", "functional"]
        ]

        priority_questions = []

        # Architecture and platform questions
        priority_questions.extend(["T001", "T002"])  # Architecture pattern, Hosting

        # Application type and features
        priority_questions.extend(["F001", "F002"])  # App type, Features

        # Integration needs
        text_lower = intake_text.lower()
        if any(word in text_lower for word in ["integration", "api", "system"]):
            priority_questions.append("B011")  # Integration needs

        selected_ids = [qid for qid in priority_questions if qid in tech_questions][:4]

        confidence_scores = {qid: 0.85 for qid in selected_ids}

        return AgentRecommendation(
            agent_name="technical_architect",
            question_ids=selected_ids,
            confidence_scores=confidence_scores,
            reasoning="Focused on architecture patterns, technology stack, and technical feasibility",
            domain_expertise=["system_architecture", "tech_stack_selection", "scalability_design"],
            priority=2,
        )

    async def _simulate_compliance_expert(self, intake_text: str) -> AgentRecommendation:
        """Simulate ComplianceExpert agent behavior."""

        # Focus on compliance and security
        priority_questions = []

        # Always ask about compliance requirements
        priority_questions.append("B008")  # Compliance requirements

        # Industry-specific compliance
        text_lower = intake_text.lower()
        if "healthcare" in text_lower:
            # Would focus on HIPAA-related questions
            pass
        elif any(word in text_lower for word in ["finance", "payment", "bank"]):
            # Would focus on PCI-DSS, SOX questions
            pass

        # Authentication and security for functional stage
        priority_questions.append("F003")  # Authentication methods

        selected_ids = [
            qid
            for qid in priority_questions
            if any(q.id == qid for q in self.question_selector.catalog)
        ][:3]

        confidence_scores = {qid: 0.95 for qid in selected_ids}

        return AgentRecommendation(
            agent_name="compliance_expert",
            question_ids=selected_ids,
            confidence_scores=confidence_scores,
            reasoning="Focused on regulatory compliance, data protection, and security requirements",
            domain_expertise=["regulatory_compliance", "data_protection", "security_requirements"],
            priority=2,
        )

    async def _simulate_industry_expert(self, intake_text: str) -> AgentRecommendation:
        """Simulate IndustryExpert agent behavior."""

        text_lower = intake_text.lower()
        priority_questions = []

        # Industry identification
        priority_questions.append("B003")  # Industry sector

        # Industry-specific features
        if "ecommerce" in text_lower or "retail" in text_lower:
            priority_questions.append("B010")  # Business model

        # Scale considerations by industry
        if any(word in text_lower for word in ["enterprise", "large", "corporate"]):
            priority_questions.append("B009")  # User scale

        selected_ids = [
            qid
            for qid in priority_questions
            if any(q.id == qid for q in self.question_selector.catalog)
        ][:4]

        confidence_scores = {qid: 0.8 for qid in selected_ids}

        return AgentRecommendation(
            agent_name="industry_expert",
            question_ids=selected_ids,
            confidence_scores=confidence_scores,
            reasoning="Focused on industry-specific requirements and domain knowledge",
            domain_expertise=["sector_requirements", "industry_standards", "market_analysis"],
            priority=3,
        )

    async def _simulate_performance_engineer(self, intake_text: str) -> AgentRecommendation:
        """Simulate PerformanceEngineer agent behavior."""

        # Focus on NFR questions
        nfr_questions = [q.id for q in self.question_selector.catalog if q.stage == "nfr"]

        priority_questions = []

        # Core performance questions
        priority_questions.extend(["N001", "N002"])  # Performance, Availability

        # Scale-related questions
        text_lower = intake_text.lower()
        if any(word in text_lower for word in ["scale", "users", "concurrent", "load"]):
            priority_questions.append("B009")  # Expected users

        selected_ids = [qid for qid in priority_questions if qid in nfr_questions][:3]

        confidence_scores = {qid: 0.9 for qid in selected_ids}

        return AgentRecommendation(
            agent_name="performance_engineer",
            question_ids=selected_ids,
            confidence_scores=confidence_scores,
            reasoning="Focused on performance requirements, scalability, and system reliability",
            domain_expertise=[
                "performance_requirements",
                "scalability_analysis",
                "monitoring_design",
            ],
            priority=2,
        )

    async def _build_consensus(
        self,
        baseline_result: QuestionSelectionResult,
        agent_recommendations: List[AgentRecommendation],
    ) -> AgentConsensus:
        """
        Build consensus from multiple agent recommendations.

        Args:
            baseline_result: Original question selection result
            agent_recommendations: List of agent recommendations

        Returns:
            Agent consensus result
        """
        if not agent_recommendations:
            return AgentConsensus(
                selected_questions=baseline_result.selected_ids,
                agent_votes={},
                confidence_matrix={},
                consensus_score=1.0,
                final_reasoning="No agent recommendations available, using baseline",
            )

        # Collect all recommended questions with votes
        question_votes = {}
        confidence_matrix = {}

        # Add baseline as a "vote"
        for qid in baseline_result.selected_ids:
            question_votes[qid] = question_votes.get(qid, 0) + 1

        # Add agent votes
        agent_votes = {}
        for rec in agent_recommendations:
            agent_votes[rec.agent_name] = rec.question_ids
            confidence_matrix[rec.agent_name] = rec.confidence_scores

            for qid in rec.question_ids:
                question_votes[qid] = question_votes.get(qid, 0) + 1

        # Calculate consensus score
        total_voters = len(agent_recommendations) + 1  # +1 for baseline
        consensus_threshold_votes = int(total_voters * self.consensus_threshold)

        # Select questions with sufficient votes
        consensus_questions = [
            qid for qid, votes in question_votes.items() if votes >= consensus_threshold_votes
        ]

        # If consensus is too restrictive, use top-voted questions
        if len(consensus_questions) < 5:
            sorted_questions = sorted(question_votes.items(), key=lambda x: x[1], reverse=True)
            consensus_questions = [qid for qid, _ in sorted_questions[:8]]

        # Calculate overall consensus score
        if question_votes:
            consensus_score = sum(question_votes.values()) / (len(question_votes) * total_voters)
        else:
            consensus_score = 0.0

        reasoning_parts = []
        for rec in agent_recommendations:
            reasoning_parts.append(f"{rec.agent_name}: {rec.reasoning}")
        final_reasoning = "; ".join(reasoning_parts)

        return AgentConsensus(
            selected_questions=consensus_questions,
            agent_votes=agent_votes,
            confidence_matrix=confidence_matrix,
            consensus_score=consensus_score,
            final_reasoning=final_reasoning,
        )

    async def _merge_selections(
        self, baseline: QuestionSelectionResult, consensus: AgentConsensus
    ) -> QuestionSelectionResult:
        """
        Merge baseline selection with agent consensus.

        Args:
            baseline: Original selection result
            consensus: Agent consensus result

        Returns:
            Merged selection result
        """
        # Start with consensus questions
        merged_ids = consensus.selected_questions.copy()

        # Add high-priority baseline questions if missing
        for qid in baseline.selected_ids:
            if qid not in merged_ids:
                question = next((q for q in self.question_selector.catalog if q.id == qid), None)
                if question and question.required:
                    merged_ids.append(qid)

        # Limit to max questions
        merged_ids = merged_ids[:10]

        # Update metadata
        enhanced_metadata = baseline.selection_metadata.copy()
        enhanced_metadata.update(
            {
                "agent_consensus_score": consensus.consensus_score,
                "agent_votes": consensus.agent_votes,
                "consensus_questions": len(consensus.selected_questions),
                "final_reasoning": consensus.final_reasoning,
            }
        )

        return QuestionSelectionResult(
            selected_ids=merged_ids, selection_metadata=enhanced_metadata
        )
