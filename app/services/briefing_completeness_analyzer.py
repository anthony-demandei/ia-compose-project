"""
Briefing Completeness Analyzer - Analisa se um briefing está completo o suficiente
para pular perguntas e ir direto para o resumo.

Usa IA para pontuar completude de 0-100% baseado em múltiplas dimensões.
"""

import json
from typing import Dict, List, Any
from dataclasses import dataclass, field
from openai import AsyncOpenAI

from app.utils.pii_safe_logging import get_pii_safe_logger
from app.utils.config import get_settings
from app.services.universal_project_classifier import UniversalCategory, UniversalProjectClassifier

logger = get_pii_safe_logger(__name__)

# Usando UniversalCategory do classificador universal
# Isso garante consistência em todo o sistema V3.0
CompletenessCategory = UniversalCategory


@dataclass
class CategoryScore:
    """Pontuação de uma categoria específica."""

    category: UniversalCategory
    score: float  # 0-100
    weight: float  # Peso da categoria no score total
    missing_items: List[str] = field(default_factory=list)
    found_items: List[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class CompletenessResult:
    """Resultado da análise de completude."""

    overall_score: float  # 0-100
    category_scores: Dict[UniversalCategory, CategoryScore]
    is_complete: bool  # True se score > threshold (90%)
    missing_critical_areas: List[str] = field(default_factory=list)
    suggested_questions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning_summary: str = ""
    should_skip_questions: bool = False

    def get_top_missing_areas(self, max_areas: int = 3) -> List[str]:
        """Retorna as principais áreas faltantes."""
        return self.missing_critical_areas[:max_areas]


class BriefingCompletenessAnalyzer:
    """
    Analisa completude de briefings usando IA e scoring multi-dimensional.

    Features:
    - Scoring 0-100% baseado em múltiplas categorias
    - Detecção de informações críticas faltantes
    - Sugestão de perguntas apenas para lacunas importantes
    - Threshold configurável para pular perguntas (default: 90%)
    """

    def __init__(self, api_key: str = None, threshold: float = 0.9):
        """
        Inicializa o analisador de completude.

        Args:
            api_key: Chave da OpenAI API (usa ENV se não fornecida)
            threshold: Score mínimo para considerar briefing completo (0-1.0)
        """
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.model = settings.openai_model
        self.threshold = threshold
        self.temperature = 0.1  # Baixa para análise consistente

        # Inicializar classificador universal para pesos adaptativos
        self.classifier = UniversalProjectClassifier(api_key=api_key)

        # Pesos padrão universais (soma = 1.0)
        self.default_weights = {
            UniversalCategory.OBJECTIVE: 0.22,  # O que faz? Para que serve?
            UniversalCategory.FUNCTIONAL: 0.20,  # Que funcionalidades específicas?
            UniversalCategory.TECHNICAL: 0.18,  # Como será feito? Tecnologias?
            UniversalCategory.SCOPE: 0.15,  # Qual escopo? O que inclui/exclui?
            UniversalCategory.CONSTRAINTS: 0.10,  # Limitações, requisitos especiais?
            UniversalCategory.RESOURCES: 0.08,  # Prazo, orçamento, equipe?
            UniversalCategory.ENVIRONMENT: 0.04,  # Onde roda? Deploy? Infra?
            UniversalCategory.SUCCESS_CRITERIA: 0.03,  # Como medir sucesso? KPIs?
        }

        # Cache de análises
        self.analysis_cache: Dict[str, CompletenessResult] = {}

        logger.info(f"BriefingCompletenessAnalyzer initialized with threshold={threshold:.0%}")

    async def analyze_completeness(
        self, briefing_text: str, project_classification=None
    ) -> CompletenessResult:
        """
        Analisa completude de um briefing.

        Args:
            briefing_text: Texto do briefing a analisar

        Returns:
            CompletenessResult com score e análise detalhada
        """
        try:
            # Check cache
            cache_key = self._generate_cache_key(briefing_text)
            if cache_key in self.analysis_cache:
                logger.info("Using cached completeness analysis")
                return self.analysis_cache[cache_key]

            logger.info("Analyzing briefing completeness with AI")

            # 1. Classificar projeto se não fornecido
            if project_classification is None:
                project_classification = await self.classifier.classify_project(briefing_text)

            # 2. Usar pesos adaptativos baseados na classificação
            adaptive_weights = project_classification.category_weights

            # 3. Análise detalhada com GPT
            analysis = await self._analyze_with_gpt(briefing_text, project_classification)

            # 4. Calcular scores por categoria
            category_scores = self._calculate_category_scores(analysis, adaptive_weights)

            # 5. Calcular score geral ponderado
            overall_score = self._calculate_overall_score(category_scores)

            # 4. Identificar áreas críticas faltantes
            missing_areas = self._identify_missing_areas(category_scores, analysis)

            # 5. Sugerir perguntas se necessário
            suggested_questions = []
            if overall_score < 100:
                suggested_questions = self._suggest_questions(missing_areas, analysis)

            # 6. Determinar se deve pular perguntas
            should_skip = overall_score >= (self.threshold * 100)

            # 7. Compilar resultado
            result = CompletenessResult(
                overall_score=overall_score,
                category_scores=category_scores,
                is_complete=should_skip,
                missing_critical_areas=missing_areas,
                suggested_questions=suggested_questions[:5],  # Max 5 perguntas
                confidence=analysis.get("confidence", 0.8),
                reasoning_summary=analysis.get("summary", ""),
                should_skip_questions=should_skip,
            )

            # Cache result
            self.analysis_cache[cache_key] = result

            logger.info(
                f"Completeness analysis: score={overall_score:.1f}%, "
                f"should_skip={should_skip}, missing_areas={len(missing_areas)}"
            )

            return result

        except Exception as e:
            logger.error(f"Error analyzing completeness: {str(e)}")
            # Return conservative result on error
            return CompletenessResult(
                overall_score=50.0,
                category_scores={},
                is_complete=False,
                should_skip_questions=False,
            )

    async def _analyze_with_gpt(
        self, briefing_text: str, project_classification=None
    ) -> Dict[str, Any]:
        """Análise detalhada usando GPT."""
        # Contexto do projeto para análise personalizada
        project_context = ""
        if project_classification:
            project_context = f"""
        CONTEXTO DO PROJETO:
        - Tipo: {project_classification.project_type.value}
        - Complexidade: {project_classification.complexity.value}
        - Domínio: {project_classification.domain_context or 'genérico'}
        """

        prompt = f"""
        Analise este briefing e avalie sua completude usando categorias UNIVERSAIS que se aplicam a qualquer projeto.
        {project_context}
        BRIEFING:
        {briefing_text}
        
        Avalie cada categoria de 0-100 baseado em quão completa está a informação:
        
        Retorne JSON no formato:
        {{
            "objective": {{
                "score": 0-100,
                "found": ["objetivos/finalidades claros mencionados"],
                "missing": ["aspectos do objetivo que precisam esclarecimento"],
                "reasoning": "explicação da pontuação"
            }},
            "functional": {{
                "score": 0-100,
                "found": ["funcionalidades/recursos descritos"],
                "missing": ["funcionalidades que precisam detalhamento"],
                "reasoning": "explicação"
            }},
            "technical": {{
                "score": 0-100,
                "found": ["especificações técnicas mencionadas"],
                "missing": ["detalhes técnicos faltantes"],
                "reasoning": "explicação"
            }},
            "scope": {{
                "score": 0-100,
                "found": ["definições de escopo fornecidas"],
                "missing": ["limites/escopo não definidos"],
                "reasoning": "explicação"
            }},
            "constraints": {{
                "score": 0-100,
                "found": ["restrições/limitações mencionadas"],
                "missing": ["constraintes não especificados"],
                "reasoning": "explicação"
            }},
            "resources": {{
                "score": 0-100,
                "found": ["recursos disponíveis (prazo/orçamento/equipe)"],
                "missing": ["recursos não definidos"],
                "reasoning": "explicação"
            }},
            "environment": {{
                "score": 0-100,
                "found": ["ambiente/deploy/infra mencionados"],
                "missing": ["detalhes de ambiente necessários"],
                "reasoning": "explicação"
            }},
            "success": {{
                "score": 0-100,
                "found": ["critérios de sucesso/KPIs definidos"],
                "missing": ["métricas de sucesso faltantes"],
                "reasoning": "explicação"
            }},
            "critical_gaps": [
                "lista das lacunas mais críticas que impedem início do desenvolvimento"
            ],
            "next_questions": [
                "perguntas específicas mais importantes para preencher lacunas"
            ],
            "confidence": 0.0-1.0,
            "summary": "resumo de 2-3 frases sobre a completude do briefing"
        }}
        
        IMPORTANTE:
        - Score 100 = informação completa, nada mais necessário
        - Score 80-99 = quase completo, apenas detalhes menores faltando
        - Score 60-79 = bom mas precisa esclarecimentos importantes
        - Score 40-59 = básico, muitas informações importantes faltando
        - Score 0-39 = muito incompleto, precisa de muitos detalhes
        
        CONTEXTO UNIVERSAL:
        - Estas categorias se aplicam a QUALQUER projeto: desde robôs scrapers simples até plataformas complexas
        - Adapte a avaliação ao tipo de projeto detectado
        - Seja rigoroso mas justo baseado na complexidade esperada
        - Um scraper simples não precisa de todos os detalhes de uma plataforma enterprise
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um expert em análise de requisitos de software. "
                        "Avalie briefings de forma precisa e objetiva.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Error in GPT analysis: {str(e)}")
            return self._get_default_analysis()

    def _calculate_category_scores(
        self, analysis: Dict[str, Any], weights: Dict[UniversalCategory, float] = None
    ) -> Dict[UniversalCategory, CategoryScore]:
        """Calcula scores por categoria baseado na análise."""
        category_scores = {}
        weights = weights or self.default_weights

        for category in UniversalCategory:
            category_key = category.value
            category_data = analysis.get(category_key, {})

            if isinstance(category_data, dict):
                score = CategoryScore(
                    category=category,
                    score=float(category_data.get("score", 50)),
                    weight=weights.get(category, 0.1),
                    found_items=category_data.get("found", []),
                    missing_items=category_data.get("missing", []),
                    reasoning=category_data.get("reasoning", ""),
                )
            else:
                # Fallback para dados mal formatados
                score = CategoryScore(
                    category=category, score=50.0, weight=weights.get(category, 0.1)
                )

            category_scores[category] = score

        return category_scores

    def _calculate_overall_score(
        self, category_scores: Dict[UniversalCategory, CategoryScore]
    ) -> float:
        """Calcula score geral ponderado."""
        total_score = 0.0
        total_weight = 0.0

        for category, score_data in category_scores.items():
            total_score += score_data.score * score_data.weight
            total_weight += score_data.weight

        if total_weight > 0:
            return total_score / total_weight
        return 50.0  # Default se não houver pesos

    def _identify_missing_areas(
        self, category_scores: Dict[UniversalCategory, CategoryScore], analysis: Dict[str, Any]
    ) -> List[str]:
        """Identifica áreas críticas faltantes."""
        missing_areas = []

        # Adicionar gaps críticos da análise
        critical_gaps = analysis.get("critical_gaps", [])
        if isinstance(critical_gaps, list):
            missing_areas.extend(critical_gaps)

        # Adicionar categorias com score baixo
        for category, score_data in category_scores.items():
            if score_data.score < 60:  # Threshold para área problemática
                # Adicionar itens faltantes mais importantes
                for item in score_data.missing_items[:2]:  # Top 2 de cada categoria
                    if item not in missing_areas:
                        missing_areas.append(item)

        return missing_areas[:10]  # Limitar a 10 áreas

    def _suggest_questions(self, missing_areas: List[str], analysis: Dict[str, Any]) -> List[str]:
        """Sugere perguntas baseadas nas áreas faltantes."""
        questions = []

        # Adicionar perguntas sugeridas pela análise
        next_questions = analysis.get("next_questions", [])
        if isinstance(next_questions, list):
            questions.extend(next_questions)

        # Gerar perguntas para áreas faltantes se necessário
        if len(questions) < 5 and missing_areas:
            for area in missing_areas:
                if len(questions) >= 5:
                    break
                # Gerar pergunta baseada na área
                question = self._generate_question_for_area(area)
                if question and question not in questions:
                    questions.append(question)

        return questions

    def _generate_question_for_area(self, area: str) -> str:
        """Gera uma pergunta para uma área específica."""
        # Mapeamento simples de áreas para perguntas
        # Em produção, isso poderia usar IA para gerar perguntas contextuais
        question_templates = {
            "prazo": "Qual é o prazo desejado para entrega do projeto?",
            "orçamento": "Qual é o orçamento disponível para este projeto?",
            "usuários": "Quantos usuários simultâneos o sistema deve suportar?",
            "tecnologia": "Há alguma preferência ou restrição de tecnologia?",
            "integração": "Quais sistemas externos precisam ser integrados?",
            "segurança": "Quais são os requisitos de segurança e compliance?",
            "deploy": "Onde o sistema será hospedado (cloud, on-premise)?",
            "manutenção": "Haverá necessidade de suporte e manutenção pós-entrega?",
        }

        # Procurar keyword match
        area_lower = area.lower()
        for key, question in question_templates.items():
            if key in area_lower:
                return question

        # Pergunta genérica se não encontrar match
        return f"Poderia fornecer mais detalhes sobre: {area}?"

    def _get_default_analysis(self) -> Dict[str, Any]:
        """Retorna análise padrão para fallback com categorias universais."""
        return {
            "objective": {
                "score": 50,
                "found": [],
                "missing": ["objetivo claro"],
                "reasoning": "Análise indisponível",
            },
            "functional": {
                "score": 50,
                "found": [],
                "missing": ["funcionalidades"],
                "reasoning": "Análise indisponível",
            },
            "technical": {
                "score": 50,
                "found": [],
                "missing": ["detalhes técnicos"],
                "reasoning": "Análise indisponível",
            },
            "scope": {
                "score": 50,
                "found": [],
                "missing": ["definição de escopo"],
                "reasoning": "Análise indisponível",
            },
            "constraints": {
                "score": 50,
                "found": [],
                "missing": ["limitações"],
                "reasoning": "Análise indisponível",
            },
            "resources": {
                "score": 50,
                "found": [],
                "missing": ["recursos disponíveis"],
                "reasoning": "Análise indisponível",
            },
            "environment": {
                "score": 50,
                "found": [],
                "missing": ["ambiente de deploy"],
                "reasoning": "Análise indisponível",
            },
            "success": {
                "score": 50,
                "found": [],
                "missing": ["critérios de sucesso"],
                "reasoning": "Análise indisponível",
            },
            "critical_gaps": ["Análise completa não disponível"],
            "next_questions": [],
            "confidence": 0.5,
            "summary": "Análise automática não disponível. Usando valores padrão universais.",
        }

    def _generate_cache_key(self, text: str) -> str:
        """Gera chave única para cache."""
        import hashlib

        return hashlib.md5(text.encode()).hexdigest()

    async def explain_analysis(self, result: CompletenessResult) -> str:
        """
        Gera explicação detalhada da análise de completude.

        Returns:
            Explicação em texto formatado
        """
        explanation = []

        explanation.append("# Análise de Completude do Briefing\n")
        explanation.append(f"**Score Geral**: {result.overall_score:.1f}%")
        explanation.append(f"**Status**: {'✅ Completo' if result.is_complete else '⚠️ Incompleto'}")
        explanation.append(
            f"**Ação**: {'Pular perguntas → Resumo' if result.should_skip_questions else 'Fazer perguntas'}\n"
        )

        explanation.append("## Scores por Categoria\n")
        for category, score_data in sorted(
            result.category_scores.items(), key=lambda x: x[1].score, reverse=True
        ):
            emoji = "✅" if score_data.score >= 80 else "⚠️" if score_data.score >= 60 else "❌"
            explanation.append(f"{emoji} **{category.value.title()}**: {score_data.score:.0f}%")
            if score_data.reasoning:
                explanation.append(f"   - {score_data.reasoning}")

        if result.missing_critical_areas:
            explanation.append("\n## Áreas Críticas Faltantes\n")
            for area in result.missing_critical_areas[:5]:
                explanation.append(f"- {area}")

        if result.suggested_questions:
            explanation.append("\n## Perguntas Sugeridas\n")
            for i, question in enumerate(result.suggested_questions, 1):
                explanation.append(f"{i}. {question}")

        explanation.append(f"\n**Resumo**: {result.reasoning_summary}")

        return "\n".join(explanation)

    def get_analyzer_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do analisador."""
        return {
            "threshold": f"{self.threshold:.0%}",
            "cached_analyses": len(self.analysis_cache),
            "model": self.model,
            "categories": len(UniversalCategory),
        }
