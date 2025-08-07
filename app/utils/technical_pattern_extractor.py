"""
Technical Pattern Extractor - Extrai padrões técnicos avançados e insights arquiteturais.

Este módulo complementa o KnowledgeSanitizer com análise mais profunda
de padrões técnicos usando IA para identificar relações e tendências.
"""

import json
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum
from openai import AsyncOpenAI

from app.utils.pii_safe_logging import get_pii_safe_logger
from app.utils.config import get_settings

logger = get_pii_safe_logger(__name__)


@dataclass
class TechnicalPattern:
    """Padrão técnico identificado."""

    pattern_type: str  # "stack", "architecture", "integration", "feature"
    pattern_name: str
    confidence: float  # 0-1
    context: str
    related_patterns: List[str] = None


@dataclass
class ArchitecturalInsight:
    """Insight arquitetural extraído."""

    insight_type: str  # "scalability", "performance", "security", "maintainability"
    description: str
    technical_context: List[str]
    applicable_domains: List[str]
    confidence: float


class PatternCategory(Enum):
    """Categorias de padrões técnicos."""

    TECHNOLOGY_STACK = "technology_stack"
    ARCHITECTURE = "architecture"
    INTEGRATION = "integration"
    FEATURE = "feature"
    DEPLOYMENT = "deployment"
    SECURITY = "security"
    PERFORMANCE = "performance"


class TechnicalPatternExtractor:
    """
    Extrator avançado de padrões técnicos usando IA.

    Identifica padrões complexos, relações entre tecnologias,
    e insights arquiteturais que podem beneficiar outros projetos.
    """

    def __init__(self, openai_api_key: str = None):
        """Inicializa o extrator com configurações."""
        settings = get_settings()
        self.openai_client = AsyncOpenAI(api_key=openai_api_key or settings.openai_api_key)
        self.model = settings.openai_model
        self.temperature = 0.1  # Baixa para consistência

        # Cache de padrões identificados
        self.pattern_cache: Dict[str, List[TechnicalPattern]] = {}

    async def extract_advanced_patterns(
        self, sanitized_text: str, domain: str = None
    ) -> List[TechnicalPattern]:
        """
        Extrai padrões técnicos avançados usando IA.

        Args:
            sanitized_text: Texto já sanitizado (sem PII)
            domain: Domínio do projeto (opcional)

        Returns:
            Lista de padrões técnicos identificados
        """
        try:
            # Verificar cache primeiro
            cache_key = f"{hash(sanitized_text)}_{domain}"
            if cache_key in self.pattern_cache:
                logger.debug("Using cached technical patterns")
                return self.pattern_cache[cache_key]

            # Extrair padrões usando IA
            patterns = await self._analyze_with_ai(sanitized_text, domain)

            # Cache resultado
            self.pattern_cache[cache_key] = patterns

            logger.info(f"Extracted {len(patterns)} advanced technical patterns")
            return patterns

        except Exception as e:
            logger.error(f"Error extracting advanced patterns: {str(e)}")
            return []

    async def extract_architectural_insights(
        self, patterns: List[TechnicalPattern], project_context: Dict[str, Any] = None
    ) -> List[ArchitecturalInsight]:
        """
        Extrai insights arquiteturais baseado nos padrões identificados.

        Args:
            patterns: Padrões técnicos já identificados
            project_context: Contexto do projeto (sanitizado)

        Returns:
            Lista de insights arquiteturais
        """
        try:
            if not patterns:
                return []

            # Gerar insights usando IA
            insights = await self._generate_architectural_insights(patterns, project_context)

            logger.info(f"Generated {len(insights)} architectural insights")
            return insights

        except Exception as e:
            logger.error(f"Error extracting architectural insights: {str(e)}")
            return []

    async def identify_technology_relationships(
        self, tech_stack: List[str]
    ) -> Dict[str, List[str]]:
        """
        Identifica relacionamentos entre tecnologias.

        Args:
            tech_stack: Lista de tecnologias

        Returns:
            Mapeamento de relacionamentos entre tecnologias
        """
        try:
            if len(tech_stack) < 2:
                return {}

            relationships = await self._analyze_tech_relationships(tech_stack)

            logger.info(f"Identified relationships for {len(tech_stack)} technologies")
            return relationships

        except Exception as e:
            logger.error(f"Error identifying technology relationships: {str(e)}")
            return {}

    async def _analyze_with_ai(self, text: str, domain: str = None) -> List[TechnicalPattern]:
        """Analisa texto usando IA para extrair padrões técnicos."""

        domain_context = f"no domínio {domain}" if domain else ""

        prompt = f"""
        Analise o seguinte texto técnico sanitizado {domain_context} e identifique padrões técnicos APENAS:
        
        TEXTO: {text}
        
        Identifique padrões nas seguintes categorias:
        1. TECHNOLOGY_STACK: Tecnologias e suas versões/configurações específicas
        2. ARCHITECTURE: Padrões arquiteturais e estruturais
        3. INTEGRATION: Padrões de integração e APIs
        4. FEATURE: Features técnicas e funcionalidades
        5. DEPLOYMENT: Estratégias de deploy e infraestrutura
        6. SECURITY: Padrões de segurança implementados
        7. PERFORMANCE: Otimizações e padrões de performance
        
        Para cada padrão identificado, forneça:
        - Categoria do padrão
        - Nome específico do padrão
        - Nível de confiança (0-1)
        - Contexto técnico
        - Padrões relacionados (se houver)
        
        IMPORTANTE:
        - Ignore qualquer dado específico de cliente ou empresa
        - Foque APENAS em aspectos técnicos reutilizáveis
        - Seja preciso e técnico nas identificações
        - Use terminologia padrão da indústria
        
        Retorne JSON no formato:
        {{
            "patterns": [
                {{
                    "pattern_type": "TECHNOLOGY_STACK",
                    "pattern_name": "react-typescript-tailwind",
                    "confidence": 0.9,
                    "context": "Frontend moderno com tipagem forte",
                    "related_patterns": ["node-backend", "rest-api"]
                }}
            ]
        }}
        """

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um arquiteto de software especialista em identificar padrões técnicos reutilizáveis. Seja preciso e técnico.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            patterns = []

            for pattern_data in result.get("patterns", []):
                pattern = TechnicalPattern(
                    pattern_type=pattern_data.get("pattern_type", ""),
                    pattern_name=pattern_data.get("pattern_name", ""),
                    confidence=float(pattern_data.get("confidence", 0.5)),
                    context=pattern_data.get("context", ""),
                    related_patterns=pattern_data.get("related_patterns", []),
                )
                patterns.append(pattern)

            return patterns

        except Exception as e:
            logger.error(f"Error in AI pattern analysis: {str(e)}")
            return []

    async def _generate_architectural_insights(
        self, patterns: List[TechnicalPattern], context: Dict[str, Any] = None
    ) -> List[ArchitecturalInsight]:
        """Gera insights arquiteturais usando IA."""

        patterns_text = "\n".join(
            [f"- {p.pattern_type}: {p.pattern_name} (confiança: {p.confidence})" for p in patterns]
        )

        context_text = ""
        if context:
            context_text = f"\nContexto adicional: {json.dumps(context, indent=2)}"

        prompt = f"""
        Com base nos seguintes padrões técnicos identificados, gere insights arquiteturais reutilizáveis:
        
        PADRÕES IDENTIFICADOS:
        {patterns_text}
        {context_text}
        
        Gere insights nas seguintes categorias:
        1. SCALABILITY: Como os padrões afetam escalabilidade
        2. PERFORMANCE: Implicações de performance das escolhas técnicas
        3. SECURITY: Considerações de segurança dos padrões
        4. MAINTAINABILITY: Facilidade de manutenção e evolução
        
        Para cada insight:
        - Forneça descrição técnica clara
        - Liste contexto técnico específico
        - Indique domínios onde é aplicável
        - Avalie nível de confiança
        
        FOQUE EM:
        - Lições aprendidas reutilizáveis
        - Trade-offs arquiteturais
        - Melhores práticas identificadas
        - Padrões que funcionam bem juntos
        
        Retorne JSON:
        {{
            "insights": [
                {{
                    "insight_type": "SCALABILITY",
                    "description": "Microserviços com React permite escala independente",
                    "technical_context": ["microservices", "react", "api-gateway"],
                    "applicable_domains": ["ecommerce", "fintech"],
                    "confidence": 0.85
                }}
            ]
        }}
        """

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um arquiteto sênior especialista em extrair insights técnicos reutilizáveis de padrões identificados.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            insights = []

            for insight_data in result.get("insights", []):
                insight = ArchitecturalInsight(
                    insight_type=insight_data.get("insight_type", ""),
                    description=insight_data.get("description", ""),
                    technical_context=insight_data.get("technical_context", []),
                    applicable_domains=insight_data.get("applicable_domains", []),
                    confidence=float(insight_data.get("confidence", 0.5)),
                )
                insights.append(insight)

            return insights

        except Exception as e:
            logger.error(f"Error generating architectural insights: {str(e)}")
            return []

    async def _analyze_tech_relationships(self, tech_stack: List[str]) -> Dict[str, List[str]]:
        """Analisa relacionamentos entre tecnologias."""

        prompt = f"""
        Analise as seguintes tecnologias e identifique seus relacionamentos técnicos:
        
        TECNOLOGIAS: {', '.join(tech_stack)}
        
        Para cada tecnologia, identifique:
        1. Tecnologias que funcionam bem juntas (synergies)
        2. Possíveis conflitos ou incompatibilidades
        3. Dependências técnicas
        4. Complementaridades arquiteturais
        
        Retorne JSON:
        {{
            "relationships": {{
                "react": {{
                    "complements": ["typescript", "node.js"],
                    "conflicts": [],
                    "depends_on": ["javascript"],
                    "enables": ["spa-architecture"]
                }}
            }}
        }}
        """

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um especialista em arquitetura de software com conhecimento profundo de relacionamentos entre tecnologias.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("relationships", {})

        except Exception as e:
            logger.error(f"Error analyzing tech relationships: {str(e)}")
            return {}

    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas dos padrões extraídos."""
        total_patterns = sum(len(patterns) for patterns in self.pattern_cache.values())

        if total_patterns == 0:
            return {"total_patterns": 0, "cache_size": 0}

        # Contar padrões por categoria
        category_counts = {}
        for patterns in self.pattern_cache.values():
            for pattern in patterns:
                category = pattern.pattern_type
                category_counts[category] = category_counts.get(category, 0) + 1

        return {
            "total_patterns": total_patterns,
            "cache_size": len(self.pattern_cache),
            "patterns_by_category": category_counts,
            "average_confidence": sum(
                pattern.confidence
                for patterns in self.pattern_cache.values()
                for pattern in patterns
            )
            / total_patterns
            if total_patterns > 0
            else 0.0,
        }

    def clear_cache(self):
        """Limpa cache de padrões."""
        self.pattern_cache.clear()
        logger.info("Technical pattern cache cleared")


# Função de conveniência
def create_technical_pattern_extractor(openai_api_key: str = None) -> TechnicalPatternExtractor:
    """Cria uma instância do extrator de padrões técnicos."""
    return TechnicalPatternExtractor(openai_api_key)
