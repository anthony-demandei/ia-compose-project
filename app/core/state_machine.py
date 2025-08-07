from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging
from app.models.base import DiscoveryStage, ValidationResult
from app.models.session import DiscoverySession

logger = logging.getLogger(__name__)


class StateTransition(Enum):
    STAY = "stay"
    ADVANCE = "advance"
    COMPLETE = "complete"


class DiscoveryStateMachine:
    """
    Gerencia as transições entre os 9 estágios de descoberta.
    Cada estágio tem critérios específicos de completude que devem ser atendidos
    antes de avançar para o próximo.
    """

    def __init__(self):
        self._stage_order = [
            DiscoveryStage.BUSINESS_CONTEXT,
            DiscoveryStage.USERS_AND_JOURNEYS,
            DiscoveryStage.FUNCTIONAL_SCOPE,
            DiscoveryStage.CONSTRAINTS_POLICIES,
            DiscoveryStage.NON_FUNCTIONAL,
            DiscoveryStage.TECH_PREFERENCES,
            DiscoveryStage.DELIVERY_BUDGET,
            DiscoveryStage.REVIEW_GAPS,
            DiscoveryStage.FINALIZE_DOCS,
        ]

        # Mapeamento de transições válidas
        self._valid_transitions = {
            DiscoveryStage.BUSINESS_CONTEXT: [DiscoveryStage.USERS_AND_JOURNEYS],
            DiscoveryStage.USERS_AND_JOURNEYS: [DiscoveryStage.FUNCTIONAL_SCOPE],
            DiscoveryStage.FUNCTIONAL_SCOPE: [DiscoveryStage.CONSTRAINTS_POLICIES],
            DiscoveryStage.CONSTRAINTS_POLICIES: [DiscoveryStage.NON_FUNCTIONAL],
            DiscoveryStage.NON_FUNCTIONAL: [DiscoveryStage.TECH_PREFERENCES],
            DiscoveryStage.TECH_PREFERENCES: [DiscoveryStage.DELIVERY_BUDGET],
            DiscoveryStage.DELIVERY_BUDGET: [DiscoveryStage.REVIEW_GAPS],
            DiscoveryStage.REVIEW_GAPS: [DiscoveryStage.FINALIZE_DOCS],
            DiscoveryStage.FINALIZE_DOCS: [],
        }

    def get_current_stage(self, session: DiscoverySession) -> DiscoveryStage:
        """Retorna o estágio atual da sessão."""
        return session.current_stage

    def get_next_stage(self, current_stage: DiscoveryStage) -> Optional[DiscoveryStage]:
        """Retorna o próximo estágio válido ou None se for o último."""
        try:
            current_index = self._stage_order.index(current_stage)
            if current_index < len(self._stage_order) - 1:
                return self._stage_order[current_index + 1]
            return None
        except ValueError:
            logger.error(f"Invalid stage: {current_stage}")
            return None

    def get_previous_stage(self, current_stage: DiscoveryStage) -> Optional[DiscoveryStage]:
        """Retorna o estágio anterior ou None se for o primeiro."""
        try:
            current_index = self._stage_order.index(current_stage)
            if current_index > 0:
                return self._stage_order[current_index - 1]
            return None
        except ValueError:
            logger.error(f"Invalid stage: {current_stage}")
            return None

    def can_advance_to_stage(self, from_stage: DiscoveryStage, to_stage: DiscoveryStage) -> bool:
        """Verifica se a transição é válida."""
        return to_stage in self._valid_transitions.get(from_stage, [])

    def process_stage_transition(
        self, session: DiscoverySession, validation_result: ValidationResult
    ) -> Tuple[StateTransition, Optional[DiscoveryStage]]:
        """
        Processa transição de estágio baseado no resultado da validação.

        Returns:
            Tuple[StateTransition, Optional[DiscoveryStage]]:
            (tipo_transição, próximo_estágio_ou_None)
        """
        current_stage = session.current_stage

        # Se estamos no último estágio e está completo, finalizar
        if current_stage == DiscoveryStage.FINALIZE_DOCS:
            if validation_result.is_complete:
                return StateTransition.COMPLETE, None
            else:
                return StateTransition.STAY, current_stage

        # Se o estágio atual não está completo, permanecer
        if not validation_result.is_complete:
            return StateTransition.STAY, current_stage

        # Se está completo, avançar para o próximo estágio
        next_stage = self.get_next_stage(current_stage)
        if next_stage is None:
            return StateTransition.COMPLETE, None

        return StateTransition.ADVANCE, next_stage

    def advance_to_next_stage(self, session: DiscoverySession) -> bool:
        """
        Avança a sessão para o próximo estágio.

        Returns:
            bool: True se conseguiu avançar, False caso contrário
        """
        next_stage = self.get_next_stage(session.current_stage)
        if next_stage is None:
            logger.warning(f"Cannot advance from final stage: {session.current_stage}")
            return False

        logger.info(f"Session {session.id}: {session.current_stage} -> {next_stage}")
        session.current_stage = next_stage
        return True

    def get_stage_progress(self, session: DiscoverySession) -> Dict[str, float]:
        """
        Calcula o progresso geral da descoberta.

        Returns:
            Dict com progresso por estágio e progresso geral
        """
        current_index = self._stage_order.index(session.current_stage)
        total_stages = len(self._stage_order)

        progress = {}

        # Estágios anteriores estão 100% completos
        for i, stage in enumerate(self._stage_order):
            if i < current_index:
                progress[stage.value] = 1.0
            elif i == current_index:
                # Estágio atual - precisa calcular baseado na validação
                progress[stage.value] = 0.5  # Placeholder - será calculado pela validação
            else:
                # Estágios futuros estão em 0%
                progress[stage.value] = 0.0

        # Progresso geral
        completed_stages = current_index
        overall_progress = completed_stages / total_stages
        progress["overall"] = overall_progress

        return progress

    def is_final_stage(self, stage: DiscoveryStage) -> bool:
        """Verifica se é o estágio final."""
        return stage == DiscoveryStage.FINALIZE_DOCS

    def get_stage_description(self, stage: DiscoveryStage) -> str:
        """Retorna descrição do estágio atual."""
        descriptions = {
            DiscoveryStage.BUSINESS_CONTEXT: "Contexto do Negócio - Definindo objetivo, personas, KPIs e riscos principais",
            DiscoveryStage.USERS_AND_JOURNEYS: "Usuários e Jornadas - Mapeando perfis, jornadas críticas e acessibilidade",
            DiscoveryStage.FUNCTIONAL_SCOPE: "Escopo Funcional - Definindo features obrigatórias, opcionais e integrações",
            DiscoveryStage.CONSTRAINTS_POLICIES: "Restrições e Políticas - LGPD, segurança e requisitos de auditoria",
            DiscoveryStage.NON_FUNCTIONAL: "Requisitos Não-Funcionais - SLOs, disponibilidade e custos",
            DiscoveryStage.TECH_PREFERENCES: "Preferências Técnicas - Stacks permitidas, vedadas e legado",
            DiscoveryStage.DELIVERY_BUDGET: "Entrega e Orçamento - Marcos, prazos e governança",
            DiscoveryStage.REVIEW_GAPS: "Revisão de Lacunas - Identificando gaps e trade-offs",
            DiscoveryStage.FINALIZE_DOCS: "Finalização - Gerando documentação e tarefas",
        }
        return descriptions.get(stage, f"Estágio {stage.value}")

    def validate_session_integrity(self, session: DiscoverySession) -> List[str]:
        """
        Valida a integridade da sessão e retorna lista de problemas encontrados.
        """
        issues = []

        # Verificar se o estágio atual é válido
        if session.current_stage not in self._stage_order:
            issues.append(f"Estágio inválido: {session.current_stage}")

        # Verificar se há mensagens para o estágio atual
        if not session.messages:
            issues.append("Sessão sem mensagens")

        # Verificar consistência temporal
        if session.updated_at < session.created_at:
            issues.append("Data de atualização inválida")

        return issues
