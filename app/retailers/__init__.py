
from .generic import GenericChecker
from .target import TargetChecker
from .walmart import WalmartChecker
from .topps import ToppsChecker

CHECKERS = {
    "target": TargetChecker(),
    "walmart": WalmartChecker(),
    "topps": ToppsChecker(),
    "other": GenericChecker(),
}
