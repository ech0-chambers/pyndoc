"""Container and bracket AST tokens for grouping mathematical expressions."""

from abc import ABC, abstractmethod
import builtins
from typing import Optional, Any
from .config import ACTIVE_CONFIG
from .core import (
    Token,
    CallableToken,
    Literal,
    Macro,
    Concatenation,
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
            return self.children[0].value
        return None

    def __getitem__(self, index: int) -> Token:
        return self.children[index]

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        if len(self) == 1:
            return self.children[0](*args, **kwargs)
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
        return f"{scale_left}{self.left_bracket} {', '.join(str(child) for child in self.children)} {scale_right}{self.right_bracket}"


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
        return as_token(val)(*args, **kwargs)


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
        self.left_bracket = self.__bracket_shorthands.get(left, left)
        self.right_bracket = self.__bracket_shorthands.get(right, right)


class ArrayIndex(Token):
    def __init__(
        self,
        array: str | Token,
        *index: str | Token,
        separate: Optional[bool] = None,
        bracket_type: Optional[str] = None,
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
    def separate(self, value: Optional[bool]) -> None:
        self._separate = value

    @property
    def bracket_type(self) -> str:
        if self._bracket_type is not None:
            return self._bracket_type
        return ACTIVE_CONFIG.array_index_bracket_type

    @bracket_type.setter
    def bracket_type(self, value: Optional[str]) -> None:
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
        bracket_type = bracket_types.get(self.bracket_type, ("[", "]"))
        bracket_type = (
            Macro("texttt", bracket_type[0]),
            Macro("texttt", bracket_type[1]),
        )
        if self.separate:
            output.extend(bracket_type[0] & i & bracket_type[1] for i in self.index)
        else:
            output.append(bracket_type[0] & Sequence(*self.index) & bracket_type[1])
        return str(Concatenation(*output))


def bracket(*children: Token | str | float) -> Bracket:
    """A set of brackets, such as `(a, b, c)`."""
    return Bracket(*children)


paren = bracket


def square_bracket(*children: Token | str | float) -> SquareBracket:
    """A set of square brackets, such as `[a, b, c]`."""
    return SquareBracket(*children)


def curly_bracket(*children: Token | str | float) -> CurlyBracket:
    """A set of curly brackets, such as `{a, b, c}`."""
    return CurlyBracket(*children)


brace = curly_bracket


def absolute(*children: Token | str | float) -> AbsoluteValue:
    """The absolute value of an expression, such as `|a|`."""
    return AbsoluteValue(*children)


abs = absolute


def angle_bracket(*children: Token | str | float) -> AngleBracket:
    """A set of angle brackets, such as `<a, b, c>`."""
    return AngleBracket(*children)


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
]

