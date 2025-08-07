from typing import Dict, List, Any, Optional
import logging
from app.models.base import DiscoveryStage, ValidationResult, StageChecklist
from app.models.discovery import Requirements

logger = logging.getLogger(__name__)


class ValidationEngine:
    """
    Engine de validação que verifica a completude de cada estágio
    através de checklists específicos e regras de negócio.
    """

    def __init__(self):
        self._stage_checklists = self._initialize_checklists()

    def _initialize_checklists(self) -> Dict[DiscoveryStage, StageChecklist]:
        """Inicializa os checklists para cada estágio."""
        return {
            DiscoveryStage.BUSINESS_CONTEXT: StageChecklist(
                stage=DiscoveryStage.BUSINESS_CONTEXT,
                required_items=["tipo_aplicativo", "nome_projeto", "descricao_basica"],
                optional_items=[
                    "stack_tecnologico",
                    "identidade_visual",
                    "tipo_notificacoes",
                    "preferencias_design",
                ],
                validation_rules={
                    "tipo_aplicativo": "Deve especificar se é web, mobile ou desktop",
                    "nome_projeto": "Deve ter um nome para o projeto",
                    "descricao_basica": "Deve ter uma descrição básica do que faz",
                },
                minimum_completeness=0.8,
            ),
            DiscoveryStage.USERS_AND_JOURNEYS: StageChecklist(
                stage=DiscoveryStage.USERS_AND_JOURNEYS,
                required_items=["perfis", "jornadas_criticas", "acessibilidade", "idiomas"],
                optional_items=["preferencias_ux"],
                validation_rules={
                    "perfis": "Deve conter pelo menos 2 perfis de usuário detalhados",
                    "jornadas_criticas": "Deve mapear pelo menos 3 jornadas críticas",
                    "acessibilidade": "Deve especificar requisitos de acessibilidade",
                    "idiomas": "Deve definir idiomas suportados",
                },
                minimum_completeness=0.8,
            ),
            DiscoveryStage.FUNCTIONAL_SCOPE: StageChecklist(
                stage=DiscoveryStage.FUNCTIONAL_SCOPE,
                required_items=["features_must", "features_should", "integracoes"],
                optional_items=["webhooks", "apis_externas"],
                validation_rules={
                    "features_must": "Deve conter pelo menos 5 features obrigatórias",
                    "features_should": "Deve conter pelo menos 3 features desejáveis",
                    "integracoes": "Deve especificar integrações necessárias",
                },
                minimum_completeness=0.8,
            ),
            DiscoveryStage.CONSTRAINTS_POLICIES: StageChecklist(
                stage=DiscoveryStage.CONSTRAINTS_POLICIES,
                required_items=["lgpd_pii", "seguranca", "auditoria"],
                optional_items=["compliance", "restricoes_legais"],
                validation_rules={
                    "lgpd_pii": "Deve especificar tratamento de dados pessoais",
                    "seguranca": "Deve definir requisitos de segurança mínimos",
                    "auditoria": "Deve especificar requisitos de auditoria",
                },
                minimum_completeness=0.8,
            ),
            DiscoveryStage.NON_FUNCTIONAL: StageChecklist(
                stage=DiscoveryStage.NON_FUNCTIONAL,
                required_items=["slos", "disponibilidade", "custo_alvo"],
                optional_items=["escalabilidade", "performance_requirements"],
                validation_rules={
                    "slos": "Deve definir SLOs para latência e throughput",
                    "disponibilidade": "Deve especificar uptime desejado",
                    "custo_alvo": "Deve definir orçamento aproximado",
                },
                minimum_completeness=0.8,
            ),
            DiscoveryStage.TECH_PREFERENCES: StageChecklist(
                stage=DiscoveryStage.TECH_PREFERENCES,
                required_items=["stacks_permitidas", "stacks_vedadas"],
                optional_items=["legado", "infraestrutura_preferida", "restricoes_tecnicas"],
                validation_rules={
                    "stacks_permitidas": "Deve especificar tecnologias aprovadas",
                    "stacks_vedadas": "Deve especificar tecnologias proibidas",
                },
                minimum_completeness=0.8,
            ),
            DiscoveryStage.DELIVERY_BUDGET: StageChecklist(
                stage=DiscoveryStage.DELIVERY_BUDGET,
                required_items=["marcos", "prazos", "budget", "governanca"],
                optional_items=["recursos_disponiveis"],
                validation_rules={
                    "marcos": "Deve definir pelo menos 3 marcos principais",
                    "prazos": "Deve especificar cronograma macro",
                    "budget": "Deve definir orçamento disponível",
                    "governanca": "Deve especificar processo de aprovação",
                },
                minimum_completeness=0.8,
            ),
            DiscoveryStage.REVIEW_GAPS: StageChecklist(
                stage=DiscoveryStage.REVIEW_GAPS,
                required_items=["lacunas_identificadas", "trade_offs", "decisoes_pendentes"],
                optional_items=["riscos_aceitos", "confirmacoes_necessarias"],
                validation_rules={
                    "lacunas_identificadas": "Deve listar lacunas encontradas",
                    "trade_offs": "Deve documentar decisões de trade-off",
                    "decisoes_pendentes": "Deve listar decisões em aberto",
                },
                minimum_completeness=0.8,
            ),
            DiscoveryStage.FINALIZE_DOCS: StageChecklist(
                stage=DiscoveryStage.FINALIZE_DOCS,
                required_items=["all_stages_complete"],
                validation_rules={
                    "all_stages_complete": "Todos os estágios anteriores devem estar completos"
                },
                minimum_completeness=1.0,
            ),
        }

    def validate_stage(self, stage: DiscoveryStage, requirements: Requirements) -> ValidationResult:
        """
        Valida um estágio específico baseado no checklist e dados coletados.

        Args:
            stage: Estágio a ser validado
            requirements: Dados coletados até agora

        Returns:
            ValidationResult com detalhes da validação
        """
        checklist = self._stage_checklists.get(stage)
        if not checklist:
            logger.error(f"Checklist não encontrado para estágio: {stage}")
            return ValidationResult(
                is_complete=False,
                completeness_score=0.0,
                missing_items=[f"Checklist não configurado para {stage}"],
                suggestions=["Configurar checklist para este estágio"],
            )

        stage_data = requirements.get_stage_data(stage)
        if not stage_data:
            return ValidationResult(
                is_complete=False,
                completeness_score=0.0,
                missing_items=checklist.required_items,
                suggestions=["Nenhum dado coletado para este estágio"],
            )

        # Validar items obrigatórios
        validated_items = []
        missing_items = []
        suggestions = []

        stage_dict = stage_data.dict()

        for item in checklist.required_items:
            validation_result = self._validate_item(
                item, stage_dict.get(item), checklist.validation_rules.get(item)
            )

            if validation_result["is_valid"]:
                validated_items.append(item)
            else:
                missing_items.append(item)
                if validation_result["suggestion"]:
                    suggestions.append(validation_result["suggestion"])

        # Calcular score de completude
        total_required = len(checklist.required_items)
        completed_required = len(validated_items)

        if total_required > 0:
            completeness_score = completed_required / total_required
        else:
            completeness_score = 1.0

        # Verificar se atende o mínimo necessário
        is_complete = completeness_score >= checklist.minimum_completeness

        # Validação especial para FINALIZE_DOCS
        if stage == DiscoveryStage.FINALIZE_DOCS:
            is_complete = self._validate_finalize_stage(requirements)
            completeness_score = 1.0 if is_complete else 0.0

        return ValidationResult(
            is_complete=is_complete,
            completeness_score=completeness_score,
            missing_items=missing_items,
            suggestions=suggestions,
            validated_data={item: stage_dict.get(item) for item in validated_items},
        )

    def _validate_item(
        self, item_name: str, item_value: Any, validation_rule: Optional[str]
    ) -> Dict[str, Any]:
        """Valida um item específico baseado nas regras."""
        if item_value is None:
            return {
                "is_valid": False,
                "suggestion": f"Ainda preciso saber: {item_name.replace('_', ' ')}",
            }

        # Validações específicas por tipo
        if isinstance(item_value, str):
            if not item_value.strip():
                return {
                    "is_valid": False,
                    "suggestion": f"Campo '{item_name.replace('_', ' ')}' não pode estar vazio",
                }

            # Para campos técnicos, aceitar respostas curtas
            if item_name in ["tipo_aplicativo", "nome_projeto"]:
                # Aceita qualquer resposta não vazia
                return {"is_valid": True, "suggestion": None}

        elif isinstance(item_value, list):
            # Para listas, aceitar mesmo se tiver apenas 1 item
            # Não exigir quantidade mínima rígida
            if not item_value:
                return {
                    "is_valid": False,
                    "suggestion": f"Preciso de pelo menos uma opção para '{item_name.replace('_', ' ')}'",
                }

        elif isinstance(item_value, dict):
            # Para dicionários, aceitar se tiver qualquer conteúdo
            if not item_value:
                return {
                    "is_valid": False,
                    "suggestion": f"Preciso de informações sobre '{item_name.replace('_', ' ')}'",
                }

        return {"is_valid": True, "suggestion": None}

    def _get_minimum_items_for_field(self, field_name: str) -> int:
        """Retorna o número mínimo de itens para campos de lista."""
        # Simplificado - apenas 1 item mínimo para todos os campos
        # Não exigir múltiplos itens obrigatoriamente
        return 1

    def _validate_finalize_stage(self, requirements: Requirements) -> bool:
        """Validação especial para o estágio de finalização."""
        # Verificar se todos os estágios anteriores estão completos
        stages_to_check = [
            DiscoveryStage.BUSINESS_CONTEXT,
            DiscoveryStage.USERS_AND_JOURNEYS,
            DiscoveryStage.FUNCTIONAL_SCOPE,
            DiscoveryStage.CONSTRAINTS_POLICIES,
            DiscoveryStage.NON_FUNCTIONAL,
            DiscoveryStage.TECH_PREFERENCES,
            DiscoveryStage.DELIVERY_BUDGET,
            DiscoveryStage.REVIEW_GAPS,
        ]

        for stage in stages_to_check:
            validation = self.validate_stage(stage, requirements)
            if not validation.is_complete:
                logger.warning(f"Estágio {stage} não está completo para finalização")
                return False

        return True

    def get_missing_items(self, stage: DiscoveryStage, requirements: Requirements) -> List[str]:
        """Retorna lista de itens faltantes para um estágio."""
        validation = self.validate_stage(stage, requirements)
        return validation.missing_items

    def calculate_completeness_score(
        self, stage: DiscoveryStage, requirements: Requirements
    ) -> float:
        """Calcula score de completude de um estágio."""
        validation = self.validate_stage(stage, requirements)
        return validation.completeness_score

    def get_validation_suggestions(
        self, stage: DiscoveryStage, requirements: Requirements
    ) -> List[str]:
        """Retorna sugestões para completar um estágio."""
        validation = self.validate_stage(stage, requirements)
        return validation.suggestions

    def get_stage_checklist(self, stage: DiscoveryStage) -> Optional[StageChecklist]:
        """Retorna o checklist de um estágio."""
        return self._stage_checklists.get(stage)

    def validate_all_stages(
        self, requirements: Requirements
    ) -> Dict[DiscoveryStage, ValidationResult]:
        """Valida todos os estágios e retorna resultados."""
        results = {}

        for stage in DiscoveryStage:
            if stage != DiscoveryStage.FINALIZE_DOCS:
                results[stage] = self.validate_stage(stage, requirements)

        return results
