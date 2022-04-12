import abc


class CommaSeparatedField(set, abc.ABC):

    name: str = None

    def make_help_text(self) -> str:
        """
        Generate help text that wraps each category in backticks.
        """
        formatted = [f"`{item}`" for item in sorted(self)]
        # Add an "and" at the end of the list
        if len(formatted) > 1:
            formatted[-1] = f"and {formatted[-1]}"
        help_text = (
            f"A comma separated list of {self.name}; available {self.name} include: "
            f"{', '.join(formatted)}."
        )
        return help_text
