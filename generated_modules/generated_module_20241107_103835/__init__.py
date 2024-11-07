def is_palindrome(num):
    """
    Check if a given number is a palindrome.

    Args:
        num (int): The number to check.

    Returns:
        bool: True if the number is a palindrome, False otherwise.

    Raises:
        TypeError: If the input is not an integer.
    """
    if not isinstance(num, int):
        raise TypeError("Input must be an integer")

    if num < 0:
        return False

    return str(num) == str(num)[::-1]