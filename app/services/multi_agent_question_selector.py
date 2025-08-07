"""
Multi-Agent Question Selector for Intelligent Intake System.
Implements collaborative question selection using specialized agents.
"""

import asyncio
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.models.intake import Question
from app.services.advanced_scoring_engine import (
    QuestionScore,
    ScoringContext,
)
from app.services.context_manager import ContextManager
from app.services.validation_engine_v2 import ValidationEngineV2
from app.services.context_inference_engine import ContextInferenceEngine, InferenceResult
from app.services.smart_question_filter import SmartQuestionFilter
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


@dataclass
class AgentVote:
    """Voto de um agent para seleção de perguntas."""

    agent_id: str
    question_id: str
    score: float
    confidence: float
    reasoning: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentConsensus:
    """Consenso entre agents para uma pergunta."""

    question_id: str
    votes: List[AgentVote] = field(default_factory=list)
    avg_score: float = 0.0
    confidence: float = 0.0
    consensus_reached: bool = False
    disagreement_level: float = 0.0
    final_score: float = 0.0


@dataclass
class SelectionResult:
    """Resultado da seleção multi-agent."""

    selected_questions: List[str]
    consensus_data: Dict[str, AgentConsensus] = field(default_factory=dict)
    agent_participation: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    selection_metadata: Dict[str, Any] = field(default_factory=dict)
    validation_result: Optional[Any] = None
    execution_time: float = 0.0


class SpecializedAgent:
    """Representa um agent especializado para seleção de perguntas."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        expertise_domains: List[str],
        question_stages: List[str],
        weight: float = 1.0,
    ):
        """
        Inicializa agent especializado.

        Args:
            agent_id: Identificador único do agent
            name: Nome do agent
            expertise_domains: Domínios de especialidade
            question_stages: Estágios de perguntas que o agent analisa
            weight: Peso do agent no consenso (0.0-1.0)
        """
        self.agent_id = agent_id
        self.name = name
        self.expertise_domains = expertise_domains
        self.question_stages = question_stages
        self.weight = weight

        # Estatísticas do agent
        self.stats = {
            "total_consultations": 0,
            "avg_confidence": 0.0,
            "consensus_rate": 0.0,
            "questions_recommended": 0,
        }

    async def analyze_question(self, question: Question, context: ScoringContext) -> AgentVote:
        """
        Analisa uma pergunta específica baseada na especialidade do agent.

        Args:
            question: Pergunta a ser analisada
            context: Contexto de pontuação

        Returns:
            AgentVote com pontuação e reasoning
        """
        try:
            # Calcular pontuação baseada na especialidade
            score = await self._calculate_specialized_score(question, context)

            # Calcular confiança baseada na expertise
            confidence = self._calculate_confidence(question, context)

            # Gerar reasoning
            reasoning = self._generate_reasoning(question, context, score)

            # Atualizar estatísticas
            self.stats["total_consultations"] += 1

            vote = AgentVote(
                agent_id=self.agent_id,
                question_id=question.id,
                score=score,
                confidence=confidence,
                reasoning=reasoning,
                metadata={
                    "agent_name": self.name,
                    "expertise_match": self._calculate_expertise_match(question),
                    "stage_relevance": question.stage in self.question_stages,
                },
            )

            return vote

        except Exception as e:
            logger.error(f"Error in agent {self.agent_id} analysis: {str(e)}")
            return AgentVote(
                agent_id=self.agent_id,
                question_id=question.id,
                score=0.0,
                confidence=0.0,
                reasoning=[f"Erro na análise: {str(e)}"],
            )

    async def _calculate_specialized_score(
        self, question: Question, context: ScoringContext
    ) -> float:
        """Calcula pontuação especializada baseada no tipo de agent."""
        base_score = 0.5  # Score base

        # Implementação específica por tipo de agent
        if self.agent_id == "business_analyst":
            return await self._score_business_relevance(question, context)
        elif self.agent_id == "technical_architect":
            return await self._score_technical_importance(question, context)
        elif self.agent_id == "compliance_expert":
            return await self._score_compliance_relevance(question, context)
        elif self.agent_id == "industry_expert":
            return await self._score_industry_specificity(question, context)
        elif self.agent_id == "performance_engineer":
            return await self._score_performance_impact(question, context)
        else:
            # Agent genérico
            return base_score

    async def _score_business_relevance(self, question: Question, context: ScoringContext) -> float:
        """Pontuação do Business Analyst."""
        score = 0.0

        # Relevância para estágio de negócio
        if question.stage == "business":
            score += 0.4

        # Keywords de negócio
        business_keywords = [
            "objetivo",
            "roi",
            "receita",
            "custo",
            "eficiência",
            "stakeholder",
            "métrica",
            "kpi",
            "orçamento",
            "cronograma",
        ]

        question_text = question.text.lower()
        for keyword in business_keywords:
            if keyword in question_text:
                score += 0.1

        # Relevância para contexto
        if context.classified_tags:
            business_tags = ["business-objective", "strategic", "stakeholders", "budget"]
            matching_tags = set(question.tags or []).intersection(set(business_tags))
            score += len(matching_tags) * 0.15

        # Criticidade da pergunta
        if getattr(question, "required", False):
            score += 0.2

        return min(1.0, score)

    async def _score_technical_importance(
        self, question: Question, context: ScoringContext
    ) -> float:
        """Pontuação do Technical Architect."""
        score = 0.0

        # Relevância para estágios técnicos
        if question.stage in ["technical", "functional"]:
            score += 0.4

        # Keywords técnicos
        technical_keywords = [
            "arquitetura",
            "tecnologia",
            "api",
            "database",
            "integração",
            "infraestrutura",
            "deployment",
            "escalabilidade",
            "plataforma",
        ]

        question_text = question.text.lower()
        for keyword in technical_keywords:
            if keyword in question_text:
                score += 0.12

        # Complexidade técnica do projeto
        if context.project_complexity == "high":
            score *= 1.3
        elif context.project_complexity == "low":
            score *= 0.8

        # Tags técnicos
        if question.tags:
            technical_tags = ["architecture", "technical", "integration", "platform"]
            matching_tags = set(question.tags).intersection(set(technical_tags))
            score += len(matching_tags) * 0.2

        return min(1.0, score)

    async def _score_compliance_relevance(
        self, question: Question, context: ScoringContext
    ) -> float:
        """Pontuação do Compliance Expert."""
        score = 0.0

        # Keywords de compliance
        compliance_keywords = [
            "lgpd",
            "gdpr",
            "hipaa",
            "sox",
            "pci",
            "segurança",
            "privacidade",
            "auditoria",
            "conformidade",
            "regulamentação",
        ]

        question_text = question.text.lower()
        for keyword in compliance_keywords:
            if keyword in question_text:
                score += 0.25

        # Contexto de compliance
        if context.compliance_requirements:
            score += 0.3

        # Setor regulamentado
        regulated_industries = ["healthcare", "finance", "government"]
        if context.detected_industry in regulated_industries:
            score += 0.2

        # Tags de compliance
        if question.tags:
            compliance_tags = ["compliance", "security", "regulatory", "audit"]
            matching_tags = set(question.tags).intersection(set(compliance_tags))
            score += len(matching_tags) * 0.3

        return min(1.0, score)

    async def _score_industry_specificity(
        self, question: Question, context: ScoringContext
    ) -> float:
        """Pontuação do Industry Expert."""
        score = 0.0

        if not context.detected_industry:
            return 0.1  # Score baixo se não há indústria detectada

        # Mapeamento de keywords por indústria
        industry_keywords = {
            "healthcare": ["saúde", "paciente", "médico", "clínica", "hospital", "prontuário"],
            "finance": ["financeiro", "pagamento", "transação", "banco", "crédito", "investimento"],
            "ecommerce": ["produto", "carrinho", "checkout", "pedido", "estoque", "catálogo"],
            "education": ["aluno", "curso", "aula", "escola", "universidade", "ensino"],
            "government": ["público", "cidadão", "processo", "órgão", "lei", "regulamento"],
        }

        keywords = industry_keywords.get(context.detected_industry, [])
        question_text = question.text.lower()

        for keyword in keywords:
            if keyword in question_text:
                score += 0.3

        # Bonus para indústrias específicas
        if question.tags:
            if f"industry-{context.detected_industry}" in question.tags:
                score += 0.4

        return min(1.0, score)

    async def _score_performance_impact(self, question: Question, context: ScoringContext) -> float:
        """Pontuação do Performance Engineer."""
        score = 0.0

        # Relevância para NFRs
        if question.stage == "nfr":
            score += 0.5

        # Keywords de performance
        performance_keywords = [
            "performance",
            "latência",
            "throughput",
            "escalabilidade",
            "disponibilidade",
            "monitoramento",
            "cache",
            "otimização",
            "carga",
            "concorrência",
        ]

        question_text = question.text.lower()
        for keyword in performance_keywords:
            if keyword in question_text:
                score += 0.2

        # Volume de usuários alto
        if context.user_count_estimate and context.user_count_estimate > 10000:
            score *= 1.4

        # Tags de performance
        if question.tags:
            performance_tags = ["performance", "scalability", "availability", "monitoring"]
            matching_tags = set(question.tags).intersection(set(performance_tags))
            score += len(matching_tags) * 0.25

        return min(1.0, score)

    def _calculate_confidence(self, question: Question, context: ScoringContext) -> float:
        """Calcula confiança do agent na análise."""
        confidence = 0.5  # Base confidence

        # Expertise match
        expertise_match = self._calculate_expertise_match(question)
        confidence += expertise_match * 0.3

        # Stage relevance
        if question.stage in self.question_stages:
            confidence += 0.2

        # Informações disponíveis no contexto
        if context.classified_tags:
            confidence += 0.1
        if context.detected_industry:
            confidence += 0.1
        if context.compliance_requirements:
            confidence += 0.1

        return min(1.0, confidence)

    def _calculate_expertise_match(self, question: Question) -> float:
        """Calcula match entre expertise do agent e pergunta."""
        if not question.tags:
            return 0.3  # Match baixo sem tags

        # Verificar sobreposição entre domains e tags
        question_domains = set(question.tags)
        agent_domains = set(self.expertise_domains)

        intersection = question_domains.intersection(agent_domains)
        union = question_domains.union(agent_domains)

        if not union:
            return 0.3

        # Jaccard similarity
        return len(intersection) / len(union)

    def _generate_reasoning(
        self, question: Question, context: ScoringContext, score: float
    ) -> List[str]:
        """Gera reasoning para a pontuação."""
        reasoning = []

        # Reasoning baseado no score
        if score > 0.8:
            reasoning.append(f"Pergunta altamente relevante para {self.name}")
        elif score > 0.6:
            reasoning.append(f"Pergunta moderadamente relevante para {self.name}")
        elif score > 0.3:
            reasoning.append(f"Pergunta com baixa relevância para {self.name}")
        else:
            reasoning.append(f"Pergunta não relevante para {self.name}")

        # Reasoning específico por agent
        if self.agent_id == "business_analyst":
            if question.stage == "business":
                reasoning.append("Pergunta no estágio de negócio - especialidade principal")
            if getattr(question, "required", False):
                reasoning.append("Pergunta obrigatória - crítica para objetivos de negócio")

        elif self.agent_id == "technical_architect":
            if question.stage in ["technical", "functional"]:
                reasoning.append("Pergunta em estágio técnico - área de especialização")
            if context.project_complexity == "high":
                reasoning.append("Projeto complexo - pergunta mais relevante")

        elif self.agent_id == "compliance_expert":
            if context.compliance_requirements:
                reasoning.append("Requisitos de compliance detectados - pergunta relevante")
            if context.detected_industry in ["healthcare", "finance"]:
                reasoning.append(f"Setor {context.detected_industry} - compliance crítico")

        return reasoning


class MultiAgentQuestionSelector:
    """
    Seletor de perguntas baseado em consenso multi-agent V2.0.

    Orquestra múltiplos agents especializados para seleção colaborativa
    de perguntas mais relevantes para cada contexto específico.

    V2.0 Features:
    - Context Inference Engine para análise semântica
    - Smart Question Filter para eliminar redundâncias
    - Context-aware agent scoring
    """

    def __init__(
        self,
        catalog_path: str = "app/data/question_catalog_v2.yaml",
        context_manager: Optional[ContextManager] = None,
        validation_engine: Optional[ValidationEngineV2] = None,
        context_inference_engine: Optional[ContextInferenceEngine] = None,
        smart_question_filter: Optional[SmartQuestionFilter] = None,
        consensus_threshold: float = 0.7,
        max_questions: int = 15,
    ):
        """
        Inicializa o seletor multi-agent V2.0.

        Args:
            catalog_path: Caminho para catálogo de perguntas
            context_manager: Gerenciador de contexto
            validation_engine: Motor de validação
            context_inference_engine: Motor de inferência de contexto
            smart_question_filter: Filtro inteligente de perguntas
            consensus_threshold: Threshold para consenso (0.0-1.0)
            max_questions: Número máximo de perguntas selecionadas
        """
        self.catalog_path = catalog_path
        self.context_manager = context_manager
        self.validation_engine = validation_engine
        self.context_inference_engine = context_inference_engine
        self.smart_question_filter = smart_question_filter
        self.consensus_threshold = consensus_threshold
        self.max_questions = max_questions

        # Carregar catálogo
        self.catalog: List[Question] = []
        self._load_catalog()

        # Inicializar agents especializados
        self.agents = self._initialize_agents()

        # Thread pool para processamento paralelo
        self.executor = ThreadPoolExecutor(max_workers=len(self.agents))

        # Estatísticas
        self.selection_stats = {
            "total_selections": 0,
            "consensus_rate": 0.0,
            "avg_agent_participation": 0.0,
            "validation_pass_rate": 0.0,
        }

        # Versão do sistema
        self.version = "2.0"

        logger.info(
            f"Multi-Agent Question Selector V{self.version} initialized with {len(self.agents)} agents"
        )
        logger.info(f"Context inference: {'enabled' if context_inference_engine else 'disabled'}")
        logger.info(f"Smart filtering: {'enabled' if smart_question_filter else 'disabled'}")

    def _load_catalog(self):
        """Carrega catálogo de perguntas."""
        try:
            import yaml

            with open(self.catalog_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            for q_data in data.get("catalog", []):
                question = Question(**q_data)
                self.catalog.append(question)

            logger.info(f"Loaded catalog with {len(self.catalog)} questions")

        except Exception as e:
            logger.error(f"Error loading catalog: {str(e)}")
            raise

    def _initialize_agents(self) -> List[SpecializedAgent]:
        """Inicializa agents especializados."""
        agents = [
            SpecializedAgent(
                agent_id="business_analyst",
                name="Business Analyst",
                expertise_domains=[
                    "business-objective",
                    "strategic",
                    "stakeholders",
                    "budget",
                    "planning",
                    "roi",
                    "metrics",
                ],
                question_stages=["business"],
                weight=1.0,
            ),
            SpecializedAgent(
                agent_id="technical_architect",
                name="Technical Architect",
                expertise_domains=[
                    "architecture",
                    "technical",
                    "integration",
                    "platform",
                    "scalability",
                    "infrastructure",
                    "deployment",
                ],
                question_stages=["technical", "functional"],
                weight=1.0,
            ),
            SpecializedAgent(
                agent_id="compliance_expert",
                name="Compliance Expert",
                expertise_domains=[
                    "compliance",
                    "security",
                    "regulatory",
                    "audit",
                    "privacy",
                    "data-protection",
                ],
                question_stages=["business", "nfr"],
                weight=0.9,
            ),
            SpecializedAgent(
                agent_id="industry_expert",
                name="Industry Expert",
                expertise_domains=["industry", "domain", "sector-specific", "vertical", "market"],
                question_stages=["business", "functional"],
                weight=0.8,
            ),
            SpecializedAgent(
                agent_id="performance_engineer",
                name="Performance Engineer",
                expertise_domains=[
                    "performance",
                    "scalability",
                    "availability",
                    "monitoring",
                    "optimization",
                    "capacity",
                ],
                question_stages=["nfr", "technical"],
                weight=0.9,
            ),
        ]

        return agents

    async def select_questions(
        self, intake_text: str, context: ScoringContext, session_id: Optional[str] = None
    ) -> SelectionResult:
        """
        Seleciona perguntas usando consenso multi-agent com context awareness V2.0.

        Args:
            intake_text: Texto de intake do cliente
            context: Contexto de pontuação
            session_id: ID da sessão (para context manager)

        Returns:
            SelectionResult com perguntas selecionadas e metadata
        """
        start_time = datetime.utcnow()

        try:
            logger.info("Starting multi-agent question selection V2.0")

            # 1. Análise de contexto com Context Inference Engine
            inference_result = None
            enhanced_context = context

            if self.context_inference_engine:
                logger.info("Running context inference analysis")
                inference_result = await self.context_inference_engine.analyze_context(intake_text)
                enhanced_context = self._enhance_context_with_inference(context, inference_result)

            # 2. Consultar todos os agents em paralelo com contexto enriquecido
            agent_votes = await self._consult_agents(enhanced_context, inference_result)

            # 3. Construir consenso
            consensus_data = await self._build_consensus(agent_votes)

            # 4. Selecionar perguntas baseado no consenso
            pre_filtered_questions = self._select_questions_from_consensus(
                consensus_data, enhanced_context
            )

            # 5. Aplicar filtro inteligente para remover redundâncias
            selected_questions = pre_filtered_questions
            filter_decisions = []

            if self.smart_question_filter and inference_result:
                logger.info("Applying smart question filtering")
                candidate_questions = [q for q in self.catalog if q.id in pre_filtered_questions]

                filtered_questions, filter_decisions = self.smart_question_filter.filter_questions(
                    candidate_questions, intake_text, inference_result
                )

                selected_questions = [q.id for q in filtered_questions]

                logger.info(
                    f"Smart filter removed {len(pre_filtered_questions) - len(selected_questions)} redundant questions"
                )

            # 6. Validar seleção
            validation_result = None
            if self.validation_engine:
                all_scores = [
                    self._consensus_to_question_score(consensus)
                    for consensus in consensus_data.values()
                ]
                validation_result = await self.validation_engine.validate_question_selection(
                    selected_questions, all_scores, context
                )

            # 7. Salvar contexto dos agents
            if self.context_manager and session_id:
                await self._save_agent_contexts(session_id, agent_votes, consensus_data)

            # 8. Preparar resultado
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            result = SelectionResult(
                selected_questions=selected_questions,
                consensus_data=consensus_data,
                agent_participation=self._calculate_agent_participation(agent_votes),
                selection_metadata={
                    "version": self.version,
                    "consensus_threshold": self.consensus_threshold,
                    "total_questions_evaluated": len(self.catalog),
                    "consensus_reached_count": len(
                        [c for c in consensus_data.values() if c.consensus_reached]
                    ),
                    "avg_consensus_confidence": np.mean(
                        [c.confidence for c in consensus_data.values()]
                    )
                    if consensus_data
                    else 0.0,
                    "context_inference_used": inference_result is not None,
                    "smart_filtering_used": bool(filter_decisions),
                    "questions_filtered_count": len(filter_decisions) if filter_decisions else 0,
                    "inference_summary": inference_result.reasoning_summary
                    if inference_result
                    else None,
                    "detected_domain": inference_result.detected_domain
                    if inference_result
                    else None,
                    "filter_explanation": (
                        self.smart_question_filter.get_filter_explanation(filter_decisions)
                        if self.smart_question_filter and filter_decisions
                        else None
                    ),
                },
                validation_result=validation_result,
                execution_time=execution_time,
            )

            # 9. Atualizar estatísticas
            self._update_selection_stats(result)

            logger.info(f"Multi-agent selection V{self.version} completed in {execution_time:.2f}s")
            logger.info(
                f"Selected {len(selected_questions)} questions with {len(consensus_data)} consensus items"
            )
            if inference_result:
                logger.info(
                    f"Context analysis - Domain: {inference_result.detected_domain}, Obvious answers: {len(inference_result.obvious_answers)}"
                )
            if filter_decisions:
                logger.info(
                    f"Smart filtering removed {len([d for d in filter_decisions if d.should_exclude])} redundant questions"
                )

            return result

        except Exception as e:
            logger.error(f"Error in multi-agent selection: {str(e)}")
            # Fallback para seleção básica
            return await self._fallback_selection(intake_text, context)

    def _enhance_context_with_inference(
        self, context: ScoringContext, inference_result: InferenceResult
    ) -> ScoringContext:
        """
        Enriquece contexto de pontuação com resultados da análise de inferência.
        """
        try:
            # Criar novo contexto baseado no existente
            enhanced_context = ScoringContext(
                intake_text=context.intake_text,
                classified_tags=context.classified_tags or [],
                detected_industry=inference_result.detected_domain or context.detected_industry,
                compliance_requirements=context.compliance_requirements or [],
                project_complexity=context.project_complexity,
                budget_range=context.budget_range,
                timeline_constraint=context.timeline_constraint,
                user_count_estimate=context.user_count_estimate,
                existing_systems=context.existing_systems or [],
            )

            # Enriquecer com informações inferidas
            if inference_result.detected_domain:
                enhanced_context.detected_industry = inference_result.detected_domain

            # Adicionar tags inferidas
            inferred_tags = [info.key for info in inference_result.inferred_info]
            enhanced_context.classified_tags.extend(inferred_tags)

            # Definir complexidade se não foi especificada
            if (
                not enhanced_context.project_complexity
                or enhanced_context.project_complexity == "medium"
            ):
                context_enhancement = self.context_inference_engine.get_context_enhancement(
                    inference_result
                )
                enhanced_context.project_complexity = context_enhancement.get(
                    "project_complexity", "medium"
                )

            return enhanced_context

        except Exception as e:
            logger.error(f"Error enhancing context: {str(e)}")
            return context

    async def _consult_agents(
        self, context: ScoringContext, inference_result: Optional[InferenceResult] = None
    ) -> Dict[str, List[AgentVote]]:
        """Consulta todos os agents em paralelo."""
        agent_votes = {}

        # Criar tasks para consulta paralela
        tasks = []
        for agent in self.agents:
            task = asyncio.create_task(self._consult_single_agent(agent, context, inference_result))
            tasks.append((agent.agent_id, task))

        # Aguardar todas as consultas
        for agent_id, task in tasks:
            try:
                votes = await task
                agent_votes[agent_id] = votes
            except Exception as e:
                logger.error(f"Error consulting agent {agent_id}: {str(e)}")
                agent_votes[agent_id] = []

        return agent_votes

    async def _consult_single_agent(
        self,
        agent: SpecializedAgent,
        context: ScoringContext,
        inference_result: Optional[InferenceResult] = None,
    ) -> List[AgentVote]:
        """Consulta um agent específico sobre todas as perguntas."""
        votes = []

        # Filtrar perguntas relevantes para o agent
        relevant_questions = [
            q
            for q in self.catalog
            if q.stage in agent.question_stages
            or (q.tags and any(tag in agent.expertise_domains for tag in q.tags))
        ]

        # Se temos inferência de contexto, filtrar perguntas redundantes imediatamente
        if inference_result and self.context_inference_engine:
            filtered_relevant = [
                q
                for q in relevant_questions
                if not self.context_inference_engine.get_exclusion_rules_for_question(
                    q.id, inference_result
                )
            ]

            if len(filtered_relevant) < len(relevant_questions):
                logger.debug(
                    f"Agent {agent.agent_id}: Context inference filtered out {len(relevant_questions) - len(filtered_relevant)} redundant questions"
                )
                relevant_questions = filtered_relevant

        # Se não há perguntas específicas, analisar todas (com peso menor)
        if not relevant_questions:
            relevant_questions = self.catalog

        # Analisar cada pergunta
        for question in relevant_questions:
            try:
                vote = await agent.analyze_question(question, context)
                votes.append(vote)
            except Exception as e:
                logger.error(
                    f"Error in agent {agent.agent_id} analyzing question {question.id}: {str(e)}"
                )

        logger.info(f"Agent {agent.agent_id} analyzed {len(votes)} questions (context-aware)")
        return votes

    async def _build_consensus(
        self, agent_votes: Dict[str, List[AgentVote]]
    ) -> Dict[str, AgentConsensus]:
        """Constrói consenso entre agents para cada pergunta."""
        consensus_data = {}

        # Agrupar votos por pergunta
        question_votes = {}
        for agent_id, votes in agent_votes.items():
            for vote in votes:
                if vote.question_id not in question_votes:
                    question_votes[vote.question_id] = []
                question_votes[vote.question_id].append(vote)

        # Calcular consenso para cada pergunta
        for question_id, votes in question_votes.items():
            consensus = self._calculate_consensus(question_id, votes)
            consensus_data[question_id] = consensus

        return consensus_data

    def _calculate_consensus(self, question_id: str, votes: List[AgentVote]) -> AgentConsensus:
        """Calcula consenso para uma pergunta específica."""
        if not votes:
            return AgentConsensus(question_id=question_id)

        # Estatísticas básicas
        scores = [vote.score for vote in votes]
        confidences = [vote.confidence for vote in votes]

        avg_score = np.mean(scores)
        avg_confidence = np.mean(confidences)

        # Calcular dispersão (disagreement)
        score_std = np.std(scores) if len(scores) > 1 else 0.0
        disagreement_level = score_std

        # Determinar se consenso foi alcançado
        consensus_reached = disagreement_level < (1.0 - self.consensus_threshold)

        # Score final ponderado por peso dos agents
        weighted_score = 0.0
        total_weight = 0.0

        for vote in votes:
            agent = next((a for a in self.agents if a.agent_id == vote.agent_id), None)
            weight = agent.weight if agent else 1.0

            weighted_score += vote.score * weight * vote.confidence
            total_weight += weight * vote.confidence

        final_score = weighted_score / total_weight if total_weight > 0 else avg_score

        return AgentConsensus(
            question_id=question_id,
            votes=votes,
            avg_score=avg_score,
            confidence=avg_confidence,
            consensus_reached=consensus_reached,
            disagreement_level=disagreement_level,
            final_score=final_score,
        )

    def _select_questions_from_consensus(
        self, consensus_data: Dict[str, AgentConsensus], context: ScoringContext
    ) -> List[str]:
        """Seleciona perguntas baseado nos dados de consenso."""
        # Ordenar por score final
        sorted_consensus = sorted(
            consensus_data.values(), key=lambda x: x.final_score, reverse=True
        )

        selected_questions = []
        stage_counts = {}

        # Selecionar perguntas garantindo diversidade
        for consensus in sorted_consensus:
            if len(selected_questions) >= self.max_questions:
                break

            question = next((q for q in self.catalog if q.id == consensus.question_id), None)
            if not question:
                continue

            # Verificar se pergunta atende critérios
            if not self._should_select_question(question, context, stage_counts):
                continue

            # Adicionar à seleção
            selected_questions.append(consensus.question_id)

            # Atualizar contadores de estágio
            stage = question.stage
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

        # Garantir perguntas obrigatórias
        selected_questions = self._ensure_required_questions(selected_questions)

        return selected_questions[: self.max_questions]

    def _should_select_question(
        self, question: Question, context: ScoringContext, stage_counts: Dict[str, int]
    ) -> bool:
        """Determina se pergunta deve ser selecionada."""
        # Sempre selecionar perguntas obrigatórias
        if getattr(question, "required", False):
            return True

        # Limitar perguntas por estágio para diversidade
        stage = question.stage
        max_per_stage = max(2, self.max_questions // 4)  # Distribuir entre estágios

        if stage_counts.get(stage, 0) >= max_per_stage:
            return False

        # Verificar condições da pergunta (se aplicável)
        if hasattr(question, "condition") and question.condition:
            # Por ora, não temos respostas anteriores, então incluir
            pass

        return True

    def _ensure_required_questions(self, selected_questions: List[str]) -> List[str]:
        """Garante que perguntas obrigatórias estão incluídas."""
        required_questions = [q.id for q in self.catalog if getattr(q, "required", False)]

        missing_required = set(required_questions) - set(selected_questions)

        # Adicionar perguntas obrigatórias faltantes
        for q_id in missing_required:
            if len(selected_questions) < self.max_questions:
                selected_questions.append(q_id)
            else:
                # Substituir pergunta de menor prioridade
                # (implementação simplificada)
                selected_questions[-1] = q_id

        return selected_questions

    def _consensus_to_question_score(self, consensus: AgentConsensus) -> "QuestionScore":
        """Converte consenso para QuestionScore (para validação)."""
        from app.services.advanced_scoring_engine import QuestionScore

        agent_votes_dict = {vote.agent_id: vote.score for vote in consensus.votes}

        return QuestionScore(
            question_id=consensus.question_id,
            total_score=consensus.final_score,
            agent_votes=agent_votes_dict,
            confidence=consensus.confidence,
            reasoning=[
                f"Consenso multi-agent: {consensus.consensus_reached}",
                f"Score médio: {consensus.avg_score:.2f}",
                f"Nível de discordância: {consensus.disagreement_level:.2f}",
            ],
        )

    async def _save_agent_contexts(
        self,
        session_id: str,
        agent_votes: Dict[str, List[AgentVote]],
        consensus_data: Dict[str, AgentConsensus],
    ):
        """Salva contextos dos agents."""
        if not self.context_manager:
            return

        for agent_id, votes in agent_votes.items():
            # Preparar dados do agent
            recommendations = [vote.question_id for vote in votes if vote.score > 0.6]

            confidence_scores = {vote.question_id: vote.score for vote in votes}

            reasoning = []
            for vote in votes[:5]:  # Top 5 reasoning
                reasoning.extend(vote.reasoning)

            # Salvar contexto
            await self.context_manager.add_agent_context(
                session_id=session_id,
                agent_id=agent_id,
                recommendations=recommendations,
                confidence_scores=confidence_scores,
                reasoning=reasoning,
                metadata={
                    "total_votes": len(votes),
                    "avg_score": np.mean([v.score for v in votes]),
                    "avg_confidence": np.mean([v.confidence for v in votes]),
                },
            )

    def _calculate_agent_participation(
        self, agent_votes: Dict[str, List[AgentVote]]
    ) -> Dict[str, Dict[str, Any]]:
        """Calcula métricas de participação dos agents."""
        participation = {}

        for agent_id, votes in agent_votes.items():
            if not votes:
                participation[agent_id] = {
                    "votes_count": 0,
                    "avg_score": 0.0,
                    "avg_confidence": 0.0,
                    "participation_rate": 0.0,
                }
                continue

            scores = [vote.score for vote in votes]
            confidences = [vote.confidence for vote in votes]

            participation[agent_id] = {
                "votes_count": len(votes),
                "avg_score": np.mean(scores),
                "avg_confidence": np.mean(confidences),
                "high_confidence_votes": len([c for c in confidences if c > 0.8]),
                "participation_rate": len(votes) / len(self.catalog),
            }

        return participation

    def _update_selection_stats(self, result: SelectionResult):
        """Atualiza estatísticas de seleção."""
        self.selection_stats["total_selections"] += 1

        # Taxa de consenso
        if result.consensus_data:
            consensus_count = len(
                [c for c in result.consensus_data.values() if c.consensus_reached]
            )
            current_consensus_rate = consensus_count / len(result.consensus_data)
        else:
            current_consensus_rate = 0.0

        # Média móvel
        total = self.selection_stats["total_selections"]
        prev_rate = self.selection_stats["consensus_rate"]
        self.selection_stats["consensus_rate"] = (
            prev_rate * (total - 1) + current_consensus_rate
        ) / total

        # Taxa de participação dos agents
        if result.agent_participation:
            avg_participation = np.mean(
                [p["participation_rate"] for p in result.agent_participation.values()]
            )

            prev_participation = self.selection_stats["avg_agent_participation"]
            self.selection_stats["avg_agent_participation"] = (
                prev_participation * (total - 1) + avg_participation
            ) / total

        # Taxa de aprovação na validação
        if result.validation_result:
            validation_passed = result.validation_result.is_valid
            prev_pass_rate = self.selection_stats["validation_pass_rate"]
            self.selection_stats["validation_pass_rate"] = (
                prev_pass_rate * (total - 1) + (1.0 if validation_passed else 0.0)
            ) / total

    async def _fallback_selection(
        self, intake_text: str, context: ScoringContext
    ) -> SelectionResult:
        """Seleção de fallback em caso de erro."""
        logger.warning("Using fallback question selection")

        # Seleção básica - primeiras perguntas de cada estágio
        stages = ["business", "functional", "technical", "nfr"]
        selected_questions = []

        for stage in stages:
            stage_questions = [q for q in self.catalog if q.stage == stage]
            if stage_questions:
                # Pegar as primeiras perguntas do estágio
                selected_questions.extend([q.id for q in stage_questions[:3]])

        return SelectionResult(
            selected_questions=selected_questions[: self.max_questions],
            selection_metadata={"fallback": True},
        )

    def get_agent_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas dos agents."""
        stats = {}

        for agent in self.agents:
            stats[agent.agent_id] = {
                "name": agent.name,
                "expertise_domains": agent.expertise_domains,
                "question_stages": agent.question_stages,
                "weight": agent.weight,
                "stats": agent.stats.copy(),
            }

        return stats

    def get_selection_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de seleção."""
        return {
            **self.selection_stats,
            "version": self.version,
            "total_agents": len(self.agents),
            "catalog_size": len(self.catalog),
            "consensus_threshold": self.consensus_threshold,
            "max_questions": self.max_questions,
            "context_inference_enabled": self.context_inference_engine is not None,
            "smart_filtering_enabled": self.smart_question_filter is not None,
        }

    def get_question_by_id(self, question_id: str) -> Optional[Question]:
        """Retorna pergunta por ID (compatibilidade com IntakeEngine)."""
        return next((q for q in self.catalog if q.id == question_id), None)

    def get_next_questions(
        self, all_question_ids: List[str], answered_questions: Dict[str, Any], batch_size: int = 3
    ) -> List[Question]:
        """
        Retorna próximas perguntas do wizard (compatibilidade com IntakeEngine).

        Args:
            all_question_ids: Todas as perguntas selecionadas
            answered_questions: Respostas já fornecidas {question_id: value}
            batch_size: Número de perguntas para retornar

        Returns:
            Lista de próximas perguntas para mostrar
        """
        try:
            # Encontrar perguntas não respondidas
            unanswered_ids = [qid for qid in all_question_ids if qid not in answered_questions]

            # Pegar próximas perguntas até o batch_size
            next_ids = unanswered_ids[:batch_size]

            # Converter IDs para objetos Question
            next_questions = []
            for qid in next_ids:
                question = self.get_question_by_id(qid)
                if question:
                    next_questions.append(question)

            logger.debug(
                f"Returning {len(next_questions)} next questions from {len(unanswered_ids)} unanswered"
            )
            return next_questions

        except Exception as e:
            logger.error(f"Error getting next questions: {str(e)}")
            return []
