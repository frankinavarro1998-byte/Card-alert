from .generic import GenericChecker


class TargetChecker(GenericChecker):
    name = "target"
    positive_signals = GenericChecker.positive_signals + ("shipping", "pick it up", "add for shipping")
    negative_signals = GenericChecker.negative_signals + ("not eligible for shipping", "this item isn't available")
