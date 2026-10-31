"""Container and bracket AST tokens for grouping mathematical expressions."""

import builtins
import math
from abc import ABC, abstractmethod
from typing import Any

from .config import ACTIVE_CONFIG
from .core import (
    CallableToken,
    Concatenation,
    Literal,
    Macro,
    Token,
    as_token,
    register_token_converter,
)
from .typography import texttt


class _Container(CallableToken, ABC):
    def __init__(self, *children: str | float | Token) -> None:
        self.children = [as_token(child) for child in children]

    @abstractmethod
    def __str__(self) -> str:
        pass

    @property
    def value(self) -> Any:
        if len(self.children) == 1:
            child = self.children[0]
            return getattr(child, "value", None)
        return None

    def __getitem__(self, index: int) -> Token:
        return self.children[index]

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        if len(self) == 1:
            child = self.children[0]
            if isinstance(child, CallableToken):
                return child(*args, **kwargs)
            return Literal(str(child))
        raise ValueError(f"Cannot call a container with multiple {len(self)} children")

    def __len__(self) -> int:
        return len(self.children)

    def __iter__(self):
        return iter(self.children)


class Collection(_Container):
    def __str__(self) -> str:
        return " ".join(str(child) for child in self.children)


class Sequence(_Container):
    def __str__(self) -> str:
        return ", ".join(str(child) for child in self.children)


class Bracket(_Container):
    def __init__(
        self, *children: str | float | Token, scale: bool = False
    ) -> None:
        """A bracketed expression, such as `(a + b)`.

        Parameters
        ----------
        scale : bool, optional
            If True, the brackets will be scaled to fit the contents. Default False
        """
        super().__init__(*children)
        self.scale = scale
        self.left_bracket = "("
        self.right_bracket = ")"

    def __str__(self) -> str:
        scale_left, scale_right = ("\\left", "\\right") if self.scale else ("", "")
        # Command delimiters ending in letters (e.g. \lfloor, \langle, \lbrace) require
        # whitespace separation to prevent TeX syntax collisions with adjacent tokens.
        left_pad = " " if self.left_bracket and self.left_bracket[-1].isalpha() else ""
        right_pad = " " if self.right_bracket and self.right_bracket[-1].isalpha() else ""
        inner = ", ".join(str(child) for child in self.children)
        return f"{scale_left}{self.left_bracket}{left_pad}{inner}{right_pad}{scale_right}{self.right_bracket}"


class SquareBracket(Bracket):
    def __init__(
        self, *children: str | float | Token, scale: bool = False
    ) -> None:
        """A square bracketed expression, such as `[a + b]`."""
        super().__init__(*children, scale=scale)
        self.left_bracket = "["
        self.right_bracket = "]"


class CurlyBracket(Bracket):
    def __init__(
        self, *children: str | float | Token, scale: bool = False
    ) -> None:
        """A curly bracketed/braced expression, such as `{a + b}`."""
        super().__init__(*children, scale=scale)
        self.left_bracket = "\\lbrace"
        self.right_bracket = "\\rbrace"


class AngleBracket(Bracket):
    def __init__(
        self, *children: str | float | Token, scale: bool = False
    ) -> None:
        """An angle bracketed expression, such as `<a + b>`."""
        super().__init__(*children, scale=scale)
        self.left_bracket = "\\langle"
        self.right_bracket = "\\rangle"


class AbsoluteValue(Bracket):
    def __init__(
        self, *children: str | float | Token, scale: bool = False
    ) -> None:
        """An absolute value expression, such as `|a + b|`."""
        super().__init__(*children, scale=scale)
        self.left_bracket = "|"
        self.right_bracket = "|"

    @property
    def value(self) -> Any:
        child_val = super().value
        if child_val is None:
            return None
        try:
            return builtins.abs(child_val)
        except TypeError:
            return None

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        val = self.value
        if val is None:
            raise ValueError(
                "Cannot evaluate AbsoluteValue of expression without a numeric value"
            )
        tok = as_token(val)
        if isinstance(tok, CallableToken):
            return tok(*args, **kwargs)
        return Literal(str(val))


class Norm(Bracket):
    def __init__(
        self, *children: str | float | Token, scale: bool = False
    ) -> None:
        r"""A norm expression, such as `\|a + b\|`."""
        super().__init__(*children, scale=scale)
        self.left_bracket = "\\|"
        self.right_bracket = "\\|"

    @property
    def value(self) -> Any:
        child_val = super().value
        if child_val is None:
            return None
        try:
            return builtins.abs(child_val)
        except TypeError:
            return None

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        val = self.value
        if val is None:
            raise ValueError(
                "Cannot evaluate Norm of expression without a numeric value"
            )
        tok = as_token(val)
        if isinstance(tok, CallableToken):
            return tok(*args, **kwargs)
        return Literal(str(val))


class Floor(Bracket):
    def __init__(
        self, *children: str | float | Token, scale: bool = False
    ) -> None:
        r"""A floor expression, such as `\lfloor a \rfloor`."""
        super().__init__(*children, scale=scale)
        self.left_bracket = "\\lfloor"
        self.right_bracket = "\\rfloor"

    @property
    def value(self) -> Any:
        child_val = super().value
        if child_val is None:
            return None
        try:
            return math.floor(child_val)
        except TypeError:
            return None

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        val = self.value
        if val is None:
            raise ValueError(
                "Cannot evaluate Floor of expression without a numeric value"
            )
        tok = as_token(val)
        if isinstance(tok, CallableToken):
            return tok(*args, **kwargs)
        return Literal(str(val))


class Ceil(Bracket):
    def __init__(
        self, *children: str | float | Token, scale: bool = False
    ) -> None:
        r"""A ceiling expression, such as `\lceil a \rceil`."""
        super().__init__(*children, scale=scale)
        self.left_bracket = "\\lceil"
        self.right_bracket = "\\rceil"

    @property
    def value(self) -> Any:
        child_val = super().value
        if child_val is None:
            return None
        try:
            return math.ceil(child_val)
        except TypeError:
            return None

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        val = self.value
        if val is None:
            raise ValueError(
                "Cannot evaluate Ceil of expression without a numeric value"
            )
        tok = as_token(val)
        if isinstance(tok, CallableToken):
            return tok(*args, **kwargs)
        return Literal(str(val))


class MixedBracket(Bracket):
    __bracket_shorthands = {
        "<": "\\langle",
        ">": "\\rangle",
    }

    def __init__(
        self,
        left: str | Token,
        right: str | Token,
        *children: str | float | Token,
        scale: bool = False,
    ) -> None:
        """A mixed bracketed expression, such as `[0, 1)`."""
        super().__init__(*children, scale=scale)
        self.left_bracket = self.__bracket_shorthands.get(str(left), str(left))
        self.right_bracket = self.__bracket_shorthands.get(str(right), str(right))


class ArrayIndex(Token):
    def __init__(
        self,
        array: str | Token,
        *index: str | Token,
        separate: bool | None = None,
        bracket_type: str | None = None,
    ):
        self.array = texttt(array) if isinstance(array, str) else as_token(array)
        self.index = [texttt(i) if isinstance(i, str) else as_token(i) for i in index]
        self._separate = separate
        self._bracket_type = bracket_type

    @property
    def separate(self) -> bool:
        if self._separate is not None:
            return self._separate
        return ACTIVE_CONFIG.array_index_separate

    @separate.setter
    def separate(self, value: bool | None) -> None:
        self._separate = value

    @property
    def bracket_type(self) -> str:
        if self._bracket_type is not None:
            return self._bracket_type
        return ACTIVE_CONFIG.array_index_bracket_type

    @bracket_type.setter
    def bracket_type(self, value: str | None) -> None:
        self._bracket_type = value

    def __str__(self) -> str:
        output = [self.array]
        bracket_types = {
            "square": ("[", "]"),
            "curly": ("\\{", "\\}"),
            "angle": ("\\langle", "\\rangle"),
            "absolute": ("|", "|"),
            "round": ("(", ")"),
            "paren": ("(", ")"),
        }
        raw_delims = bracket_types.get(self.bracket_type, ("[", "]"))
        delim_macros = (
            Macro("texttt", raw_delims[0]),
            Macro("texttt", raw_delims[1]),
        )
        if self.separate:
            output.extend(delim_macros[0] & i & delim_macros[1] for i in self.index)
        else:
            output.append(delim_macros[0] & Sequence(*self.index) & delim_macros[1])
        return str(Concatenation(*output))


def bracket(*children: Token | str | float, scale: bool = False) -> Bracket:
    """A set of brackets, such as `(a, b, c)`."""
    return Bracket(*children, scale=scale)


paren = bracket


def square_bracket(
    *children: Token | str | float, scale: bool = False
) -> SquareBracket:
    """A set of square brackets, such as `[a, b, c]`."""
    return SquareBracket(*children, scale=scale)


def curly_bracket(
    *children: Token | str | float, scale: bool = False
) -> CurlyBracket:
    """A set of curly brackets, such as `{a, b, c}`."""
    return CurlyBracket(*children, scale=scale)


brace = curly_bracket


def absolute(
    *children: Token | str | float, scale: bool = False
) -> AbsoluteValue:
    """The absolute value of an expression, such as `|a|`."""
    return AbsoluteValue(*children, scale=scale)


abs = absolute  # noqa: A001


def angle_bracket(
    *children: Token | str | float, scale: bool = False
) -> AngleBracket:
    """A set of angle brackets, such as `<a, b, c>`."""
    return AngleBracket(*children, scale=scale)


def norm(*children: Token | str | float, scale: bool = False) -> Norm:
    r"""The norm of an expression, such as `\|a\|`."""
    return Norm(*children, scale=scale)


def floor(*children: Token | str | float, scale: bool = False) -> Floor:
    r"""The floor of an expression, such as `\lfloor a \rfloor`."""
    return Floor(*children, scale=scale)


def ceil(*children: Token | str | float, scale: bool = False) -> Ceil:
    r"""The ceiling of an expression, such as `\lceil a \rceil`."""
    return Ceil(*children, scale=scale)


register_token_converter(
    list, lambda v: SquareBracket(*[as_token(x) for x in v], scale=True)
)
register_token_converter(
    tuple, lambda v: Bracket(*[as_token(x) for x in v], scale=True)
)
register_token_converter(
    set, lambda v: CurlyBracket(*[as_token(x) for x in v], scale=True)
)


__all__ = [
    "_Container",
    "Collection",
    "Sequence",
    "Bracket",
    "SquareBracket",
    "CurlyBracket",
    "AngleBracket",
    "AbsoluteValue",
    "Norm",
    "Floor",
    "Ceil",
    "MixedBracket",
    "ArrayIndex",
    "bracket",
    "paren",
    "square_bracket",
    "curly_bracket",
    "brace",
    "absolute",
    "abs",
    "angle_bracket",
    "norm",
    "floor",
    "ceil",
]

