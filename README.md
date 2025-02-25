# Python and commandline client for NRP repositories

Note: At this time, only the Invenio repositories are supported.
The client uses a pluggable architecture to support other repository types.

## Installation

```bash
uv venv --python=python3.12 nrp-cmd-venv
source nrp-cmd-venv/bin/activate
uv pip install nrp-cmd
```

## Usage

```bash
nrp-cmd create record '{"title": "abc"}' --set r
nrp-cmd upload file @r ~/Downloads/ubuntu-24.04-desktop-amd64.iso
nrp-cmd list records "metadata.title:abc"
nrp-cmd get record @r
nrp-cmd delete record @r
```