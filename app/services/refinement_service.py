from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from openai import AsyncOpenAI

from app.models.session import DiscoverySession
from app.models.documents import GeneratedDocument, DocumentType
from app.services.storage_service import GCSStorageService
from app.services.document_generator import DocumentGenerator

logger = logging.getLogger(__name__)


class RefinementService:
    """
    Serviço para refinamento de documentos com controle de versões.
    Processa feedback do usuário e gera versões aprimoradas dos documentos.
    """

    def __init__(self, openai_api_key: str, storage_service: GCSStorageService):
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.storage_service = storage_service
        self.document_generator = DocumentGenerator(openai_api_key)

    async def get_current_documents(self, session_id: str) -> List[GeneratedDocument]:
        """
        Retorna a versão mais recente dos documentos de uma sessão.

        Args:
            session_id: ID da sessão

        Returns:
            Lista de documentos da versão mais recente
        """
        try:
            all_documents = await self.storage_service.list_session_documents(session_id)

            if not all_documents:
                return []

            # Agrupar por tipo e pegar a versão mais recente de cada
            latest_docs = {}
            for doc in all_documents:
                doc_type = doc.document_type.value
                version_num = int(doc.version.replace("v", ""))

                if doc_type not in latest_docs or version_num > int(
                    latest_docs[doc_type].version.replace("v", "")
                ):
                    latest_docs[doc_type] = doc

            return list(latest_docs.values())

        except Exception as e:
            logger.error(f"Erro ao buscar documentos atuais: {str(e)}")
            return []

    async def process_refinement(
        self,
        session: DiscoverySession,
        refinements: List[str],
        new_version: str,
        target_documents: Optional[List[DocumentType]] = None,
        additional_context: Optional[str] = None,
    ):
        """
        Processa refinamentos e gera nova versão dos documentos.

        Args:
            session: Sessão da descoberta
            refinements: Lista de refinamentos solicitados
            new_version: Nova versão a ser gerada (ex: v2)
            target_documents: Documentos específicos para refinar (opcional)
            additional_context: Contexto adicional (opcional)
        """
        try:
            logger.info(f"Iniciando refinamento para sessão {session.id} - versão {new_version}")

            # Buscar documentos atuais
            current_documents = await self.get_current_documents(session.id)
            if not current_documents:
                logger.error(f"Nenhum documento encontrado para refinamento: {session.id}")
                return

            # Filtrar documentos se especificado
            if target_documents:
                current_documents = [
                    doc for doc in current_documents if doc.document_type in target_documents
                ]

            # Construir contexto de refinamento
            refinement_context = self._build_refinement_context(
                refinements, additional_context, session.requirements
            )

            # Refinar cada documento
            refined_documents = []
            for doc in current_documents:
                # Baixar conteúdo completo do documento atual
                current_doc = await self.storage_service.get_document(
                    session.id, doc.document_type, doc.version
                )

                if not current_doc:
                    logger.warning(f"Documento não encontrado: {doc.document_type}")
                    continue

                # Gerar versão refinada
                refined_content = await self._refine_document(current_doc, refinement_context)

                # Criar novo documento com versão atualizada
                refined_doc = await self.storage_service._save_single_document(
                    session.id, doc.document_type, refined_content, new_version
                )

                refined_documents.append(refined_doc)
                logger.info(f"Documento refinado: {doc.document_type.value} -> {new_version}")

            # Salvar metadados da nova versão
            await self._save_refinement_metadata(
                session, refined_documents, refinements, new_version
            )

            logger.info(f"Refinamento concluído: {len(refined_documents)} documentos atualizados")

        except Exception as e:
            logger.error(f"Erro no processamento de refinamento: {str(e)}")
            raise

    async def _refine_document(
        self, current_document: GeneratedDocument, refinement_context: str
    ) -> str:
        """
        Refina um documento individual baseado no contexto de refinamento.

        Args:
            current_document: Documento atual
            refinement_context: Contexto com refinamentos solicitados

        Returns:
            Conteúdo refinado do documento
        """
        try:
            refinement_prompt = f"""
            Você é um especialista em documentação técnica. Refine o documento abaixo baseado nos feedbacks e refinamentos solicitados.
            
            DOCUMENTO ATUAL ({current_document.document_type.value}):
            {current_document.content}
            
            REFINAMENTOS SOLICITADOS:
            {refinement_context}
            
            INSTRUÇÕES:
            - Mantenha a estrutura geral do documento
            - Incorpore os refinamentos de forma natural
            - Melhore a clareza e detalhamento onde necessário
            - Mantenha o formato Markdown
            - Preserve metadados importantes
            - Seja específico e técnico quando apropriado
            
            Retorne o documento refinado completo:
            """

            from app.utils.config import get_settings

            settings = get_settings()

            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um especialista em documentação técnica que cria documentos estruturados, detalhados e profissionais.",
                    },
                    {"role": "user", "content": refinement_prompt},
                ],
                temperature=0.3,  # Baixa temperatura para consistência
                max_tokens=4000,
            )

            refined_content = response.choices[0].message.content

            # Adicionar metadados de refinamento
            refinement_header = f"""---
session_id: {current_document.session_id}
document_type: {current_document.document_type.value}
generated_at: {datetime.utcnow().isoformat()}
version: {current_document.version}
refined_at: {datetime.utcnow().isoformat()}
refinement_applied: true
---

"""

            return refinement_header + refined_content

        except Exception as e:
            logger.error(f"Erro ao refinar documento {current_document.document_type}: {str(e)}")
            # Retornar documento original em caso de erro
            return current_document.content

    def _build_refinement_context(
        self, refinements: List[str], additional_context: Optional[str], requirements
    ) -> str:
        """
        Constrói contexto estruturado para refinamento.

        Args:
            refinements: Lista de refinamentos solicitados
            additional_context: Contexto adicional
            requirements: Requisitos atualizados

        Returns:
            Contexto formatado para a IA
        """
        context_parts = []

        # Refinamentos principais
        context_parts.append("## REFINAMENTOS SOLICITADOS:")
        for i, refinement in enumerate(refinements, 1):
            context_parts.append(f"{i}. {refinement}")

        # Contexto adicional
        if additional_context:
            context_parts.append(f"\n## CONTEXTO ADICIONAL:\n{additional_context}")

        # Resumo dos requisitos atuais
        context_parts.append(
            f"""
## REQUISITOS ATUAIS (RESUMO):

**Objetivo:** {requirements.business_context.objetivo}

**Features Principais:**
{self._format_list(requirements.functional_scope.features_must[:5])}

**Tecnologias:**
{self._format_list(requirements.tech_preferences.stacks_permitidas[:3])}

**Restrições:**
- Disponibilidade: {requirements.non_functional.disponibilidade}
- Custo: {requirements.non_functional.custo_alvo}
"""
        )

        return "\n".join(context_parts)

    def _format_list(self, items: List[str]) -> str:
        """Formata lista para contexto."""
        if not items:
            return "- N/A"
        return "\n".join([f"- {item}" for item in items])

    async def _save_refinement_metadata(
        self,
        session: DiscoverySession,
        refined_documents: List[GeneratedDocument],
        refinements: List[str],
        version: str,
    ):
        """
        Salva metadados do refinamento.

        Args:
            session: Sessão da descoberta
            refined_documents: Documentos refinados
            refinements: Refinamentos aplicados
            version: Nova versão
        """
        try:
            refinement_metadata = {
                "session_id": session.id,
                "version": version,
                "refined_at": datetime.utcnow().isoformat(),
                "refinements_applied": refinements,
                "refined_documents": [
                    {"type": doc.document_type.value, "filename": doc.file_name, "uri": doc.gcs_uri}
                    for doc in refined_documents
                ],
                "total_versions": int(version.replace("v", "")),
            }

            # Salvar metadados de refinamento
            import json

            metadata_filename = f"sessions/{session.id}/refinement_{version}.json"
            metadata_blob = self.storage_service.bucket.blob(metadata_filename)
            metadata_blob.upload_from_string(
                json.dumps(refinement_metadata, indent=2, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
            )

            logger.debug(f"Metadados de refinamento salvos: {metadata_filename}")

        except Exception as e:
            logger.error(f"Erro ao salvar metadados de refinamento: {str(e)}")

    async def get_refinement_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retorna histórico de refinamentos de uma sessão.

        Args:
            session_id: ID da sessão

        Returns:
            Lista com histórico de refinamentos
        """
        try:
            prefix = f"sessions/{session_id}/refinement_"
            blobs = self.storage_service.client.list_blobs(
                self.storage_service.bucket, prefix=prefix
            )

            refinements = []
            for blob in blobs:
                if blob.name.endswith(".json"):
                    import json

                    metadata = json.loads(blob.download_as_text())
                    refinements.append(metadata)

            # Ordenar por versão
            refinements.sort(key=lambda x: int(x["version"].replace("v", "")))
            return refinements

        except Exception as e:
            logger.error(f"Erro ao buscar histórico de refinamentos: {str(e)}")
            return []

    async def compare_versions(
        self, session_id: str, version1: str, version2: str, document_type: DocumentType
    ) -> Dict[str, Any]:
        """
        Compara duas versões de um documento.

        Args:
            session_id: ID da sessão
            version1: Primeira versão
            version2: Segunda versão
            document_type: Tipo do documento

        Returns:
            Dicionário com comparação
        """
        try:
            # Buscar ambas as versões
            doc1 = await self.storage_service.get_document(session_id, document_type, version1)
            doc2 = await self.storage_service.get_document(session_id, document_type, version2)

            if not doc1 or not doc2:
                return {"error": "Uma ou ambas as versões não foram encontradas"}

            # Comparação básica (implementação simplificada)
            comparison = {
                "session_id": session_id,
                "document_type": document_type.value,
                "version1": version1,
                "version2": version2,
                "content1_length": len(doc1.content),
                "content2_length": len(doc2.content),
                "size_difference": len(doc2.content) - len(doc1.content),
                "generated_at1": doc1.generated_at.isoformat()
                if hasattr(doc1, "generated_at")
                else None,
                "generated_at2": doc2.generated_at.isoformat()
                if hasattr(doc2, "generated_at")
                else None,
            }

            return comparison

        except Exception as e:
            logger.error(f"Erro ao comparar versões: {str(e)}")
            return {"error": str(e)}
