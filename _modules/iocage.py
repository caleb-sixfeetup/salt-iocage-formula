# -*- coding: utf-8 -*-
'''
Support for iocage (jails tooks on FreeBSD)
'''
from __future__ import absolute_import

# Import python libs
# import os

import logging
# Import salt libs
import salt.utils
from salt.exceptions import CommandExecutionError  # , SaltInvocationError

log = logging.getLogger(__name__)

__virtualname__ = 'iocage'


def __virtual__():
    '''
    Module load only if php is installed
    '''
    if salt.utils.which('iocage'):
        return __virtualname__
    else:
        return False


def _option_exists(name, **kwargs):
    '''
    Check if a given property is in the all properties list
    '''
    return name in list_properties(name, **kwargs)


def _exec(cmd, output='stdout'):
    cmd_ret = __salt__['cmd.run_all'](cmd)
    if cmd_ret['retcode'] == 0:
        return cmd_ret[output]
    else:
        raise CommandExecutionError(
            'Error in command "%s" : %s' % (cmd, str(cmd_ret)))


def _list_properties(jail_name, **kwargs):
    '''
    Returns result of iocage get all or iocage defaults (according to the
    jail name)
    '''
    if jail_name == 'defaults':
        cmd = 'iocage defaults'
    else:
        cmd = 'iocage get all %s' % (jail_name,)

    return _exec(cmd).split('\n')


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

    if property_name == 'all':
        return list_properties(jail_name, **kwargs)
    else:
        return _exec('iocage get %s %s' % (property_name, jail_name))


if __name__ == "__main__":
    __salt__ = ''

    import sys
    sys.exit(0)
