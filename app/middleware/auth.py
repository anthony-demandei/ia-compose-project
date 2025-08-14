"""
API Key Authentication Middleware for Demandei Platform.
Provides fixed API key validation for the IA Compose API.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.utils.config import get_settings

# Initialize HTTP Bearer token security with auto_error=False to handle missing credentials
security = HTTPBearer(auto_error=False)


class APIKeyAuth:
    """API Key authentication handler for Demandei platform."""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.demandei_api_key
        # Allow test keys and development keys
        if not self.api_key or self.api_key == "your_demandei_api_key_here":
            raise ValueError("DEMANDEI_API_KEY environment variable not properly configured")
    
    def verify_api_key(self, credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> bool:
        """
        Verify if the provided API key is valid for Demandei platform.
        
        Args:
            credentials: HTTP Bearer credentials from request header (optional)
            
        Returns:
            bool: True if API key is valid
            
        Raises:
            HTTPException: If API key is invalid or missing
        """
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if credentials.credentials != self.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return True


# Global API key authentication instance (lazy initialization)
_api_key_auth = None


def get_api_key_auth() -> APIKeyAuth:
    """Dependency to get API key authentication instance."""
    global _api_key_auth
    if _api_key_auth is None:
        _api_key_auth = APIKeyAuth()
    return _api_key_auth


def verify_demandei_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> bool:
    """
    FastAPI dependency for API key verification.
    
    Usage:
        @router.post("/endpoint")
        async def protected_endpoint(
            request: RequestModel,
            authenticated: bool = Depends(verify_demandei_api_key)
        ):
            # Endpoint logic here
            pass
    
    Args:
        credentials: HTTP Bearer credentials from request
        
    Returns:
        bool: True if authentication successful
        
    Raises:
        HTTPException: If authentication fails
    """
    return get_api_key_auth().verify_api_key(credentials)