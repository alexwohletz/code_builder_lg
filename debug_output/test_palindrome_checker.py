import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict, List
import pytest
from unittest.mock import patch
from palindrome_checker import PalindromeChecker

@pytest.fixture
def palindrome_checker_instance():
    instance = PalindromeChecker()
    yield instance
@pytest.mark.parametrize("input_value, expected", [
    ('a', True),
    ('1', True),
    ('A', True),
    ('', False),
    (' ', False),
    ('A man, a plan, a canal, Panama', True),
    ('No lemon, no melon', True),
    ('Was it a car or a cat I saw?', True),
    ('Not a palindrome', False),
    (-121, True),
    (12321, True),
    (123456, False),
    ('12321', True),
    ('123456', False),
    ('Able was I, I saw Elba', True),
    ('Madam, in Eden, I\'m Adam', True),
    ('Step on no pets', True),
    ('Eva, can I see bees in a cave?', True),
    ('A Toyota. Race fast, safe car. A Toyota.', True),
    ('A Santa at NASA', True),
    ('Was it a car or a cat I saw?', True),
    ('No lemon, no melon', True),
    ('A man, a plan, a canal, Panama', True),
    ('Not a palindrome', False),
    ('', False),
    (' ', False),
    ('a', True),
    ('1', True),
    ('A', True),
    ('12321', True),
    ('123456', False),
    ('Able was I, I saw Elba', True),
    ('Madam, in Eden, I\'m Adam', True),
    ('Step on no pets', True),
    ('Eva, can I see bees in a cave?', True),
    ('A Toyota. Race fast, safe car. A Toyota.', True),
    ('A Santa at NASA', True),
])
def test_is_palindrome_happy_path(palindrome_checker_instance, input_value, expected):
    with patch('utils.Utils.validate_input') as mock_validate_input:
        with patch('utils.Utils.convert_to_string') as mock_convert_to_string:
            mock_convert_to_string.return_value = str(input_value).replace(" ", "").lower().replace(",", "").replace(".", "").replace("?", "").replace("'", "").replace("!", "")
            result = palindrome_checker_instance.is_palindrome(input_value)
            assert result == expected
            mock_validate_input.assert_called_once_with(input_value)
            mock_convert_to_string.assert_called_once_with(input_value)
@pytest.mark.parametrize("input_value, expected_exception", [
    (None, ValueError),
    ([], ValueError),
    ({}, ValueError),
    (3.14, ValueError),
    (True, ValueError),
    (False, ValueError),
])
def test_is_palindrome_error_scenarios(palindrome_checker_instance, input_value, expected_exception):
    with pytest.raises(expected_exception):
        palindrome_checker_instance.is_palindrome(input_value)