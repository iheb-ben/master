import re


def is_field_norm_compliant(field_name: str) -> bool:
    """
    Checks if the class attribute complies with naming conventions:
    - Must be entirely lowercase.
    - Can contain underscores `_` within the name.
    - Must not start or end with an underscore, nor have consecutive underscores.
    - Must not contain uppercase letters.

    Args:
        field_name (str): The class attribute name to check.

    Returns:
        bool: True if the attribute name complies, False otherwise.
    """
    return bool(re.match(r"^(?!_)(?!.*__)[a-z_]+(?<!_)$", field_name))


def is_class_norm_compliant(class_name: str) -> bool:
    """
    Checks if the class name complies with naming conventions:
    - Can optionally start with a single underscore `_`.
    - Must contain only uppercase and lowercase letters (A-Z, a-z).
    Args:
        class_name (str): The class name to check.
    Returns:
        bool: True if the class name complies, False otherwise.
    """
    return bool(re.match(r"^_?[A-Za-z]+$", class_name))


def clean_string_advanced(message, chars_to_remove=None):
    """
    Cleans the input message by removing trailing specified characters.
    Defaults to whitespace if no characters are specified.
    """
    if chars_to_remove is None:
        chars_to_remove = " \t\n\r"
    return message.rstrip(chars_to_remove)
