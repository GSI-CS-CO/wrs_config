# wrs_config
Script tool to generate WRS configurations

## Overview

The tool is used to generate configuration files (dot-config_*) for dedicated WRS layers used in GSI WR Timing Networks:
- Grand Master
- Service
- Local Master
- Distribution
- Access (and its special cases)

## Structure

The tool consists of a set of items (VLAN definition, WRS layers, port roles and default configuration object), Python modules to generate configuration objects (JSON) and WRS port-models (in DOT and SVG). For more details on items refer to [Network: White Rabbit Installation](https://www-acc.gsi.de/wiki/Timing/Intern/TimingSystemNetworkWRInstallation). It also uses an external tool from CERN: WRS configuration generator.

The tool directory contents are:
- items: vlans.json, switch_layers.json, port_roles.json, dot-config.json
- configuration object generator: make_config_obj.py
- WRS port-model generator: make_port_model.py
- desired switch roles: switches.json
- generated configurations and objects: dot-config_* in 'output' sub-directory

## Workflow

The WRS configuration is generated in two steps. User needs to supply required switch roles in 'switches.json'.

In the first step, the configuration object generator produces so-called configuration objects in JSON. For that object generator uses provided items. The items are templates defined by WRS experts.

> *Switch roles* -> **configuration object generator** -> *configuration objects (JSON)*

In the next step, the desired switch configurations are generated with the CERN tool.

> *Configuration objects* -> **CERN configuration generator** -> *configurations (dot-config_*)*

Optionally, one can make WRS port-model from the generated configuration. The port-models are actually designated to visualize the VLAN configuration of WRS.

> *Configuration* -> **port-model generator** -> *port-model (DOT, SVG)*

## Installation

A host with Python (2.7) and pydot package is required!

1. Download the repo.

```
git clone https://github.com/GSI-CS-CO/wrs_config --recursive
```

## Usage

In order to generate pre-defined configurations, invoke following make commands:

```
make clean
make all
```

It will produce WRS configurations in 'output/config' sub-directory.
An another remote Git repository, wrs_tn2_configuration, which contains generated WRS configurations, is embedded as submodule.
Once user is confident with newly generated dot-configs, they have to committed manually into the submodule repository.

## Which Packages are Required?

### System

```
(sudo) apt install whois
```

### Python

```
(sudo) pip install requests
(sudo) pip install pydot
```
