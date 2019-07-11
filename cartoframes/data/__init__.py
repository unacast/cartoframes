"""Data namespace contains the class to manage your data: Dataset."""
from __future__ import absolute_import

from .dataset import Dataset, is_sql_query, is_geojson_file
from .dataset_info import DatasetInfo

__all__ = [
    'Dataset',
    'DatasetInfo',
    'is_sql_query',
    'is_geojson_file'
]
