"""The modin dropin for Kedro"""
try:
    import modin.pandas as modin_pandas  # pylint: disable=import-error
except ImportError as ex:
    raise ImportError(
        "You need to install modin before using this dropin. "
        "See the modin documentation at https://modin.readthedocs.io."
    ) from ex

from kedro_dataframe_dropin.core import patch_datasets

datasets = patch_datasets(modin_pandas)
for dataset_name, dataset in datasets:
    globals()[dataset_name] = dataset
