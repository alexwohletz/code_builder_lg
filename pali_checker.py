def is_palindrome(number):
    """
    Check if a given number is a palindrome.

    Args:
        number (int): The number to check.

    Returns:
        bool: True if the number is a palindrome, False otherwise.

    Raises:
        TypeError: If the input is not an integer.
    """
    if not isinstance(number, int):
        raise TypeError("Input must be an integer")

    if number < 0:
        return False

    original_number = number
    reversed_number = 0

    while number > 0:
        digit = number % 10
        reversed_number = reversed_number * 10 + digit
        number //= 10

    return original_number == reversed_number

if __name__ == "__main__":
    print(is_palindrome(12321))
    print(is_palindrome(12345))
    print(is_palindrome(-12321))