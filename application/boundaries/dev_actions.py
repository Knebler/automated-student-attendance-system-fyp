"""Registry for dev-exposed actions.

This module provides a simple decorator/registration API so boundaries
or other modules can expose functions (callables) to the developer
testing UI at /dev/test-endpoint.

Each action entry must provide a callable that accepts (app, **kwargs)
so the dev endpoint can invoke it with the current Flask app.
"""
from typing import Callable, Dict, List

_ACTIONS: Dict[str, Dict] = {}

def register_action(name: str, func: Callable, params: List[dict], description: str = ''):
    """Register a dev action.

    - name: unique string id for the action
    - func: callable(app, **kwargs) -> result
    - params: list of parameter dicts { name, label?, placeholder? }
    - description: short help text
    """
    if params is None:
        params = []

    _ACTIONS[name] = {
        'name': name,
        'func': func,
        'params': params,
        'description': description
    }

def get_actions():
    """Return a list of registered action metadata dicts."""
    return list(_ACTIONS.values())

def get_action(name: str):
    """Return the action metadata (or None)."""
    return _ACTIONS.get(name)


# Built-in echo action
def _echo(app, message=None, **_kwargs):
    return message or ''

register_action(
    'echo',
    _echo,
    params=[{'name': 'message', 'label': 'Message', 'placeholder': 'Plain text message to echo back'}],
    description='Echo back a provided message (dev friendly)'
)
