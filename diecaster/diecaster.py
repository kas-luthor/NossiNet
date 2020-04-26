from lua import LuaState
from random import Random
from os.path import realpath, dirname, join

with open(join(dirname(realpath(__file__)), "diecaster.lua"), "rt") as luaFile:
    _luaCode: str = luaFile.read()


class Engine(LuaState):
    """The dice rolling engine"""

    def __init__(self):
        super().__init__()

        random: Random = Random()
        self.setHostField("random", lambda max: random.randrange(max))

        self.runString(_luaCode, "diecaster.lua")

