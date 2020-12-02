[![CircleCI](https://circleci.com/gh/logdna/ansible-logdna.svg?style=svg)](https://circleci.com/gh/logdna/ansible-logdna)

# Deploy LogDNA Agent with Ansible

## Description
Ansible Galaxy Role to install and configure LogDNA Agent

## Requirements
* Ansible version: `>=2.1`
* Tested on the following Operating Systems:
    * CentOS 6
    * CentOS 7
    * Ubuntu 12.04 - Precise
    * Ubuntu 14.04 - Trusty
    * Ubuntu 16.04 - Xenial
    * Ubuntu 17.10 - Artful
    * Debian 8 - Jessie

## Role Variables
### Task-specific Variables
* `agent_install`: `true` if to be installed (default: `true`)
* `agent_config`: `true` if to be configured (default: `true`)
* `agent_service`: (default: `started`), supporting:
    * `started`: to start LogDNA Agent Service if `conf_key` is specified
    * `restarted`: to restart LogDNA Agent Service
    * `stopped`: to stop LogDNA Agent Service.

### Configuration Variables
These variables map directly to the native configuration options for the LogDNA Agent:
* `conf_key`: LogDNA Ingestion Key - LogDNA Agent service will not start if `conf_key` is not specified
* `conf_config`: File Path for the LogDNA Agent configuration (defaults to `/etc/logdna.conf`)
* `conf_logdir`: Log Directories to be added
* `conf_logfile`: Log Files to be added
* `conf_exclude`: Log Files or Directories to be excluded
* `conf_exclude_regex`: Exclusion Rule for Log Lines
* `conf_hostname`: Alternative host name to be used
* `conf_tags`: Tags to be added.

## How to Install
* Online from Ansible Galaxy: `ansible-galaxy install logdna.logdna`
* Directly from Source Code: `ansible-galaxy install git+https://github.com/logdna/ansible-logdna.git`

## Example Playbook
```bash
- hosts: <hosts>
  vars:
    conf_key: <LogDNA Ingestion Key>
  roles:
     - { role: logdna.logdna }
```

## Use Cases
* To install, configure, and start the service on specified hosts:
```bash
- hosts: <hosts>
  vars:
    conf_key: <LogDNA Ingestion Key>
    # All other configuration parameter specifications
  roles:
     - { role: logdna.logdna }
```
* To reconfigure and restart the service on specified hosts:
```bash
- hosts: <hosts>
  vars:
    # reconfiguration parameter specifications
    agent_service: restarted
  roles:
     - { role: logdna.logdna }
```
* Just install but don't configure or touch the service:
```bash
- hosts: <hosts>
  vars:
    # do not set LogDNA Ingestion Key
    agent_config: false
  roles:
     - { role: logdna.logdna }
```
* Stop the service:
```bash
- hosts: <hosts>
  vars:
    agent_install: false
    agent_config: false
    agent_service: stopped
  roles:
     - { role: logdna.logdna }
```

## LogDNA Callback Plugin

LogDNA Callback Plugin is a handler that can send the logs from each `ansible-playbook` run to LogDNA. Currently the ansible v2 event categories are supported: `FAILED`, `OK`, `UNREACHABLE`, `SKIPPED`. It can be installed with the following steps:
* Download the plugin from [here](https://raw.githubusercontent.com/logdna/ansible-logdna/master/lib/ansible/plugins/callback/logdna.py) into the folder of callback plugins. You can find the folder with the following command: `echo $(ansible-doc -F | awk 'FNR == 1 {print $2}' | sed 's/\/modules/+/g' | cut -d'+' -f 1)/plugins/callback`
* If there is no `ansible.cfg` on your system, do the following steps:
  * Make sure `/etc/ansible` folder exists by doing `mkdir -p /etc/ansible`
  * Download `ansible.cfg` from [here](https://raw.githubusercontent.com/ansible/ansible/devel/examples/ansible.cfg) into `/etc/ansible/`
* Do `ANSIBLE_CONFIG=< Path to ansible.cfg >`
* Open `ansible.cfg` and do the following steps:
  * Uncomment the line containing `callback_whitelist`, if commented, and append `logdna`
  * Uncomment the line containing `callback_plugins`, if commented, and update the path to Callback Plugins
* In order to make the plugin working, the following environmental variables should be set:
  * `LOGDNA_INGESTION_KEY`: LogDNA Ingestion Key in order to stream the logs - **required**
  * `LOGDNA_APPNAME`: Override the default app name for log messages `Ansible` by default - **optional**
  * `LOGDNA_DISABLE_LOGLEVELS`: Do not send events with log levels; `False` by default - **optional**
  * `LOGDNA_IGNORE_FAILED`: Whether to ignore failed tasks or not; `False` by default - **optional**
  * `LOGDNA_IGNORE_OK`: Whether to ignore OK tasks or not; `False` by default - **optional**
  * `LOGDNA_IGNORE_SKIPPED`: Whether to ignore skipped tasks or not; `False` by default - **optional**
  * `LOGDNA_IGNORE_UNREACHABLE`: Whether to ignore unreachable tasks or not; `False` by default - **optional**
  * `LOGDNA_HOST`: Use alternative logging endpoint host, `logs.logdna.com` by default - **optional**
  * `LOGDNA_ENDPOINT`: Use alternative logging endpoint resouce, `/logs/ingest` by default - **optional**
  * `LOGDNA_HOSTNAME`: Alternative Host Name to be used in the logs - **optional**
  * `LOGDNA_TAGS`: Comma-separated list of tags; `ansible` by default - **optional**
  * `LOGDNA_LOG_FORMAT`: Override the default line message format - **optional**

Environment variables can also be placed in your `ansible.cfg` with the variables being all lowercase. For example:
```
[callback_logdna]
logdna_ingestion_key = ffffffffffffffffffffffffffffffffff
logdna_log_format = action={action} changed={changed} host={host} playbook={playbook} role={role} status={status} {name}
```

## Contributing

Contributions are always welcome. See the [contributing guide](https://github.com/logdna/ansible-logdna/blob/master/CONTRIBUTING.md) to learn how you can help.

## License and Authors

* Authors:
  * [Samir Musali](https://github.com/ldsamir), LogDNA
  * [Jonathan Kelley](https://github.com/jondkelley), LogDNA
* License: MIT
