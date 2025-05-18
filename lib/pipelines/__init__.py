"""
Pipeline module collection for data extraction from various platforms.
"""

# Import all pipeline modules to make them available when importing the pipelines package
from . import alibaba_1688

# For direct imports like `from lib.pipelines import alibaba_1688`
__all__ = ['alibaba_1688']
