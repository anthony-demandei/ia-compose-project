"""
Universal Project Classifier - Classifica qualquer tipo de projeto
para determinar categorias relevantes e pesos adaptativos.

Funciona com qualquer domínio: desde robôs scrapers simples até plataformas complexas.
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from openai import AsyncOpenAI

from app.utils.pii_safe_logging import get_pii_safe_logger
from app.utils.config import get_settings

logger = get_pii_safe_logger(__name__)


class ProjectComplexity(Enum):
    """Níveis de complexidade do projeto."""

    SIMPLE = "simple"  # Script, automação básica, landing page
    MODERATE = "moderate"  # App básico, site com CMS, integração
    COMPLEX = "complex"  # Sistema completo, SaaS, plataforma
    ENTERPRISE = "enterprise"  # ERP, sistema crítico, alta escala


class ProjectType(Enum):
    """Tipos universais de projeto."""

    AUTOMATION = "automation"  # Scripts, bots, scrapers, automações
    WEBSITE = "website"  # Landing pages, blogs, sites corporativos
    APPLICATION = "application"  # Web apps, mobile apps, desktop
    SYSTEM = "system"  # CRM, ERP, sistemas internos
    PLATFORM = "platform"  # SaaS, marketplaces, redes sociais
    INTEGRATION = "integration"  # APIs, webhooks, sincronização
    CONTENT = "content"  # Blogs, portfólios, catálogos
    ECOMMERCE = "ecommerce"  # Lojas virtuais, vendas online
    SERVICE = "service"  # Serviços profissionais, consultoria


class UniversalCategory(Enum):
    """Categorias universais que se aplicam a qualquer projeto."""

    OBJECTIVE = "objective"  # O que faz? Para que serve?
    SCOPE = "scope"  # Qual escopo? O que inclui/exclui?
    TECHNICAL = "technical"  # Como será feito? Tecnologias?
    FUNCTIONAL = "functional"  # Que funcionalidades específicas?
    CONSTRAINTS = "constraints"  # Limitações, requisitos especiais?
    RESOURCES = "resources"  # Prazo, orçamento, equipe?
    ENVIRONMENT = "environment"  # Onde roda? Deploy? Infra?
    SUCCESS_CRITERIA = "success"  # Como medir sucesso? KPIs?


@dataclass
class ProjectClassification:
    """Resultado da classificação do projeto."""

    project_type: ProjectType
    complexity: ProjectComplexity
    category_weights: Dict[UniversalCategory, float]
    critical_categories: List[UniversalCategory]
    domain_context: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""
    suggested_questions_focus: List[str] = field(default_factory=list)


class UniversalProjectClassifier:
    """
    Classificador universal que funciona com qualquer tipo de projeto.

    Exemplos suportados:
    - Robô scraper para Mercado Livre
    - Landing page para advogado
    - Sistema de agendamento médico
    - App de delivery local
    - Automação de planilhas
    - API de integração
    - Blog WordPress customizado
    """

    def __init__(self, api_key: str = None):
        """
        Inicializa o classificador universal.

        Args:
            api_key: Chave da OpenAI API (usa ENV se não fornecida)
        """
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.model = settings.openai_model
        self.temperature = 0.2  # Baixa para classificação consistente

        # Definir pesos padrão por tipo de projeto
        self.default_weights = self._initialize_default_weights()

        # Cache de classificações
        self.classification_cache: Dict[str, ProjectClassification] = {}

        logger.info("UniversalProjectClassifier initialized")

    def _initialize_default_weights(self) -> Dict[ProjectType, Dict[UniversalCategory, float]]:
        """Inicializa pesos padrão por tipo de projeto."""
        return {
            ProjectType.AUTOMATION: {
                UniversalCategory.OBJECTIVE: 0.25,  # Muito importante: o que automatizar?
                UniversalCategory.TECHNICAL: 0.25,  # Como implementar?
                UniversalCategory.FUNCTIONAL: 0.20,  # Que features específicas?
                UniversalCategory.CONSTRAINTS: 0.10,  # Limitações técnicas
                UniversalCategory.SCOPE: 0.10,  # Escopo claro
                UniversalCategory.RESOURCES: 0.05,  # Menos crítico
                UniversalCategory.ENVIRONMENT: 0.03,  # Onde executar
                UniversalCategory.SUCCESS_CRITERIA: 0.02,  # Como medir sucesso
            },
            ProjectType.WEBSITE: {
                UniversalCategory.OBJECTIVE: 0.30,  # Finalidade do site
                UniversalCategory.FUNCTIONAL: 0.25,  # Que funcionalidades
                UniversalCategory.SCOPE: 0.15,  # O que incluir
                UniversalCategory.TECHNICAL: 0.10,  # Stack menos crítico
                UniversalCategory.SUCCESS_CRITERIA: 0.08,  # Conversões, métricas
                UniversalCategory.RESOURCES: 0.07,  # Prazo/orçamento
                UniversalCategory.CONSTRAINTS: 0.03,  # Limitações
                UniversalCategory.ENVIRONMENT: 0.02,  # Hosting
            },
            ProjectType.APPLICATION: {
                UniversalCategory.FUNCTIONAL: 0.25,  # Features principais
                UniversalCategory.TECHNICAL: 0.20,  # Arquitetura importante
                UniversalCategory.OBJECTIVE: 0.15,  # Finalidade
                UniversalCategory.SCOPE: 0.15,  # Escopo das features
                UniversalCategory.CONSTRAINTS: 0.10,  # Restrições técnicas
                UniversalCategory.RESOURCES: 0.08,  # Cronograma
                UniversalCategory.ENVIRONMENT: 0.05,  # Deploy
                UniversalCategory.SUCCESS_CRITERIA: 0.02,  # KPIs
            },
            ProjectType.SYSTEM: {
                UniversalCategory.FUNCTIONAL: 0.20,  # Processos de negócio
                UniversalCategory.TECHNICAL: 0.20,  # Arquitetura complexa
                UniversalCategory.SCOPE: 0.18,  # Definir bem escopo
                UniversalCategory.OBJECTIVE: 0.15,  # Objetivos de negócio
                UniversalCategory.CONSTRAINTS: 0.12,  # Integrações, compliance
                UniversalCategory.RESOURCES: 0.08,  # Cronograma crítico
                UniversalCategory.ENVIRONMENT: 0.05,  # Infra corporativa
                UniversalCategory.SUCCESS_CRITERIA: 0.02,  # ROI
            },
            ProjectType.PLATFORM: {
                UniversalCategory.FUNCTIONAL: 0.22,  # Features da plataforma
                UniversalCategory.TECHNICAL: 0.22,  # Escalabilidade crítica
                UniversalCategory.SCOPE: 0.18,  # Definir MVP vs full
                UniversalCategory.OBJECTIVE: 0.12,  # Modelo de negócio
                UniversalCategory.CONSTRAINTS: 0.10,  # Performance, segurança
                UniversalCategory.RESOURCES: 0.08,  # Budget significativo
                UniversalCategory.ENVIRONMENT: 0.06,  # Cloud, infra
                UniversalCategory.SUCCESS_CRITERIA: 0.02,  # Métricas usuários
            },
            ProjectType.INTEGRATION: {
                UniversalCategory.TECHNICAL: 0.35,  # APIs, protocolos
                UniversalCategory.FUNCTIONAL: 0.25,  # O que integrar
                UniversalCategory.CONSTRAINTS: 0.15,  # Limitações sistemas
                UniversalCategory.OBJECTIVE: 0.10,  # Por que integrar
                UniversalCategory.SCOPE: 0.08,  # Escopo da integração
                UniversalCategory.RESOURCES: 0.04,  # Timeline
                UniversalCategory.ENVIRONMENT: 0.02,  # Onde executar
                UniversalCategory.SUCCESS_CRITERIA: 0.01,  # Sucesso da sync
            },
            ProjectType.CONTENT: {
                UniversalCategory.OBJECTIVE: 0.30,  # Finalidade do conteúdo
                UniversalCategory.FUNCTIONAL: 0.25,  # Que tipo de conteúdo
                UniversalCategory.SCOPE: 0.20,  # Volume, categorias
                UniversalCategory.TECHNICAL: 0.10,  # CMS, tecnologia
                UniversalCategory.SUCCESS_CRITERIA: 0.08,  # Engajamento, SEO
                UniversalCategory.RESOURCES: 0.04,  # Timeline criação
                UniversalCategory.CONSTRAINTS: 0.02,  # Limitações design
                UniversalCategory.ENVIRONMENT: 0.01,  # Onde publicar
            },
            ProjectType.ECOMMERCE: {
                UniversalCategory.FUNCTIONAL: 0.25,  # Catálogo, checkout
                UniversalCategory.TECHNICAL: 0.20,  # Pagamentos, segurança
                UniversalCategory.OBJECTIVE: 0.15,  # Modelo de vendas
                UniversalCategory.SCOPE: 0.15,  # Que produtos/serviços
                UniversalCategory.CONSTRAINTS: 0.10,  # Compliance, integração
                UniversalCategory.RESOURCES: 0.08,  # Budget marketing
                UniversalCategory.SUCCESS_CRITERIA: 0.05,  # Conversão, vendas
                UniversalCategory.ENVIRONMENT: 0.02,  # Hosting, CDN
            },
            ProjectType.SERVICE: {
                UniversalCategory.OBJECTIVE: 0.35,  # Que serviço oferece
                UniversalCategory.FUNCTIONAL: 0.20,  # Como funciona processo
                UniversalCategory.SCOPE: 0.15,  # Que serviços incluir
                UniversalCategory.SUCCESS_CRITERIA: 0.12,  # Como medir qualidade
                UniversalCategory.TECHNICAL: 0.08,  # Stack simples
                UniversalCategory.RESOURCES: 0.05,  # Timeline
                UniversalCategory.CONSTRAINTS: 0.03,  # Regulamentações
                UniversalCategory.ENVIRONMENT: 0.02,  # Onde operar
            },
        }

    async def classify_project(self, briefing_text: str) -> ProjectClassification:
        """
        Classifica um projeto baseado no briefing.

        Args:
            briefing_text: Descrição do projeto

        Returns:
            ProjectClassification com tipo, complexidade e pesos
        """
        try:
            # Verificar cache
            cache_key = self._generate_cache_key(briefing_text)
            if cache_key in self.classification_cache:
                logger.info("Using cached project classification")
                return self.classification_cache[cache_key]

            logger.info("Classifying project with AI")

            # 1. Análise com IA para classificação
            analysis = await self._analyze_with_ai(briefing_text)

            # 2. Determinar tipo e complexidade
            project_type = self._map_to_project_type(analysis.get("project_type", "application"))
            complexity = self._map_to_complexity(analysis.get("complexity", "moderate"))

            # 3. Calcular pesos baseados no tipo
            base_weights = self.default_weights.get(
                project_type, self.default_weights[ProjectType.APPLICATION]
            )

            # 4. Ajustar pesos baseado na complexidade
            adjusted_weights = self._adjust_weights_for_complexity(base_weights, complexity)

            # 5. Identificar categorias críticas
            critical_categories = self._identify_critical_categories(analysis, adjusted_weights)

            # 6. Determinar focos para perguntas
            question_focus = self._determine_question_focus(analysis, critical_categories)

            # 7. Compilar resultado
            result = ProjectClassification(
                project_type=project_type,
                complexity=complexity,
                category_weights=adjusted_weights,
                critical_categories=critical_categories,
                domain_context=analysis.get("domain_context"),
                confidence=float(analysis.get("confidence", 0.8)),
                reasoning=analysis.get("reasoning", ""),
                suggested_questions_focus=question_focus,
            )

            # Cache resultado
            self.classification_cache[cache_key] = result

            logger.info(
                f"Project classified as {project_type.value} ({complexity.value}) "
                f"with {len(critical_categories)} critical categories"
            )

            return result

        except Exception as e:
            logger.error(f"Error classifying project: {str(e)}")
            # Retornar classificação padrão
            return self._get_default_classification()

    async def _analyze_with_ai(self, briefing_text: str) -> Dict[str, Any]:
        """Analisa o projeto com IA para classificação."""

        prompt = f"""
        Analise esta descrição de projeto e classifique-o em categorias universais.
        
        DESCRIÇÃO DO PROJETO:
        {briefing_text}
        
        Retorne JSON com:
        {{
            "project_type": "automation|website|application|system|platform|integration|content|ecommerce|service",
            "complexity": "simple|moderate|complex|enterprise",
            "domain_context": "contexto específico do domínio detectado ou 'generic'",
            "key_characteristics": ["característica1", "característica2"],
            "missing_critical_info": ["informação faltante crítica1", "informação2"],
            "confidence": 0.0-1.0,
            "reasoning": "explicação da classificação em 2-3 frases"
        }}
        
        DIRETRIZES DE CLASSIFICAÇÃO:
        
        **PROJECT_TYPE:**
        - automation: Scripts, bots, scrapers, automações, rotinas
        - website: Landing pages, sites institucionais, blogs, portfólios
        - application: Apps web/mobile com interação complexa
        - system: CRM, ERP, sistemas internos, gestão de processos
        - platform: SaaS, marketplaces, redes sociais, multi-tenant
        - integration: APIs, webhooks, sincronização entre sistemas
        - content: Blogs, catálogos, sites de conteúdo
        - ecommerce: Lojas virtuais, vendas online
        - service: Serviços profissionais, consultoria, agendamentos
        
        **COMPLEXITY:**
        - simple: Script básico, landing page, automação simples
        - moderate: App com algumas features, site com CMS, integração básica
        - complex: Sistema completo, múltiplas integrações, arquitetura robusta
        - enterprise: Sistemas críticos, alta escala, compliance rigoroso
        
        **DOMAIN_CONTEXT (exemplos):**
        fintech: bancos, pagamentos, investimentos, carteiras, criptomoedas
        healthcare: saúde, médico, hospital, telemedicina, prontuário
        education: escola, curso, e-learning, universidade, LMS
        ecommerce: loja virtual, marketplace, vendas online
        industry: indústria, manufatura, automação industrial, IoT
        real_estate: imobiliário, imóveis, corretora, aluguel
        automotive: automotivo, carros, concessionária, oficina
        gaming: jogos, entretenimento, multiplayer, streaming
        media: mídia, vídeo, conteúdo, publicação, streaming
        legal: jurídico, advocacia, processos, contratos
        food_beverage: restaurante, delivery, comida, cardápio
        travel: turismo, hotel, reserva, booking, viagem
        hr: RH, recursos humanos, recrutamento, folha
        analytics: BI, dashboard, relatórios, métricas, KPIs
        security: segurança, monitoramento, firewall, antivirus
        generic: desenvolvimento genérico, sistema, software

        **EXAMPLES:**
        - "robô scraper mercado livre" → automation, simple, ecommerce
        - "landing page advogado" → website, simple, legal
        - "app delivery restaurante" → application, moderate, food_beverage
        - "sistema ERP completo" → system, complex, generic
        - "plataforma fintech pagamentos" → platform, complex, fintech
        - "dashboard analytics vendas" → application, moderate, analytics
        - "sistema hospital prontuários" → system, complex, healthcare
        - "e-learning universidade" → platform, moderate, education
        
        Seja preciso na classificação baseado na descrição fornecida.
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um expert em classificação de projetos de software. "
                        "Classifique projetos de forma precisa baseado na descrição.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=800,
                response_format={"type": "json_object"},
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Error in AI project classification: {str(e)}")
            return self._get_default_analysis()

    def _map_to_project_type(self, type_str: str) -> ProjectType:
        """Mapeia string para ProjectType enum."""
        mapping = {
            "automation": ProjectType.AUTOMATION,
            "website": ProjectType.WEBSITE,
            "application": ProjectType.APPLICATION,
            "system": ProjectType.SYSTEM,
            "platform": ProjectType.PLATFORM,
            "integration": ProjectType.INTEGRATION,
            "content": ProjectType.CONTENT,
            "ecommerce": ProjectType.ECOMMERCE,
            "service": ProjectType.SERVICE,
        }
        return mapping.get(type_str, ProjectType.APPLICATION)

    def _map_to_complexity(self, complexity_str: str) -> ProjectComplexity:
        """Mapeia string para ProjectComplexity enum."""
        mapping = {
            "simple": ProjectComplexity.SIMPLE,
            "moderate": ProjectComplexity.MODERATE,
            "complex": ProjectComplexity.COMPLEX,
            "enterprise": ProjectComplexity.ENTERPRISE,
        }
        return mapping.get(complexity_str, ProjectComplexity.MODERATE)

    def _adjust_weights_for_complexity(
        self, base_weights: Dict[UniversalCategory, float], complexity: ProjectComplexity
    ) -> Dict[UniversalCategory, float]:
        """Ajusta pesos baseado na complexidade."""
        adjusted = base_weights.copy()

        if complexity == ProjectComplexity.SIMPLE:
            # Projetos simples: foco em objective e technical
            adjusted[UniversalCategory.OBJECTIVE] *= 1.2
            adjusted[UniversalCategory.TECHNICAL] *= 1.1
            adjusted[UniversalCategory.RESOURCES] *= 0.8
            adjusted[UniversalCategory.SUCCESS_CRITERIA] *= 0.7

        elif complexity == ProjectComplexity.COMPLEX:
            # Projetos complexos: mais equilíbrio, foco em constraints
            adjusted[UniversalCategory.CONSTRAINTS] *= 1.3
            adjusted[UniversalCategory.SCOPE] *= 1.2
            adjusted[UniversalCategory.RESOURCES] *= 1.1

        elif complexity == ProjectComplexity.ENTERPRISE:
            # Projetos enterprise: foco em constraints, environment, success
            adjusted[UniversalCategory.CONSTRAINTS] *= 1.4
            adjusted[UniversalCategory.ENVIRONMENT] *= 1.3
            adjusted[UniversalCategory.SUCCESS_CRITERIA] *= 1.2
            adjusted[UniversalCategory.RESOURCES] *= 1.1

        # Normalizar para soma = 1.0
        total = sum(adjusted.values())
        for category in adjusted:
            adjusted[category] /= total

        return adjusted

    def _identify_critical_categories(
        self, analysis: Dict[str, Any], weights: Dict[UniversalCategory, float]
    ) -> List[UniversalCategory]:
        """Identifica categorias críticas baseado na análise."""
        # Ordenar por peso (descendente)
        sorted_categories = sorted(weights.items(), key=lambda x: x[1], reverse=True)

        # Pegar top 3-4 categorias mais importantes
        critical = [cat for cat, weight in sorted_categories[:4] if weight > 0.1]

        return critical

    def _determine_question_focus(
        self, analysis: Dict[str, Any], critical_categories: List[UniversalCategory]
    ) -> List[str]:
        """Determina focos para geração de perguntas."""
        focus_areas = []

        # Áreas faltantes da análise
        missing_info = analysis.get("missing_critical_info", [])
        focus_areas.extend(missing_info[:3])

        # Áreas baseadas nas categorias críticas
        category_focus_map = {
            UniversalCategory.OBJECTIVE: "clarificar objetivo e finalidade",
            UniversalCategory.SCOPE: "definir escopo e limites",
            UniversalCategory.TECHNICAL: "especificar requisitos técnicos",
            UniversalCategory.FUNCTIONAL: "detalhar funcionalidades",
            UniversalCategory.CONSTRAINTS: "identificar restrições e limitações",
            UniversalCategory.RESOURCES: "definir cronograma e orçamento",
            UniversalCategory.ENVIRONMENT: "especificar ambiente de deploy",
            UniversalCategory.SUCCESS_CRITERIA: "estabelecer métricas de sucesso",
        }

        for category in critical_categories[:3]:  # Top 3
            focus = category_focus_map.get(category)
            if focus and focus not in focus_areas:
                focus_areas.append(focus)

        return focus_areas[:5]  # Máximo 5 focos

    def _get_default_analysis(self) -> Dict[str, Any]:
        """Retorna análise padrão para fallback."""
        return {
            "project_type": "application",
            "complexity": "moderate",
            "domain_context": "generic",
            "key_characteristics": ["desenvolvimento de software"],
            "missing_critical_info": ["especificações técnicas", "cronograma"],
            "confidence": 0.5,
            "reasoning": "Análise automática não disponível. Usando classificação padrão.",
        }

    def _get_default_classification(self) -> ProjectClassification:
        """Retorna classificação padrão para fallback."""
        base_weights = self.default_weights[ProjectType.APPLICATION]

        return ProjectClassification(
            project_type=ProjectType.APPLICATION,
            complexity=ProjectComplexity.MODERATE,
            category_weights=base_weights,
            critical_categories=[
                UniversalCategory.FUNCTIONAL,
                UniversalCategory.TECHNICAL,
                UniversalCategory.OBJECTIVE,
            ],
            confidence=0.5,
            reasoning="Classificação padrão devido a erro na análise",
            suggested_questions_focus=["especificar funcionalidades", "definir tecnologia"],
        )

    def _generate_cache_key(self, text: str) -> str:
        """Gera chave única para cache."""
        import hashlib

        return hashlib.md5(text.encode()).hexdigest()

    def get_supported_types(self) -> Dict[str, str]:
        """Retorna tipos de projeto suportados."""
        return {
            "automation": "Scripts, bots, scrapers, automações",
            "website": "Landing pages, sites, blogs, portfólios",
            "application": "Apps web/mobile interativos",
            "system": "CRM, ERP, sistemas internos",
            "platform": "SaaS, marketplaces, plataformas",
            "integration": "APIs, webhooks, sincronização",
            "content": "Sites de conteúdo, catálogos",
            "ecommerce": "Lojas virtuais, vendas online",
            "service": "Serviços profissionais, agendamentos",
        }

    def get_classifier_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do classificador."""
        return {
            "cached_classifications": len(self.classification_cache),
            "supported_types": len(ProjectType),
            "supported_complexities": len(ProjectComplexity),
            "universal_categories": len(UniversalCategory),
            "model": self.model,
        }
