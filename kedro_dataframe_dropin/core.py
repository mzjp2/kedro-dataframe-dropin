"""Core functionality for kedro_dataframe"""
import importlib.util
import types
import warnings
from contextlib import contextmanager
from typing import List, Tuple

import fsspec
import pandas
from kedro.extras.datasets import pandas as kedro_pandas_module
from kedro.extras.datasets.pandas import __all__ as dataset_class_names
from kedro.io import AbstractDataSet


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


class FakeFilesystem:  # pylint: disable=too-few-public-methods
    "A dummy dropin for an fsspec filesystem"

    @staticmethod
    @contextmanager
    def open(path, **kwargs):
        """A dummy dropin for an fsspec filesystem open method.
        Forwards the path passed in rather than opening and reading in a buffer
        """
        if kwargs:
            warnings.warn("Filesystem arguments provided, they will be ignored.")
        yield path


def patch_datasets(pandas_dropin: types.ModuleType) -> List[Tuple[str, type]]:
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


def patch_dataset_filesystem(dataset: AbstractDataSet):
    """Patches the use of fsspec in Kedro datasets to simply use the filepath
    which modules like dask-cudf then use `fsspec` internally to read anyway.
    This is because file handles are hard to pass across workers
    (since they are not serializable) but filepaths are.
    """
    original_dataset_init = dataset.__init__

    def _fake_dataset_init(self, *args, **kwargs):
        original_dataset_init(self, *args, **kwargs)
        for attr_name, attr in self.__dict__.items():
            if isinstance(attr, fsspec.AbstractFileSystem):
                setattr(self, attr_name, FakeFilesystem)

    dataset.__init__ = _fake_dataset_init
    return dataset
