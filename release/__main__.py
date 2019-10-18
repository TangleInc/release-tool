from .plugins.conf import parse_and_combine_args
from .release import run


run(settings=parse_and_combine_args())
