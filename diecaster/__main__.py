# This is just example code

from sys import path
from os.path import dirname

path.insert(0, dirname(dirname(__file__)))

from diecaster import Engine, compile, parse


def parse2(input: str):
    print(input, "=>", parse(input))
    print(" " * len(input), "=>", compile(input))


parse2("5")
parse2("(5)")
parse2("((5))")
parse2("5d10")
parse2("(5)d10")
parse2("5 - 2 - 3")
parse2("5-(2)-3")
parse2("5 - 2 - 2d10 + 3")

_res = compile("d90-90")
print(_res)


def whatever(n: int) -> int:
    return n + 3


with Engine() as state:
    state.setHostField("getMySides", whatever)
    state.loadMain(
        """
        return values(chain(
            dice(20, 20)
            , multi(3)
            , f(6)
        ))
        """
    )

    state.setTimeoutCheckInterval(100_000)
    state.setTimeout(5)

    # print(state.runMain()[0])
    print(state.doString(f"return values({_res})")[0])
