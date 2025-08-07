from typing import List, Optional, Dict
import json
import logging
from datetime import datetime
from pathlib import Path

from app.models.documents import GeneratedDocument, DocumentType, DocumentSet, TaskSet
from app.models.session import DiscoverySession

logger = logging.getLogger(__name__)

class LocalStorageService:
    """
    Serviço para armazenamento local de documentos e sessões.
    Usado para desenvolvimento/teste sem dependência do Google Cloud.
    """
    
    def __init__(self, storage_path: str = "./storage"):
        self.storage_path = Path(storage_path)
        self.documents_path = self.storage_path / "documents"
        self.sessions_path = self.storage_path / "sessions"
        
        # Criar diretórios se não existirem
        self._ensure_directories()
        
        logger.info(f"LocalStorageService inicializado: {self.storage_path}")
    
    def _ensure_directories(self):
        """Cria diretórios necessários se não existirem."""
        self.storage_path.mkdir(exist_ok=True)
        self.documents_path.mkdir(exist_ok=True)
        self.sessions_path.mkdir(exist_ok=True)
    
    async def save_documents(self, 
                           session: DiscoverySession,
                           doc_set: DocumentSet,
                           task_set: TaskSet) -> List[GeneratedDocument]:
        """
        Salva todos os 6 documentos no armazenamento local.
        
        Args:
            session: Sessão da descoberta
            doc_set: Conjunto de documentos técnicos
            task_set: Conjunto de listas de tarefas
            
        Returns:
            Lista de GeneratedDocument com caminhos locais
        """
        documents = []
        
        try:
            # Criar diretório da sessão
            session_dir = self.documents_path / session.id
            session_dir.mkdir(exist_ok=True)
            
            # Documentos técnicos
            backend_doc = await self._save_single_document(
                session_dir,
                session.id,
                DocumentType.BACKEND,
                doc_set.backend_md,
                doc_set.version
            )
            documents.append(backend_doc)
            
            frontend_doc = await self._save_single_document(
                session_dir,
                session.id,
                DocumentType.FRONTEND,
                doc_set.frontend_md,
                doc_set.version
            )
            documents.append(frontend_doc)
            
            database_doc = await self._save_single_document(
                session_dir,
                session.id,
                DocumentType.DATABASE,
                doc_set.bancodedados_md,
                doc_set.version
            )
            documents.append(database_doc)
            
            # Listas de tarefas
            tasks_backend_doc = await self._save_single_document(
                session_dir,
                session.id,
                DocumentType.TASKS_BACKEND,
                task_set.tarefas_backend_md,
                task_set.version
            )
            documents.append(tasks_backend_doc)
            
            tasks_frontend_doc = await self._save_single_document(
                session_dir,
                session.id,
                DocumentType.TASKS_FRONTEND,
                task_set.tarefas_frontend_md,
                task_set.version
            )
            documents.append(tasks_frontend_doc)
            
            tasks_database_doc = await self._save_single_document(
                session_dir,
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
                                  session_dir: Path,
                                  session_id: str,
                                  doc_type: DocumentType,
                                  content: str,
                                  version: str) -> GeneratedDocument:
        """
        Salva um documento individual no armazenamento local.
        """
        try:
            # Gerar nome do arquivo
            filename = self._generate_filename(doc_type, version)
            file_path = session_dir / filename
            
            # Adicionar metadados no início do documento
            metadata_header = f"""---
session_id: {session_id}
document_type: {doc_type.value}
generated_at: {datetime.utcnow().isoformat()}
version: {version}
storage_type: local
---

"""
            
            full_content = metadata_header + content
            
            # Escrever arquivo
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            # Criar URI local (path relativo para servir via FastAPI)
            local_uri = f"/storage/documents/{session_id}/{filename}"
            
            # Criar objeto GeneratedDocument
            document = GeneratedDocument(
                session_id=session_id,
                document_type=doc_type,
                content=content,
                version=version,
                gcs_uri=local_uri,  # Usando campo gcs_uri para armazenar path local
                file_name=filename
            )
            
            logger.debug(f"Documento salvo localmente: {file_path}")
            return document
            
        except Exception as e:
            logger.error(f"Erro ao salvar documento {doc_type}: {str(e)}")
            raise
    
    async def _save_session_metadata(self, 
                                   session: DiscoverySession,
                                   documents: List[GeneratedDocument]):
        """Salva metadados da sessão."""
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
            metadata_file = self.sessions_path / f"{session.id}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Metadados salvos: {metadata_file}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar metadados: {str(e)}")
    
    def _generate_filename(self, doc_type: DocumentType, version: str) -> str:
        """Gera nome do arquivo."""
        type_mapping = {
            DocumentType.BACKEND: "backend",
            DocumentType.FRONTEND: "frontend",
            DocumentType.DATABASE: "bancodedados",
            DocumentType.TASKS_BACKEND: "tarefas_backend",
            DocumentType.TASKS_FRONTEND: "tarefas_frontend",
            DocumentType.TASKS_DATABASE: "tarefas_bancodedados"
        }
        
        type_name = type_mapping.get(doc_type, doc_type.value)
        return f"{type_name}_{version}.md"
    
    def _summarize_requirements(self, requirements) -> Dict:
        """Cria resumo dos requisitos."""
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
        """Recupera um documento específico."""
        try:
            filename = self._generate_filename(doc_type, version)
            file_path = self.documents_path / session_id / filename
            
            if not file_path.exists():
                logger.warning(f"Documento não encontrado: {file_path}")
                return None
            
            # Ler conteúdo
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Gerar URI local
            local_uri = f"/storage/documents/{session_id}/{filename}"
            
            return GeneratedDocument(
                session_id=session_id,
                document_type=doc_type,
                content=content,
                version=version,
                gcs_uri=local_uri,
                file_name=filename
            )
            
        except Exception as e:
            logger.error(f"Erro ao recuperar documento: {str(e)}")
            return None
    
    async def list_session_documents(self, session_id: str) -> List[GeneratedDocument]:
        """Lista todos os documentos de uma sessão."""
        try:
            session_dir = self.documents_path / session_id
            if not session_dir.exists():
                return []
            
            documents = []
            for file_path in session_dir.glob("*.md"):
                filename = file_path.name
                
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
                
                # Gerar URI local
                local_uri = f"/storage/documents/{session_id}/{filename}"
                
                document = GeneratedDocument(
                    session_id=session_id,
                    document_type=doc_type,
                    content="",  # Não carregar conteúdo na listagem
                    version=version,
                    gcs_uri=local_uri,
                    file_name=filename
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
        """Remove todos os documentos de uma sessão."""
        try:
            import shutil
            session_dir = self.documents_path / session_id
            
            if session_dir.exists():
                shutil.rmtree(session_dir)
                logger.info(f"Diretório removido: {session_dir}")
            
            # Remover metadados
            metadata_file = self.sessions_path / f"{session_id}_metadata.json"
            if metadata_file.exists():
                metadata_file.unlink()
                logger.info(f"Metadados removidos: {metadata_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao remover documentos da sessão {session_id}: {str(e)}")
            return False