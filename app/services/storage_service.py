from typing import List, Optional, Dict
import logging
from datetime import datetime, timedelta
from google.cloud import storage
from google.cloud.exceptions import NotFound
import os
import json

from app.models.documents import GeneratedDocument, DocumentType, DocumentSet, TaskSet
from app.models.session import DiscoverySession

logger = logging.getLogger(__name__)

class GCSStorageService:
    """
    Serviço para persistência de documentos no Google Cloud Storage.
    Gerencia upload, download, versionamento e URIs públicas.
    """
    
    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        self.bucket_name = bucket_name
        
        # Initialize GCS client
        if credentials_path and os.path.exists(credentials_path):
            self.client = storage.Client.from_service_account_json(credentials_path)
        else:
            # Use default credentials (ADC)
            self.client = storage.Client()
        
        self.bucket = self.client.bucket(bucket_name)
        
        # Verificar se bucket existe
        try:
            self.bucket.reload()
            logger.info(f"Conectado ao bucket GCS: {bucket_name}")
        except NotFound:
            logger.error(f"Bucket não encontrado: {bucket_name}")
            raise
    
    async def save_documents(self, 
                           session: DiscoverySession,
                           doc_set: DocumentSet,
                           task_set: TaskSet) -> List[GeneratedDocument]:
        """
        Salva todos os 6 documentos no GCS e retorna lista com URIs.
        
        Args:
            session: Sessão da descoberta
            doc_set: Conjunto de documentos técnicos
            task_set: Conjunto de listas de tarefas
            
        Returns:
            Lista de GeneratedDocument com URIs do GCS
        """
        documents = []
        
        try:
            # Documentos técnicos
            backend_doc = await self._save_single_document(
                session.id,
                DocumentType.BACKEND,
                doc_set.backend_md,
                doc_set.version
            )
            documents.append(backend_doc)
            
            frontend_doc = await self._save_single_document(
                session.id,
                DocumentType.FRONTEND,
                doc_set.frontend_md,
                doc_set.version
            )
            documents.append(frontend_doc)
            
            database_doc = await self._save_single_document(
                session.id,
                DocumentType.DATABASE,
                doc_set.bancodedados_md,
                doc_set.version
            )
            documents.append(database_doc)
            
            # Listas de tarefas
            tasks_backend_doc = await self._save_single_document(
                session.id,
                DocumentType.TASKS_BACKEND,
                task_set.tarefas_backend_md,
                task_set.version
            )
            documents.append(tasks_backend_doc)
            
            tasks_frontend_doc = await self._save_single_document(
                session.id,
                DocumentType.TASKS_FRONTEND,
                task_set.tarefas_frontend_md,
                task_set.version
            )
            documents.append(tasks_frontend_doc)
            
            tasks_database_doc = await self._save_single_document(
                session.id,
                DocumentType.TASKS_DATABASE,
                task_set.tarefas_bancodedados_md,
                task_set.version
            )
            documents.append(tasks_database_doc)
            
            # Salvar metadados da sessão
            await self._save_session_metadata(session, documents)
            
            logger.info(f"Salvos {len(documents)} documentos para sessão {session.id}")
            return documents
            
        except Exception as e:
            logger.error(f"Erro ao salvar documentos: {str(e)}")
            raise
    
    async def _save_single_document(self,
                                  session_id: str,
                                  doc_type: DocumentType,
                                  content: str,
                                  version: str) -> GeneratedDocument:
        """
        Salva um documento individual no GCS.
        
        Args:
            session_id: ID da sessão
            doc_type: Tipo do documento
            content: Conteúdo do documento
            version: Versão do documento
            
        Returns:
            GeneratedDocument com URI do GCS
        """
        try:
            # Gerar nome do arquivo
            filename = self._generate_filename(session_id, doc_type, version)
            
            # Criar blob no GCS
            blob = self.bucket.blob(filename)
            
            # Metadados
            blob.metadata = {
                "session_id": session_id,
                "document_type": doc_type.value,
                "version": version,
                "generated_at": datetime.utcnow().isoformat(),
                "content_type": "text/markdown"
            }
            
            # Upload do conteúdo
            blob.upload_from_string(
                content,
                content_type="text/markdown; charset=utf-8"
            )
            
            # Gerar URI pública (temporária por 7 dias)
            public_uri = blob.generate_signed_url(
                expiration=datetime.utcnow() + timedelta(days=7),
                method="GET"
            )
            
            # Criar objeto GeneratedDocument
            document = GeneratedDocument(
                session_id=session_id,
                document_type=doc_type,
                content=content,
                version=version,
                gcs_uri=public_uri,
                file_name=filename
            )
            
            logger.debug(f"Documento salvo: {filename}")
            return document
            
        except Exception as e:
            logger.error(f"Erro ao salvar documento {doc_type}: {str(e)}")
            raise
    
    async def _save_session_metadata(self, 
                                   session: DiscoverySession,
                                   documents: List[GeneratedDocument]):
        """
        Salva metadados da sessão e índice de documentos.
        
        Args:
            session: Sessão da descoberta
            documents: Lista de documentos gerados
        """
        try:
            metadata = {
                "session_id": session.id,
                "created_at": session.created_at.isoformat(),
                "completed_at": session.updated_at.isoformat(),
                "current_stage": session.current_stage.value,
                "version": session.version,
                "total_messages": len(session.messages),
                "requirements_summary": self._summarize_requirements(session.requirements),
                "documents": [
                    {
                        "id": doc.id,
                        "type": doc.document_type.value,
                        "filename": doc.file_name,
                        "version": doc.version,
                        "uri": doc.gcs_uri
                    }
                    for doc in documents
                ]
            }
            
            # Salvar como JSON
            metadata_filename = f"sessions/{session.id}/metadata.json"
            metadata_blob = self.bucket.blob(metadata_filename)
            metadata_blob.upload_from_string(
                json.dumps(metadata, indent=2, ensure_ascii=False),
                content_type="application/json; charset=utf-8"
            )
            
            logger.debug(f"Metadados salvos: {metadata_filename}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar metadados: {str(e)}")
    
    def _generate_filename(self, 
                          session_id: str, 
                          doc_type: DocumentType, 
                          version: str) -> str:
        """
        Gera nome único para o arquivo no GCS.
        
        Args:
            session_id: ID da sessão
            doc_type: Tipo do documento
            version: Versão do documento
            
        Returns:
            Nome do arquivo no formato: sessions/{session_id}/{type}_{version}.md
        """
        type_mapping = {
            DocumentType.BACKEND: "backend",
            DocumentType.FRONTEND: "frontend",
            DocumentType.DATABASE: "bancodedados",
            DocumentType.TASKS_BACKEND: "tarefas_backend",
            DocumentType.TASKS_FRONTEND: "tarefas_frontend",
            DocumentType.TASKS_DATABASE: "tarefas_bancodedados"
        }
        
        type_name = type_mapping.get(doc_type, doc_type.value)
        return f"sessions/{session_id}/{type_name}_{version}.md"
    
    def _summarize_requirements(self, requirements) -> Dict:
        """
        Cria resumo dos requisitos para metadados.
        
        Args:
            requirements: Objeto Requirements
            
        Returns:
            Dicionário com resumo
        """
        return {
            "objetivo": requirements.business_context.objetivo[:100] + "..." if requirements.business_context.objetivo else "",
            "total_personas": len(requirements.business_context.personas),
            "total_features_must": len(requirements.functional_scope.features_must),
            "total_features_should": len(requirements.functional_scope.features_should),
            "total_integracoes": len(requirements.functional_scope.integracoes),
            "disponibilidade": requirements.non_functional.disponibilidade,
            "custo_alvo": requirements.non_functional.custo_alvo
        }
    
    async def get_document(self, 
                         session_id: str, 
                         doc_type: DocumentType, 
                         version: str = "v1") -> Optional[GeneratedDocument]:
        """
        Recupera um documento específico do GCS.
        
        Args:
            session_id: ID da sessão
            doc_type: Tipo do documento
            version: Versão do documento
            
        Returns:
            GeneratedDocument ou None se não encontrado
        """
        try:
            filename = self._generate_filename(session_id, doc_type, version)
            blob = self.bucket.blob(filename)
            
            if not blob.exists():
                logger.warning(f"Documento não encontrado: {filename}")
                return None
            
            # Baixar conteúdo
            content = blob.download_as_text()
            
            # Gerar URI temporária
            public_uri = blob.generate_signed_url(
                expiration=datetime.utcnow() + timedelta(hours=24),
                method="GET"
            )
            
            return GeneratedDocument(
                session_id=session_id,
                document_type=doc_type,
                content=content,
                version=version,
                gcs_uri=public_uri,
                file_name=filename
            )
            
        except Exception as e:
            logger.error(f"Erro ao recuperar documento: {str(e)}")
            return None
    
    async def list_session_documents(self, session_id: str) -> List[GeneratedDocument]:
        """
        Lista todos os documentos de uma sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Lista de documentos encontrados
        """
        try:
            prefix = f"sessions/{session_id}/"
            blobs = self.client.list_blobs(self.bucket, prefix=prefix)
            
            documents = []
            for blob in blobs:
                # Pular metadados
                if blob.name.endswith('.json'):
                    continue
                
                # Extrair informações do nome do arquivo
                filename = os.path.basename(blob.name)
                if not filename.endswith('.md'):
                    continue
                
                # Parse do nome: {type}_{version}.md
                name_parts = filename.replace('.md', '').split('_')
                if len(name_parts) < 2:
                    continue
                
                doc_type_str = '_'.join(name_parts[:-1])
                version = name_parts[-1]
                
                # Mapear tipo
                doc_type = self._map_filename_to_type(doc_type_str)
                if not doc_type:
                    continue
                
                # Gerar URI temporária
                public_uri = blob.generate_signed_url(
                    expiration=datetime.utcnow() + timedelta(hours=24),
                    method="GET"
                )
                
                document = GeneratedDocument(
                    session_id=session_id,
                    document_type=doc_type,
                    content="",  # Não baixar conteúdo na listagem
                    version=version,
                    gcs_uri=public_uri,
                    file_name=blob.name
                )
                documents.append(document)
            
            return documents
            
        except Exception as e:
            logger.error(f"Erro ao listar documentos da sessão {session_id}: {str(e)}")
            return []
    
    def _map_filename_to_type(self, filename: str) -> Optional[DocumentType]:
        """Mapeia nome do arquivo para DocumentType."""
        mapping = {
            "backend": DocumentType.BACKEND,
            "frontend": DocumentType.FRONTEND,
            "bancodedados": DocumentType.DATABASE,
            "tarefas_backend": DocumentType.TASKS_BACKEND,
            "tarefas_frontend": DocumentType.TASKS_FRONTEND,
            "tarefas_bancodedados": DocumentType.TASKS_DATABASE
        }
        return mapping.get(filename)
    
    async def delete_session_documents(self, session_id: str) -> bool:
        """
        Remove todos os documentos de uma sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            True se removido com sucesso
        """
        try:
            prefix = f"sessions/{session_id}/"
            blobs = self.client.list_blobs(self.bucket, prefix=prefix)
            
            deleted_count = 0
            for blob in blobs:
                blob.delete()
                deleted_count += 1
            
            logger.info(f"Removidos {deleted_count} arquivos da sessão {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao remover documentos da sessão {session_id}: {str(e)}")
            return False