# Caos Collector

## How to start development

  1. Setup VM with `vagrant up && vagrant ssh`
  2. Run collector cli with `tox -e venv -- <args>`

## How to build a release

Releases can be made by using the script `build_release.sh`. To make a
release for HEAD just run `build_release.sh` without arguments. It will
generate a `.tar.gz` archive under the `releases` directory (made
through `git archive`) together with a wheel distribution.

The same script can be used to generate a release for a tag or commit
different from HEAD by using the `-t` argument: `build_release.sh -t
<tag>` or `build_release.sh -t <commit>`.

At the end the script generates also a minimal docker image to be used
to deploy the collector.
