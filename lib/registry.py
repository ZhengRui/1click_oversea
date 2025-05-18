from typing import Dict, List, Optional

from .pipeline import Pipeline


class PipelineRegistry:
    """
    Registry for storing and retrieving common pipelines.
    """

    _registry: Dict[str, Pipeline] = {}

    @classmethod
    def register(cls, name: str, pipeline: Pipeline) -> None:
        """Register a pipeline with a given name."""
        cls._registry[name] = pipeline

    @classmethod
    def get(cls, name: str) -> Optional[Pipeline]:
        """Get a registered pipeline by name."""
        return cls._registry.get(name)

    @classmethod
    def list_pipelines(cls) -> List[str]:
        """List all registered pipeline names."""
        return list(cls._registry.keys())

    @classmethod
    def register_pipeline(cls, name: str = None):
        """Decorator to register a pipeline factory function."""

        def decorator(func):
            pipeline = func()
            registry_name = name or pipeline.name
            cls.register(registry_name, pipeline)
            return func

        return decorator
