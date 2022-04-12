from typing import Iterable


def make_comma_separated_help_text(items: Iterable, name: str) -> str:
    """
    Generate help text that wraps each category in backticks.
    """
    formatted = [f"`{item}`" for item in sorted(items)]
    # Add an "and" at the end of the list
    if len(formatted) > 1:
        formatted[-1] = f"and {formatted[-1]}"
    help_text = (
        f"A comma separated list of {name}; available {name} include: "
        f"{', '.join(formatted)}."
    )
    return help_text
