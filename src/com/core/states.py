"""
State machine for Gamma bot.
"""
from typing import Dict, Optional, Any

_states: Dict[int, Dict[str, Any]] = {}

def set_state(user_id: int, estado: str, datos: Optional[Dict[str, Any]] = None) -> None:
    """
    Sets the state for a given user.
    
    Args:
        user_id: The Telegram user ID.
        estado: The state string.
        datos: Optional dictionary with state data.
    """
    if datos is None:
        datos = {}
    _states[user_id] = {'estado': estado, 'datos': datos}

def get_state(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Gets the state for a given user.
    
    Args:
        user_id: The Telegram user ID.
        
    Returns:
        The state dictionary containing 'estado' and 'datos', or None if no state is set.
    """
    return _states.get(user_id)

def clear_state(user_id: int) -> None:
    """
    Clears the state for a given user.
    
    Args:
        user_id: The Telegram user ID.
    """
    if user_id in _states:
        del _states[user_id]

def has_state(user_id: int) -> bool:
    """
    Checks if a user has a state set.
    
    Args:
        user_id: The Telegram user ID.
        
    Returns:
        True if the user has a state, False otherwise.
    """
    return user_id in _states
