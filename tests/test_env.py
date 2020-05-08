# coding: utf-8
import os
import sys
from mock import patch
import pytest  # type: ignore
from decouple import Config, RepositoryEnv, UndefinedValueError
from io import StringIO


ENVFILE = '''
KeyTrue=True
KeyOne=1
KeyYes=yes
KeyOn=on
KeyY=y

KeyFalse=False
KeyZero=0
KeyNo=no
KeyN=n
KeyOff=off
KeyEmpty=

#CommentedKey=None
PercentNotEscaped=%%
NoInterpolation=%(KeyOff)s
IgnoreSpace = text
RespectSingleQuoteSpace = ' text'
RespectDoubleQuoteSpace = " text"
KeyOverrideByEnv=NotThis

KeyWithSingleQuoteEnd=text'
KeyWithSingleQuoteMid=te'xt
KeyWithSingleQuoteBegin='text
KeyWithDoubleQuoteEnd=text"
KeyWithDoubleQuoteMid=te"xt
KeyWithDoubleQuoteBegin="text
KeyIsSingleQuote='
KeyIsDoubleQuote="
'''

@pytest.fixture(scope='module')
def config() -> Config:
    with patch('decouple.open', return_value=StringIO(ENVFILE), create=True):
        return Config(RepositoryEnv('.env'))


def test_env_comment(config: Config) -> None:
    with pytest.raises(UndefinedValueError):
        config('CommentedKey')


def test_env_percent_not_escaped(config: Config) -> None:
    assert '%%' == config('PercentNotEscaped')


def test_env_no_interpolation(config: Config) -> None:
    assert '%(KeyOff)s' == config('NoInterpolation')


def test_env_bool_true(config: Config) -> None:
    assert True is config('KeyTrue', cast=bool)
    assert True is config('KeyOne', cast=bool)
    assert True is config('KeyYes', cast=bool)
    assert True is config('KeyOn', cast=bool)
    assert True is config('KeyY', cast=bool)
    assert True is config('Key1int', default=1, cast=bool)

def test_env_bool_false(config: Config) -> None:
    assert False is config('KeyFalse', cast=bool)
    assert False is config('KeyZero', cast=bool)
    assert False is config('KeyNo', cast=bool)
    assert False is config('KeyOff', cast=bool)
    assert False is config('KeyN', cast=bool)
    assert False is config('KeyEmpty', cast=bool)
    assert False is config('Key0int', default=0, cast=bool)


def test_env_os_environ(config: Config) -> None:
    os.environ['KeyOverrideByEnv'] = 'This'
    assert 'This' == config('KeyOverrideByEnv')
    del os.environ['KeyOverrideByEnv']


def test_env_undefined_but_present_in_os_environ(config: Config) -> None:
    os.environ['KeyOnlyEnviron'] = ''
    assert '' == config('KeyOnlyEnviron')
    del os.environ['KeyOnlyEnviron']


def test_env_undefined(config: Config) -> None:
    with pytest.raises(UndefinedValueError):
        config('UndefinedKey')


def test_env_default_none(config: Config) -> None:
    assert None is config('UndefinedKey', default=None)


def test_env_empty(config: Config) -> None:
    assert '' == config('KeyEmpty', default=None)
    assert '' == config('KeyEmpty')


def test_env_support_space(config: Config) -> None:
    assert 'text' == config('IgnoreSpace')
    assert ' text' == config('RespectSingleQuoteSpace')
    assert ' text' == config('RespectDoubleQuoteSpace')


def test_env_empty_string_means_false(config: Config) -> None:
    assert False is config('KeyEmpty', cast=bool)

def test_env_with_quote(config: Config) -> None:
    assert "text'" == config('KeyWithSingleQuoteEnd')
    assert 'text"' == config('KeyWithDoubleQuoteEnd')
    assert "te'xt" == config('KeyWithSingleQuoteMid')
    assert "'text" == config('KeyWithSingleQuoteBegin')
    assert 'te"xt' == config('KeyWithDoubleQuoteMid')
    assert '"text' == config('KeyWithDoubleQuoteBegin')
    assert '"' == config('KeyIsDoubleQuote')
    assert "'" == config('KeyIsSingleQuote')
