""" Base class to implement a new LLM

This module is the base class to integrate the various LLMs API. This module also
includes the Base LLM classes for OpenAI and Google PaLM.

Example:

    ```
    from .base import BaseOpenAI

    class CustomLLM(BaseOpenAI):

        Custom Class Starts here!!
    ```
"""

from __future__ import annotations

import ast
import re
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Optional

from pandasai.helpers.memory import Memory
from pandasai.prompts.generate_system_message import GenerateSystemMessagePrompt

from ..exceptions import (
    APIKeyNotFoundError,
    MethodNotImplementedError,
    NoCodeFoundError,
)
from ..prompts.base import BasePrompt

if TYPE_CHECKING:
    from pandasai.pipelines.pipeline_context import PipelineContext


class LLM:
    """Base class to implement a new LLM."""

    last_prompt: Optional[str] = None

    def is_pandasai_llm(self) -> bool:
        """
        Return True if the LLM is from pandasAI.

        Returns:
            bool: True if the LLM is from pandasAI

        """
        return True

    @property
    def type(self) -> str:
        """
        Return type of LLM.

        Raises:
            APIKeyNotFoundError: Type has not been implemented

        Returns:
            str: Type of LLM a string

        """
        raise APIKeyNotFoundError("Type has not been implemented")

    def _polish_code(self, code: str) -> str:
        """
        Polish the code by removing the leading "python" or "py",  \
        removing surrounding '`' characters  and removing trailing spaces and new lines.

        Args:
            code (str): A string of Python code.

        Returns:
            str: Polished code.

        """
        if re.match(r"^(python|py)", code):
            code = re.sub(r"^(python|py)", "", code)
        if re.match(r"^`.*`$", code):
            code = re.sub(r"^`(.*)`$", r"\1", code)
        code = code.strip()
        return code

    def _is_python_code(self, string):
        """
        Return True if it is valid python code.
        Args:
            string (str):

        Returns (bool): True if Python Code otherwise False

        """
        try:
            ast.parse(string)
            return True
        except SyntaxError:
            return False

    def _extract_code(self, response: str, separator: str = "```") -> str:
        """
        Extract the code from the response.

        Args:
            response (str): Response
            separator (str, optional): Separator. Defaults to "```".

        Raises:
            NoCodeFoundError: No code found in the response

        Returns:
            str: Extracted code from the response

        """
        code = response

        # If separator is in the response then we want the code in between only
        if separator in response and len(code.split(separator)) > 1:
            code = code.split(separator)[1]
        code = self._polish_code(code)

        # Even if the separator is not in the response, the output might still be valid python code
        if not self._is_python_code(code):
            raise NoCodeFoundError("No code found in the response")

        return code

    def prepend_system_prompt(self, prompt: BasePrompt, memory: Memory):
        """
        Append system prompt to the chat prompt, useful when model doesn't have messages for chat history
        Args:
            prompt (BasePrompt): prompt for chat method
            memory (Memory): user conversation history
        """
        return self.get_system_prompt(memory) + prompt if memory else prompt

    def get_system_prompt(self, memory: Memory) -> Any:
        """
        Generate system prompt with agent info and previous conversations
        """
        system_prompt = GenerateSystemMessagePrompt(memory=memory)
        return system_prompt.to_string()

    def get_messages(self, memory: Memory) -> Any:
        """
        Return formatted messages
        Args:
            memory (Memory): Get past Conversation from memory
        """
        return memory.get_previous_conversation()

    @abstractmethod
    def call(self, instruction: BasePrompt, context: PipelineContext = None) -> str:
        """
        Execute the LLM with given prompt.

        Args:
            instruction (BasePrompt): A prompt object with instruction for LLM.
            context (PipelineContext, optional): PipelineContext. Defaults to None.

        Raises:
            MethodNotImplementedError: Call method has not been implemented

        """
        raise MethodNotImplementedError("Call method has not been implemented")

    def generate_code(self, instruction: BasePrompt, context: PipelineContext) -> str:
        """
        Generate the code based on the instruction and the given prompt.

        Args:
            instruction (BasePrompt): Prompt with instruction for LLM.

        Returns:
            str: A string of Python code.

        """
        response = self.call(instruction, context)
        return self._extract_code(response)


class BaseGoogle(LLM):
    """Base class to implement a new Google LLM

    LLM base class is extended to be used with
    """

    temperature: Optional[float] = 0
    top_p: Optional[float] = 0.8
    top_k: Optional[int] = 40
    max_output_tokens: Optional[int] = 1000

    def _valid_params(self):
        return ["temperature", "top_p", "top_k", "max_output_tokens"]

    def _set_params(self, **kwargs):
        """
        Dynamically set Parameters for the object.

        Args:
            **kwargs:
                Possible keyword arguments: "temperature", "top_p", "top_k",
                "max_output_tokens".

        Returns:
            None.

        """

        valid_params = self._valid_params()
        for key, value in kwargs.items():
            if key in valid_params:
                setattr(self, key, value)

    def _validate(self):
        """Validates the parameters for Google"""

        if self.temperature is not None and not 0 <= self.temperature <= 1:
            raise ValueError("temperature must be in the range [0.0, 1.0]")

        if self.top_p is not None and not 0 <= self.top_p <= 1:
            raise ValueError("top_p must be in the range [0.0, 1.0]")

        if self.top_k is not None and not 0 <= self.top_k <= 100:
            raise ValueError("top_k must be in the range [0.0, 100.0]")

        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be greater than zero")

    @abstractmethod
    def _generate_text(self, prompt: str, memory: Optional[Memory] = None) -> str:
        """
        Generates text for prompt, specific to implementation.

        Args:
            prompt (str): A string representation of the prompt.

        Returns:
            str: LLM response.

        """
        raise MethodNotImplementedError("method has not been implemented")

    def call(self, instruction: BasePrompt, context: PipelineContext = None) -> str:
        """
        Call the Google LLM.

        Args:
            instruction (BasePrompt): Instruction to pass.
            context (PipelineContext): Pass PipelineContext.

        Returns:
            str: LLM response.

        """
        self.last_prompt = instruction.to_string()
        memory = context.memory if context else None
        return self._generate_text(self.last_prompt, memory)
