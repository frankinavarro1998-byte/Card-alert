from .generic import GenericChecker


class WalmartChecker(GenericChecker):
    name = "walmart"
    positive_signals = GenericChecker.positive_signals + ("pickup", "delivery", "shipping")
    negative_signals = GenericChecker.negative_signals + ("this item is unavailable", "not available")
