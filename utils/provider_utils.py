import inspect
from typing import Optional, Type

def find_provider_class(module, base_class: Type) -> Optional[Type]:
    """
    Finds a class in the module that is a subclass of the base_class.
    
    Args:
        module: The module object to search in.
        base_class: The class type to look for subclasses of.
        
    Returns:
        The found subclass, or None if not found.
    """
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, base_class) and obj is not base_class:
            return obj
    return None
