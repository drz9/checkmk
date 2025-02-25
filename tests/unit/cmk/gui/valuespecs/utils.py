#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from contextlib import contextmanager
from typing import TypeVar
from unittest.mock import patch

import pytest

import cmk.gui.valuespec as vs
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html


@contextmanager
def request_var(  # type:ignore[no-untyped-def]
    **request_variables: str,
):
    with patch.dict(html.request.legacy_vars, request_variables):
        yield


T = TypeVar("T")


def validate(valuespec: vs.ValueSpec[T], value: T) -> None:
    valuespec.validate_datatype(value, "varprefix")
    valuespec.validate_value(value, "varprefix")


def expect_validate_failure(
    valuespec: vs.ValueSpec[T], value: T, *, match: str | None = None
) -> None:
    with pytest.raises(MKUserError, match=match):
        validate(valuespec, value)


def expect_validate_success(valuespec: vs.ValueSpec[T], value: T) -> None:
    validate(valuespec, value)


def _validate_migrate_or_transform(valuespec: vs.Migrate | vs.Transform, value: object) -> None:
    valuespec.validate_datatype(value, "varprefix")
    valuespec.validate_value(value, "varprefix")


def expect_validate_failure_migrate_or_transform(
    valuespec: vs.Migrate | vs.Transform, value: object, *, match: str | None = None
) -> None:
    with pytest.raises(MKUserError, match=match):
        _validate_migrate_or_transform(valuespec, value)


def expect_validate_success_migrate_or_transform(
    valuespec: vs.Migrate | vs.Transform, value: object
) -> None:
    _validate_migrate_or_transform(valuespec, value)


def raise_exception() -> None:
    raise Exception("This is an exception")
