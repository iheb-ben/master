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
    pattern = r"^(?!_)(?!.*__)[a-z_]+(?<!_)$"
    return bool(re.match(pattern, field_name))


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
    pattern = r"^_?[A-Za-z]+$"
    return bool(re.match(pattern, class_name))
