# Import directly from the registry.py file to avoid circular imports
import importlib.util
import os

# Load registry.py as a module
registry_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'registry.py')
spec = importlib.util.spec_from_file_location("tools_registry", registry_file)
registry_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry_module)

# Extract the needed items
TOOL_REGISTRY = registry_module.TOOL_REGISTRY
TOOL_CATEGORIES = registry_module.TOOL_CATEGORIES
get_tool_descriptions_for_prompt = registry_module.get_tool_descriptions_for_prompt
get_tools_by_category = registry_module.get_tools_by_category
CONTEXT_HINTS = registry_module.CONTEXT_HINTS

# Now import the loaders
from tools.registry.dynamic_loader import DynamicToolRegistry
from tools.registry.enhanced_dynamic_loader import EnhancedDynamicToolRegistry

__all__ = [
    'DynamicToolRegistry',
    'EnhancedDynamicToolRegistry',
    'TOOL_REGISTRY',
    'TOOL_CATEGORIES',
    'get_tool_descriptions_for_prompt',
    'get_tools_by_category',
    'CONTEXT_HINTS'
]