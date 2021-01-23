"""Core functionality for kedro_dataframe"""
# pylint: disable=protected-access
import importlib.util
import types
from typing import List

import pandas
from kedro.extras.datasets import pandas as kedro_pandas_module
from kedro.extras.datasets.pandas import __all__ as dataset_class_names
from kedro.io import AbstractDataSet

DATASET_METHOD_MAPPINGS = {
    "CSVDataSet": ["read_csv", "to_csv"],
    "ExcelDataSet": ["read_excel", "to_excel"],
    "FeatherDataSet": ["read_feather", "to_feather"],
    "HDFDataSet": ["read_hdf", "to_hdf"],
    "JSONDataSet": ["read_json", "to_json"],
    "ParquetDataSet": ["read_parquet", "to_parquet"],
    "ORCDataSet": ["read_orc", "to_orc"],
}


def _collect_dataset_modules() -> List[types.ModuleType]:
    return [
        module
        for module in kedro_pandas_module.__dict__.values()
        if isinstance(module, types.ModuleType)
    ]


def _clone_dataset_modules() -> List[types.ModuleType]:
    dataset_modules = _collect_dataset_modules()

    module_clones = []
    for module in dataset_modules:
        module_clone = importlib.util.module_from_spec(module.__spec__)
        module.__spec__.loader.exec_module(module_clone)
        module_clones.append(module_clone)
    return module_clones


def patch_datasets(pandas_dropin: types.ModuleType) -> List[AbstractDataSet]:
    """Given a pandas dropin module, this iterates through all Kedro pandas modules,
    swaps out pandas for the pandas dropin specified and then extracts out the
    dataset definitions and returns it as a list of tuples of dataset names to
    their patched class types.

    Args:
        pandas_dropin: The module replacement for pandas (e.g modin or cudf)

    Returns:
        A list of tuples of dataset names and their patched class type.
    """
    patched_datasets = []

    module_clones = _clone_dataset_modules()
    for module_clone in module_clones:
        for attr_name, attr in module_clone.__dict__.items():
            if attr is pandas:
                setattr(module_clone, attr_name, pandas_dropin)
        for dataset_name in dataset_class_names:
            if hasattr(module_clone, dataset_name):
                patched_datasets.append(
                    (dataset_name, getattr(module_clone, dataset_name))
                )
    return patched_datasets


# pylint: disable=unused-argument
def patch_io_methods(
    dataset: AbstractDataSet, module_dropin: types.ModuleType
) -> AbstractDataSet:
    """Patches the load and save methods for things like dask and dask_cudf
    so that we bypass fsspec and instead pass the filepath straight to Dask
    (which internally uses fsspec anyway) but benefits from the fact that
    a string is serializable, and each Dask worker can read chunks of the file,
    rather than a single fsspec file handle/buffer which cannot be shared across
    processes/workers.
    """
    if dataset.__name__ in ("SQLTableDataSet", "GBQTableDataSet"):
        raise NotImplementedError("Datasets not supported yet")

    load_method = DATASET_METHOD_MAPPINGS[dataset.__name__][0]
    save_method = DATASET_METHOD_MAPPINGS[dataset.__name__][1]

    def _patched_load(self, *args, **kwargs):
        if self._version:
            raise ValueError("Does not work with versioning")
        return getattr(module_dropin, load_method)(
            self._filepath, storage_options=self._fs_open_args_load, **self._load_args
        )

    def _patched_save(self, data, *args, **kwargs):
        if self._version:
            raise ValueError("Does not work with versioning")
        self._fs_open_args_save.pop("mode", None)
        return getattr(data, save_method)(
            self._filepath, storage_options=self._fs_open_args_save, **self._save_args
        )

    dataset._load = _patched_load
    dataset._save = _patched_save
    return dataset
