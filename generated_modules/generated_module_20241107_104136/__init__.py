def is_palindrome(num):
    """
    Check if a given number is a palindrome.

    Args:
        num (int): The number to check.

    Returns:
        bool: True if the number is a palindrome, False otherwise.

    Raises:
        TypeError: If input is not an integer.
    """
    # Check if input is an integer
    if not isinstance(num, int):
        raise TypeError("Input must be an integer")

    # Handle negative numbers by converting to positive
    num = abs(num)

    # Convert number to string for easy comparison
    num_str = str(num)

    # Check if string is equal to its reverse
    return num_str == num_str[::-1]