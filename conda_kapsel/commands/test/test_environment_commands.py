# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2016, Continuum Analytics, Inc. All rights reserved.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# ----------------------------------------------------------------------------
from __future__ import absolute_import, print_function

import os

from conda_kapsel.commands.main import _parse_args_and_run_subcommand
from conda_kapsel.project_file import DEFAULT_PROJECT_FILENAME
from conda_kapsel.internal.test.tmpfile_utils import with_directory_contents
from conda_kapsel.internal.simple_status import SimpleStatus
from conda_kapsel.project import Project


def _monkeypatch_pwd(monkeypatch, dirname):
    from os.path import abspath as real_abspath

    def mock_abspath(path):
        if path == ".":
            return dirname
        else:
            return real_abspath(path)

    monkeypatch.setattr('os.path.abspath', mock_abspath)


def _monkeypatch_add_env_spec(monkeypatch, result):
    params = {}

    def mock_add_env_spec(*args, **kwargs):
        params['args'] = args
        params['kwargs'] = kwargs
        return result

    monkeypatch.setattr("conda_kapsel.project_ops.add_env_spec", mock_add_env_spec)

    return params


def _monkeypatch_add_packages(monkeypatch, result):
    params = {}

    def mock_add_packages(*args, **kwargs):
        params['args'] = args
        params['kwargs'] = kwargs
        return result

    monkeypatch.setattr("conda_kapsel.project_ops.add_packages", mock_add_packages)

    return params


def _monkeypatch_remove_packages(monkeypatch, result):
    params = {}

    def mock_remove_packages(*args, **kwargs):
        params['args'] = args
        params['kwargs'] = kwargs
        return result

    monkeypatch.setattr("conda_kapsel.project_ops.remove_packages", mock_remove_packages)

    return params


def _test_environment_command_with_project_file_problems(capsys, monkeypatch, command, append_dirname=False):
    def check(dirname):
        if append_dirname:
            command.append(dirname)
        _monkeypatch_pwd(monkeypatch, dirname)

        code = _parse_args_and_run_subcommand(command)
        assert code == 1

        out, err = capsys.readouterr()
        assert '' == out
        assert ('variables section contains wrong value type 42,' + ' should be dict or list of requirements\n' +
                'Unable to load the project.\n') == err

    with_directory_contents({DEFAULT_PROJECT_FILENAME: "variables:\n  42"}, check)


def test_add_env_spec_no_packages(capsys, monkeypatch):
    def check(dirname):
        _monkeypatch_pwd(monkeypatch, dirname)
        _monkeypatch_add_env_spec(monkeypatch, SimpleStatus(success=True, description='Environment looks good.'))

        code = _parse_args_and_run_subcommand(['anaconda-project', 'add-env-spec', '--name', 'foo'])
        assert code == 0

        out, err = capsys.readouterr()
        assert ('Environment looks good.\n' + 'Added environment foo to the project file.\n') == out
        assert '' == err

    with_directory_contents(dict(), check)


def test_add_env_spec_with_packages(capsys, monkeypatch):
    def check(dirname):
        _monkeypatch_pwd(monkeypatch, dirname)
        params = _monkeypatch_add_env_spec(monkeypatch,
                                           SimpleStatus(success=True,
                                                        description='Environment looks good.'))

        code = _parse_args_and_run_subcommand(['anaconda-project', 'add-env-spec', '--name', 'foo', '--channel', 'c1',
                                               '--channel=c2', 'a', 'b'])
        assert code == 0

        out, err = capsys.readouterr()
        assert ('Environment looks good.\n' + 'Added environment foo to the project file.\n') == out
        assert '' == err

        assert 1 == len(params['args'])
        assert dict(name='foo', packages=['a', 'b'], channels=['c1', 'c2']) == params['kwargs']

    with_directory_contents(dict(), check)


def test_add_env_spec_fails(capsys, monkeypatch):
    def check(dirname):
        _monkeypatch_pwd(monkeypatch, dirname)
        _monkeypatch_add_env_spec(monkeypatch,
                                  SimpleStatus(success=False,
                                               description='Environment variable MYDATA is not set.',
                                               logs=['This is a log message.'],
                                               errors=['This is an error message.']))

        code = _parse_args_and_run_subcommand(['anaconda-project', 'add-env-spec', '--name', 'foo'])
        assert code == 1

        out, err = capsys.readouterr()
        assert '' == out
        assert 'This is a log message.\nThis is an error message.\nEnvironment variable MYDATA is not set.\n' == err

    with_directory_contents(dict(), check)


def test_remove_env_spec_missing(capsys, monkeypatch):
    def check(dirname):
        _monkeypatch_pwd(monkeypatch, dirname)
        code = _parse_args_and_run_subcommand(['anaconda-project', 'remove-env-spec', '--name', 'foo'])
        assert code == 1

        out, err = capsys.readouterr()
        assert '' == out
        assert "Environment spec foo doesn't exist.\n" == err

    with_directory_contents(dict(), check)


def test_remove_env_spec_fails(capsys, monkeypatch):
    def check(dirname):
        from shutil import rmtree as real_rmtree
        _monkeypatch_pwd(monkeypatch, dirname)

        test_filename = os.path.join(dirname, 'envs', 'foo')

        # only allow mock to have side effect once
        # later, when cleaning up directory, allow removal
        mock_called = []

        def mock_remove(path, ignore_errors=False, onerror=None):
            if path == test_filename and not mock_called:
                mock_called.append(True)
                raise Exception('Error')
            return real_rmtree(path, ignore_errors, onerror)

        monkeypatch.setattr('shutil.rmtree', mock_remove)

        code = _parse_args_and_run_subcommand(['anaconda-project', 'remove-env-spec', '--name', 'foo'])
        assert code == 1

        out, err = capsys.readouterr()
        assert '' == out
        assert ("Failed to remove environment files in %s: Error.\n" % os.path.join(dirname, "envs", "foo")) == err

    with_directory_contents(
        {
            DEFAULT_PROJECT_FILENAME: 'env_specs:\n  foo:\n    channels: []\n    packages:\n    - bar\n',
            'envs/foo/bin/test': 'code here'
        }, check)


def test_remove_env_spec(capsys, monkeypatch):
    def check(dirname):
        _monkeypatch_pwd(monkeypatch, dirname)

        code = _parse_args_and_run_subcommand(['anaconda-project', 'remove-env-spec', '--name', 'foo'])
        assert code == 0

        out, err = capsys.readouterr()
        assert '' == err
        assert ('Deleted environment files in %s.\nRemoved environment foo from the project file.\n' % os.path.join(
            dirname, "envs", "foo")) == out

    with_directory_contents(
        {
            DEFAULT_PROJECT_FILENAME: 'env_specs:\n  foo:\n    channels: []\n    packages:\n    - bar\n',
            'envs/foo/bin/test': 'code here'
        }, check)


def test_remove_env_spec_default(capsys, monkeypatch):
    def check(dirname):
        _monkeypatch_pwd(monkeypatch, dirname)

        code = _parse_args_and_run_subcommand(['anaconda-project', 'remove-env-spec', '--name', 'default'])
        assert code == 1

        out, err = capsys.readouterr()
        assert '' == out
        assert "Cannot remove default environment spec.\n" == err

    with_directory_contents({}, check)


def test_add_env_spec_with_project_file_problems(capsys, monkeypatch):
    _test_environment_command_with_project_file_problems(capsys, monkeypatch,
                                                         ['anaconda-project', 'add-env-spec', '--name', 'foo'])


def test_remove_env_spec_with_project_file_problems(capsys, monkeypatch):
    _test_environment_command_with_project_file_problems(capsys, monkeypatch,
                                                         ['anaconda-project', 'remove-env-spec', '--name', 'foo'])


def test_add_packages_with_project_file_problems(capsys, monkeypatch):
    _test_environment_command_with_project_file_problems(capsys, monkeypatch,
                                                         ['anaconda-project', 'add-packages', 'foo'])


def test_remove_packages_with_project_file_problems(capsys, monkeypatch):
    _test_environment_command_with_project_file_problems(capsys, monkeypatch,
                                                         ['anaconda-project', 'remove-packages', 'foo'])


def test_add_packages_to_all_environments(capsys, monkeypatch):
    def check(dirname):
        _monkeypatch_pwd(monkeypatch, dirname)
        params = _monkeypatch_add_packages(monkeypatch, SimpleStatus(success=True, description='Installed ok.'))

        code = _parse_args_and_run_subcommand(['anaconda-project', 'add-packages', '--channel', 'c1', '--channel=c2',
                                               'a', 'b'])
        assert code == 0

        out, err = capsys.readouterr()
        assert ('Installed ok.\n' + 'Added packages to project file: a, b.\n') == out
        assert '' == err

        assert 1 == len(params['args'])
        assert dict(env_spec_name=None, packages=['a', 'b'], channels=['c1', 'c2']) == params['kwargs']

    with_directory_contents(dict(), check)


def test_add_packages_to_specific_environment(capsys, monkeypatch):
    def check(dirname):
        _monkeypatch_pwd(monkeypatch, dirname)
        params = _monkeypatch_add_packages(monkeypatch, SimpleStatus(success=True, description='Installed ok.'))

        code = _parse_args_and_run_subcommand(['anaconda-project', 'add-packages', '--env-spec', 'foo', '--channel',
                                               'c1', '--channel=c2', 'a', 'b'])
        assert code == 0

        out, err = capsys.readouterr()
        assert ('Installed ok.\n' + 'Added packages to environment foo in project file: a, b.\n') == out
        assert '' == err

        assert 1 == len(params['args'])
        assert dict(env_spec_name='foo', packages=['a', 'b'], channels=['c1', 'c2']) == params['kwargs']

    with_directory_contents({DEFAULT_PROJECT_FILENAME: """
env_specs:
  foo:
   packages:
     - bar
"""}, check)


def test_remove_packages_from_all_environments(capsys, monkeypatch):
    def check(dirname):
        _monkeypatch_pwd(monkeypatch, dirname)
        params = _monkeypatch_remove_packages(monkeypatch, SimpleStatus(success=True, description='Installed ok.'))

        code = _parse_args_and_run_subcommand(['anaconda-project', 'remove-packages', 'bar'])
        assert code == 0

        out, err = capsys.readouterr()
        assert ('Installed ok.\n' + 'Removed packages from project file: bar.\n') == out
        assert '' == err

        assert 1 == len(params['args'])
        assert dict(env_spec_name=None, packages=['bar']) == params['kwargs']

    with_directory_contents(dict(), check)


def test_remove_packages_from_specific_environment(capsys, monkeypatch):
    def check(dirname):
        _monkeypatch_pwd(monkeypatch, dirname)
        params = _monkeypatch_remove_packages(monkeypatch, SimpleStatus(success=True, description='Installed ok.'))

        code = _parse_args_and_run_subcommand(['anaconda-project', 'remove-packages', '--env-spec', 'foo', 'bar'])
        assert code == 0

        out, err = capsys.readouterr()
        assert ('Installed ok.\n' + 'Removed packages from environment foo in project file: bar.\n') == out
        assert '' == err

        assert 1 == len(params['args'])
        assert dict(env_spec_name='foo', packages=['bar']) == params['kwargs']

    with_directory_contents(dict(), check)


def test_list_environments(capsys, monkeypatch):
    def check_list_not_empty(dirname):
        code = _parse_args_and_run_subcommand(['anaconda-project', 'list-env-specs', '--directory', dirname])

        assert code == 0
        out, err = capsys.readouterr()
        expected_out = """
Environments for project: {dirname}

Name     Description
====     ===========
bar
default  Default
foo
""".format(dirname=dirname).strip() + "\n"

        assert out == expected_out

    with_directory_contents(
        {DEFAULT_PROJECT_FILENAME: ('env_specs:\n'
                                    '  foo:\n'
                                    '    packages:\n'
                                    '      - bar\n'
                                    '  bar:\n'
                                    '    packages:\n'
                                    '      - bar\n')}, check_list_not_empty)


def test_list_empty_environments(capsys, monkeypatch):
    def check_list_empty(dirname):
        code = _parse_args_and_run_subcommand(['anaconda-project', 'list-env-specs', '--directory', dirname])

        assert code == 0
        out, err = capsys.readouterr()
        expected_out = """
Environments for project: {dirname}

Name     Description
====     ===========
default  Default
""".format(dirname=dirname).strip() + "\n"
        assert out == expected_out

    with_directory_contents({DEFAULT_PROJECT_FILENAME: ''}, check_list_empty)


def test_list_environments_with_project_file_problems(capsys, monkeypatch):
    _test_environment_command_with_project_file_problems(capsys,
                                                         monkeypatch,
                                                         ['anaconda-project', 'list-env-specs', '--directory'],
                                                         append_dirname=True)


def test_list_packages_wrong_env(capsys):
    def check_missing_env(dirname):
        env_name = 'not-there'
        code = _parse_args_and_run_subcommand(['anaconda-project', 'list-packages', '--directory', dirname,
                                               '--env-spec', env_name])

        assert code == 1

        expected_err = "Project doesn't have an environment called '{}'\n".format(env_name)

        out, err = capsys.readouterr()
        assert out == ""
        assert err == expected_err

    with_directory_contents({DEFAULT_PROJECT_FILENAME: ""}, check_missing_env)


def _test_list_packages(capsys, env, expected_deps):
    def check_list_not_empty(dirname):
        params = ['anaconda-project', 'list-packages', '--directory', dirname]
        if env:
            params.extend(['--env-spec', env])

        code = _parse_args_and_run_subcommand(params)

        assert code == 0
        out, err = capsys.readouterr()

        project = Project(dirname)
        expected_out = "Packages for environment '{}':\n{}".format(
            (env or project.default_env_spec_name), expected_deps)
        assert out == expected_out

    project_contents = ('env_specs:\n'
                        '  foo:\n'
                        '    packages:\n'
                        '      - requests\n'
                        '      - flask\n'
                        '  bar:\n'
                        '    packages:\n'
                        '      - httplib\n'
                        '      - django\n\n'
                        'packages:\n'
                        ' - mandatory_package\n')

    with_directory_contents({DEFAULT_PROJECT_FILENAME: project_contents}, check_list_not_empty)


def test_list_packages_from_env(capsys):
    _test_list_packages(capsys, 'bar', '\ndjango\nhttplib\nmandatory_package\n\n')
    _test_list_packages(capsys, 'foo', '\nflask\nmandatory_package\nrequests\n\n')


def test_list_packages_default_env(capsys):
    _test_list_packages(capsys, None, '\nmandatory_package\n\n')


def test_list_packages_with_project_file_problems(capsys, monkeypatch):
    _test_environment_command_with_project_file_problems(capsys,
                                                         monkeypatch,
                                                         ['anaconda-project', 'list-packages', '--directory'],
                                                         append_dirname=True)