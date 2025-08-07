"""
Advanced Validation Engine V2 for Intelligent Intake System.
Implements complex validation rules, business logic validation, and quality assurance.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import yaml

from app.models.intake import Question, IntakeSession, Answer
from app.services.advanced_scoring_engine import QuestionScore, ScoringContext
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class ValidationSeverity(Enum):
    """Severidade da validação."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Categorias de validação."""

    BUSINESS_LOGIC = "business_logic"
    DATA_CONSISTENCY = "data_consistency"
    COMPLETENESS = "completeness"
    DEPENDENCY = "dependency"
    CONSTRAINT = "constraint"
    QUALITY = "quality"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"


@dataclass
class ValidationIssue:
    """Representa um problema de validação encontrado."""

    rule_id: str
    category: ValidationCategory
    severity: ValidationSeverity
    message: str
    question_id: Optional[str] = None
    answer_value: Optional[Any] = None
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ValidationResult:
    """Resultado completo da validação."""

    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    score: float = 1.0  # 0-1, onde 1 é perfeito
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationRule:
    """Regra de validação configurável."""

    rule_id: str
    name: str
    description: str
    category: ValidationCategory
    severity: ValidationSeverity
    enabled: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    custom_logic: Optional[str] = None  # Para regras customizadas em Python


class ValidationEngineV2:
    """
    Motor de validação avançado para sistema de intake inteligente.

    Funcionalidades:
    - Validação de regras de negócio complexas
    - Verificação de consistência de dados
    - Validação de dependências entre perguntas
    - Quality assurance automatizada
    - Sugestões de melhoria
    - Compliance e regulatory validation
    """

    def __init__(
        self,
        rules_config_path: str = "app/data/validation_rules_v2.yaml",
        catalog_path: str = "app/data/question_catalog_v2.yaml",
    ):
        """
        Inicializa o motor de validação.

        Args:
            rules_config_path: Caminho para configuração de regras
            catalog_path: Caminho para catálogo de perguntas
        """
        self.rules_config_path = rules_config_path
        self.catalog_path = catalog_path

        # Carregar configurações
        self.validation_rules: List[ValidationRule] = []
        self.catalog: List[Question] = []
        self.business_rules: Dict[str, Any] = {}
        self.compliance_rules: Dict[str, Any] = {}

        # Cache de validações
        self.validation_cache: Dict[str, ValidationResult] = {}

        # Métricas de performance
        self.validation_stats = {
            "total_validations": 0,
            "cache_hits": 0,
            "avg_validation_time": 0.0,
            "rule_execution_count": {},
        }

        self._load_configurations()
        logger.info("Validation Engine V2 initialized")

    def _load_configurations(self):
        """Carrega configurações de validação e catálogo."""
        try:
            # Carregar regras de validação
            with open(self.rules_config_path, "r", encoding="utf-8") as f:
                rules_data = yaml.safe_load(f)

            self._parse_validation_rules(rules_data)

            # Carregar catálogo de perguntas
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                catalog_data = yaml.safe_load(f)

            self.catalog = []
            for q_data in catalog_data.get("catalog", []):
                question = Question(**q_data)
                self.catalog.append(question)

            # Carregar regras de negócio específicas
            self.business_rules = catalog_data.get("business_rules", {})
            self.compliance_rules = catalog_data.get("compliance_rules", {})

            logger.info(f"Loaded {len(self.validation_rules)} validation rules")
            logger.info(f"Loaded catalog with {len(self.catalog)} questions")

        except Exception as e:
            logger.error(f"Error loading validation configurations: {str(e)}")
            # Carregar regras básicas por fallback
            self._load_fallback_rules()

    def _parse_validation_rules(self, rules_data: Dict[str, Any]):
        """Parseia regras de validação do YAML."""
        rules_list = rules_data.get("validation_rules", [])

        for rule_data in rules_list:
            rule = ValidationRule(
                rule_id=rule_data["rule_id"],
                name=rule_data["name"],
                description=rule_data["description"],
                category=ValidationCategory(rule_data["category"]),
                severity=ValidationSeverity(rule_data["severity"]),
                enabled=rule_data.get("enabled", True),
                conditions=rule_data.get("conditions", {}),
                parameters=rule_data.get("parameters", {}),
                custom_logic=rule_data.get("custom_logic"),
            )
            self.validation_rules.append(rule)

    def _load_fallback_rules(self):
        """Carrega regras básicas de fallback."""
        basic_rules = [
            ValidationRule(
                rule_id="REQUIRED_FIELD_CHECK",
                name="Required Field Validation",
                description="Valida que campos obrigatórios foram preenchidos",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.ERROR,
            ),
            ValidationRule(
                rule_id="DEPENDENCY_CHECK",
                name="Dependency Validation",
                description="Valida dependências entre perguntas",
                category=ValidationCategory.DEPENDENCY,
                severity=ValidationSeverity.WARNING,
            ),
            ValidationRule(
                rule_id="DATA_CONSISTENCY",
                name="Data Consistency Check",
                description="Valida consistência entre respostas relacionadas",
                category=ValidationCategory.DATA_CONSISTENCY,
                severity=ValidationSeverity.WARNING,
            ),
        ]

        self.validation_rules.extend(basic_rules)

    async def validate_intake_session(
        self, session: IntakeSession, scoring_context: Optional[ScoringContext] = None
    ) -> ValidationResult:
        """
        Valida sessão completa de intake.

        Args:
            session: Sessão de intake para validar
            scoring_context: Contexto de pontuação para validações avançadas

        Returns:
            ValidationResult com todos os issues encontrados
        """
        start_time = datetime.utcnow()

        try:
            # Verificar cache
            cache_key = self._generate_cache_key(session)
            if cache_key in self.validation_cache:
                self.validation_stats["cache_hits"] += 1
                return self.validation_cache[cache_key]

            logger.info(f"Validating intake session: {session.id}")

            # Executar validações
            validation_result = ValidationResult(is_valid=True)

            # 1. Validação de completude
            await self._validate_completeness(session, validation_result)

            # 2. Validação de dependências
            await self._validate_dependencies(session, validation_result)

            # 3. Validação de consistência de dados
            await self._validate_data_consistency(session, validation_result)

            # 4. Validação de regras de negócio
            await self._validate_business_rules(session, validation_result, scoring_context)

            # 5. Validação de compliance
            await self._validate_compliance_rules(session, validation_result, scoring_context)

            # 6. Validação de qualidade
            await self._validate_quality_rules(session, validation_result)

            # 7. Validação de performance (constraints)
            await self._validate_performance_constraints(session, validation_result)

            # Calcular score final
            validation_result.score = self._calculate_validation_score(validation_result)

            # Determinar se é válido
            critical_errors = [
                i for i in validation_result.issues if i.severity == ValidationSeverity.CRITICAL
            ]
            errors = [i for i in validation_result.issues if i.severity == ValidationSeverity.ERROR]
            validation_result.is_valid = len(critical_errors) == 0 and len(errors) == 0

            # Separar warnings
            validation_result.warnings = [
                i
                for i in validation_result.issues
                if i.severity in [ValidationSeverity.WARNING, ValidationSeverity.INFO]
            ]

            # Gerar sugestões gerais
            validation_result.suggestions = self._generate_general_suggestions(validation_result)

            # Cache result
            self.validation_cache[cache_key] = validation_result

            # Atualizar métricas
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_validation_stats(execution_time)

            logger.info(
                f"Validation completed: {validation_result.score:.2f} score, {len(validation_result.issues)} issues"
            )

            return validation_result

        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
            return ValidationResult(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        rule_id="VALIDATION_ENGINE_ERROR",
                        category=ValidationCategory.QUALITY,
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Erro interno do motor de validação: {str(e)}",
                    )
                ],
            )

    async def validate_question_selection(
        self,
        selected_questions: List[str],
        all_scores: List[QuestionScore],
        context: ScoringContext,
    ) -> ValidationResult:
        """
        Valida seleção de perguntas baseada em pontuações e contexto.

        Args:
            selected_questions: IDs das perguntas selecionadas
            all_scores: Todas as pontuações calculadas
            context: Contexto de pontuação

        Returns:
            ValidationResult específico para seleção
        """
        try:
            validation_result = ValidationResult(is_valid=True)

            # 1. Validar cobertura de estágios
            await self._validate_stage_coverage(selected_questions, validation_result)

            # 2. Validar diversidade
            await self._validate_question_diversity(selected_questions, validation_result)

            # 3. Validar perguntas obrigatórias
            await self._validate_required_questions(selected_questions, context, validation_result)

            # 4. Validar consistência de pontuação
            await self._validate_scoring_consistency(
                selected_questions, all_scores, validation_result
            )

            # 5. Validar limites de seleção
            await self._validate_selection_limits(selected_questions, validation_result)

            # 6. Validar relevância para contexto
            await self._validate_context_relevance(selected_questions, context, validation_result)

            # Calcular score
            validation_result.score = self._calculate_validation_score(validation_result)
            validation_result.is_valid = (
                len(
                    [
                        i
                        for i in validation_result.issues
                        if i.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]
                    ]
                )
                == 0
            )

            return validation_result

        except Exception as e:
            logger.error(f"Error validating question selection: {str(e)}")
            return ValidationResult(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        rule_id="SELECTION_VALIDATION_ERROR",
                        category=ValidationCategory.QUALITY,
                        severity=ValidationSeverity.ERROR,
                        message=f"Erro na validação de seleção: {str(e)}",
                    )
                ],
            )

    async def _validate_completeness(self, session: IntakeSession, result: ValidationResult):
        """Valida completude da sessão."""
        try:
            # Verificar se texto de intake existe
            if not session.intake_text or len(session.intake_text.strip()) < 10:
                result.issues.append(
                    ValidationIssue(
                        rule_id="INCOMPLETE_INTAKE_TEXT",
                        category=ValidationCategory.COMPLETENESS,
                        severity=ValidationSeverity.ERROR,
                        message="Texto de intake muito curto ou ausente",
                        suggestions=["Forneça uma descrição mais detalhada do projeto"],
                    )
                )

            # Verificar perguntas obrigatórias respondidas
            required_questions = [q for q in self.catalog if getattr(q, "required", False)]
            required_ids = {q.id for q in required_questions}
            answered_ids = {answer.question_id for answer in session.answers}

            missing_required = required_ids - answered_ids

            if missing_required:
                for q_id in missing_required:
                    question = next((q for q in self.catalog if q.id == q_id), None)
                    result.issues.append(
                        ValidationIssue(
                            rule_id="MISSING_REQUIRED_QUESTION",
                            category=ValidationCategory.COMPLETENESS,
                            severity=ValidationSeverity.ERROR,
                            message=f"Pergunta obrigatória não respondida: {question.text if question else q_id}",
                            question_id=q_id,
                            suggestions=[
                                "Complete todas as perguntas obrigatórias antes de prosseguir"
                            ],
                        )
                    )

            # Verificar respostas vazias
            for answer in session.answers:
                if not self._is_valid_answer_value(answer.value):
                    question = next((q for q in self.catalog if q.id == answer.question_id), None)
                    result.issues.append(
                        ValidationIssue(
                            rule_id="EMPTY_ANSWER",
                            category=ValidationCategory.COMPLETENESS,
                            severity=ValidationSeverity.WARNING,
                            message=f"Resposta vazia ou inválida para: {question.text if question else answer.question_id}",
                            question_id=answer.question_id,
                            answer_value=answer.value,
                        )
                    )

        except Exception as e:
            logger.error(f"Error in completeness validation: {str(e)}")

    async def _validate_dependencies(self, session: IntakeSession, result: ValidationResult):
        """Valida dependências entre perguntas."""
        try:
            answered_questions = {answer.question_id: answer.value for answer in session.answers}

            for question in self.catalog:
                if not question.condition or question.id not in answered_questions:
                    continue

                # Verificar se condição foi atendida para pergunta respondida
                condition_met = self._evaluate_question_condition(
                    question.condition, answered_questions
                )

                if not condition_met:
                    result.issues.append(
                        ValidationIssue(
                            rule_id="DEPENDENCY_VIOLATION",
                            category=ValidationCategory.DEPENDENCY,
                            severity=ValidationSeverity.WARNING,
                            message=f"Pergunta {question.id} foi respondida mas sua condição não foi atendida",
                            question_id=question.id,
                            metadata={
                                "condition": question.condition.__dict__
                                if question.condition
                                else None
                            },
                        )
                    )

            # Verificar dependências reversas - perguntas que deveriam ter sido apresentadas
            for question in self.catalog:
                if question.condition and question.id not in answered_questions:
                    condition_met = self._evaluate_question_condition(
                        question.condition, answered_questions
                    )

                    if condition_met and getattr(question, "required", False):
                        result.issues.append(
                            ValidationIssue(
                                rule_id="MISSING_DEPENDENT_QUESTION",
                                category=ValidationCategory.DEPENDENCY,
                                severity=ValidationSeverity.ERROR,
                                message=f"Pergunta dependente obrigatória não foi apresentada: {question.text}",
                                question_id=question.id,
                                suggestions=[
                                    f"Incluir pergunta {question.id} baseada nas respostas fornecidas"
                                ],
                            )
                        )

        except Exception as e:
            logger.error(f"Error in dependency validation: {str(e)}")

    async def _validate_data_consistency(self, session: IntakeSession, result: ValidationResult):
        """Valida consistência entre respostas relacionadas."""
        try:
            answers_dict = {answer.question_id: answer.value for answer in session.answers}

            # Regra: Orçamento vs Cronograma
            budget_q = answers_dict.get("B004")  # Orçamento
            timeline_q = answers_dict.get("B005")  # Cronograma

            if budget_q and timeline_q:
                if self._is_inconsistent_budget_timeline(budget_q, timeline_q):
                    result.issues.append(
                        ValidationIssue(
                            rule_id="BUDGET_TIMELINE_INCONSISTENCY",
                            category=ValidationCategory.DATA_CONSISTENCY,
                            severity=ValidationSeverity.WARNING,
                            message="Orçamento e cronograma podem estar inconsistentes",
                            suggestions=[
                                "Revisar se o orçamento é adequado para o cronograma proposto"
                            ],
                        )
                    )

            # Regra: Número de usuários vs Performance Requirements
            users_q = answers_dict.get("B009")  # Número de usuários
            performance_q = answers_dict.get("N001")  # Performance

            if users_q and performance_q:
                if self._is_inconsistent_users_performance(users_q, performance_q):
                    result.issues.append(
                        ValidationIssue(
                            rule_id="USERS_PERFORMANCE_INCONSISTENCY",
                            category=ValidationCategory.DATA_CONSISTENCY,
                            severity=ValidationSeverity.WARNING,
                            message="Número de usuários e requisitos de performance podem estar inconsistentes",
                            suggestions=[
                                "Considerar requisitos de performance mais rigorosos para alta carga de usuários"
                            ],
                        )
                    )

            # Regra: Compliance vs Industry
            compliance_q = answers_dict.get("B008")  # Compliance
            industry_q = answers_dict.get("B003")  # Setor

            if compliance_q and industry_q:
                missing_compliance = self._check_missing_industry_compliance(
                    industry_q, compliance_q
                )
                if missing_compliance:
                    result.issues.append(
                        ValidationIssue(
                            rule_id="MISSING_INDUSTRY_COMPLIANCE",
                            category=ValidationCategory.COMPLIANCE,
                            severity=ValidationSeverity.WARNING,
                            message=f"Compliance obrigatório para o setor pode estar faltando: {', '.join(missing_compliance)}",
                            suggestions=[f"Considerar adicionar: {', '.join(missing_compliance)}"],
                        )
                    )

        except Exception as e:
            logger.error(f"Error in data consistency validation: {str(e)}")

    async def _validate_business_rules(
        self, session: IntakeSession, result: ValidationResult, context: Optional[ScoringContext]
    ):
        """Valida regras específicas de negócio."""
        try:
            answers_dict = {answer.question_id: answer.value for answer in session.answers}

            # Regra de negócio: Projetos críticos precisam de alta disponibilidade
            criticality = answers_dict.get("B020")  # Criticidade do sistema
            availability = answers_dict.get("N002")  # Disponibilidade

            if criticality == "mission_critical" and availability:
                if availability in ["two_nines", "best_effort", "maintenance_ok"]:
                    result.issues.append(
                        ValidationIssue(
                            rule_id="CRITICAL_SYSTEM_LOW_AVAILABILITY",
                            category=ValidationCategory.BUSINESS_LOGIC,
                            severity=ValidationSeverity.ERROR,
                            message="Sistemas críticos precisam de alta disponibilidade (99.9% ou superior)",
                            suggestions=[
                                "Revisar requisitos de disponibilidade para sistemas críticos"
                            ],
                        )
                    )

            # Regra de negócio: E-commerce precisa de integração de pagamento
            project_type = answers_dict.get("F001")  # Tipo de aplicação
            integrations = answers_dict.get("B012", [])  # Integrações

            if project_type == "ecommerce" and isinstance(integrations, list):
                if "payment" not in integrations:
                    result.issues.append(
                        ValidationIssue(
                            rule_id="ECOMMERCE_MISSING_PAYMENT",
                            category=ValidationCategory.BUSINESS_LOGIC,
                            severity=ValidationSeverity.WARNING,
                            message="Plataformas de e-commerce geralmente precisam de integração com gateway de pagamento",
                            suggestions=[
                                "Considerar adicionar integração com gateway de pagamento"
                            ],
                        )
                    )

            # Regra de negócio: Sistemas com muitos usuários precisam de monitoramento
            user_count = answers_dict.get("B009")  # Número de usuários

            if user_count and user_count in ["50k_100k", "over_100k"]:
                # Verificar se há perguntas sobre monitoramento
                monitoring_mentioned = any(
                    "monitor" in str(answer.value).lower()
                    or "observab" in str(answer.value).lower()
                    for answer in session.answers
                )

                if not monitoring_mentioned:
                    result.issues.append(
                        ValidationIssue(
                            rule_id="HIGH_SCALE_MISSING_MONITORING",
                            category=ValidationCategory.BUSINESS_LOGIC,
                            severity=ValidationSeverity.WARNING,
                            message="Sistemas de alta escala precisam de estratégia de monitoramento",
                            suggestions=["Incluir requisitos de monitoramento e observabilidade"],
                        )
                    )

        except Exception as e:
            logger.error(f"Error in business rules validation: {str(e)}")

    async def _validate_compliance_rules(
        self, session: IntakeSession, result: ValidationResult, context: Optional[ScoringContext]
    ):
        """Valida regras de compliance e regulamentações."""
        try:
            answers_dict = {answer.question_id: answer.value for answer in session.answers}

            # LGPD: Verificar se sistemas com dados pessoais têm LGPD
            industry = answers_dict.get("B003")  # Setor
            compliance = answers_dict.get("B008", [])  # Compliance

            if isinstance(compliance, list):
                # Setores que obrigatoriamente precisam de LGPD
                lgpd_required_industries = ["healthcare", "finance", "education"]

                if industry in lgpd_required_industries and "lgpd" not in compliance:
                    result.issues.append(
                        ValidationIssue(
                            rule_id="MISSING_LGPD_COMPLIANCE",
                            category=ValidationCategory.COMPLIANCE,
                            severity=ValidationSeverity.ERROR,
                            message=f"Setor {industry} obrigatoriamente precisa de compliance LGPD",
                            suggestions=["Adicionar LGPD aos requisitos de compliance"],
                        )
                    )

                # PCI-DSS para sistemas com pagamento
                payment_integration = answers_dict.get("B012", [])
                if isinstance(payment_integration, list) and "payment" in payment_integration:
                    if "pci_dss" not in compliance:
                        result.issues.append(
                            ValidationIssue(
                                rule_id="MISSING_PCI_DSS_COMPLIANCE",
                                category=ValidationCategory.COMPLIANCE,
                                severity=ValidationSeverity.ERROR,
                                message="Sistemas com processamento de pagamentos precisam de compliance PCI-DSS",
                                suggestions=["Adicionar PCI-DSS aos requisitos de compliance"],
                            )
                        )

                # HIPAA para healthcare
                if industry == "healthcare" and "hipaa" not in compliance:
                    result.issues.append(
                        ValidationIssue(
                            rule_id="MISSING_HIPAA_COMPLIANCE",
                            category=ValidationCategory.COMPLIANCE,
                            severity=ValidationSeverity.ERROR,
                            message="Sistemas de saúde precisam de compliance HIPAA",
                            suggestions=["Adicionar HIPAA aos requisitos de compliance"],
                        )
                    )

        except Exception as e:
            logger.error(f"Error in compliance validation: {str(e)}")

    async def _validate_quality_rules(self, session: IntakeSession, result: ValidationResult):
        """Valida regras de qualidade das respostas."""
        try:
            # Verificar qualidade do texto de intake
            intake_quality = self._assess_intake_text_quality(session.intake_text)

            if intake_quality < 0.5:
                result.issues.append(
                    ValidationIssue(
                        rule_id="LOW_INTAKE_QUALITY",
                        category=ValidationCategory.QUALITY,
                        severity=ValidationSeverity.WARNING,
                        message="Texto de intake pode ser mais detalhado e específico",
                        suggestions=[
                            "Incluir mais detalhes sobre objetivos do projeto",
                            "Especificar funcionalidades desejadas",
                            "Mencionar tecnologias ou restrições conhecidas",
                        ],
                    )
                )

            # Verificar consistência nas respostas
            answer_consistency = self._assess_answer_consistency(session.answers)

            if answer_consistency < 0.7:
                result.issues.append(
                    ValidationIssue(
                        rule_id="INCONSISTENT_ANSWERS",
                        category=ValidationCategory.QUALITY,
                        severity=ValidationSeverity.INFO,
                        message="Algumas respostas podem ser inconsistentes entre si",
                        suggestions=["Revisar respostas para garantir consistência"],
                    )
                )

        except Exception as e:
            logger.error(f"Error in quality validation: {str(e)}")

    async def _validate_performance_constraints(
        self, session: IntakeSession, result: ValidationResult
    ):
        """Valida constraints de performance e viabilidade."""
        try:
            answers_dict = {answer.question_id: answer.value for answer in session.answers}

            # Verificar se número de perguntas está dentro do limite
            if len(session.answers) > 15:
                result.issues.append(
                    ValidationIssue(
                        rule_id="TOO_MANY_QUESTIONS",
                        category=ValidationCategory.PERFORMANCE,
                        severity=ValidationSeverity.WARNING,
                        message=f"Número de perguntas ({len(session.answers)}) pode ser muito alto para boa UX",
                        suggestions=[
                            "Considerar reduzir número de perguntas para melhorar experiência"
                        ],
                    )
                )

            # Verificar complexidade vs orçamento
            budget = answers_dict.get("B004")
            complexity_indicators = 0

            # Contar indicadores de complexidade
            if answers_dict.get("B011") == "multiple":  # Múltiplos sistemas
                complexity_indicators += 1

            if (
                answers_dict.get("B008") and len(answers_dict.get("B008", [])) > 2
            ):  # Muito compliance
                complexity_indicators += 1

            if answers_dict.get("B009") in ["50k_100k", "over_100k"]:  # Muitos usuários
                complexity_indicators += 1

            if answers_dict.get("N002") in ["five_nines", "four_nines"]:  # Alta disponibilidade
                complexity_indicators += 1

            # Verificar se orçamento é compatível com complexidade
            if budget and complexity_indicators >= 3:
                low_budget_ranges = ["under_50k", "50k_200k"]
                if budget in low_budget_ranges:
                    result.issues.append(
                        ValidationIssue(
                            rule_id="BUDGET_COMPLEXITY_MISMATCH",
                            category=ValidationCategory.CONSTRAINT,
                            severity=ValidationSeverity.WARNING,
                            message="Orçamento pode ser insuficiente para a complexidade do projeto",
                            suggestions=[
                                "Considerar aumentar orçamento",
                                "Reduzir escopo para adequar ao orçamento",
                                "Implementar projeto em fases",
                            ],
                        )
                    )

        except Exception as e:
            logger.error(f"Error in performance constraints validation: {str(e)}")

    async def _validate_stage_coverage(
        self, selected_questions: List[str], result: ValidationResult
    ):
        """Valida cobertura adequada de estágios."""
        try:
            # Contar perguntas por estágio
            stage_counts = {}
            for q_id in selected_questions:
                question = next((q for q in self.catalog if q.id == q_id), None)
                if question:
                    stage = question.stage
                    stage_counts[stage] = stage_counts.get(stage, 0) + 1

            # Verificar cobertura mínima
            required_stages = ["business", "functional", "technical", "nfr"]
            missing_stages = []

            for stage in required_stages:
                if stage_counts.get(stage, 0) == 0:
                    missing_stages.append(stage)

            if missing_stages:
                result.issues.append(
                    ValidationIssue(
                        rule_id="INCOMPLETE_STAGE_COVERAGE",
                        category=ValidationCategory.COMPLETENESS,
                        severity=ValidationSeverity.WARNING,
                        message=f"Estágios sem cobertura: {', '.join(missing_stages)}",
                        suggestions=[
                            f"Incluir pelo menos uma pergunta de cada estágio: {', '.join(missing_stages)}"
                        ],
                    )
                )

            # Verificar distribuição balanceada
            total_questions = len(selected_questions)
            for stage, count in stage_counts.items():
                percentage = (count / total_questions) * 100

                if percentage > 60:  # Muito concentrado em um estágio
                    result.issues.append(
                        ValidationIssue(
                            rule_id="UNBALANCED_STAGE_DISTRIBUTION",
                            category=ValidationCategory.QUALITY,
                            severity=ValidationSeverity.INFO,
                            message=f"Muitas perguntas concentradas no estágio {stage} ({percentage:.1f}%)",
                            suggestions=[
                                "Considerar distribuir perguntas mais uniformemente entre estágios"
                            ],
                        )
                    )

        except Exception as e:
            logger.error(f"Error in stage coverage validation: {str(e)}")

    async def _validate_question_diversity(
        self, selected_questions: List[str], result: ValidationResult
    ):
        """Valida diversidade das perguntas selecionadas."""
        try:
            # Verificar tipos de pergunta
            question_types = {}
            for q_id in selected_questions:
                question = next((q for q in self.catalog if q.id == q_id), None)
                if question:
                    q_type = question.type
                    question_types[q_type] = question_types.get(q_type, 0) + 1

            # Alertar se muito concentrado em um tipo
            total = len(selected_questions)
            for q_type, count in question_types.items():
                if (count / total) > 0.8:  # Mais de 80% de um tipo
                    result.issues.append(
                        ValidationIssue(
                            rule_id="LOW_QUESTION_TYPE_DIVERSITY",
                            category=ValidationCategory.QUALITY,
                            severity=ValidationSeverity.INFO,
                            message=f"Muitas perguntas do tipo {q_type} ({count}/{total})",
                            suggestions=[
                                "Incluir variedade de tipos de pergunta para melhor cobertura"
                            ],
                        )
                    )

        except Exception as e:
            logger.error(f"Error in diversity validation: {str(e)}")

    async def _validate_required_questions(
        self, selected_questions: List[str], context: ScoringContext, result: ValidationResult
    ):
        """Valida se perguntas obrigatórias foram incluídas."""
        try:
            required_questions = [q for q in self.catalog if getattr(q, "required", False)]
            required_ids = {q.id for q in required_questions}
            selected_ids = set(selected_questions)

            missing_required = required_ids - selected_ids

            if missing_required:
                for q_id in missing_required:
                    question = next((q for q in self.catalog if q.id == q_id), None)
                    result.issues.append(
                        ValidationIssue(
                            rule_id="MISSING_REQUIRED_IN_SELECTION",
                            category=ValidationCategory.COMPLETENESS,
                            severity=ValidationSeverity.ERROR,
                            message=f"Pergunta obrigatória não selecionada: {question.text if question else q_id}",
                            question_id=q_id,
                            suggestions=["Incluir todas as perguntas obrigatórias na seleção"],
                        )
                    )

        except Exception as e:
            logger.error(f"Error in required questions validation: {str(e)}")

    async def _validate_scoring_consistency(
        self,
        selected_questions: List[str],
        all_scores: List[QuestionScore],
        result: ValidationResult,
    ):
        """Valida consistência das pontuações na seleção."""
        try:
            if not all_scores:
                return

            # Verificar se perguntas de alta pontuação foram selecionadas
            sorted_scores = sorted(all_scores, key=lambda x: x.total_score, reverse=True)
            top_scored = [s.question_id for s in sorted_scores[: len(selected_questions) + 5]]
            selected_set = set(selected_questions)

            # Contar quantas das top-scored estão selecionadas
            top_selected_count = len(selected_set.intersection(set(top_scored[:10])))

            if top_selected_count < len(selected_questions) * 0.6:  # Menos de 60% das top
                result.issues.append(
                    ValidationIssue(
                        rule_id="LOW_SCORING_CONSISTENCY",
                        category=ValidationCategory.QUALITY,
                        severity=ValidationSeverity.INFO,
                        message="Seleção pode não estar priorizando perguntas de maior pontuação",
                        suggestions=["Revisar algoritmo de seleção para melhor usar pontuações"],
                    )
                )

        except Exception as e:
            logger.error(f"Error in scoring consistency validation: {str(e)}")

    async def _validate_selection_limits(
        self, selected_questions: List[str], result: ValidationResult
    ):
        """Valida se seleção respeita limites configurados."""
        try:
            # Limite máximo de perguntas (configurável via YAML)
            max_questions = 15  # Default, deveria vir da configuração

            if len(selected_questions) > max_questions:
                result.issues.append(
                    ValidationIssue(
                        rule_id="EXCEEDED_QUESTION_LIMIT",
                        category=ValidationCategory.CONSTRAINT,
                        severity=ValidationSeverity.ERROR,
                        message=f"Número de perguntas ({len(selected_questions)}) excede limite máximo ({max_questions})",
                        suggestions=[f"Reduzir seleção para no máximo {max_questions} perguntas"],
                    )
                )

            # Limite mínimo
            min_questions = 5

            if len(selected_questions) < min_questions:
                result.issues.append(
                    ValidationIssue(
                        rule_id="INSUFFICIENT_QUESTIONS",
                        category=ValidationCategory.COMPLETENESS,
                        severity=ValidationSeverity.WARNING,
                        message=f"Poucas perguntas selecionadas ({len(selected_questions)}), mínimo recomendado: {min_questions}",
                        suggestions=[
                            f"Selecionar pelo menos {min_questions} perguntas para cobertura adequada"
                        ],
                    )
                )

        except Exception as e:
            logger.error(f"Error in selection limits validation: {str(e)}")

    async def _validate_context_relevance(
        self, selected_questions: List[str], context: ScoringContext, result: ValidationResult
    ):
        """Valida relevância das perguntas para o contexto."""
        try:
            # Verificar se perguntas específicas da indústria foram incluídas
            if context.detected_industry:
                industry_relevant_questions = []
                for q_id in selected_questions:
                    question = next((q for q in self.catalog if q.id == q_id), None)
                    if question and self._is_industry_relevant(question, context.detected_industry):
                        industry_relevant_questions.append(q_id)

                if len(industry_relevant_questions) == 0:
                    result.issues.append(
                        ValidationIssue(
                            rule_id="MISSING_INDUSTRY_SPECIFIC_QUESTIONS",
                            category=ValidationCategory.QUALITY,
                            severity=ValidationSeverity.INFO,
                            message=f"Nenhuma pergunta específica para indústria {context.detected_industry}",
                            suggestions=["Incluir perguntas relevantes para o setor identificado"],
                        )
                    )

            # Verificar compliance relevance
            if context.compliance_requirements:
                compliance_questions = 0
                for q_id in selected_questions:
                    question = next((q for q in self.catalog if q.id == q_id), None)
                    if question and any(
                        "compliance" in tag or "security" in tag for tag in question.tags
                    ):
                        compliance_questions += 1

                if compliance_questions == 0:
                    result.issues.append(
                        ValidationIssue(
                            rule_id="MISSING_COMPLIANCE_QUESTIONS",
                            category=ValidationCategory.COMPLIANCE,
                            severity=ValidationSeverity.WARNING,
                            message="Requisitos de compliance identificados mas sem perguntas específicas",
                            suggestions=["Incluir perguntas sobre compliance e segurança"],
                        )
                    )

        except Exception as e:
            logger.error(f"Error in context relevance validation: {str(e)}")

    def _generate_cache_key(self, session: IntakeSession) -> str:
        """Gera chave única para cache de validação."""
        # Usar hash do conteúdo para cache
        content = f"{session.id}_{session.status}_{len(session.answers)}"
        for answer in session.answers:
            content += f"_{answer.question_id}_{str(answer.value)}"

        import hashlib
        return hashlib.md5(content.encode()).hexdigest()

    def _calculate_validation_score(self, result: ValidationResult) -> float:
        """Calcula score de validação baseado nos issues."""
        if not result.issues:
            return 1.0

        # Penalizações por severidade
        penalties = {
            ValidationSeverity.INFO: 0.02,
            ValidationSeverity.WARNING: 0.05,
            ValidationSeverity.ERROR: 0.15,
            ValidationSeverity.CRITICAL: 0.40,
        }

        total_penalty = 0.0
        for issue in result.issues:
            total_penalty += penalties.get(issue.severity, 0.10)

        # Score = 1.0 - penalizações (mínimo 0.0)
        return max(0.0, 1.0 - total_penalty)

    def _generate_general_suggestions(self, result: ValidationResult) -> List[str]:
        """Gera sugestões gerais baseadas nos issues encontrados."""
        suggestions = []

        # Sugestões baseadas em categorias de issues
        categories = {issue.category for issue in result.issues}

        if ValidationCategory.COMPLETENESS in categories:
            suggestions.append("Complete todas as informações obrigatórias")

        if ValidationCategory.COMPLIANCE in categories:
            suggestions.append("Revisar requisitos de compliance e regulamentações")

        if ValidationCategory.DATA_CONSISTENCY in categories:
            suggestions.append("Verificar consistência entre respostas relacionadas")

        if ValidationCategory.BUSINESS_LOGIC in categories:
            suggestions.append("Alinhar requisitos técnicos com objetivos de negócio")

        return suggestions

    def _is_valid_answer_value(self, value: Any) -> bool:
        """Verifica se valor da resposta é válido."""
        if value is None:
            return False

        if isinstance(value, str):
            return len(value.strip()) > 0

        if isinstance(value, list):
            return len(value) > 0 and all(self._is_valid_answer_value(item) for item in value)

        return True

    def _evaluate_question_condition(self, condition, answers_dict: Dict[str, Any]) -> bool:
        """Avalia condição de pergunta."""
        try:
            if not condition or not hasattr(condition, "all"):
                return True

            # Implementação simplificada - expandir conforme necessário
            for rule in condition.all:
                question_id = rule.get("q")
                operator = rule.get("op")
                expected_values = rule.get("v", [])

                if question_id not in answers_dict:
                    return False

                actual_value = answers_dict[question_id]

                if operator == "in":
                    if actual_value not in expected_values:
                        return False
                elif operator == "eq":
                    if actual_value != expected_values[0] if expected_values else None:
                        return False
                elif operator == "contains":
                    if isinstance(actual_value, list):
                        if not any(v in actual_value for v in expected_values):
                            return False
                    else:
                        if expected_values[0] not in str(actual_value):
                            return False

            return True

        except Exception as e:
            logger.error(f"Error evaluating condition: {str(e)}")
            return True  # Default to true on error

    def _is_inconsistent_budget_timeline(self, budget: str, timeline: str) -> bool:
        """Verifica inconsistência entre orçamento e cronograma."""
        # Lógica simplificada - expandir conforme necessário
        high_budget = budget in ["1m_5m", "over_5m"]
        short_timeline = timeline in ["under_3m", "3_6m"]

        low_budget = budget in ["under_50k", "50k_200k"]
        long_timeline = timeline in ["18_24m", "over_24m"]

        return (high_budget and short_timeline) or (low_budget and long_timeline)

    def _is_inconsistent_users_performance(self, users: str, performance: str) -> bool:
        """Verifica inconsistência entre usuários e performance."""
        high_users = users in ["50k_100k", "over_100k"]
        low_performance = performance in ["best_effort", "batch_ok", "standard"]

        return high_users and low_performance

    def _check_missing_industry_compliance(self, industry: str, compliance: List[str]) -> List[str]:
        """Verifica compliance obrigatório faltante por setor."""
        industry_compliance = {
            "healthcare": ["lgpd", "hipaa"],
            "finance": ["lgpd", "sox", "pci_dss"],
            "ecommerce": ["lgpd", "pci_dss"],
            "education": ["lgpd"],
            "government": ["lgpd"],
        }

        required = industry_compliance.get(industry, [])
        return [req for req in required if req not in compliance]

    def _assess_intake_text_quality(self, text: str) -> float:
        """Avalia qualidade do texto de intake."""
        if not text:
            return 0.0

        score = 0.0

        # Comprimento adequado
        if len(text) > 50:
            score += 0.3
        if len(text) > 200:
            score += 0.2

        # Palavras-chave técnicas
        technical_keywords = [
            "sistema",
            "aplicação",
            "plataforma",
            "integração",
            "api",
            "banco",
            "usuário",
        ]
        found_keywords = sum(1 for kw in technical_keywords if kw in text.lower())
        score += min(0.3, found_keywords * 0.1)

        # Objetivos mencionados
        objective_keywords = ["objetivo", "meta", "problema", "solução", "necessidade"]
        found_objectives = sum(1 for kw in objective_keywords if kw in text.lower())
        score += min(0.2, found_objectives * 0.1)

        return min(1.0, score)

    def _assess_answer_consistency(self, answers: List[Answer]) -> float:
        """Avalia consistência entre respostas."""
        if len(answers) < 2:
            return 1.0

        # Implementação básica - expandir conforme necessário
        return 0.8  # Placeholder

    def _is_industry_relevant(self, question: Question, industry: str) -> bool:
        """Verifica se pergunta é relevante para indústria."""
        industry_keywords = {
            "healthcare": ["saúde", "paciente", "hipaa", "médico"],
            "finance": ["financeiro", "pagamento", "sox", "pci"],
            "ecommerce": ["produto", "carrinho", "checkout", "e-commerce"],
        }

        keywords = industry_keywords.get(industry, [])
        question_text = question.text.lower()

        return any(keyword in question_text for keyword in keywords)

    def _update_validation_stats(self, execution_time: float):
        """Atualiza estatísticas de validação."""
        self.validation_stats["total_validations"] += 1

        # Média móvel do tempo de execução
        current_avg = self.validation_stats["avg_validation_time"]
        total = self.validation_stats["total_validations"]

        self.validation_stats["avg_validation_time"] = (
            current_avg * (total - 1) + execution_time
        ) / total

    def get_validation_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do motor de validação."""
        return {
            **self.validation_stats,
            "active_rules": len([r for r in self.validation_rules if r.enabled]),
            "cache_size": len(self.validation_cache),
            "catalog_size": len(self.catalog),
        }

    def get_validation_rules_info(self) -> Dict[str, Any]:
        """Retorna informações sobre regras de validação."""
        rules_by_category = {}
        rules_by_severity = {}

        for rule in self.validation_rules:
            # Por categoria
            category = rule.category.value
            if category not in rules_by_category:
                rules_by_category[category] = []
            rules_by_category[category].append(
                {"rule_id": rule.rule_id, "name": rule.name, "enabled": rule.enabled}
            )

            # Por severidade
            severity = rule.severity.value
            rules_by_severity[severity] = rules_by_severity.get(severity, 0) + 1

        return {
            "total_rules": len(self.validation_rules),
            "enabled_rules": len([r for r in self.validation_rules if r.enabled]),
            "rules_by_category": rules_by_category,
            "rules_by_severity": rules_by_severity,
        }
