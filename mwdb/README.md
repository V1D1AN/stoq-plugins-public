# MWDB

[stoQ](https://stoq-framework.readthedocs.io/en/latest/index.html) plugin that scans payloads using [Mwdb](https://github.com/CERT-Polska/mwdb-core)

## Plugin Classes

- [Worker](https://stoq-framework.readthedocs.io/en/latest/dev/workers.html)

## Configuration

All options below may be set by:

- [plugin configuration file](https://stoq-framework.readthedocs.io/en/latest/dev/plugin_overview.html#configuration)
- [`stoq` command](https://stoq-framework.readthedocs.io/en/latest/gettingstarted.html#plugin-options)
- [`Stoq` class](https://stoq-framework.readthedocs.io/en/latest/dev/core.html?highlight=plugin_opts#using-providers)

### Options

- `mwdb_url` [str]: URL for Falcon Sandbox

- `apikey` [str]: Falcon Sandbox API key
