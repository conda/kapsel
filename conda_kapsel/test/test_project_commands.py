# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2016, Continuum Analytics, Inc. All rights reserved.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# ----------------------------------------------------------------------------
from __future__ import absolute_import, print_function

from conda_kapsel.project_commands import CommandExecInfo

import os
import platform
import pytest


def test_execvpe_with_shell_on_unix(monkeypatch):
    if platform.system() == 'Windows':
        return

    executed = {}

    def mock_execvpe(file, args, env):
        executed['file'] = file
        executed['args'] = args
        executed['env'] = env

    monkeypatch.setattr('os.execvpe', mock_execvpe)
    info = CommandExecInfo(cwd=os.getcwd(), args=['foo bar'], shell=True, env=dict(FOO='bar'))

    info.execvpe()

    assert executed['file'] == '/bin/sh'
    assert executed['args'] == ['/bin/sh', '-c', 'foo bar']
    assert executed['env'] == dict(FOO='bar')


def test_execvpe_with_shell_on_windows(monkeypatch):
    def mock_platform_system():
        return 'Windows'

    monkeypatch.setattr('platform.system', mock_platform_system)

    executed = {}

    def mock_popen(args, env, cwd, shell):
        executed['args'] = args
        executed['env'] = env
        executed['cwd'] = cwd
        executed['shell'] = shell

    monkeypatch.setattr('subprocess.Popen', mock_popen)

    info = CommandExecInfo(cwd='/somewhere', args=['foo bar'], shell=True, env=dict(FOO='bar'))
    with pytest.raises(SystemExit) as excinfo:
        info.execvpe()
    assert excinfo.value.code == 0

    assert executed['args'] == 'foo bar'
    assert executed['shell'] is True
    assert executed['env'] == dict(FOO='bar')
    assert executed['cwd'] == '/somewhere'
