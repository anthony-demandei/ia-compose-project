"""
Multi-Agent API endpoints for the intelligent intake system.
Provides direct access to multi-agent coordination and individual agent capabilities.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List

from app.models.intake import IntakeRequest
from app.services.multi_agent_coordinator import MultiAgentCoordinator
from app.utils.config import get_settings
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)

# Criar router
router = APIRouter(prefix="/v1/multi-agent", tags=["multi-agent"])


# Dependency para obter o MultiAgentCoordinator
def get_multi_agent_coordinator() -> MultiAgentCoordinator:
    """Dependency para obter o MultiAgentCoordinator."""
    settings = get_settings()
    from app.services.question_selector import QuestionSelector

    question_selector = QuestionSelector(settings.openai_api_key)
    return MultiAgentCoordinator(question_selector)


@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_with_agents(
    request: IntakeRequest,
    coordinator: MultiAgentCoordinator = Depends(get_multi_agent_coordinator),
) -> Dict[str, Any]:
    """
    Analyze intake text using multiple specialized agents.

    Returns detailed analysis from each agent including:
    - Question recommendations
    - Confidence scores
    - Agent reasoning
    - Consensus building results
    """
    try:
        logger.info("Iniciando análise multi-agent")

        # Perform enhanced question selection
        result = await coordinator.enhanced_question_selection(
            intake_text=request.text, session_context=request.metadata
        )

        # Extract agent-specific information from metadata
        agent_info = {}
        if "agent_votes" in result.selection_metadata:
            agent_votes = result.selection_metadata["agent_votes"]

            for agent_name, questions in agent_votes.items():
                agent_info[agent_name] = {
                    "recommended_questions": questions,
                    "question_count": len(questions),
                    "expertise": coordinator._get_agent_expertise(agent_name),
                }

        return {
            "analysis_id": f"multi-agent-{hash(request.text) % 10000}",
            "selected_questions": result.selected_ids,
            "total_questions": len(result.selected_ids),
            "consensus_score": result.selection_metadata.get("agent_consensus_score", 0.0),
            "agent_analysis": agent_info,
            "metadata": {
                "relevant_agents": result.selection_metadata.get("relevant_agents", []),
                "consensus_questions": result.selection_metadata.get("consensus_questions", 0),
                "final_reasoning": result.selection_metadata.get("final_reasoning", ""),
                "multi_agent_enabled": result.selection_metadata.get("multi_agent_enabled", False),
            },
        }

    except Exception as e:
        logger.error(f"Erro na análise multi-agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents", response_model=Dict[str, Any])
async def list_available_agents(
    coordinator: MultiAgentCoordinator = Depends(get_multi_agent_coordinator),
) -> Dict[str, Any]:
    """
    List all available agents and their capabilities.
    """
    try:
        agents_info = {}

        for agent_name, endpoint in coordinator.agent_endpoints.items():
            agents_info[agent_name] = {
                "endpoint": endpoint,
                "domain": agent_name.split("_")[0],
                "expertise": coordinator._get_agent_expertise(agent_name),
                "question_stages": coordinator._get_agent_stages(agent_name),
                "status": "available",  # In real implementation, check actual status
            }

        return {
            "available_agents": list(agents_info.keys()),
            "total_agents": len(agents_info),
            "agents": agents_info,
            "orchestrator": {
                "endpoint": coordinator.orchestrator_endpoint,
                "max_concurrent_agents": coordinator.max_concurrent_agents,
                "consensus_threshold": coordinator.consensus_threshold,
                "confidence_threshold": coordinator.confidence_threshold,
            },
        }

    except Exception as e:
        logger.error(f"Erro ao listar agentes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/{agent_name}/consult", response_model=Dict[str, Any])
async def consult_specific_agent(
    agent_name: str,
    request: IntakeRequest,
    coordinator: MultiAgentCoordinator = Depends(get_multi_agent_coordinator),
) -> Dict[str, Any]:
    """
    Consult a specific agent directly for analysis.

    Useful for testing individual agent behavior or getting
    domain-specific insights.
    """
    try:
        if agent_name not in coordinator.agent_endpoints:
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{agent_name}' not found. Available agents: {list(coordinator.agent_endpoints.keys())}",
            )

        logger.info(f"Consultando agente específico: {agent_name}")

        # Consult individual agent
        recommendation = await coordinator._consult_agent(
            agent_name, request.text, request.metadata
        )

        return {
            "agent_name": recommendation.agent_name,
            "recommended_questions": recommendation.question_ids,
            "confidence_scores": recommendation.confidence_scores,
            "reasoning": recommendation.reasoning,
            "domain_expertise": recommendation.domain_expertise,
            "priority": recommendation.priority,
            "question_count": len(recommendation.question_ids),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao consultar agente {agent_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consensus", response_model=Dict[str, Any])
async def build_consensus(
    agent_recommendations: List[Dict[str, Any]],
    coordinator: MultiAgentCoordinator = Depends(get_multi_agent_coordinator),
) -> Dict[str, Any]:
    """
    Build consensus from provided agent recommendations.

    Useful for testing consensus algorithms or processing
    external agent recommendations.
    """
    try:
        logger.info(f"Construindo consenso de {len(agent_recommendations)} recomendações")

        # Convert input to AgentRecommendation objects
        from app.services.multi_agent_coordinator import AgentRecommendation

        recommendations = []

        for rec_data in agent_recommendations:
            recommendation = AgentRecommendation(
                agent_name=rec_data.get("agent_name", "unknown"),
                question_ids=rec_data.get("question_ids", []),
                confidence_scores=rec_data.get("confidence_scores", {}),
                reasoning=rec_data.get("reasoning", ""),
                domain_expertise=rec_data.get("domain_expertise", []),
                priority=rec_data.get("priority", 5),
            )
            recommendations.append(recommendation)

        # Build consensus (requires baseline result)
        from app.models.intake import QuestionSelectionResult

        baseline_result = QuestionSelectionResult(selected_ids=[], selection_metadata={})

        consensus = await coordinator._build_consensus(baseline_result, recommendations)

        return {
            "consensus_questions": consensus.selected_questions,
            "consensus_score": consensus.consensus_score,
            "agent_votes": consensus.agent_votes,
            "confidence_matrix": consensus.confidence_matrix,
            "final_reasoning": consensus.final_reasoning,
            "total_questions": len(consensus.selected_questions),
        }

    except Exception as e:
        logger.error(f"Erro ao construir consenso: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=Dict[str, Any])
async def multi_agent_health_check(
    coordinator: MultiAgentCoordinator = Depends(get_multi_agent_coordinator),
) -> Dict[str, Any]:
    """
    Check health status of multi-agent system.
    """
    try:
        # In a real implementation, this would ping all agent endpoints
        health_status = {
            "status": "healthy",
            "service": "multi-agent-coordination",
            "version": "1.0.0",
            "agents": {},
            "orchestrator": {"status": "healthy", "endpoint": coordinator.orchestrator_endpoint},
        }

        # Check each agent endpoint (simulated for now)
        for agent_name, endpoint in coordinator.agent_endpoints.items():
            health_status["agents"][agent_name] = {
                "status": "healthy",  # Would be actual health check result
                "endpoint": endpoint,
                "last_check": "2025-01-06T10:30:00Z",
            }

        return health_status

    except Exception as e:
        logger.error(f"Erro no health check multi-agent: {str(e)}")
        return {"status": "unhealthy", "service": "multi-agent-coordination", "error": str(e)}


@router.get("/metrics", response_model=Dict[str, Any])
async def get_multi_agent_metrics(
    coordinator: MultiAgentCoordinator = Depends(get_multi_agent_coordinator),
) -> Dict[str, Any]:
    """
    Get performance metrics for the multi-agent system.
    """
    try:
        # In a real implementation, this would gather actual metrics
        metrics = {
            "system_metrics": {
                "total_agents": len(coordinator.agent_endpoints),
                "active_agents": len(coordinator.agent_endpoints),  # Simulated
                "avg_consensus_score": 0.85,  # Simulated
                "avg_response_time_ms": 250,  # Simulated
                "total_requests": 1000,  # Simulated
                "successful_requests": 950,  # Simulated
                "error_rate": 0.05,  # Simulated
            },
            "agent_metrics": {},
            "orchestrator_metrics": {
                "consensus_success_rate": 0.92,
                "avg_agents_per_request": 2.8,
                "timeout_rate": 0.02,
            },
        }

        # Simulated per-agent metrics
        for agent_name in coordinator.agent_endpoints.keys():
            metrics["agent_metrics"][agent_name] = {
                "requests_handled": 200,  # Simulated
                "avg_response_time_ms": 180,  # Simulated
                "success_rate": 0.95,  # Simulated
                "avg_confidence_score": 0.82,  # Simulated
                "questions_recommended": 50,  # Simulated
            }

        return metrics

    except Exception as e:
        logger.error(f"Erro ao obter métricas multi-agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper methods for MultiAgentCoordinator
def _extend_coordinator_methods():
    """Add helper methods to MultiAgentCoordinator."""

    def _get_agent_expertise(self, agent_name: str) -> List[str]:
        """Get expertise areas for an agent."""
        expertise_map = {
            "business_analyst": ["business_requirements", "stakeholder_analysis", "roi_analysis"],
            "technical_architect": [
                "system_architecture",
                "tech_stack_selection",
                "scalability_design",
            ],
            "compliance_expert": [
                "regulatory_compliance",
                "data_protection",
                "security_requirements",
            ],
            "industry_expert": ["sector_requirements", "industry_standards", "market_analysis"],
            "performance_engineer": [
                "performance_requirements",
                "scalability_analysis",
                "monitoring_design",
            ],
        }
        return expertise_map.get(agent_name, [])

    def _get_agent_stages(self, agent_name: str) -> List[str]:
        """Get question stages for an agent."""
        stages_map = {
            "business_analyst": ["business"],
            "technical_architect": ["technical", "functional"],
            "compliance_expert": ["business", "nfr"],
            "industry_expert": ["business", "functional"],
            "performance_engineer": ["nfr", "technical"],
        }
        return stages_map.get(agent_name, [])

    # Add methods to MultiAgentCoordinator class
    MultiAgentCoordinator._get_agent_expertise = _get_agent_expertise
    MultiAgentCoordinator._get_agent_stages = _get_agent_stages


# Execute the extension
_extend_coordinator_methods()
