# coding: utf-8
from __future__ import annotations
import os
import sys
from mock import patch, mock_open
import pytest  # type: ignore
from decouple import Config, RepositoryIni, UndefinedValueError
from io import StringIO



INIFILE = '''
[settings]
KeyTrue=True
KeyOne=1
KeyYes=yes
KeyY=y
KeyOn=on

KeyFalse=False
KeyZero=0
KeyNo=no
KeyN=n
KeyOff=off
KeyEmpty=

#CommentedKey=None
PercentIsEscaped=%%
Interpolation=%(KeyOff)s
IgnoreSpace = text
KeyOverrideByEnv=NotThis
'''

@pytest.fixture(scope='module')
def config() -> Config:
    with patch('decouple.open', return_value=StringIO(INIFILE), create=True):
        return Config(RepositoryIni('settings.ini'))


def test_ini_comment(config: Config) -> None:
    with pytest.raises(UndefinedValueError):
        config('CommentedKey')


def test_ini_percent_escape(config: Config) -> None:
    assert '%' == config('PercentIsEscaped')


def test_ini_interpolation(config: Config) -> None:
    assert 'off' == config('Interpolation')


def test_ini_bool_true(config: Config) -> None:
    assert True is config('KeyTrue', cast=bool)
    assert True is config('KeyOne', cast=bool)
    assert True is config('KeyYes', cast=bool)
    assert True is config('KeyY', cast=bool)
    assert True is config('KeyOn', cast=bool)
    assert True is config('Key1int', default=1, cast=bool)


def test_ini_bool_false(config: Config) -> None:
    assert False is config('KeyFalse', cast=bool)
    assert False is config('KeyZero', cast=bool)
    assert False is config('KeyNo', cast=bool)
    assert False is config('KeyOff', cast=bool)
    assert False is config('KeyN', cast=bool)
    assert False is config('KeyEmpty', cast=bool)
    assert False is config('Key0int', default=0, cast=bool)


def test_init_undefined(config: Config) -> None:
    with pytest.raises(UndefinedValueError):
        config('UndefinedKey')


def test_ini_default_none(config: Config) -> None:
    assert None is config('UndefinedKey', default=None)


def test_ini_default_bool(config: Config) -> None:
    assert False is config('UndefinedKey', default=False, cast=bool)
    assert True is config('UndefinedKey', default=True, cast=bool)


def test_ini_default(config: Config) -> None:
    assert False is config('UndefinedKey', default=False)
    assert True is config('UndefinedKey', default=True)


def test_ini_default_invalid_bool(config: Config) -> None:
    with pytest.raises(ValueError):
        config('UndefinedKey', default='NotBool', cast=bool)


def test_ini_empty(config: Config) -> None:
    assert '' is config('KeyEmpty', default=None)


def test_ini_support_space(config: Config) -> None:
    assert 'text' == config('IgnoreSpace')


def test_ini_os_environ(config: Config) -> None:
    os.environ['KeyOverrideByEnv'] = 'This'
    assert 'This' == config('KeyOverrideByEnv')
    del os.environ['KeyOverrideByEnv']


def test_ini_undefined_but_present_in_os_environ(config: Config) -> None:
    os.environ['KeyOnlyEnviron'] = ''
    assert '' == config('KeyOnlyEnviron')
    del os.environ['KeyOnlyEnviron']


def test_ini_empty_string_means_false(config: Config) -> None:
    assert False is config('KeyEmpty', cast=bool)
