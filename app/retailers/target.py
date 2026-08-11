from .generic import GenericChecker


class TargetChecker(GenericChecker):
    name = "target"

    positive_signals = (
        "add to cart",
        "add for shipping",
    )

    negative_signals = GenericChecker.negative_signals + (
        "not eligible for shipping",
        "this item isn't available",
        "item unavailable",
        "out of stock",
        "sold out",
    )
