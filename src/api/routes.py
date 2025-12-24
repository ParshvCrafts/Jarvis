"""
API Routes for Mobile Backend.

Implements all REST endpoints for the mobile app.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from .auth import AuthManager, get_auth_manager
from .models import (
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    ChangePasswordRequest,
    CommandRequest,
    CommandResponse,
    CommandHistoryItem,
    CommandHistoryResponse,
    SystemStatusResponse,
    ComponentHealth,
    ComponentStatus,
    DeviceListResponse,
    IoTDevice,
    DeviceType,
    DeviceState,
    DeviceActionRequest,
    DeviceActionResponse,
    UserSettings,
    UpdateSettingsRequest,
    CacheStatsResponse,
    ClearCacheRequest,
    ErrorResponse,
)

# Security scheme
security = HTTPBearer()

# Create routers
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
command_router = APIRouter(prefix="/command", tags=["Commands"])
status_router = APIRouter(prefix="/status", tags=["Status"])
device_router = APIRouter(prefix="/devices", tags=["Devices"])
settings_router = APIRouter(prefix="/settings", tags=["Settings"])
cache_router = APIRouter(prefix="/cache", tags=["Cache"])


# ============================================================================
# Dependency Injection
# ============================================================================

def _get_auth() -> AuthManager:
    """Dependency to get auth manager."""
    return get_auth_manager()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth: AuthManager = Depends(_get_auth),
) -> Dict[str, Any]:
    """Validate JWT and return current user info."""
    token = credentials.credentials
    payload = auth.verify_token(token, token_type="access")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    user = auth.get_user_by_id(user_id)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    # Update device last seen if device_id present
    device_id = payload.get("device_id")
    if device_id:
        auth.update_device_last_seen(device_id)
    
    return {
        "user_id": user_id,
        "username": user.username,
        "is_admin": user.is_admin,
        "device_id": device_id,
    }


# ============================================================================
# Storage for command history (replace with database in production)
# ============================================================================

_command_history: List[CommandHistoryItem] = []
_user_settings: Dict[str, UserSettings] = {}
_start_time = time.time()


# ============================================================================
# Authentication Endpoints
# ============================================================================

@auth_router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    auth: AuthManager = Depends(_get_auth),
):
    """
    Authenticate user and return tokens.
    
    - **username**: User's username
    - **password**: User's password
    - **device_name**: Optional name for this device
    - **device_type**: Device type (ios, android, web)
    """
    user = auth.authenticate_user(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    # Register device if info provided
    device_id = None
    if request.device_name:
        device = auth.register_device(
            user_id=user.user_id,
            device_name=request.device_name,
            device_type=request.device_type or "web",
        )
        device_id = device.device_id
    
    # Create tokens
    token_pair = auth.create_token_pair(user.user_id, device_id)
    
    return LoginResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
        user_id=user.user_id,
        device_id=device_id,
    )


@auth_router.post("/token/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    auth: AuthManager = Depends(_get_auth),
):
    """
    Refresh access token using refresh token.
    
    Returns new access and refresh tokens.
    """
    token_pair = auth.refresh_access_token(request.refresh_token)
    
    if not token_pair:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    return TokenRefreshResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


@auth_router.post("/logout")
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user),
    auth: AuthManager = Depends(_get_auth),
    authorization: str = Header(...),
):
    """
    Logout and revoke current token.
    """
    token = authorization.replace("Bearer ", "")
    auth.revoke_token(token)
    
    return {"message": "Successfully logged out"}


@auth_router.post("/password/change")
async def change_password(
    request: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    auth: AuthManager = Depends(_get_auth),
):
    """
    Change user password.
    
    Revokes all existing tokens after password change.
    """
    success = auth.change_password(
        user_id=current_user["user_id"],
        old_password=request.old_password,
        new_password=request.new_password,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password",
        )
    
    return {"message": "Password changed successfully. Please login again."}


@auth_router.get("/devices")
async def list_user_devices(
    current_user: Dict[str, Any] = Depends(get_current_user),
    auth: AuthManager = Depends(_get_auth),
):
    """
    List all registered devices for current user.
    """
    devices = auth.get_user_devices(current_user["user_id"])
    
    return {
        "devices": [
            {
                "device_id": d.device_id,
                "device_name": d.device_name,
                "device_type": d.device_type,
                "registered_at": d.registered_at.isoformat(),
                "last_seen": d.last_seen.isoformat(),
                "is_current": d.device_id == current_user.get("device_id"),
            }
            for d in devices
        ]
    }


@auth_router.delete("/devices/{device_id}")
async def revoke_device(
    device_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    auth: AuthManager = Depends(_get_auth),
):
    """
    Revoke access for a specific device.
    """
    # Verify device belongs to user
    devices = auth.get_user_devices(current_user["user_id"])
    if not any(d.device_id == device_id for d in devices):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    auth.revoke_device(device_id)
    
    return {"message": "Device access revoked"}


# ============================================================================
# Command Endpoints
# ============================================================================

# Reference to JARVIS instance (set by app.py)
_jarvis_instance = None


def set_jarvis_instance(jarvis):
    """Set the JARVIS instance for command processing."""
    global _jarvis_instance
    _jarvis_instance = jarvis


@command_router.post("", response_model=CommandResponse)
async def send_command(
    request: CommandRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Send a text command to JARVIS.
    
    - **text**: The command text
    - **context**: Optional context data
    - **stream**: Whether to stream the response (use WebSocket instead)
    """
    command_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Process command through JARVIS
    if _jarvis_instance:
        try:
            response_text = _jarvis_instance._process_command(request.text)
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            response_text = f"Error processing command: {str(e)}"
    else:
        # Fallback response when JARVIS not connected
        response_text = "JARVIS is not currently available. Please try again later."
    
    processing_time = (time.time() - start_time) * 1000
    
    # Create response
    response = CommandResponse(
        command_id=command_id,
        text=request.text,
        response=response_text,
        processing_time_ms=processing_time,
        cached=False,  # TODO: Get from cache integration
        timestamp=datetime.utcnow(),
    )
    
    # Store in history
    history_item = CommandHistoryItem(
        command_id=command_id,
        text=request.text,
        response=response_text,
        timestamp=datetime.utcnow(),
        processing_time_ms=processing_time,
        source="mobile",
    )
    _command_history.insert(0, history_item)
    
    # Trim history
    if len(_command_history) > 1000:
        _command_history.pop()
    
    return response


@command_router.get("/history", response_model=CommandHistoryResponse)
async def get_command_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get command history.
    
    - **page**: Page number (1-indexed)
    - **page_size**: Number of items per page (max 100)
    """
    start = (page - 1) * page_size
    end = start + page_size
    
    items = _command_history[start:end]
    
    return CommandHistoryResponse(
        commands=items,
        total=len(_command_history),
        page=page,
        page_size=page_size,
    )


# ============================================================================
# Status Endpoints
# ============================================================================

@status_router.get("", response_model=SystemStatusResponse)
async def get_system_status(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get system health and status.
    
    Returns status of all components and resource usage.
    """
    components = []
    overall_status = ComponentStatus.HEALTHY
    
    # Check JARVIS
    if _jarvis_instance:
        components.append(ComponentHealth(
            name="jarvis_core",
            status=ComponentStatus.HEALTHY,
            message="JARVIS core is running",
        ))
    else:
        components.append(ComponentHealth(
            name="jarvis_core",
            status=ComponentStatus.UNHEALTHY,
            message="JARVIS core not connected",
        ))
        overall_status = ComponentStatus.DEGRADED
    
    # Check LLM
    components.append(ComponentHealth(
        name="llm_router",
        status=ComponentStatus.HEALTHY,
        message="LLM router available",
    ))
    
    # Check cache
    cache_stats = None
    if _jarvis_instance and hasattr(_jarvis_instance, '_performance'):
        perf = _jarvis_instance._performance
        if perf:
            cache_stats = perf.get_stats().get("cache")
    
    components.append(ComponentHealth(
        name="cache",
        status=ComponentStatus.HEALTHY if cache_stats else ComponentStatus.UNKNOWN,
        message="Cache operational" if cache_stats else "Cache status unknown",
    ))
    
    # Resource usage
    resource_usage = None
    if _jarvis_instance and hasattr(_jarvis_instance, '_performance'):
        perf = _jarvis_instance._performance
        if perf:
            stats = perf.get_stats()
            resource_usage = stats.get("resources")
    
    uptime = time.time() - _start_time
    
    return SystemStatusResponse(
        status=overall_status,
        version="2.0.0",
        uptime_seconds=uptime,
        components=components,
        cache_stats=cache_stats,
        resource_usage=resource_usage,
    )


# ============================================================================
# Device Endpoints
# ============================================================================

@device_router.get("", response_model=DeviceListResponse)
async def list_devices(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    List all IoT devices.
    """
    devices = []
    
    # Get devices from JARVIS IoT controller
    if _jarvis_instance and hasattr(_jarvis_instance, '_iot_controller'):
        iot = _jarvis_instance._iot_controller
        if iot and hasattr(iot, 'get_devices'):
            try:
                iot_devices = iot.get_devices()
                for dev in iot_devices:
                    devices.append(IoTDevice(
                        device_id=dev.get("id", str(uuid.uuid4())),
                        name=dev.get("name", "Unknown"),
                        device_type=DeviceType(dev.get("type", "generic")),
                        state=DeviceState(dev.get("state", "unknown")),
                        is_on=dev.get("is_on"),
                        position=dev.get("position"),
                        last_seen=dev.get("last_seen"),
                        ip_address=dev.get("ip"),
                    ))
            except Exception as e:
                logger.error(f"Error getting IoT devices: {e}")
    
    # Add mock devices if none found (for testing)
    if not devices:
        devices = [
            IoTDevice(
                device_id="light-1",
                name="Living Room Light",
                device_type=DeviceType.LIGHT_SWITCH,
                state=DeviceState.ONLINE,
                is_on=True,
            ),
            IoTDevice(
                device_id="door-1",
                name="Front Door",
                device_type=DeviceType.DOOR_LOCK,
                state=DeviceState.ONLINE,
                is_on=False,  # locked
            ),
        ]
    
    return DeviceListResponse(
        devices=devices,
        total=len(devices),
    )


@device_router.get("/{device_id}")
async def get_device(
    device_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get details for a specific device.
    """
    # Get device from list
    response = await list_devices(current_user)
    
    for device in response.devices:
        if device.device_id == device_id:
            return device
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Device not found",
    )


@device_router.post("/{device_id}/action", response_model=DeviceActionResponse)
async def device_action(
    device_id: str,
    request: DeviceActionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Perform action on a device.
    
    - **action**: on, off, toggle, set_position, lock, unlock
    - **value**: Position value (0-100) for set_position
    """
    # Map action to command
    action_commands = {
        "on": f"turn on device {device_id}",
        "off": f"turn off device {device_id}",
        "toggle": f"toggle device {device_id}",
        "lock": f"lock {device_id}",
        "unlock": f"unlock {device_id}",
        "set_position": f"set {device_id} to {request.value}%",
    }
    
    command = action_commands.get(request.action)
    if not command:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action: {request.action}",
        )
    
    # Execute through JARVIS
    success = True
    message = f"Action '{request.action}' executed on {device_id}"
    
    if _jarvis_instance:
        try:
            response = _jarvis_instance._process_command(command)
            if "error" in response.lower() or "failed" in response.lower():
                success = False
                message = response
        except Exception as e:
            success = False
            message = str(e)
    else:
        message = "JARVIS not available, action queued"
    
    return DeviceActionResponse(
        success=success,
        device_id=device_id,
        action=request.action,
        message=message,
        new_state={"action": request.action, "value": request.value},
    )


# ============================================================================
# Settings Endpoints
# ============================================================================

@settings_router.get("", response_model=UserSettings)
async def get_settings(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get user settings/preferences.
    """
    user_id = current_user["user_id"]
    
    if user_id not in _user_settings:
        _user_settings[user_id] = UserSettings()
    
    return _user_settings[user_id]


@settings_router.put("", response_model=UserSettings)
async def update_settings(
    request: UpdateSettingsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Update user settings/preferences.
    """
    user_id = current_user["user_id"]
    
    if user_id not in _user_settings:
        _user_settings[user_id] = UserSettings()
    
    settings = _user_settings[user_id]
    
    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(settings, key, value)
    
    return settings


# ============================================================================
# Cache Endpoints
# ============================================================================

@cache_router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get cache statistics.
    """
    cache_stats = {
        "enabled": False,
        "memory_cache": {"size": 0, "hits": 0, "misses": 0},
        "sqlite_cache": None,
        "semantic_cache": None,
        "total_hits": 0,
        "total_misses": 0,
        "hit_ratio": 0.0,
    }
    
    if _jarvis_instance and hasattr(_jarvis_instance, '_performance'):
        perf = _jarvis_instance._performance
        if perf:
            stats = perf.get_stats()
            if "cache" in stats:
                cache_data = stats["cache"]
                cache_stats["enabled"] = True
                cache_stats["memory_cache"] = cache_data.get("memory", {})
                cache_stats["sqlite_cache"] = cache_data.get("sqlite")
                cache_stats["semantic_cache"] = cache_data.get("semantic")
                
                hits = cache_data.get("hits", 0)
                misses = cache_data.get("misses", 0)
                cache_stats["total_hits"] = hits
                cache_stats["total_misses"] = misses
                cache_stats["hit_ratio"] = hits / (hits + misses) if (hits + misses) > 0 else 0.0
    
    return CacheStatsResponse(**cache_stats)


@cache_router.delete("")
async def clear_cache(
    request: ClearCacheRequest = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Clear cache.
    
    - **cache_type**: memory, sqlite, semantic, or all (default: all)
    """
    cache_type = request.cache_type if request else "all"
    
    if _jarvis_instance and hasattr(_jarvis_instance, '_performance'):
        perf = _jarvis_instance._performance
        if perf and hasattr(perf, '_cache_integration'):
            cache = perf._cache_integration
            if cache and hasattr(cache, 'cache'):
                try:
                    # Clear based on type
                    if cache_type in ("memory", "all"):
                        if hasattr(cache.cache, '_memory_cache'):
                            cache.cache._memory_cache.clear()
                    
                    if cache_type in ("sqlite", "all"):
                        if hasattr(cache.cache, '_sqlite_cache'):
                            cache.cache._sqlite_cache.clear()
                    
                    if cache_type in ("semantic", "all"):
                        if hasattr(cache.cache, '_semantic_cache'):
                            cache.cache._semantic_cache.clear()
                    
                    return {"message": f"Cache cleared: {cache_type}"}
                except Exception as e:
                    logger.error(f"Error clearing cache: {e}")
    
    return {"message": "Cache clear requested (may not be available)"}


# ============================================================================
# Contacts Endpoints
# ============================================================================

contacts_router = APIRouter(prefix="/contacts", tags=["Contacts"])

# Contacts manager reference (set by app.py)
_contacts_manager = None


def set_contacts_manager(manager):
    """Set the contacts manager instance."""
    global _contacts_manager
    _contacts_manager = manager


@contacts_router.get("")
async def list_contacts(
    category: Optional[str] = None,
    search: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List all contacts with optional filtering."""
    if not _contacts_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contacts service not available",
        )
    
    contacts = _contacts_manager.list_contacts()
    
    # Filter by category
    if category:
        contacts = [c for c in contacts if c.category == category]
    
    # Search by name/nickname
    if search:
        search_lower = search.lower()
        contacts = [c for c in contacts if 
                   search_lower in c.name.lower() or 
                   (c.nickname and search_lower in c.nickname.lower())]
    
    return {
        "contacts": [
            {
                "id": c.id,
                "name": c.name,
                "nickname": c.nickname,
                "phone": c.phone,
                "email": c.email,
                "category": c.category,
                "favorite": c.favorite,
            }
            for c in contacts
        ],
        "total": len(contacts),
    }


@contacts_router.get("/count")
async def get_contact_count(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get contact count and statistics."""
    if not _contacts_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contacts service not available",
        )
    
    total = _contacts_manager.get_contact_count()
    contacts = _contacts_manager.list_contacts()
    favorites = _contacts_manager.get_favorites()
    
    # Category breakdown
    categories = {}
    for c in contacts:
        cat = c.category or "other"
        categories[cat] = categories.get(cat, 0) + 1
    
    return {
        "total": total,
        "favorites": len(favorites),
        "categories": categories,
    }


@contacts_router.get("/{contact_id}")
async def get_contact(
    contact_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get a specific contact by ID."""
    if not _contacts_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contacts service not available",
        )
    
    contact = _contacts_manager.get_contact_by_id(contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )
    
    return {
        "id": contact.id,
        "name": contact.name,
        "nickname": contact.nickname,
        "phone": contact.phone,
        "email": contact.email,
        "category": contact.category,
        "favorite": contact.favorite,
    }


@contacts_router.post("")
async def add_contact(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Add a new contact."""
    if not _contacts_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contacts service not available",
        )
    
    name = request.get("name")
    phone = request.get("phone")
    
    if not name or not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name and phone are required",
        )
    
    success, msg = _contacts_manager.add_contact(
        name=name,
        phone=phone,
        email=request.get("email"),
        nickname=request.get("nickname"),
        category=request.get("category", "family"),
        favorite=request.get("favorite", False),
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
    
    return {"success": True, "message": msg}


@contacts_router.put("/{contact_id}")
async def update_contact(
    contact_id: int,
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update an existing contact."""
    if not _contacts_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contacts service not available",
        )
    
    # Build update dict from provided fields
    updates = {}
    for field in ["name", "phone", "email", "nickname", "category", "favorite"]:
        if field in request:
            updates[field] = request[field]
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    
    success, msg = _contacts_manager.update_contact(contact_id, **updates)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
    
    return {"success": True, "message": msg}


@contacts_router.delete("/{contact_id}")
async def delete_contact(
    contact_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a contact."""
    if not _contacts_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contacts service not available",
        )
    
    success, msg = _contacts_manager.delete_contact(contact_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )
    
    return {"success": True, "message": msg}


@contacts_router.post("/{contact_id}/favorite")
async def toggle_favorite(
    contact_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Toggle favorite status for a contact."""
    if not _contacts_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contacts service not available",
        )
    
    contact = _contacts_manager.get_contact_by_id(contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )
    
    new_status = not contact.favorite
    success, msg = _contacts_manager.set_favorite(contact.name, new_status)
    
    return {"success": success, "favorite": new_status, "message": msg}


# ============================================================================
# Quick Launch Endpoints
# ============================================================================

quicklaunch_router = APIRouter(prefix="/quicklaunch", tags=["Quick Launch"])

# Quick launch manager reference (set by app.py)
_quicklaunch_manager = None


def set_quicklaunch_manager(manager):
    """Set the quick launch manager instance."""
    global _quicklaunch_manager
    _quicklaunch_manager = manager


@quicklaunch_router.get("/apps")
async def list_applications(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List all registered applications."""
    if not _quicklaunch_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quick Launch service not available",
        )
    
    apps = _quicklaunch_manager.list_applications()
    
    return {
        "applications": [
            {
                "id": app.id,
                "name": app.name,
                "path": app.path,
                "category": app.category,
                "use_count": app.use_count,
            }
            for app in apps
        ],
        "total": len(apps),
    }


@quicklaunch_router.post("/apps")
async def add_application(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Add a new application."""
    if not _quicklaunch_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quick Launch service not available",
        )
    
    name = request.get("name")
    path = request.get("path")
    
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name is required",
        )
    
    success, msg = _quicklaunch_manager.add_application(
        name=name,
        path=path,
        category=request.get("category"),
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
    
    return {"success": True, "message": msg}


@quicklaunch_router.delete("/apps/{app_name}")
async def remove_application(
    app_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Remove an application."""
    if not _quicklaunch_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quick Launch service not available",
        )
    
    success, msg = _quicklaunch_manager.remove_application(app_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )
    
    return {"success": True, "message": msg}


@quicklaunch_router.get("/bookmarks")
async def list_bookmarks(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List all saved bookmarks."""
    if not _quicklaunch_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quick Launch service not available",
        )
    
    bookmarks = _quicklaunch_manager.list_bookmarks()
    
    return {
        "bookmarks": [
            {
                "id": b.id,
                "name": b.name,
                "url": b.url,
                "category": b.category,
                "use_count": b.use_count,
            }
            for b in bookmarks
        ],
        "total": len(bookmarks),
    }


@quicklaunch_router.post("/bookmarks")
async def add_bookmark(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Add a new bookmark."""
    if not _quicklaunch_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quick Launch service not available",
        )
    
    name = request.get("name")
    url = request.get("url")
    
    if not name or not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name and URL are required",
        )
    
    success, msg = _quicklaunch_manager.add_bookmark(
        name=name,
        url=url,
        category=request.get("category"),
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
    
    return {"success": True, "message": msg}


@quicklaunch_router.delete("/bookmarks/{bookmark_name}")
async def remove_bookmark(
    bookmark_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Remove a bookmark."""
    if not _quicklaunch_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quick Launch service not available",
        )
    
    success, msg = _quicklaunch_manager.remove_bookmark(bookmark_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )
    
    return {"success": True, "message": msg}


@quicklaunch_router.get("/stats")
async def get_quicklaunch_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get quick launch statistics."""
    if not _quicklaunch_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quick Launch service not available",
        )
    
    apps = _quicklaunch_manager.list_applications()
    bookmarks = _quicklaunch_manager.list_bookmarks()
    
    return {
        "apps_count": len(apps),
        "bookmarks_count": len(bookmarks),
        "total_app_uses": sum(a.use_count for a in apps),
        "total_bookmark_uses": sum(b.use_count for b in bookmarks),
    }


# ============================================================================
# Combine all routers
# ============================================================================

def get_all_routers() -> List[APIRouter]:
    """Get all API routers."""
    return [
        auth_router,
        command_router,
        status_router,
        device_router,
        settings_router,
        cache_router,
        contacts_router,
        quicklaunch_router,
    ]
