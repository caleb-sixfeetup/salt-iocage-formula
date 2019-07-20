# -*- coding: utf-8 -*-
'''
Support for iocage (jails tools on FreeBSD)
'''
from __future__ import absolute_import

# Import python libs
# import os
import re
import logging
# Import salt libs
import salt.utils
from salt.exceptions import CommandExecutionError, SaltInvocationError

log = logging.getLogger(__name__)

__virtualname__ = 'iocage'


def __virtual__():
    '''
    Module load only if iocage is installed
    '''
    if salt.utils.path.which('iocage'):
        return __virtualname__
    else:
        return False


def _option_exists(name, **kwargs):
    '''
    Check if a given property `name` is in the all properties list
    '''
    return name in list_properties(name, **kwargs)


def _exec(cmd, output='stdout'):
    '''
    Execute commad `cmd` and returns output `output` (by default returns the
    stdout)
    '''
    cmd_ret = __salt__['cmd.run_all'](cmd)
    if cmd_ret['retcode'] == 0:
        return cmd_ret['stdout']
    else:
        raise CommandExecutionError(
            'Error in command "%s" : %s' % (cmd, str(cmd_ret)))


def _list_properties(jail_name, **kwargs):
    '''
    Returns result of iocage get all or iocage defaults (according to the
    jail name)
    '''
    if jail_name == 'defaults':
        cmd = 'iocage get all default'
    else:
        cmd = 'iocage get all %s' % (jail_name,)

    return _exec(cmd).split('\n')


def _parse_properties(**kwargs):
    '''
    Returns a rendered properties string used by iocage command line properties
    argument
    '''
    default_properties = [p.split(':')[0] for p in _list_properties('defaults')]
    default_properties.append('pkglist')

    for prop in kwargs.keys():
        if not prop.startswith('__') and prop not in default_properties:
            raise SaltInvocationError('Unknown property %s' % (prop,))

    return ' '.join(
        ['%s="%s"' % (k, v) for k, v in kwargs.items() if not k.startswith('__')])


def _list(option=None, **kwargs):
    '''
    Returns list of jails, templates or releases.
    `Option` can be None or '' for jails list, '-t' for templates or '-r'
    for downloaded releases
    '''
    if option not in [None, '', '-t', '-r']:
        raise SaltInvocationError('Bad option name in command _list')

    cmd = 'iocage list'
    if option == '-t' or option == '-r':
        cmd = '%s %s' % (cmd, option)
    lines = _exec(cmd, **kwargs).split('\n')
    log.debug('92:  %s',lines)
    if len(lines) > 2:
        if option == '-r':
            headers = ['RELEASE']
        else:
            headers = [_.strip() for _ in lines[1].split('|') if len(_) > 1]
        log.debug('98:  %s', headers)
        
        jails = []
        if len(lines) > 2:
            for l in lines[2:]:
                log.debug("102: %s",l)
                # omit all non-iocage jails
                if re.match('^[-+=]*$', l) is not None:
                    continue
                if l == '--- non iocage jails currently active ---':
                    break
                jails.append({
                    headers[k]: v for k, v in enumerate([_.strip() for _ in l.split('|')
                                                         if len(_) > 0])
                })
        log.debug("110: %s",jails)
        return jails
    else:
        raise CommandExecutionError(
            'Error in command "%s" : no results found' % (cmd, ))


def _display_list(items_list):
    '''
    Format display for the list of jails, templates or releases
    '''
    ret = []

    for item in items_list:
        ret.append(','.join(['%s=%s' % (k, v) for k, v in item.items()]),)

    return '\n'.join(ret)


def _manage_state(state, jail_name, **kwargs):
    '''
    Start / Stop / Reboot / Destroy a jail `jail_name`
    '''
    existing_jails = _list()
    for jail in existing_jails:
        if jail_name == jail['UUID'] or jail_name == jail['TAG'] or jail_name == jail['NAME']:
            if ((state == 'start' and jail['STATE'] == 'down')
                    or (state == 'stop' and jail['STATE'] == 'up')
                    or state == 'restart'
                    or state == 'destroy'):
                return _exec('iocage %s %s' % (state, jail_name))
            else:
                if state == 'start':
                    raise SaltInvocationError(
                        'jail %s is already started' % (jail_name,))
                else:
                    raise SaltInvocationError(
                        'jail %s is already stoped' % (jail_name,))

    raise SaltInvocationError('jail uuid or tag or name does not exist' % (jail_name,))


def list_jails(**kwargs):
    '''
    Get list of jails

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.list_jails
    '''
    return _display_list(_list())


def list_templates(**kwargs):
    '''
    Get list of template jails

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.list_templates
    '''
    return _display_list(_list('-t'))


def list_releases(**kwargs):
    '''
    Get list of downloaded releases

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.list_releases
    '''
    return _display_list(_list('-r'))


def list_properties(jail_name, **kwargs):
    '''
    List all properies for a given jail or defaults value

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.list_properties <jail_name>
        salt '*' iocage.list_properties defaults
    '''
    props = _list_properties(jail_name, **kwargs)

    # hack to have the same output with defaults or for a given jail
    if jail_name == 'defaults':
        return '\n'.join(props)
    else:
        return '\n'.join([_.replace(':', '=', 1) for _ in props])


def get_property(property_name, jail_name, **kwargs):
    '''
    Get property value for a given jail (or default value)

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.get_property <property> <jail_name>
        salt '*' iocage.get_property <property> defaults
    '''
    if jail_name == 'defaults':
        jail_name = 'default'

    if property_name == 'all':
        return list_properties(jail_name, **kwargs)
    else:
        return _exec('iocage get %s %s' % (property_name, jail_name))


def set_property(jail_name, **kwargs):
    '''
    Set property value for a given jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.set_property <jail_name> [<property=value>]
    '''
    if jail_name == 'defaults':
        jail_name = 'default'

    return _exec('iocage set %s %s' % (_parse_properties(**kwargs), jail_name))


def fetch(release=None, **kwargs):
    '''
    Download or update/patch release

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.fetch
        salt '*' iocage.fetch <release>
    '''
    if release is None:
        current_release = _exec('uname -r').strip()
        return _exec('iocage fetch release=%s' % (current_release,))
    else:
        return _exec('iocage fetch release=%s' % (release,))


def create(name=None, jail_type="release", template_id=None, **kwargs):
    '''
    Create a new jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.create [<option>] [<property=value>]
    '''
    _options = ['release', 'template-clone', 'base', 'empty']

    if jail_type not in _options:
        raise SaltInvocationError('Unknown option %s' % (jail_type,))

    # check template exists for cloned template
    if jail_type == 'template-clone':
        if template_id == None:
            raise SaltInvocationError('template_id not specified for cloned template')
        templates = __salt__['iocage.list_templates']().split('\n')
        tmpl_exists = False
        for tmpl in templates:
            tmpl_datas = {t.split('=')[0]: '='.join(t.split('=')[1:])
                          for t in tmpl.split(',')}
            if (tmpl_datas['TAG'] == template_id or tmpl_datas['UUID'] == template_id or
                    tmpl_datas['NAME'] == template_id ):
                tmpl_exists = True
                break
        if tmpl_exists == False:
            raise SaltInvocationError('Template id %s does not exist' % (template_id,))


    # stringify the kwargs dict into iocage create properties format
    properties = _parse_properties(**kwargs)

    # if we would like to specify a name value for the jail
    # check if another jail have not the same name
    if name is not None:
        existing_jails = _list()
        if name in [k['NAME'] for k in existing_jails]:
            raise SaltInvocationError(
                'Name %s already exists' % (name,))

    pre_cmd = 'iocage create'
    if jail_type == 'release':
        pre_cmd = 'iocage create -r' % (release_id)
    if jail_type == 'template-clone':
        pre_cmd = 'iocage clone -t %s' % (template_id)
    if jail_type == 'base':
        pre_cmd = 'iocage create -b'
    if jail_type == 'empty':
        pre_cmd = 'iocage create -e'

    # fetch a release if it's the first install
    existing_release = list_releases()
    if len(existing_release) == 0:
        fetch()

    # fetch a specifc release if not present
    if 'release' in kwargs.keys():
        if kwargs['release'] not in existing_release:
            fetch(release=kwargs['release'])

    if name:
        cmd = '%s -n %s %s' % (pre_cmd, name, properties)
    else:
        cmd = '%s %s' % (pre_cmd, properties)
    return _exec(cmd)


def start(jail_name, **kwargs):
    '''
    Start a jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.start <jail_name>
    '''
    return _manage_state('start', jail_name, **kwargs)


def stop(jail_name, **kwargs):
    '''
    Stop a jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.stop <jail_name>
    '''
    return _manage_state('stop', jail_name, **kwargs)


def restart(jail_name, **kwargs):
    '''
    Restart a jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.restart <jail_name>
    '''
    return _manage_state('restart', jail_name, **kwargs)


def destroy(jail_name, **kwargs):
    '''
    Destroy a jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.destroy <jail_name>
    '''
    return _manage_state('destroy', jail_name, **kwargs)


if __name__ == "__main__":
    __salt__ = ''

    import sys
    sys.exit(0)
