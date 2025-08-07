"""
Context Inference Engine - Análise semântica inteligente para evitar perguntas redundantes.
Usa GPT-4 para extrair informações implícitas e óbvias do texto de entrada.
"""

import json
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from openai import AsyncOpenAI

from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class InferenceConfidence(Enum):
    """Níveis de confiança na inferência."""

    CERTAIN = "certain"  # 95%+ certeza - não perguntar
    LIKELY = "likely"  # 80%+ certeza - perguntar se crítico
    POSSIBLE = "possible"  # 60%+ certeza - perguntar normalmente
    UNKNOWN = "unknown"  # < 60% certeza - sempre perguntar


@dataclass
class InferredInformation:
    """Informação inferida do contexto."""

    category: str  # "domain", "functionality", "user_type", etc.
    key: str  # identificador específico
    value: Any  # valor inferido
    confidence: InferenceConfidence
    reasoning: str  # explicação da inferência
    evidence: List[str] = field(default_factory=list)  # trechos que levaram à inferência


@dataclass
class DomainContext:
    """Contexto específico de um domínio."""

    domain: str
    characteristics: List[str]
    implied_requirements: List[str]
    automatic_assumptions: Dict[str, Any]
    typical_integrations: List[str]
    compliance_requirements: List[str]


@dataclass
class InferenceResult:
    """Resultado completo da análise de inferência."""

    inferred_info: List[InferredInformation] = field(default_factory=list)
    detected_domain: Optional[str] = None
    domain_confidence: float = 0.0
    obvious_answers: Dict[str, Any] = field(default_factory=dict)  # respostas óbvias
    redundant_question_ids: Set[str] = field(default_factory=set)  # perguntas a evitar
    focus_areas: List[str] = field(default_factory=list)  # áreas que precisam de perguntas
    reasoning_summary: str = ""


class ContextInferenceEngine:
    """
    Motor de inferência que analisa texto de entrada e extrai informações implícitas.

    Evita perguntas redundantes identificando o que já é óbvio pelo contexto.
    """

    def __init__(self, api_key: str, model: str = None):
        """
        Inicializa o motor de inferência.

        Args:
            api_key: Chave da OpenAI API
            model: Modelo a usar para análise (usa configuração do ENV se não especificado)
        """
        from app.utils.config import get_settings

        settings = get_settings()
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model or settings.openai_model
        self.temperature = 0.1  # Baixa para respostas mais consistentes

        # Conhecimento de domínios
        self.domain_knowledge = self._initialize_domain_knowledge()

        # Cache de inferências
        self.inference_cache: Dict[str, InferenceResult] = {}

        logger.info("Context Inference Engine initialized")

    def _initialize_domain_knowledge(self) -> Dict[str, DomainContext]:
        """
        Inicializa conhecimento de domínios específicos para melhor detecção contextual.

        Sistema V3.0 Universal com Especialização Inteligente:
        - Detecta automaticamente o domínio via IA
        - Aplica conhecimento específico quando disponível
        - Funciona universalmente mesmo sem conhecimento específico
        """
        return {
            # Domínio genérico (fallback universal)
            "_generic": DomainContext(
                domain="generic",
                characteristics=["desenvolvimento", "sistema", "software"],
                implied_requirements=["funcionalidade", "qualidade", "entrega"],
                automatic_assumptions={},
                typical_integrations=[],
                compliance_requirements=["LGPD"],
            ),
            # 🏦 Fintech - Serviços financeiros
            "fintech": DomainContext(
                domain="fintech",
                characteristics=[
                    "pagamentos",
                    "investimentos",
                    "bancos",
                    "carteiras digitais",
                    "criptomoedas",
                ],
                implied_requirements=["alta segurança", "auditoria", "backup", "monitoramento"],
                automatic_assumptions={
                    "handles_sensitive_data": True,
                    "requires_high_security": True,
                    "needs_compliance": True,
                    "requires_audit_trail": True,
                },
                typical_integrations=[
                    "gateway de pagamento",
                    "APIs bancárias",
                    "KYC/AML",
                    "contabilidade",
                ],
                compliance_requirements=["PCI DSS", "LGPD", "Banco Central", "CVM"],
            ),
            # 🏥 Healthcare - Saúde e medicina
            "healthcare": DomainContext(
                domain="healthcare",
                characteristics=[
                    "saúde",
                    "médico",
                    "hospital",
                    "clínica",
                    "telemedicina",
                    "prontuário",
                ],
                implied_requirements=[
                    "privacidade de dados",
                    "backup seguro",
                    "disponibilidade 24/7",
                ],
                automatic_assumptions={
                    "handles_sensitive_data": True,
                    "requires_high_security": True,
                    "needs_compliance": True,
                    "requires_data_encryption": True,
                },
                typical_integrations=[
                    "sistemas hospitalares",
                    "laboratórios",
                    "farmácias",
                    "convênios",
                ],
                compliance_requirements=["LGPD", "CFM", "ANVISA", "HIPAA"],
            ),
            # 🎓 Education - Educação e e-learning
            "education": DomainContext(
                domain="education",
                characteristics=[
                    "educação",
                    "escola",
                    "universidade",
                    "curso",
                    "e-learning",
                    "LMS",
                ],
                implied_requirements=["escalabilidade", "acessibilidade", "gamificação"],
                automatic_assumptions={
                    "multi_user_system": True,
                    "requires_user_management": True,
                    "needs_reporting": True,
                },
                typical_integrations=[
                    "sistemas de avaliação",
                    "bibliotecas",
                    "videoconferência",
                    "pagamentos",
                ],
                compliance_requirements=["LGPD", "MEC", "acessibilidade WCAG"],
            ),
            # 🛒 E-commerce - Comércio eletrônico
            "ecommerce": DomainContext(
                domain="ecommerce",
                characteristics=[
                    "loja virtual",
                    "marketplace",
                    "vendas online",
                    "catálogo",
                    "checkout",
                ],
                implied_requirements=["performance", "SEO", "mobile-first", "analytics"],
                automatic_assumptions={
                    "requires_payment_integration": True,
                    "needs_inventory_management": True,
                    "requires_shipping_calculation": True,
                },
                typical_integrations=[
                    "gateways de pagamento",
                    "correios",
                    "ERP",
                    "email marketing",
                ],
                compliance_requirements=["LGPD", "Código do Consumidor", "PCI DSS"],
            ),
            # 🏭 Industry - Indústria e manufatura
            "industry": DomainContext(
                domain="industry",
                characteristics=[
                    "indústria",
                    "manufatura",
                    "produção",
                    "fábrica",
                    "automação industrial",
                ],
                implied_requirements=["tempo real", "IoT", "monitoramento", "dashboards"],
                automatic_assumptions={
                    "requires_real_time_data": True,
                    "needs_industrial_protocols": True,
                    "requires_reliability": True,
                },
                typical_integrations=["sensores IoT", "PLCs", "SCADA", "MES", "ERP"],
                compliance_requirements=["LGPD", "ISO 9001", "normas de segurança"],
            ),
            # 🏢 Real Estate - Imobiliário
            "real_estate": DomainContext(
                domain="real_estate",
                characteristics=["imobiliário", "imóveis", "corretora", "aluguel", "venda"],
                implied_requirements=["busca avançada", "geolocalização", "fotos/vídeos"],
                automatic_assumptions={
                    "requires_search_filters": True,
                    "needs_location_services": True,
                    "requires_media_handling": True,
                },
                typical_integrations=["mapas", "financiamento", "documentação", "CRM"],
                compliance_requirements=["LGPD", "CRECI", "código civil"],
            ),
            # 🚗 Automotive - Automotivo
            "automotive": DomainContext(
                domain="automotive",
                characteristics=["automotivo", "carros", "concessionária", "oficina", "peças"],
                implied_requirements=["catálogo complexo", "compatibilidade", "estoque"],
                automatic_assumptions={
                    "requires_parts_compatibility": True,
                    "needs_inventory_management": True,
                    "requires_service_scheduling": True,
                },
                typical_integrations=[
                    "fabricantes",
                    "distribuidores",
                    "seguradoras",
                    "financeiras",
                ],
                compliance_requirements=["LGPD", "DENATRAN", "normas técnicas"],
            ),
            # 🎮 Gaming - Jogos e entretenimento
            "gaming": DomainContext(
                domain="gaming",
                characteristics=["jogo", "game", "entretenimento", "multiplayer", "streaming"],
                implied_requirements=["baixa latência", "escalabilidade", "anti-cheat"],
                automatic_assumptions={
                    "requires_real_time_communication": True,
                    "needs_user_authentication": True,
                    "requires_performance_optimization": True,
                },
                typical_integrations=[
                    "plataformas de jogos",
                    "payment processors",
                    "streaming",
                    "analytics",
                ],
                compliance_requirements=["LGPD", "classificação etária", "termos de uso"],
            ),
            # 📺 Media - Mídia e conteúdo
            "media": DomainContext(
                domain="media",
                characteristics=["mídia", "streaming", "vídeo", "áudio", "conteúdo", "publicação"],
                implied_requirements=["CDN", "transcodificação", "DRM", "analytics"],
                automatic_assumptions={
                    "requires_media_processing": True,
                    "needs_content_delivery": True,
                    "requires_rights_management": True,
                },
                typical_integrations=["CDNs", "transcodificação", "analytics", "monetização"],
                compliance_requirements=["LGPD", "direitos autorais", "classificação"],
            ),
            # ⚖️ Legal - Jurídico e advocacia
            "legal": DomainContext(
                domain="legal",
                characteristics=["jurídico", "advocacia", "escritório", "processos", "contratos"],
                implied_requirements=[
                    "confidencialidade",
                    "auditoria",
                    "backup",
                    "assinatura digital",
                ],
                automatic_assumptions={
                    "handles_confidential_data": True,
                    "requires_document_management": True,
                    "needs_deadline_tracking": True,
                },
                typical_integrations=["tribunais", "cartórios", "assinatura digital", "timesheet"],
                compliance_requirements=["LGPD", "OAB", "Marco Civil da Internet"],
            ),
            # 🍔 Food & Beverage - Alimentação
            "food_beverage": DomainContext(
                domain="food_beverage",
                characteristics=["restaurante", "delivery", "comida", "cardápio", "pedidos"],
                implied_requirements=["tempo real", "geolocalização", "pagamentos", "avaliações"],
                automatic_assumptions={
                    "requires_order_management": True,
                    "needs_delivery_tracking": True,
                    "requires_payment_processing": True,
                },
                typical_integrations=["delivery platforms", "POS", "pagamentos", "avaliações"],
                compliance_requirements=["LGPD", "ANVISA", "código sanitário"],
            ),
            # ✈️ Travel - Turismo e viagens
            "travel": DomainContext(
                domain="travel",
                characteristics=["turismo", "viagem", "hotel", "reserva", "booking"],
                implied_requirements=["disponibilidade", "pagamentos", "calendários", "mapas"],
                automatic_assumptions={
                    "requires_booking_system": True,
                    "needs_payment_processing": True,
                    "requires_calendar_integration": True,
                },
                typical_integrations=["GDS", "hotéis", "companhias aéreas", "pagamentos"],
                compliance_requirements=["LGPD", "EMBRATUR", "normas internacionais"],
            ),
            # 💼 HR - Recursos Humanos
            "hr": DomainContext(
                domain="hr",
                characteristics=[
                    "RH",
                    "recursos humanos",
                    "recrutamento",
                    "folha",
                    "colaboradores",
                ],
                implied_requirements=["privacidade", "relatórios", "integrações", "workflow"],
                automatic_assumptions={
                    "handles_personal_data": True,
                    "requires_workflow_management": True,
                    "needs_reporting_tools": True,
                },
                typical_integrations=[
                    "folha de pagamento",
                    "contabilidade",
                    "benefícios",
                    "treinamentos",
                ],
                compliance_requirements=["LGPD", "CLT", "eSocial"],
            ),
            # 📊 Analytics - BI e relatórios
            "analytics": DomainContext(
                domain="analytics",
                characteristics=["BI", "analytics", "dashboard", "relatórios", "métricas", "KPIs"],
                implied_requirements=["performance", "visualizações", "tempo real", "exportação"],
                automatic_assumptions={
                    "requires_data_processing": True,
                    "needs_visualization_tools": True,
                    "requires_export_capabilities": True,
                },
                typical_integrations=["bancos de dados", "APIs", "ferramentas de BI", "exportação"],
                compliance_requirements=["LGPD", "auditoria de dados"],
            ),
            # 🔒 Security - Cibersegurança
            "security": DomainContext(
                domain="security",
                characteristics=[
                    "segurança",
                    "cibersegurança",
                    "monitoramento",
                    "firewall",
                    "antivirus",
                ],
                implied_requirements=["tempo real", "alertas", "logs", "compliance"],
                automatic_assumptions={
                    "requires_real_time_monitoring": True,
                    "needs_alert_system": True,
                    "requires_log_management": True,
                },
                typical_integrations=["SIEM", "threat intelligence", "compliance tools", "alertas"],
                compliance_requirements=["LGPD", "ISO 27001", "normas de segurança"],
            ),
        }

    async def analyze_context(self, intake_text: str) -> InferenceResult:
        """
        Analisa o texto de entrada e extrai informações implícitas.

        Args:
            intake_text: Texto de descrição do projeto

        Returns:
            InferenceResult com informações inferidas
        """
        try:
            # Verificar cache
            cache_key = self._generate_cache_key(intake_text)
            if cache_key in self.inference_cache:
                logger.info("Using cached inference result")
                return self.inference_cache[cache_key]

            logger.info("Analyzing context with AI inference")

            # 1. Análise inicial com GPT-4
            analysis = await self._analyze_with_gpt(intake_text)

            # 2. Detectar domínio principal
            domain_result = await self._detect_domain(intake_text, analysis)

            # 3. Aplicar conhecimento específico do domínio
            domain_insights = self._apply_domain_knowledge(domain_result["domain"], analysis)

            # 4. Identificar respostas óbvias
            obvious_answers = self._identify_obvious_answers(intake_text, analysis, domain_insights)

            # 5. Identificar perguntas redundantes
            redundant_questions = await self._identify_redundant_questions(
                obvious_answers, analysis
            )

            # 6. Sugerir áreas de foco
            focus_areas = self._suggest_focus_areas(analysis, obvious_answers)

            # 7. Compilar resultado
            result = InferenceResult(
                inferred_info=self._compile_inferred_info(analysis, domain_insights),
                detected_domain=domain_result["domain"],
                domain_confidence=domain_result["confidence"],
                obvious_answers=obvious_answers,
                redundant_question_ids=redundant_questions,
                focus_areas=focus_areas,
                reasoning_summary=analysis.get("reasoning_summary", ""),
            )

            # Cache resultado
            self.inference_cache[cache_key] = result

            logger.info(
                f"Context analysis completed: domain={result.detected_domain}, "
                f"obvious_answers={len(result.obvious_answers)}, "
                f"redundant_questions={len(result.redundant_question_ids)}"
            )

            return result

        except Exception as e:
            logger.error(f"Error in context analysis: {str(e)}")
            # Retornar resultado vazio em caso de erro
            return InferenceResult()

    async def _analyze_with_gpt(self, intake_text: str) -> Dict[str, Any]:
        """Análise inicial usando GPT-4."""
        prompt = f"""
        Analise este texto de descrição de projeto de software e extraia informações implícitas:

        TEXTO: "{intake_text}"

        Extraia as seguintes informações (retorne JSON):
        {{
            "explicit_info": {{
                "mentioned_features": ["lista de funcionalidades mencionadas"],
                "mentioned_technologies": ["tecnologias mencionadas"],
                "mentioned_integrations": ["integrações mencionadas"],
                "mentioned_user_types": ["tipos de usuários mencionados"]
            }},
            "implicit_info": {{
                "implied_domain": "domínio inferido (fintech, ecommerce, healthcare, education, etc)",
                "implied_complexity": "low/medium/high",
                "implied_user_scale": "pequeno/médio/grande",
                "implied_data_sensitivity": true/false,
                "implied_compliance_needs": ["requisitos de compliance inferidos"],
                "implied_security_level": "low/medium/high/maximum"
            }},
            "obvious_characteristics": {{
                "application_type": "web/mobile/desktop/híbrido - se óbvio",
                "primary_purpose": "finalidade principal se óbvia",
                "target_audience": "público-alvo se óbvio",
                "business_model": "B2B/B2C/interno se óbvio"
            }},
            "missing_info": [
                "informações importantes que ainda precisam ser perguntadas"
            ],
            "reasoning_summary": "explicação de 2-3 frases sobre as inferências feitas"
        }}

        IMPORTANTE:
        - Se algo NÃO está óbvio, marque como null
        - Se fintech/banco/investimento está mencionado, implica dados sensíveis = true
        - Se dashboard/gestão está mencionado, implica web app
        - Seja conservador - só marque como óbvio se REALMENTE está claro
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um expert em análise de requisitos de software. Extraia informações implícitas de forma precisa e conservadora.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Error in GPT analysis: {str(e)}")
            return {}

    async def _detect_domain(self, intake_text: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detecta contexto do projeto de forma universal.

        Não depende mais de domínios hardcoded, usa IA para detectar qualquer contexto.
        """
        # Usar análise da IA como fonte primária
        implied_domain = analysis.get("implicit_info", {}).get("implied_domain", "generic")

        # Detectar contexto automaticamente via texto
        detected_context = await self._detect_context_with_ai(intake_text)

        # Usar contexto detectado ou fallback para implícito
        final_domain = detected_context.get("context", implied_domain)
        confidence = detected_context.get("confidence", 0.7)

        return {"domain": final_domain, "confidence": confidence}

    async def _detect_context_with_ai(self, intake_text: str) -> Dict[str, Any]:
        """Detecta contexto do projeto usando IA - funciona para qualquer domínio."""
        try:
            prompt = f"""
            Analise este briefing de projeto e identifique o contexto/domínio principal.
            
            BRIEFING: {intake_text}
            
            Retorne JSON:
            {{
                "context": "nome específico do contexto/domínio detectado",
                "confidence": 0.0-1.0,
                "key_indicators": ["palavras-chave que indicam o contexto"]
            }}
            
            DOMÍNIOS SUPORTADOS:
            fintech, healthcare, education, ecommerce, industry, real_estate, 
            automotive, gaming, media, legal, food_beverage, travel, hr, 
            analytics, security, generic
            
            IMPORTANTE: 
            - Use um dos domínios listados ou "generic" se não houver match
            - Foque no setor/propósito do negócio, não na tecnologia
            - Seja específico para melhor personalização do sistema
            """

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você detecta contexto de projetos de qualquer domínio.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"},
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.warning(f"AI context detection failed: {e}")
            return {"context": "generic", "confidence": 0.5}

    def _apply_domain_knowledge(self, domain: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica conhecimento específico do domínio detectado."""
        if domain not in self.domain_knowledge:
            return {}

        context = self.domain_knowledge[domain]

        domain_insights = {
            "automatic_assumptions": context.automatic_assumptions.copy(),
            "implied_requirements": context.implied_requirements.copy(),
            "typical_integrations": context.typical_integrations.copy(),
            "compliance_requirements": context.compliance_requirements.copy(),
        }

        # Adicionar insights específicos baseado na análise
        if analysis.get("implicit_info", {}).get("implied_data_sensitivity"):
            domain_insights["automatic_assumptions"]["requires_data_protection"] = True

        return domain_insights

    def _identify_obvious_answers(
        self, intake_text: str, analysis: Dict[str, Any], domain_insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Identifica respostas que são óbvias pelo contexto."""
        obvious = {}

        # Respostas óbvias da análise GPT
        obvious_chars = analysis.get("obvious_characteristics", {})
        for key, value in obvious_chars.items():
            if value and value != "null":
                obvious[key] = value

        # Respostas óbvias do domínio
        auto_assumptions = domain_insights.get("automatic_assumptions", {})
        for key, value in auto_assumptions.items():
            if value is not None:
                obvious[key] = value

        # Análise específica por keywords
        text_lower = intake_text.lower()

        # Dados sensíveis
        sensitive_keywords = [
            "fintech",
            "banco",
            "financeiro",
            "investimento",
            "saúde",
            "médico",
            "cpf",
            "dados pessoais",
        ]
        if any(kw in text_lower for kw in sensitive_keywords):
            obvious["handles_sensitive_data"] = True
            obvious["requires_high_security"] = True

        # Tipo de aplicação
        if any(kw in text_lower for kw in ["dashboard", "web", "sistema", "plataforma"]):
            obvious["application_type"] = "web"

        if "mobile" in text_lower or "app " in text_lower:
            if "web" in obvious.get("application_type", ""):
                obvious["application_type"] = "hybrid"
            else:
                obvious["application_type"] = "mobile"

        return obvious

    async def _identify_redundant_questions(
        self, obvious_answers: Dict[str, Any], analysis: Dict[str, Any]
    ) -> Set[str]:
        """Identifica IDs de perguntas que são redundantes dado o contexto."""
        redundant = set()

        # Mapeamento de respostas óbvias para IDs de perguntas
        question_mappings = {
            "application_type": ["B001", "F001"],  # Se tipo de app é óbvio
            "handles_sensitive_data": ["Q_DADOS_SENSIVEIS", "B008"],  # Se dados sensíveis é óbvio
            "primary_purpose": ["Q_FINALIDADE", "B002"],  # Se finalidade é óbvia
            "target_audience": ["Q_PUBLICO", "B010"],  # Se público é óbvio
            "business_model": ["B010"],  # Se modelo de negócio é óbvio
        }

        # Adicionar perguntas redundantes baseado nas respostas óbvias
        for obvious_key, obvious_value in obvious_answers.items():
            if obvious_key in question_mappings and obvious_value:
                question_ids = question_mappings[obvious_key]
                redundant.update(question_ids)

        # Funcionalidades já mencionadas
        mentioned_features = analysis.get("explicit_info", {}).get("mentioned_features", [])
        if mentioned_features:
            # Se funcionalidades já foram descritas em detalhes
            if len(mentioned_features) >= 3:
                redundant.add("Q_DESC_GERAL")  # Não pedir descrição novamente
                redundant.add("F002")  # Não pedir funcionalidades principais

        # Tecnologias já mencionadas
        mentioned_techs = analysis.get("explicit_info", {}).get("mentioned_technologies", [])
        if mentioned_techs:
            redundant.add("T001")  # Não pedir preferências de tech se já mencionou

        return redundant

    def _suggest_focus_areas(
        self, analysis: Dict[str, Any], obvious_answers: Dict[str, Any]
    ) -> List[str]:
        """Sugere áreas que ainda precisam ser exploradas."""
        focus = []

        missing_info = analysis.get("missing_info", [])
        focus.extend(missing_info)

        # Áreas padrão a focar se não foram cobertas
        standard_areas = [
            "requisitos não-funcionais específicos",
            "integrações necessárias",
            "cronograma e orçamento",
            "equipe e recursos disponíveis",
        ]

        # Adicionar áreas padrão que não estão nas respostas óbvias
        for area in standard_areas:
            area_covered = any(
                area.lower() in str(value).lower()
                for value in obvious_answers.values()
                if isinstance(value, str)
            )
            if not area_covered:
                focus.append(area)

        return focus[:5]  # Limitar a 5 áreas principais

    def _compile_inferred_info(
        self, analysis: Dict[str, Any], domain_insights: Dict[str, Any]
    ) -> List[InferredInformation]:
        """Compila todas as informações inferidas em estruturas padronizadas."""
        inferred = []

        # Informações implícitas
        implicit = analysis.get("implicit_info", {})
        for key, value in implicit.items():
            if value and value != "null":
                inferred.append(
                    InferredInformation(
                        category="implicit",
                        key=key,
                        value=value,
                        confidence=InferenceConfidence.LIKELY,
                        reasoning=f"Inferido pela análise do contexto: {key}",
                        evidence=[],
                    )
                )

        # Características óbvias
        obvious = analysis.get("obvious_characteristics", {})
        for key, value in obvious.items():
            if value and value != "null":
                inferred.append(
                    InferredInformation(
                        category="obvious",
                        key=key,
                        value=value,
                        confidence=InferenceConfidence.CERTAIN,
                        reasoning=f"Óbvio pelo contexto fornecido: {key}",
                        evidence=[],
                    )
                )

        # Assumptions do domínio
        auto_assumptions = domain_insights.get("automatic_assumptions", {})
        for key, value in auto_assumptions.items():
            if value is not None:
                inferred.append(
                    InferredInformation(
                        category="domain_assumption",
                        key=key,
                        value=value,
                        confidence=InferenceConfidence.LIKELY,
                        reasoning="Assumption automática baseada no domínio detectado",
                        evidence=[],
                    )
                )

        return inferred

    def _generate_cache_key(self, intake_text: str) -> str:
        """Gera chave única para cache baseada no texto."""
        import hashlib

        return hashlib.md5(intake_text.encode()).hexdigest()

    def get_exclusion_rules_for_question(self, question_id: str, result: InferenceResult) -> bool:
        """
        Determina se uma pergunta deve ser excluída baseado na inferência.

        Args:
            question_id: ID da pergunta
            result: Resultado da inferência de contexto

        Returns:
            True se a pergunta deve ser excluída (redundante)
        """
        return question_id in result.redundant_question_ids

    def get_context_enhancement(self, result: InferenceResult) -> Dict[str, Any]:
        """
        Retorna informações para enriquecer o contexto de pontuação.

        Returns:
            Dicionário com informações para o ScoringContext
        """
        return {
            "detected_domain": result.detected_domain,
            "domain_confidence": result.domain_confidence,
            "classified_tags": [info.key for info in result.inferred_info],
            "obvious_answers": result.obvious_answers,
            "focus_areas": result.focus_areas,
            "project_complexity": self._infer_complexity(result),
        }

    def _infer_complexity(self, result: InferenceResult) -> str:
        """Infere complexidade do projeto baseado nas informações."""
        complexity_indicators = 0

        # Verificar indicadores de complexidade
        for info in result.inferred_info:
            if info.key in ["implied_data_sensitivity", "requires_high_security"]:
                complexity_indicators += 1
            elif info.key == "implied_compliance_needs" and isinstance(info.value, list):
                complexity_indicators += len(info.value)

        if complexity_indicators >= 3:
            return "high"
        elif complexity_indicators >= 1:
            return "medium"
        else:
            return "low"

    async def explain_inference(self, intake_text: str, result: InferenceResult) -> str:
        """
        Gera explicação detalhada das inferências feitas.

        Returns:
            Explicação em texto natural das inferências
        """
        explanation_parts = []

        if result.detected_domain:
            explanation_parts.append(
                f"🎯 **Domínio detectado**: {result.detected_domain} "
                f"(confiança: {result.domain_confidence:.0%})"
            )

        if result.obvious_answers:
            explanation_parts.append(
                f"✅ **Informações óbvias identificadas**: "
                f"{', '.join(result.obvious_answers.keys())}"
            )

        if result.redundant_question_ids:
            explanation_parts.append(
                f"🚫 **Perguntas redundantes filtradas**: "
                f"{len(result.redundant_question_ids)} perguntas"
            )

        if result.focus_areas:
            explanation_parts.append(
                f"🔍 **Áreas de foco sugeridas**: " f"{', '.join(result.focus_areas[:3])}"
            )

        explanation_parts.append(f"📝 **Resumo**: {result.reasoning_summary}")

        return "\n\n".join(explanation_parts)

    def get_inference_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do motor de inferência."""
        return {
            "total_inferences": len(self.inference_cache),
            "supported_domains": list(self.domain_knowledge.keys()),
            "cache_size": len(self.inference_cache),
            "model_used": self.model,
        }
