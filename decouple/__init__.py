# coding: utf-8

from __future__ import annotations

import os
import sys
import string
from shlex import shlex
from configparser import ConfigParser
from io import open
from collections import OrderedDict
from distutils.util import strtobool
from typing import Any, cast as type_cast, Callable, Dict, Iterable, Optional, List, Tuple, Type, TypeVar, Union

DEFAULT_ENCODING = 'UTF-8'

class UndefinedValueError(Exception):
    pass

T = TypeVar('T')

def _cast_do_nothing(value: T) -> T:
    return value

class Undefined(object):
    """
    Class to represent undefined type.
    """
    pass


# Reference instance to represent undefined values
undefined = Undefined()


class Config(object):
    """
    Handle .env file format used by Foreman.
    """

    def __init__(self, repository: RepositoryEmpty) -> None:
        self.repository = repository

    def _cast_boolean(self, value: Any) -> bool:
        """
        Helper to convert config values to boolean as ConfigParser do.
        """
        value = str(value)
        return bool(value) if value == '' else bool(strtobool(value))

    def get(
        self,
        option: str,
        default: Union[Undefined, Any] = undefined,
        cast: Callable[[Any], T] = _cast_do_nothing,
    ) -> T:
        """
        Return the value for option or default if defined.
        """

        # We can't avoid __contains__ because value may be empty.
        value: Union[None, str, T]
        if option in os.environ:
            value = os.environ[option]
        elif option in self.repository:
            value = self.repository[option]
        elif isinstance(default, Undefined):
            raise UndefinedValueError('{} not found. Declare it as envvar or define a default value.'.format(option))
        else:
            value = default

        if cast is bool:
            cast = type_cast(Callable[[Any], T], self._cast_boolean)

        return cast(value)

    def __call__(
        self,
        option: str,
        default: Union[Undefined, T] = undefined,
        cast: Callable[[Any], T] = _cast_do_nothing,
    ) -> T:
        """
        Convenient shortcut to get.
        """
        return self.get(option=option, default=default, cast=cast)


class RepositoryEmpty(object):
    def __init__(self, source: str = '', encoding: str = DEFAULT_ENCODING) -> None:
        pass

    def __contains__(self, key: str) -> bool:
        return False

    def __getitem__(self, key: str) -> Optional[str]:
        return None


class RepositoryIni(RepositoryEmpty):
    """
    Retrieves option keys from .ini files.
    """
    SECTION = 'settings'

    def __init__(self, source: str, encoding: str = DEFAULT_ENCODING) -> None:
        self.parser = ConfigParser()
        with open(source, encoding=encoding) as file_:
            self.parser.readfp(file_)

    def __contains__(self, key: str) -> bool:
        return (key in os.environ or
                self.parser.has_option(self.SECTION, key))

    def __getitem__(self, key: str) -> Optional[str]:
        return self.parser.get(self.SECTION, key)


class RepositoryEnv(RepositoryEmpty):
    """
    Retrieves option keys from .env files with fall back to os.environ.
    """
    def __init__(self, source: str, encoding: str = DEFAULT_ENCODING) -> None:
        self.data: Dict[str, str] = {}

        with open(source, encoding=encoding) as file_:
            for line in file_:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip()
                if len(v) >= 2 and ((v[0] == "'" and v[-1] == "'") or (v[0] == '"' and v[-1] == '"')):
                    v = v.strip('\'"')
                self.data[k] = v

    def __contains__(self, key: str) -> bool:
        return key in os.environ or key in self.data

    def __getitem__(self, key: str) -> str:
        return self.data[key]


class AutoConfig(object):
    """
    Autodetects the config file and type.

    Parameters
    ----------
    search_path : str, optional
        Initial search path. If empty, the default search path is the
        caller's path.

    """
    SUPPORTED = OrderedDict([
        ('settings.ini', RepositoryIni),
        ('.env', RepositoryEnv),
    ])

    encoding = DEFAULT_ENCODING

    def __init__(self, search_path: Optional[str] = None) -> None:
        self.search_path = search_path
        self.config: Optional[Config] = None

    def _find_file(self, path: str) -> str:
        # look for all files in the current path
        for configfile in self.SUPPORTED:
            filename = os.path.join(path, configfile)
            if os.path.isfile(filename):
                return filename

        # search the parent
        parent = os.path.dirname(path)
        if parent and parent != os.path.abspath(os.sep):
            return self._find_file(parent)

        # reached root without finding any files.
        return ''

    def _load(self, path: str) -> None:
        # Avoid unintended permission errors
        try:
            filename = self._find_file(os.path.abspath(path))
        except Exception:
            filename = ''
        Repository = self.SUPPORTED.get(os.path.basename(filename), RepositoryEmpty)

        self.config = Config(Repository(filename, encoding=self.encoding))

    def _caller_path(self) -> str:
        # MAGIC! Get the caller's module path.
        frame = sys._getframe()
        parent_frame = frame.f_back
        assert parent_frame
        grandparent_frame = parent_frame.f_back
        assert grandparent_frame
        path = os.path.dirname(grandparent_frame.f_code.co_filename)
        return path

    def __call__(
        self,
        option: str,
        default: Union[Undefined, T] = undefined,
        cast: Callable[[Any], T] = _cast_do_nothing,
    ) -> T:

        if not self.config:
            self._load(self.search_path or self._caller_path())
            assert self.config

        return self.config(option=option, default=default, cast=cast)


# A pré-instantiated AutoConfig to improve decouple's usability
# now just import config and start using with no configuration.
config = AutoConfig()

# Helpers


class Csv(object):
    """
    Produces a csv parser that return a list of transformed elements.
    """

    def __init__(
        self,
        cast: Callable[[Any], Any] = str,
        delimiter: str = ',',
        strip: str = string.whitespace,
        post_process: Callable[[Any], Iterable[T]] = list,
    ) -> None:
        """
        Parameters:
        cast -- callable that transforms the item just before it's added to the list.
        delimiter -- string of delimiters chars passed to shlex.
        strip -- string of non-relevant characters to be passed to str.strip after the split.
        post_process -- callable to post process all casted values. Default is `list`.
        """
        self.cast = cast
        self.delimiter = delimiter
        self.strip = strip
        self.post_process = post_process

    def __call__(self, value: str) -> Iterable[T]:
        """The actual transformation"""
        transform = lambda s: self.cast(s.strip(self.strip))

        splitter = shlex(value, posix=True)
        splitter.whitespace = self.delimiter
        splitter.whitespace_split = True

        return self.post_process(transform(s) for s in splitter)


class Choices(object):
    """
    Allows for cast and validation based on a list of choices.
    """

    def __init__(
        self,
        flat: Optional[List[Any]] = None,
        cast: Callable[[Any], Any] = str,
        choices: Optional[Iterable[Tuple[Any, str]]] = None,
    ) -> None:
        """
        Parameters:
        flat -- a flat list of valid choices.
        cast -- callable that transforms value before validation.
        choices -- tuple of Django-like choices.
        """
        self.flat = flat or []
        self.cast = cast
        self.choices = choices or []

        self._valid_values = []
        self._valid_values.extend(self.flat)
        self._valid_values.extend([value for value, _ in self.choices])


    def __call__(self, value: Any) -> Any:
        transform = self.cast(value)
        if transform not in self._valid_values:
            raise ValueError((
                    'Value not in list: {!r}; valid values are {!r}'
                ).format(value, self._valid_values))
        else:
            return transform
