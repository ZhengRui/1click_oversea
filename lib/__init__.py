from icecream import ic

# Import all pipeline modules to register them automatically
from . import pipelines
from .pipeline import Pipeline
from .registry import PipelineRegistry
from .slice import Slice

__all__ = ['Slice', 'Pipeline', 'PipelineRegistry', 'pipelines']

# Log successful registration
ic("Pipeline modules loaded and registered")
