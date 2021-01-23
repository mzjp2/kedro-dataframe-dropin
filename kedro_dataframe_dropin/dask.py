"""The dask dropin for Kedro"""
try:
    import dask.dataframe as dd  # pylint: disable=import-error
except ImportError as ex:
    raise ImportError(
        "You need to install dask[dataframe] before using this dropin. "
        "See the dask documentation at https://dask.org."
    ) from ex

from kedro_dataframe_dropin.core import (
    DATASET_METHOD_MAPPINGS,
    patch_datasets,
    patch_io_methods,
)

datasets = patch_datasets(dd)
for dataset_name, dataset in datasets:
    globals()[dataset_name] = (
        patch_io_methods(dataset, dd)
        if dataset_name in DATASET_METHOD_MAPPINGS
        else dataset
    )
