![logo](static/logo.png)

# kedro-dataframe-dropin

![github-action](https://github.com/mzjp2/kedro-dataframe-dropin/workflows/Lint%20and%20test/badge.svg)
![code-style](https://img.shields.io/badge/code%20style-black-000000.svg)
![license](https://img.shields.io/badge/License-MIT-green.svg)

## How do I get started?

```bash
$ pip install kedro-dataframe-dropin --upgrade
```

## Then what?

Replace your `pandas.*DataSet` in your `catalog.yml` with

```
kedro_dataframe_dropin.[rapids|modin].*DataSet
```

and reap the benefits, as long as your node and pipeline code is compatible with the `cudf`/`modin` API (that tries to replicate `pandas` as much as possible) and your data format is supported by the respective libraries (for example, `cudf` doesn't support the `read_excel` method)
## What is kedro-dataframe-dropin?

kedro-dataframe-dropin is a Kedro plugin that provides modified versions of the `pandas.*` dataset definitions (e.g `pandas.CSVDataSet`) from Kedro, where each dataset has been replaced with one of `pandas` drop-in replacements.

For example `kedro_dataframe_dropin.modin.CSVDataSet` replicates `pandas.CSVDataSet` but with the `modin.pandas` package replacing `pandas`. Likewise, `kedro_dataframe_dropin.rapids.CSVDataSet` provides a `cuDF`-backed version of the `CSVDataSet`.

## Why does this exist?

There might be several reasons why you'd want to consider a drop-in replacement for Pandas. The use-cases are outlined in various places, such as: the [modin documentation](http://modin.readthedocs.io) or [the RAPIDS website](https://rapids.ai).

However, the only dataframe-backed datasets that Kedro has out of the box are the `pandas` and `pyspark` ones. If you wanted to use, say, a `modin` dataframe backed by `Dask` or `Ray`, you'd need to write a [custom dataset](https://kedro.readthedocs.io/en/stable/07_extend_kedro/03_custom_datasets.html) for each file format (`.csv`, `.xls`, etc...).

This lets you swap out your `catalog.yml` from:

```yaml
# conf/base/catalog.yml [before]
rockets:
    type: pandas.CSVDataSet
    filepath: data/01_raw/rockets.csv

reviews:
    type: pandas.ExcelDataSet
    filepath: data/01_raw/reviews.xslsx
```

to:

```yaml
# conf/base/catalog.yml [after]
rockets:
    type: kedro_dataframe_dropin.rapids.CSVDataSet
    filepath: data/01_raw/rockets.csv

reviews:
    type: kedro_dataframe_dropin.modin.ExcelDataSet
    filepath: data/01_raw/reviews.xlsx
```

and as long as the code within your nodes fits within `modin` or `cudf`'s implementation of a subset of the `pandas` API, you'll be done!

## What dropins are currently supported?

| dropin       | supported |
| ------------ | --------- |
| modin[ray]   | ✅        |
| modin[dask]  | ✅        |
| cudf         | ✅        |
| dask         | 🟠        |
| dask-cudf    | 🟠        |

✅: compatible
🟠: No kedro versioning and some datasets (like `SQLTableDataSet`) don't work despite being available on both `kedro` and the drop-in.

## What happens when Kedro adds or changes a `pandas` dataset?

The beauty of it is that this will stay in complete sync with Kedro's `pandas.*` library without any code changes or releases required. It's implemented through hot-swapping the `pandas` module with one of the replacements you specified.

## Examples

As an example of why you might want to use this, here are the results of some very rough and preliminary benchmarking. These were conducted on a Google Colaboratory notebook (thanks Google!) with a Tesla T4 GPU and a 2-core CPU. The data used was a 5 million row CSV, weighing in at around a 100mb downloaded from [here](http://eforexcel.com/wp/downloads-18-sample-csv-files-data-sets-for-testing-sales/).

```
# base/conf/catalog.yml
cudf:
  type: kedro_dataframe_dropin.rapids.CSVDataSet
  filepath: data/01_raw/data.csv

pandas:
  type: pandas.CSVDataSet
  filepath: data/01_raw/data.csv
```

Using the two datasets within the `kedro ipython` console shows a world of difference, with reading the file in being 10x faster, doing a groupby being 6x faster and taking the mean being 5x faster.

This helps shorten:

* The feedback loop when prototyping and exploring your data within a `kedro ipython` or a `kedro jupyter` session
* The feedback loop when running your pipelines in development and debugging/experimenting with various different methodologies
* Your production runtime

```
In [1]: %timeit gdf = catalog.load("cudf")
702 ms ± 7.32 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)

In [2]: %timeit df = catalog.load("pandas")
8.22 s ± 101 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)

In [3]: %timeit gdf.groupby("Region")
4.75 µs ± 56.5 ns per loop (mean ± std. dev. of 7 runs, 100000 loops each)

In [4]: %timeit df.groupby("Region")
26.7 µs ± 397 ns per loop (mean ± std. dev. of 7 runs, 10000 loops each)

In [5]: %timeit df["Total Revenue"].mean()
11.8 ms ± 87.7 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)

In [6]: %timeit gdf["Total Revenue"].mean()
2.71 ms ± 31.3 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
```

Any additional benchmarks you do and want to share back would be much appreciated. Feel free to open an issue!

## Some special notes on RAPIDS

### The rest of the `cu*` ecosystem

Your data processing step gets faster (assuming you have the right conditions) by plugging in the `cudf` module from RAPIDs in place of `pandas`, but it doesn't end there.

You can continue to make use of your GPU speedup in the rest of your pipeline lifecycle (predictions, ML, graph, etc...) by using the rest of the `cuda` ecosystem of tools (`cuML` and the ilk) in place of tools like `sklearn`.

### Why are some data formats missing?

With the way this plugin was designed, it only hot swaps in `cudf` in place of `pandas` where the Kedro pandas dataset exists.

So as it stands today, with the Kedro codebase not having an `ORCDataSet` for example, this plugin won't have it either. You'll need to build your own custom own.

Or better yet, head over to the [Kedro](https;//github.com/quantumblacklabs/kedro) codebase and contribute the `pandas` version of it to their codebase. This plugin will then automatically pick it up and provide a `cudf`-equivalent.

## Some special notes on `dask-cuDF` and `dask`

Note that `dask` and `dask-cuDF` will delay compute and operations across nodes are actually building up a computation graph. They will be parallelised across your CPU/GPU when you invoke a `.compute()` operation (like `len` or save it to disk by having its output be a non-memory dataset in the catalog).

Note that Kedro versioning won't be possible with these datasets, since Kedro completely owns the I/O and simply passes the file handle down to `dask`/`dask-cuDF` which doesn't accept it - since file handles can't be shared across (CPU or GPU) workers. Instead what we do is extract the filepath and pass it to `dask` who also use `fsspec` and so you still have full remote-layer interopability with the benefit of parallelised compute.

Consider giving Matthew Rocklin's [blog post on `dask-cuDF`](http://matthewrocklin.com/blog/2019/01/13/dask-cudf-first-steps) and the philsophy of it simply being a different "engine" for `dask.DataFrame` a read.

## Caveats

Keep in mind that in order to remain consistent with the adage of not copying memory, when passing these dataframes between nodes, they _will not_ be copied - but simply passed through as the same underlying Python object, so if you're doing mutable operations on them across different nodes, keep in that in mind.
