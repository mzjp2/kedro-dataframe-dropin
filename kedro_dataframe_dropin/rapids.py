"""The cuDF dropin for Kedro"""
try:
    import cudf  # pylint: disable=import-error
except ImportError as ex:
    raise ImportError(
        "You need to install cuDF before using this dropin. "
        "See the cuDF documentation at https://rapids.ai/start.html."
    ) from ex

from kedro_dataframe_dropin.core import patch_datasets

datasets = patch_datasets(cudf)
for dataset_name, dataset in datasets:
    globals()[dataset_name] = dataset
