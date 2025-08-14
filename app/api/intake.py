"""
API endpoints para o sistema de intake inteligente.
Gerencia o fluxo completo de intake → wizard → escopo.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict, Any
from uuid import UUID

from app.models.intake import (
    IntakeRequest,
    AnswersRequest,
    SummaryResponse,
)
from app.services.intake_engine import IntakeEngine
from app.utils.config import get_settings
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)

# Criar router
router = APIRouter(prefix="/v1/intake", tags=["intake"])

# Instância global do engine (TODO: usar dependency injection adequado)
intake_engine: Optional[IntakeEngine] = None


def get_intake_engine() -> IntakeEngine:
    """Dependency para obter o IntakeEngine."""
    global intake_engine
    if intake_engine is None:
        settings = get_settings()
        intake_engine = IntakeEngine(openai_api_key=settings.openai_api_key)
    return intake_engine


@router.post("", response_model=Dict[str, Any])
async def create_intake(
    request: IntakeRequest, engine: IntakeEngine = Depends(get_intake_engine)
) -> Dict[str, Any]:
    """
    Cria nova sessão de intake e retorna perguntas selecionadas.

    O sistema analisa o texto fornecido e seleciona até 10 perguntas
    mais relevantes do catálogo pré-definido.
    """
    try:
        logger.info("Criando nova sessão de intake")

        # Extrair identificador do cliente dos metadados se disponível (opcional para ZEP universal)
        client_identifier = None

        if request.metadata:
            user_info = request.metadata.get("user", {})
            client_identifier = (
                user_info.get("id")
                or user_info.get("user_id")
                or user_info.get("client_id")
                or user_info.get("email")  # Fallback para email como identificador
            )

        # Criar sessão usando sistema universal ZEP
        session = await engine.create_intake_session(
            intake_text=request.text,
            metadata=request.metadata,
            user_id=client_identifier,  # Usado apenas como identificador de contexto
            user_email=None,  # Não mais necessário
            user_name=None,  # Não mais necessário
        )

        # Extrair metadados do sistema universal V3.0
        metadata = session.metadata or {}
        selection_metadata = metadata.get("selection_metadata", {})
        project_info = selection_metadata.get("project_classification", {})
        completeness_info = metadata.get("completeness_analysis", {})

        # Retornar sessão com informações universais
        return {
            "sessionId": str(session.id),
            "questionIds": session.question_ids,
            "status": session.status.value,
            "totalQuestions": len(session.question_ids),
            "engineVersion": metadata.get("engine_version", "3.0"),
            "projectClassification": {
                "type": project_info.get("type", "unknown"),
                "complexity": project_info.get("complexity", "moderate"),
                "domainContext": project_info.get("domain_context", "generic"),
                "confidence": project_info.get("confidence", 0.0),
            },
            "completenessAnalysis": {
                "score": completeness_info.get("overall_score", 0.0),
                "isComplete": completeness_info.get("is_complete", False),
                "skippedQuestions": metadata.get("skipped_questions", False),
                "missingAreas": metadata.get("missing_areas", []),
            },
            "isDynamicGeneration": metadata.get("dynamic_generation", False),
        }

    except Exception as e:
        logger.error(f"Erro ao criar intake: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=Dict[str, Any])
async def get_intake_session(
    session_id: UUID, engine: IntakeEngine = Depends(get_intake_engine)
) -> Dict[str, Any]:
    """
    Recupera informações da sessão de intake.
    """
    try:
        session = engine.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")

        # Extrair metadados do sistema universal V3.0
        metadata = session.metadata or {}
        selection_metadata = metadata.get("selection_metadata", {})
        project_info = selection_metadata.get("project_classification", {})
        completeness_info = metadata.get("completeness_analysis", {})

        return {
            "sessionId": str(session.id),
            "status": session.status.value,
            "createdAt": session.created_at.isoformat(),
            "intakeText": session.intake_text,
            "questionIds": session.question_ids,
            "answeredQuestions": len(session.answers),
            "totalQuestions": len(session.question_ids),
            "hasSummary": session.summary is not None,
            "hasScope": session.scope_document is not None,
            "engineVersion": metadata.get("engine_version", "3.0"),
            "projectClassification": {
                "type": project_info.get("type", "unknown"),
                "complexity": project_info.get("complexity", "moderate"),
                "domainContext": project_info.get("domain_context", "generic"),
                "confidence": project_info.get("confidence", 0.0),
                "reasoning": project_info.get("reasoning", ""),
            },
            "completenessAnalysis": {
                "score": completeness_info.get("overall_score", 0.0),
                "isComplete": completeness_info.get("is_complete", False),
                "skippedQuestions": metadata.get("skipped_questions", False),
                "missingAreas": metadata.get("missing_areas", []),
                "summary": completeness_info.get("summary", ""),
            },
            "isDynamicGeneration": metadata.get("dynamic_generation", False),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao recuperar sessão: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/answers", response_model=Dict[str, Any])
async def submit_answers(
    session_id: UUID, request: AnswersRequest, engine: IntakeEngine = Depends(get_intake_engine)
) -> Dict[str, Any]:
    """
    Processa respostas do wizard e retorna próximas perguntas.

    As perguntas são servidas em lotes de até 3, considerando
    condições e dependências entre perguntas.
    """
    try:
        logger.info(f"Processando {len(request.answers)} respostas para sessão {session_id}")

        # Processar respostas
        result = await engine.process_answers(session_id, request.answers)

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao processar respostas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/questions", response_model=Dict[str, Any])
async def get_questions_details(
    session_id: UUID,
    question_ids: Optional[str] = Query(None, description="IDs separados por vírgula"),
    engine: IntakeEngine = Depends(get_intake_engine),
) -> Dict[str, Any]:
    """
    Retorna detalhes das perguntas selecionadas para a sessão.
    """
    try:
        session = engine.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")

        # Filtrar perguntas solicitadas
        if question_ids:
            ids_list = question_ids.split(",")
        else:
            ids_list = session.question_ids

        # Buscar detalhes das perguntas
        questions = []
        for q_id in ids_list:
            question = engine.get_question_by_id(q_id)
            if question:
                questions.append(
                    {
                        "id": question.id,
                        "text": question.text,
                        "type": question.type,
                        "stage": question.stage,
                        "options": question.options if question.options else None,
                        "required": question.required,
                    }
                )

        return {
            "sessionId": str(session_id),
            "questions": questions,
            "totalQuestions": len(questions),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar perguntas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/summarize", response_model=SummaryResponse)
async def generate_summary(
    session_id: UUID, engine: IntakeEngine = Depends(get_intake_engine)
) -> SummaryResponse:
    """
    Gera resumo das respostas coletadas.

    O resumo é apresentado ao cliente antes da geração do escopo final.
    """
    try:
        logger.info(f"Gerando resumo para sessão {session_id}")

        summary = await engine.generate_summary(session_id)

        return summary

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao gerar resumo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/final-note", response_model=Dict[str, Any])
async def add_final_note(
    session_id: UUID, request: Dict[str, str], engine: IntakeEngine = Depends(get_intake_engine)
) -> Dict[str, Any]:
    """
    Adiciona nota final do cliente após o resumo.

    Esta é a última oportunidade do cliente adicionar informações
    antes da geração do escopo final.
    """
    try:
        note = request.get("text", "")

        if not note:
            raise HTTPException(status_code=400, detail="Nota não pode estar vazia")

        logger.info(f"Adicionando nota final à sessão {session_id}")

        success = await engine.add_final_note(session_id, note)

        if not success:
            raise HTTPException(status_code=500, detail="Erro ao adicionar nota")

        return {
            "sessionId": str(session_id),
            "success": True,
            "message": "Nota final adicionada com sucesso",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao adicionar nota final: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/scope", response_model=Dict[str, Any])
async def generate_scope(
    session_id: UUID, engine: IntakeEngine = Depends(get_intake_engine)
) -> Dict[str, Any]:
    """
    Gera documento de escopo técnico completo.

    Este é o documento final que será usado pelo desenvolvedor,
    contendo todas as especificações técnicas do projeto.
    """
    try:
        logger.info(f"Gerando escopo para sessão {session_id}")

        # Gerar documento de escopo
        scope_markdown = await engine.generate_scope_document(session_id)

        return {
            "sessionId": str(session_id),
            "scopeMd": scope_markdown,
            "status": "completed",
            "message": "Escopo gerado com sucesso",
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao gerar escopo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/scope", response_model=Dict[str, Any])
async def get_scope_document(
    session_id: UUID,
    format: str = Query("markdown", description="Formato do documento (markdown ou json)"),
    engine: IntakeEngine = Depends(get_intake_engine),
) -> Dict[str, Any]:
    """
    Recupera documento de escopo gerado anteriormente.
    """
    try:
        session = engine.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")

        if not session.scope_document:
            raise HTTPException(status_code=404, detail="Escopo ainda não foi gerado")

        return {
            "sessionId": str(session_id),
            "format": format,
            "content": session.scope_document,
            "generatedAt": session.updated_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao recuperar escopo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/questions", response_model=Dict[str, Any])
async def get_question_catalog(
    stage: Optional[str] = Query(None, description="Filtrar por estágio"),
    required_only: bool = Query(False, description="Apenas perguntas obrigatórias"),
    engine: IntakeEngine = Depends(get_intake_engine),
) -> Dict[str, Any]:
    """
    Retorna catálogo completo de perguntas disponíveis.

    Útil para debug e visualização do catálogo.
    """
    try:
        catalog = engine.question_selector.catalog

        # Aplicar filtros
        questions = catalog

        if stage:
            questions = [q for q in questions if q.stage == stage]

        if required_only:
            questions = [q for q in questions if q.required]

        # Formatar resposta
        questions_data = [
            {
                "id": q.id,
                "text": q.text,
                "type": q.type,
                "stage": q.stage,
                "required": q.required,
                "weight": q.weight,
                "tags": q.tags,
                "hasCondition": q.condition is not None,
            }
            for q in questions
        ]

        return {
            "totalQuestions": len(questions_data),
            "questions": questions_data,
            "stages": list(set(q.stage for q in catalog)),
        }

    except Exception as e:
        logger.error(f"Erro ao buscar catálogo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check
@router.get("/health")
async def health_check():
    """Verifica saúde do serviço de intake."""
    return {"status": "healthy", "service": "intake", "version": "1.0.0"}
