"""
ZEP Client wrapper para facilitar integração com o sistema.
Fornece interface simplificada para operações de memória.
"""

from typing import Optional, Dict, Any, List

try:
    from zep_cloud.client import AsyncZep
except ImportError:
    try:
        from zep_python.client import AsyncZep
    except ImportError:
        try:
            from zep_python import AsyncZep
        except ImportError:
            AsyncZep = None
from app.utils.config import get_settings
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class ZepClientWrapper:
    """
    Wrapper para AsyncZep que fornece interface simplificada
    e tratamento de erros específico para o sistema de intake.
    """

    def __init__(self):
        """Inicializa o wrapper ZEP com configurações do sistema."""
        settings = get_settings()

        if not settings.enable_zep_memory:
            self.client = None
            logger.warning("ZEP Memory is disabled in configuration")
            return

        if AsyncZep is None:
            self.client = None
            logger.error("ZEP Python library not available. Install with: pip install zep-python")
            return

        try:
            self.client = AsyncZep(api_key=settings.zep_project_key)
            self.account_id = settings.zep_account_id
            logger.info("ZEP client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ZEP client: {str(e)}")
            self.client = None

    def is_available(self) -> bool:
        """Verifica se o cliente ZEP está disponível."""
        return self.client is not None

    async def create_or_get_user(
        self, user_id: str, email: str = None, first_name: str = None, last_name: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Cria ou recupera um usuário no ZEP usando API v3.

        Args:
            user_id: ID único do usuário
            email: Email do usuário (opcional)
            first_name: Primeiro nome (opcional)
            last_name: Sobrenome (opcional)

        Returns:
            Dados do usuário ou None se erro
        """
        if not self.is_available():
            return None

        try:
            # Tentar recuperar usuário existente primeiro
            try:
                user = await self.client.user.get(user_id=user_id)
                logger.info(f"Retrieved existing ZEP user: {user_id}")
                return {"user_id": user_id, "exists": True} if user else None
            except Exception:
                # Usuário não existe, criar novo
                pass

            # Criar novo usuário usando a API v3 do ZEP
            user = await self.client.user.add(
                user_id=user_id,
                email=email or f"{user_id}@system.internal",
                first_name=first_name or "System",
                last_name=last_name or "User",
            )
            logger.info(f"Created new ZEP user: {user_id}")
            return {"user_id": user_id, "exists": False} if user else None

        except Exception as e:
            logger.error(f"Error managing ZEP user {user_id}: {str(e)}")
            # Fallback: assumir que user existe para não bloquear operação
            return {"user_id": user_id, "exists": True, "fallback": True}

    async def add_memory(
        self, thread_id: str, messages: List[Dict[str, Any]], user_id: str = None
    ) -> bool:
        """
        Adiciona mensagens a um thread ZEP usando API v3.

        Args:
            thread_id: ID do thread ZEP
            messages: Lista de mensagens no formato ZEP v3
            user_id: ID do usuário (usado para criar thread se necessário)

        Returns:
            True se sucesso, False se erro
        """
        if not self.is_available():
            return False

        try:
            # Garantir que thread existe
            if user_id:
                try:
                    await self.client.thread.create(thread_id=thread_id, user_id=user_id)
                except Exception:
                    # Thread já existe, continuar
                    pass

            # Converter mensagens para formato ZEP v3
            from zep_cloud.types import Message

            zep_messages = []
            for msg in messages:
                zep_message = Message(
                    content=msg.get("content", ""),
                    role=msg.get("role_type", "user"),  # user, assistant, system
                    name=msg.get("role", "System"),
                )
                zep_messages.append(zep_message)

            # Adicionar mensagens ao thread
            await self.client.thread.add_messages(thread_id=thread_id, messages=zep_messages)

            logger.info(f"Added {len(messages)} messages to ZEP thread: {thread_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding messages to ZEP thread {thread_id}: {str(e)}")
            return False

    async def get_memory_context(self, thread_id: str, last_n_messages: int = 6) -> Optional[str]:
        """
        Recupera contexto relevante do thread ZEP usando API v3.

        Args:
            thread_id: ID do thread ZEP
            last_n_messages: Número de mensagens recentes para incluir

        Returns:
            String de contexto ou None se erro
        """
        if not self.is_available():
            return None

        try:
            # Usar a API v3 para obter contexto do thread
            memory = await self.client.thread.get_user_context(thread_id=thread_id)

            if memory and hasattr(memory, "context"):
                logger.info(f"Retrieved context for thread: {thread_id}")
                return memory.context
            else:
                logger.info(f"No context found for thread: {thread_id}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving context from ZEP thread {thread_id}: {str(e)}")
            return None

    async def search_memory(
        self, text: str, user_id: str = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca memórias relevantes baseado em texto usando API v3.

        Args:
            text: Texto para busca
            user_id: ID do usuário para filtrar busca
            limit: Limite de resultados

        Returns:
            Lista de resultados da busca
        """
        if not self.is_available():
            return []

        try:
            # Usar API v3 de busca através do graph
            results = await self.client.graph.search(
                user_id=user_id or "demandei_universal_user", query=text, limit=limit
            )

            # Converter resultados para formato compatível
            formatted_results = []
            if results:
                # GraphSearchResults pode ter atributos como results, edges, nodes
                search_items = []

                if hasattr(results, "edges") and results.edges:
                    search_items.extend(results.edges)
                if hasattr(results, "nodes") and results.nodes:
                    search_items.extend(results.nodes)
                if hasattr(results, "results") and results.results:
                    search_items.extend(results.results)

                logger.info(f"Found {len(search_items)} search items")

                for item in search_items:
                    # Adaptar estrutura do resultado baseado no que o graph retorna
                    content = ""
                    if hasattr(item, "content"):
                        content = item.content
                    elif hasattr(item, "data"):
                        content = str(item.data)
                    elif hasattr(item, "text"):
                        content = item.text
                    else:
                        content = str(item)

                    formatted_results.append(
                        {
                            "content": content,
                            "score": getattr(item, "score", 0.0),
                            "source": "graph",
                        }
                    )
            else:
                logger.info("No search results found")

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching ZEP graph: {str(e)}")
            # Fallback: tentar buscar por threads
            try:
                # Como alternativa, listar threads do usuário universal
                # e buscar contexto relevante
                return []  # Por enquanto, retornar vazio se search falhar
            except Exception as e2:
                logger.error(f"Fallback search also failed: {str(e2)}")
                return []

    async def add_business_data(self, user_id: str, data: Dict[str, Any]) -> bool:
        """
        Adiciona dados de negócio ao grafo de conhecimento usando API v3.

        Args:
            user_id: ID do usuário
            data: Dados estruturados para adicionar

        Returns:
            True se sucesso, False se erro
        """
        if not self.is_available():
            return False

        try:
            import json

            # Adicionar dados estruturados ao grafo usando API v3
            await self.client.graph.add(user_id=user_id, type="json", data=json.dumps(data))
            logger.info(f"Added structured data to ZEP graph for user: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding data to ZEP graph for user {user_id}: {str(e)}")
            return False

    async def get_user_graph_summary(self, user_id: str) -> Optional[str]:
        """
        Recupera resumo do grafo de conhecimento do usuário.

        Args:
            user_id: ID do usuário

        Returns:
            Resumo do grafo ou None se erro
        """
        if not self.is_available():
            return None

        try:
            # Implementar quando ZEP fornecer API de resumo do grafo
            # Por enquanto, retornar informação básica
            logger.info(f"Retrieving graph summary for user: {user_id}")
            return f"User {user_id} knowledge graph data available"

        except Exception as e:
            logger.error(f"Error retrieving graph summary for user {user_id}: {str(e)}")
            return None


# Global ZEP client instance
_zep_client = None


def get_zep_client() -> ZepClientWrapper:
    """Retorna instância global do cliente ZEP."""
    global _zep_client
    if _zep_client is None:
        _zep_client = ZepClientWrapper()
    return _zep_client
