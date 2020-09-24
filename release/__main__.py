from .plugins.common import print_error
from .plugins.conf import parse_and_combine_args
from .release import run


try:
    run(settings=parse_and_combine_args())
except Exception as exc:
    print_error(str(exc), with_traceback=True)
    exit(1)
