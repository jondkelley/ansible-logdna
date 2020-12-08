# -*- coding: utf-8 -*-
# (c) 2020, Jonathan Kelley <jonathan.kelley@logdna.com>
# This file belongs as part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import (absolute_import, division, print_function)
__LEGACY_PYTHON__ = False
from ansible.module_utils.urls import open_url
from ansible.plugins.callback import CallbackBase
from datetime import datetime
from os.path import basename
from time import time
from urllib.parse import urlencode
from getpass import getuser
from json import dumps as json_dumps
from socket import (gethostname, socket, gethostbyname, AF_INET, SOCK_DGRAM)
from string import Formatter
from uuid import uuid4
from uuid import getnode

__metaclass__ = type

__CALLBACK_NAME__ = 'logdna'
__CALLBACK_VERSION__ = 2.0

DOCUMENTATION = '''
    callback: logdna
    type: aggregate
    short_description: Callback plugin that logs to the LogDNA logging platform
    author: "Jonathan Kelley <jonk@omg.lol>"
    description:
      - This ansible callback plugin sends ansible task results to the LogDNA logging service.
    version_added: "2.0"
    requirements:
      - This callback must be in the ansible.cfg callback_whitelist to function
      - You must have a LogDNA account, https://logdna.com/sign-up/
      - You must provide your LogDNA Ingestion Key (found in your settings under API Keys)
    options:
      logdna_appname:
        description: Set the LogDNA application name, default Ansible
        env:
          - name: LOGDNA_APPNAME
        ini:
          - section: callback_logdna
            key: logdna_appname
      logdna_endpoint:
        description: Optional, API endpoint resource to use, default /logs/ingest
        env:
          - name: LOGDNA_ENDPOINT
        ini:
          - section: callback_logdna
            key: logdna_endpoint
      logdna_disable_loglevels:
        description: Optional, does not send the log levels for use in the LogDNA web UI display
        env:
          - name: LOGDNA_DISABLE_LOGLEVELS
        ini:
          - section: callback_logdna
            key: logdna_disable_loglevels
      logdna_host:
        description: Optional, API hostname to forward logs to, default logs.logdna.com
        env:
          - name: LOGDNA_HOST
        ini:
          - section: callback_logdna
            key: logdna_host
      logdna_hostname:
        description: Optional, override the default log source hostname to this value
        env:
          - name: LOGDNA_HOSTNAME
        ini:
          - section: callback_logdna
            key: logdna_hostname
      logdna_ignore_failed:
        description: Optional, do not log tasks that FAIL
        env:
          - name: LOGDNA_IGNORE_FAILED
        ini:
          - section: callback_logdna
            key: logdna_ignore_failed
      logdna_ignore_ok:
        description: Optional, do not log tasks that are OK
        env:
          - name: LOGDNA_IGNORE_OK
        ini:
          - section: callback_logdna
            key: logdna_ignore_ok
      logdna_ignore_skipped:
        description: Optional, do not log tasks that are SKIPPED
        env:
          - name: LOGDNA_IGNORE_SKIPPED
        ini:
          - section: callback_logdna
            key: logdna_ignore_skipped
      logdna_ignore_unreachable:
        description: Optional, do not log tasks that were UNREACHABLE
        env:
          - name: LOGDNA_IGNORE_UNREACHABLE
        ini:
          - section: callback_logdna
            key: logdna_ignore_unreachable
      logdna_ingestion_key:
        description: Required, ingestion key used to authenticate against the LogDNA ingestion endpoint
        env:
          - name: LOGDNA_INGESTION_KEY
        ini:
          - section: callback_logdna
            key: logdna_ingestion_key
      logdna_ip_address:
        description: Optional, override the detected system IP in your log source with an alternate value
        env:
          - name: LOGDNA_IP_ADDRESS
        ini:
          - section: callback_logdna
            key: logdna_ip_address
      logdna_log_format:
        description: Optional, override the default log line formatting to your own custom format
        env:
          - name: LOGDNA_LOG_FORMAT
        ini:
          - section: callback_logdna
            key: logdna_log_format
      logdna_mac_address:
        description: Optional, override the detected system MAC address in your log source with an alternate value
        env:
          - name: LOGDNA_MAC_ADDRESS
        ini:
          - section: callback_logdna
            key: logdna_mac_address
      logdna_tags:
        description: Optional, single tag or comma-seperated list of tags to optionally include with log events
        env:
          - name: LOGDNA_TAGS
        ini:
          - section: callback_logdna
            key: logdna_tags
      logdna_use_target_host_for_hostname:
        description: Optional, use the ansible targeted host for the hostname in log messages rather then the ansible controller hostname
        env:
          - name: LOGDNA_USE_TARGET_HOST_FOR_HOSTNAME
        ini:
          - section: callback_logdna
            key: logdna_use_target_host_for_hostname
'''

EXAMPLES = '''
examples: >
  To enable this callback, add this to your ansible.cfg file in the defaults block
    [defaults]
    callback_whitelist = logdna
  Set the environment variable
    export LOGDNA_INGESTION_KEY=ffffffffffffffffffffffffffffffffff
    export LOGDNA_TAGS=example_tag1,example_tag2,example_tag3
    export LOGDNA_APPNAME=example_ansible_project
    export LOGDNA_LOG_FORMAT="action={action} changed={changed} host={host} playbook={playbook} role={role} status={status} {name}"
  Or, set the ansible.cfg variables in the callback_logdna block
    [callback_logdna]
    logdna_ingestion_key = ffffffffffffffffffffffffffffffffff
    logdna_tags = example_tag1,example_tag2,example_tag3
    logdna_appname = example_ansible_project
    logdna_log_format = action={action} changed={changed} host={host} playbook={playbook} role={role} status={status} {name}
'''


def get_local_hostname():
    """
    get hostname of ansible runner host
    """
    return str(gethostname()).split('.local')[0]


def get_hwaddr():
    """
    get hardware (MAC) address of ansible runner host
    """
    mac = "%012x" % getnode()
    return ":".join(map(lambda index: mac[index:index + 2],
                        range(int(len(mac) / 2))))


def get_ipaddr():
    """
    get local ip address of ansible runner host
    """
    try:
        return gethostbyname(get_local_hostname())
    except BaseException:
        s = socket(AF_INET, SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except BaseException:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP


class SafeFormat(Formatter):
    """
    a minimal safe formatter to prevent access
    to internal attributes of python objects
    https://lucumr.pocoo.org/2016/12/29/careful-with-str-format/
    """

    def get_field(self, field_name, args, kwargs):
        if ('.' in field_name
            or '[' in field_name
                or '(' in field_name):
            raise Exception('Invalid string formatting used '
                            'with option `logdna_log_format` '
                            'Fields cannot contain characters'
                            ' such as: . [ (')
        return super().get_field(field_name, args, kwargs)


class LogDNAHTTPIngestEndpoint():
    """
    agent class to marshallize structured ansible results of
    play state to the logdna http ingestion endpoint
    """

    def __init__(self):
        self.ansible_check_mode = False
        self.ansible_playbook = ''
        self.ansible_version = ''
        self.session = str(uuid4())
        self.host = get_local_hostname()
        self.ip_address = get_ipaddr()
        self.user = getuser()

    def send_logdna(self, conf_appname, conf_endpoint,
                    conf_disable_loglevel, conf_host, conf_hostname,
                    conf_ingestion_key, conf_ip_addr, conf_log_fmt,
                    conf_mac_addr, conf_tags, state, result, exectime):
        datetime_now = time()
        iso_now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        if result._task_fields['args'].get('_ansible_check_mode'):
            self.ansible_check_mode = True

        if result._task_fields['args'].get('_ansible_version'):
            self.ansible_version = \
                result._task_fields['args'].get('_ansible_version')

        if result._task._role:
            ansible_role = str(result._task._role)
        else:
            ansible_role = None

        if result._result.get('ansible_facts'):
            timestamp = result._result.get('ansible_facts', None).get(
                'ansible_date_time', None).get('iso8601', None)
        else:
            timestamp = iso_now

        if not conf_hostname:
            # if conf_hostname is none, use ansible target host for name
            conf_hostname = result._host.name

        meta = dict()
        meta['ansible_changed'] = result._result.get('changed')
        meta['ansible_check_mode'] = self.ansible_check_mode
        meta['ansible_host'] = result._host.name
        meta['ansible_playbook'] = self.ansible_playbook
        meta['ansible_result'] = result._result
        meta['ansible_role'] = ansible_role
        meta['ansible_session'] = self.session
        meta['ansible_status'] = state
        meta['ansible_task'] = result._task_fields
        meta['ansible_version'] = self.ansible_version
        meta['ansible_execution_time'] = exectime
        meta['system_host'] = self.host
        meta['system_ip'] = self.ip_address
        meta['system_user'] = self.user
        meta['uuid'] = result._task._uuid

        # objects accessible to log message format conversion
        # most other internal objects will be restricted because
        # of the SafeFormat() class
        action = meta['ansible_task'].get('action')
        ansible_version = meta['ansible_version']
        changed = meta['ansible_changed']
        check_mode = meta['ansible_check_mode']
        execution_time = meta['ansible_execution_time']
        host = meta['ansible_host']
        ip = meta['system_ip']
        name = result._task_fields.get('name', None)
        if not name:
            name = ''
        session = meta['ansible_session']
        user = meta['system_user']
        uuid = meta['uuid']
        playbook = meta['ansible_playbook']
        role = meta['ansible_role']
        status = meta['ansible_status']

        if conf_log_fmt:
            fmt = conf_log_fmt
        else:
            fmt = ('status={status} '
                   'action={action} '
                   'changed={changed} '
                   'play={playbook} '
                   'role={role} '
                   'host={host} '
                   'name={name}'
                   )

        safe = SafeFormat()
        log_message = safe.format(fmt,
                                  action=action,
                                  changed=changed,
                                  host=host,
                                  playbook=playbook,
                                  role=role,
                                  status=status,
                                  name=name).strip()

        logline = {
            'lines': [
                {
                    'line': log_message,
                    'timestamp': timestamp,
                    'app': conf_appname,
                    'meta': meta,
                }
            ]
        }

        loglevels = {
            'OK': 'INFO',
            'SKIPPED': 'WARN',
            'FAILED': 'ERROR',
            'UNREACHABLE': 'WARN',
        }
        if not conf_disable_loglevel:
            loglevel = loglevels.get(state, 'UNKNOWN')
            logline['lines'][0]['level'] = loglevel

        if conf_ip_addr:
            logline['lines'][0]['ip'] = conf_ip_addr

        if conf_mac_addr:
            logline['lines'][0]['mac'] = conf_mac_addr

        request_json = json_dumps(logline, sort_keys=True)

        request_params = {
            'hostname': conf_hostname,
            'now': datetime_now,
        }

        if conf_tags:
            urlparams['tags'] = conf_tags

        request_uri = 'https://{host}{endpoint}?{params}'.format(
            host=conf_host,
            endpoint=conf_endpoint,
            params=urlencode(request_params))

        user_agent = 'ansible-callback/{version}'.format(
            version=__CALLBACK_VERSION__)

        headers = {
            'content-type': 'application/json; charset=UTF-8'
        }
        open_url(
            request_uri,
            request_json,
            force_basic_auth=True,
            headers=headers,
            http_agent=user_agent,
            method='POST',
            timeout=5,
            url_username=conf_ingestion_key,
            validate_certs=True,
        )


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = __CALLBACK_VERSION__
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = __CALLBACK_NAME__
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self, display=None):
        super(CallbackModule, self).__init__(display=display)
        self.start_datetimes = {}  # Collect task start times
        self.logdna_callback = LogDNAHTTPIngestEndpoint()
        self.defaults = {
            'logdna_appname': 'Ansible',
            'logdna_endpoint': '/logs/ingest',
            'logdna_host': 'logs.logdna.com',
        }

    def _execution_timer(self, result):
        """
        timer helper method
        """
        return (
            datetime.utcnow() -
            self.start_datetimes[result._task._uuid]
        ).total_seconds()

    def _handle_event(self, status, result):
        """
        call logdna helper method
        """
        self.logdna_callback.send_logdna(
            self.conf_appname,
            self.conf_endpoint,
            self.conf_disable_loglevel,
            self.conf_host,
            self.conf_hostname,
            self.conf_ingestion_key,
            self.conf_ip_addr,
            self.conf_log_fmt,
            self.conf_mac_addr,
            self.conf_tags,
            status,
            result,
            self._execution_timer(result)
        )

    def set_options(self, task_keys=None, var_options=None, direct=None):
        """
        setup the callback options
        """
        super(CallbackModule, self).set_options(
            task_keys=task_keys, var_options=var_options, direct=direct)

        self.conf_appname = self.get_option('logdna_appname')
        if self.conf_appname is None:
            self.conf_appname = self.defaults.get('logdna_appname')

        self.conf_endpoint = self.get_option('logdna_endpoint')
        if self.conf_endpoint is None:
            self.conf_endpoint = self.defaults.get('logdna_endpoint')

        self.conf_disable_loglevel = self.get_option(
            'logdna_disable_loglevels')

        self.conf_host = self.get_option('logdna_host')
        if self.conf_host is None:
            self.conf_host = self.defaults.get('logdna_host')

        # if use_local_hostname is set to any value, use get_local_hostname()
        # of the ansible runner host, else default to logdna_hostname and
        # if that is unset, the targeted ansible host will be used.
        self.conf_use_target_host_for_hostnmae = self.get_option(
            'logdna_use_target_host_for_hostname')
        self.conf_hostname = self.get_option('logdna_hostname')
        if not self.conf_use_target_host_for_hostnmae:
            self.conf_hostname = get_local_hostname()

        self.conf_ignore_failed = self.get_option('logdna_ignore_failed')

        self.conf_ignore_ok = self.get_option('logdna_ignore_ok')

        self.conf_ignore_skipped = self.get_option('logdna_ignore_skipped')

        self.conf_ignore_unreachable = self.get_option(
            'logdna_ignore_unreachable')

        self.conf_ingestion_key = self.get_option('logdna_ingestion_key')
        if self.conf_ingestion_key is None:
            self.disabled = True
            self._display.warning(
                'To use ansible callback logdna you must provide you'
                'r ingest key with the `LOGDNA_INGESTION_KEY` enviro'
                'nment variable or in your ansible.cfg file.')

        self.conf_ip_addr = self.get_option('logdna_ip_address')
        if self.conf_ip_addr is None:
            self.conf_ip_addr = get_ipaddr()
        elif str(self.conf_ip_addr).lower().startswith('disable'):
            self.conf_ip_addr = None

        self.conf_log_fmt = self.get_option('logdna_log_format')

        self.conf_mac_addr = self.get_option('logdna_mac_address')
        if self.conf_mac_addr is None:
            self.conf_mac_addr = get_hwaddr()
        elif str(self.conf_mac_addr).lower().startswith("disable"):
            self.conf_mac_addr = None

        self.conf_tags = self.get_option('logdna_tags')

    def v2_playbook_on_start(self, playbook):
        self.logdna_callback.ansible_playbook = basename(playbook._file_name)

    def v2_playbook_on_task_start(self, task, is_conditional):
        self.start_datetimes[task._uuid] = datetime.utcnow()

    def v2_playbook_on_handler_task_start(self, task):
        self.start_datetimes[task._uuid] = datetime.utcnow()

    def v2_runner_on_ok(self, result, **kwargs):
        if not self.conf_ignore_ok:
            self._handle_event('OK', result)

    def v2_runner_on_skipped(self, result, **kwargs):
        if not self.conf_ignore_skipped:
            self._handle_event('SKIPPED', result)

    def v2_runner_on_failed(self, result, **kwargs):
        if not self.conf_ignore_failed:
            self._handle_event('FAILED', result)

    def runner_on_async_failed(self, result, **kwargs):
        if not self.conf_ignore_failed:
            self._handle_event('FAILED', result)

    def v2_runner_on_unreachable(self, result, **kwargs):
        if not self.conf_ignore_unreachable:
            self._handle_event('UNREACHABLE', result)
