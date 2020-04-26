from lark import Lark, Transformer, Tree
from os.path import realpath, dirname, join
from typing import List

with open(join(dirname(realpath(__file__)), "diecaster.lark"), "rt") as larkFile:
    _grammarCode: str = larkFile.read()

_parser = Lark(_grammarCode, start="expr")


class _TaggedStr(str):
    def __new__(cls, type, value):
        res = super().__new__(cls, value)
        res.type = type
        return res


class Visitor(Transformer):
    def dice(self, args):
        sides: str = "10"
        num: str = None
        reroll: str = None
        aggregator: str = None
        explosion: int = None
        selector: str = None
        arith: List[str] = []

        for arg in args:
            if isinstance(arg, Tree):
                if arg.data == "die":
                    sides = str(arg.children[0])
                elif arg.data == "dienum":
                    num = str(arg.children[0])
                elif arg.data == "reroll_low":
                    reroll = f"rerollLow({arg.children[0]})"
                elif arg.data == "reroll_high":
                    reroll = f"rerollHigh({arg.children[0]})"
                elif arg.data == "sum":
                    aggregator = "sum()"
                elif arg.data == "max":
                    aggregator = "max()"
                elif arg.data == "min":
                    aggregator = "min()"
                elif arg.data == "f":
                    aggregator = f"f({arg.children[0]})"
                elif arg.data == "e":
                    aggregator = f"e({arg.children[0]})"
                elif arg.data == "selector":
                    selected: str = ", ".join(str(c) for c in arg.children)
                    selector = f"selectDice({selected})"
            elif arg.type == "EXPLOSION":
                explosion = f"explosion({len(arg) - 1})"
            elif arg.type == "arith":
                arith.append(arg)

        if num is None:
            die: string = f"die({sides})"
        else:
            die: string = f"dice({num}, {sides})"

        pipe: List[str] = []

        if reroll is not None:
            pipe.append(reroll)
        if explosion is not None:
            pipe.append(explosion)
        if selector is not None:
            pipe.append(selector)
        if aggregator is not None:
            pipe.append(aggregator)
        pipe.extend(arith)

        if len(pipe) == 0:
            return die
        else:
            pipe = ", ".join(pipe)
            return f"chain({die}, {pipe})"

    def dice_expl(self, args):
        return self.dice(args)

    def plus(self, args):
        return _TaggedStr("arith", f"add({str(args[0])})")

    def minus(self, args):
        return _TaggedStr("arith", f"subtract({str(args[0])})")

    def NUM(self, value):
        return int(value)

    def DIGITS(self, value):
        return int(value)


_visitor: Visitor = Visitor()


def parse(input: str) -> Tree:
    return _parser.parse(input)


def compile(input: str) -> str:
    return _visitor.transform(_parser.parse(input))
