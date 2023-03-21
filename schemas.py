"""
Schemas
"""

from typing import Literal, Optional, Union

from pydantic import BaseModel


Role = Union[Literal['user'], Literal['system'], Literal['assistant']]


class RuneDefinition(BaseModel):
    """RuneDefinition."""
    rune_name: str
    description: str
    type: Union[Literal['normal'], Literal['invert']]
    alternatives: Optional[list[str]]
    summaries: Optional[list[str]]


class Message(BaseModel):
    """Message."""
    role: Role
    content: str


class Choice(BaseModel):
    """Choice."""
    message: Message
    finish_reason: Union[
        Literal['stop'],
        Literal['length'],
        Literal['content_filter'],
        None,
    ]
    index: int


class Usage(BaseModel):
    """Usage."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class Response(BaseModel):
    """Response."""
    id: str
    object: str
    created: int
    model: str
    usage: Usage
    choices: list[Choice]


class Prompt(BaseModel):
    """Prompt."""
    role: Role
    content: str


class Processment(BaseModel):
    """Processment."""
    rune_definition: RuneDefinition
    total_tokens: int = 0
