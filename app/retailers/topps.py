from .generic import GenericChecker


class ToppsChecker(GenericChecker):
    name = "topps"
    positive_signals = GenericChecker.positive_signals + ("add to bag",)
    negative_signals = GenericChecker.negative_signals + ("notify me when available",)
