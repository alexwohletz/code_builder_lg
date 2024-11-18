import re
from typing import Union

class Utils:
    @staticmethod
    def convert_to_string(value: Union[str, int]) -> str:
        """
        Converts an integer to a string and removes non-alphanumeric characters.
        
        :param value: The value to convert, can be a string or an integer.
        :return: A cleaned string with only alphanumeric characters.
        """
        if isinstance(value, int):
            value = str(value)
        return re.sub(r'[^a-zA-Z0-9]', '', value).lower()

    @staticmethod
    def validate_input(value: Union[str, int]) -> None:
        """
        Validates that the input is either a string or an integer.
        
        :param value: The value to validate.
        :raises ValueError: If the input is not a string or an integer.
        """
        if not isinstance(value, (str, int)):
            raise ValueError("Input must be a string or an integer.")