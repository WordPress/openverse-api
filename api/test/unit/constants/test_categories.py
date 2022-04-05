import pytest
from catalog.api.constants.categories import Categories


@pytest.mark.parametrize(
    "categories, expected",
    [
        ([], "A comma separated list of categories; available categories include: ."),
        (
            ["a"],
            "A comma separated list of categories; available categories include: `a`.",
        ),
        (
            ["a", "b"],
            "A comma separated list of categories; "
            "available categories include: `a`, and `b`.",
        ),
        (
            ["a", "b", "c"],
            "A comma separated list of categories; "
            "available categories include: `a`, `b`, and `c`.",
        ),
    ],
)
def test_make_help_text(categories, expected):
    category_class = Categories(categories)
    actual = category_class.make_help_text()
    assert actual == expected
