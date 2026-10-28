from src.adapters.base import AdapterResult, BaseAdapter, CompanyTarget
from src.adapters.generic import GenericCareerPageAdapter
from src.adapters.greenhouse import GreenhouseAdapter
from src.adapters.lever import LeverAdapter

ADAPTERS = {
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "generic": GenericCareerPageAdapter,
}

__all__ = ["ADAPTERS", "AdapterResult", "BaseAdapter", "CompanyTarget",
           "GenericCareerPageAdapter", "GreenhouseAdapter", "LeverAdapter"]
