# Caos Collector

## How to start development

  1. Setup VM with `vagrant up && vagrant ssh`
  2. Run collector cli with `tox -e venv -- <args>`

## How to build a release

Releases can be made by using the script `build_release.sh`, which
builds a release for HEAD. It will generate the file
`releases/caos_collector-<version>-py2-none-any.whl` containing the
wheel distribution.

The script `build_docker.sh` generates a minimal docker image to be used
for deployment.

## How to run in production

To run the container:
```
docker run --name caos-collector \
    -v <path to caos-collector.conf.yml>:/etc/caos/collector.conf.yaml:ro \
    caos-collector[:<tag>] <command>
```
