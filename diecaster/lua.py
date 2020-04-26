from ctypes import (
    cdll,
    c_void_p,
    c_char_p,
    c_longlong,
    c_long,
    sizeof,
    c_int,
    c_double,
    CFUNCTYPE,
    CDLL,
    c_size_t,
)
from sys import platform
from os.path import realpath, dirname, join
from types import SimpleNamespace
from typing import Any, List, Callable
from time import monotonic

if platform == "win32" or platform == "cygwin":
    _lualib: CDLL = cdll.LoadLibrary(
        join(
            dirname(realpath(__file__)),
            "lua-bin",
            "win64" if sizeof(c_void_p) == 8 else "win32",
            "lua53.dll",
        )
    )

elif platform == "darwin":
    _lualib: CDLL = cdll.LoadLibrary("liblua5.3.dylib")
else:
    _lualib: CDLL = cdll.LoadLibrary("liblua5.3.so")

_libs: List[str] = ["table", "string", "utf8", "math"]

if sizeof(c_longlong) == sizeof(c_void_p):
    _intptr_t = c_longlong
else:
    _intptr_t = c_long

_lua_int = c_longlong
_lua_num = c_double
_lua_kcon = _intptr_t
_lua_kfun = c_void_p
_lua_cfun = c_void_p
_lua_state = c_void_p
_lua_hook = c_void_p
_lua_debug = c_void_p

_lua_cfun_cb: CFUNCTYPE = CFUNCTYPE(c_int, c_void_p)
_lua_hook_cb: CFUNCTYPE = CFUNCTYPE(None, c_void_p, c_void_p)


if sizeof(c_int) >= 4:
    _LUAI_MAXSTACK: int = 1000000
else:
    _LUAI_MAXSTACK: int = 15000
_LUA_MULTRET: int = -1
_LUA_OK: int = 0
_LUA_TNONE: int = -1
_LUA_TNIL: int = 0
_LUA_TBOOLEAN: int = 1
_LUA_TLIGHTUSERDATA: int = 2
_LUA_TNUMBER: int = 3
_LUA_TSTRING: int = 4
_LUA_TTABLE: int = 5
_LUA_TFUNCTION: int = 6
_LUA_TUSERDATA: int = 7
_LUA_TTHREAD: int = 8
_LUA_REGISTRYINDEX: int = -_LUAI_MAXSTACK - 1000

_lua: SimpleNamespace = SimpleNamespace()


def _registerFunc(name: str, restype: Any, *argtypes: List[Any]):
    if hasattr(_lua, name):
        raise Exception("LUA function %s has already been registered" % name)

    func = _lualib[name]
    func.restype = restype
    func.argtypes = argtypes

    setattr(_lua, name, func)


_registerFunc("luaL_newstate", _lua_state)
_registerFunc("lua_close", None, _lua_state)
_registerFunc("luaL_requiref", None, _lua_state, c_char_p, _lua_cfun, c_int)
_registerFunc("lua_settop", None, _lua_state, c_int)
_registerFunc("lua_gettop", c_int, _lua_state)
_registerFunc("lua_tolstring", c_char_p, _lua_state, c_int, c_void_p)
_registerFunc("lua_tointegerx", _lua_int, _lua_state, c_int, c_void_p)
_registerFunc("lua_tonumberx", _lua_num, _lua_state, c_int, c_void_p)
_registerFunc("lua_toboolean", c_int, _lua_state, c_int)
_registerFunc("lua_type", c_int, _lua_state, c_int)
_registerFunc("lua_typename", c_char_p, _lua_state, c_int)
_registerFunc("lua_geti", c_int, _lua_state, c_int, _lua_int)
_registerFunc("lua_rawget", c_int, _lua_state, c_int)
_registerFunc("lua_rawgeti", c_int, _lua_state, c_int, _lua_int)
_registerFunc("lua_seti", None, _lua_state, c_int, _lua_int)
_registerFunc("lua_rawseti", None, _lua_state, c_int, _lua_int)
_registerFunc("lua_rawset", None, _lua_state, c_int)
_registerFunc("lua_pushnil", None, _lua_state)
_registerFunc("lua_pushlstring", c_char_p, _lua_state, c_char_p, c_int)
_registerFunc("lua_pushinteger", None, _lua_state, _lua_int)
_registerFunc("lua_pushnumber", None, _lua_state, _lua_num)
_registerFunc("lua_pushboolean", None, _lua_state, c_int)
_registerFunc("lua_pushcclosure", None, _lua_state, _lua_cfun, c_int)
_registerFunc("lua_pushvalue", None, _lua_state, c_int)
_registerFunc("lua_createtable", None, _lua_state, c_int, c_int)
_registerFunc(
    "lua_pcallk", c_int, _lua_state, c_int, c_int, c_int, _lua_kcon, _lua_kfun
)
_registerFunc("luaL_ref", c_int, _lua_state, c_int)
_registerFunc("lua_next", c_int, _lua_state, c_int)
_registerFunc("lua_isinteger", c_int, _lua_state, c_int)
_registerFunc("lua_setglobal", None, _lua_state, c_char_p)
_registerFunc("lua_rotate", None, _lua_state, c_int, c_int)
_registerFunc("lua_absindex", c_int, _lua_state, c_int)
_registerFunc("lua_checkstack", c_int, _lua_state, c_int)
_registerFunc("luaL_loadstring", c_int, _lua_state, c_char_p)
_registerFunc(
    "luaL_loadbufferx", c_int, _lua_state, c_char_p, c_size_t, c_char_p, c_char_p
)

for lib in _libs:
    _registerFunc("luaopen_" + lib, c_int, _lua_state)
_registerFunc("luaopen_base", c_int, _lua_state)
_registerFunc("luaopen_debug", c_int, _lua_state)

_lua.lua_pcall = lambda L, n, r, f: _lua.lua_pcallk(L, n, r, f, 0, None)
_lua.lua_pop = lambda L, n: _lua.lua_settop(L, -n - 1)
_lua.luaL_dostring = lambda L, str: _lua.luaL_loadstring(L, str) or _lua.lua_pcall(
    L, 0, _LUA_MULTRET, 0
)
_lua.lua_tostring = lambda L, i: _lua.lua_tolstring(L, i, None)
_lua.lua_tointeger = lambda L, i: _lua.lua_tointegerx(L, i, None)
_lua.lua_tonumber = lambda L, i: _lua.lua_tonumberx(L, i, None)
_lua.lua_newtable = lambda L: _lua.lua_createtable(L, 0, 0)
_lua.luaL_typename = lambda L, i: _lua.lua_typename(L, _lua.lua_type(L, i))
_lua.lua_pushcfunction = lambda L, f: _lua.lua_pushcclosure(L, f, 0)
_lua.lua_isfunction = lambda L, n: _lua.lua_type(L, n) == _LUA_TFUNCTION
_lua.luaL_loadbuffer = lambda L, s, sz, n: _lua.luaL_loadbufferx(L, s, sz, n, None)

with open(join(dirname(realpath(__file__)), "engine.lua"), "rt") as luaFile:
    _engineCode: str = luaFile.read()


class PlaceholderString(str):
    """Used to indicate non-convertable values from LUA"""

    def __repr__(self):
        return self


def _getLuaVarAt(state: _lua_state, i: int, stringFallback: bool = False) -> Any:
    type: int = _lua.lua_type(state, i)

    if type == _LUA_TNIL:
        return None

    elif type == _LUA_TBOOLEAN:
        return bool(_lua.lua_toboolean(state, i))

    elif type == _LUA_TNUMBER:
        if _lua.lua_isinteger(state, i):
            return _lua.lua_tointeger(state, i)
        else:
            return _lua.lua_tonumber(state, i)

    elif type == _LUA_TSTRING:
        return _lua.lua_tostring(state, i).decode("UTF-8")

    elif type == _LUA_TTABLE:
        numkeys: int = 0
        maxkey: int = 0
        useDict: bool = False
        i = _lua.lua_absindex(state, i)

        # push the starting "key" (nil)
        _lua.lua_pushnil(state)
        while _lua.lua_next(state, i) != 0:
            if not _lua.lua_isinteger(state, -2):
                type = _lua.luaL_typename(state, -2).decode("UTF-8")
                _lua.lua_pop(state, 2)
                useDict = True
                break

            keyval: int = _lua.lua_tointeger(state, -2)

            if keyval <= 0:
                _lua.lua_pop(state, 2)
                raise Exception("Returned table contains invalid indexes")

            if keyval > maxkey:
                maxkey = keyval
            numkeys += 1
            # pop the value, leave the next key
            _lua.lua_pop(state, 1)

        if useDict:
            res: dict = {}

            # push the starting "key" (nil)
            _lua.lua_pushnil(state)
            while _lua.lua_next(state, i) != 0:
                res[_getLuaVarAt(state, -2)] = _getLuaVarAt(state, -1, stringFallback)

                # pop the value, leave the next key
                _lua.lua_pop(state, 1)

            return res

        else:
            if maxkey != numkeys:
                raise Exception("Returned table is a sparse list")

            res: list = []

            for j in range(numkeys):
                _lua.lua_geti(state, i, j + 1)
                res.append(_getLuaVarAt(state, -1, stringFallback))
                _lua.lua_pop(state, 1)

            return res

    elif stringFallback:
        return PlaceholderString(
            "<LUA %s>" % _lua.lua_typename(state, type).decode("UTF-8")
        )

    else:
        raise Exception(
            "Illegal LUA return type: " + _lua.lua_typename(state, type).decode("UTF-8")
        )


def _createCallback(func: Callable, argStringFallback: bool = False) -> _lua_cfun_cb:
    def wrapper(state) -> int:
        try:
            args: tuple = (
                _getLuaVarAt(state, i + 1, argStringFallback)
                for i in range(_lua.lua_gettop(state))
            )
            res: Any = func(*args)

            if type(res) is not tuple:
                res = (None, res)
            else:
                res = (None, *res)

            for v in res:
                _pushValue(state, v)

            return len(res)

        except BaseException as e:
            _pushValue(state, str(e))
            return 1

    return _lua_cfun_cb(wrapper)


def _checkStack(state: _lua_state, n: int):
    if not _lua.lua_checkstack(state, 1):
        raise Exception("Unable to allocate LUA stack slots")


def _pushValue(state: _lua_state, value: Any):
    if value is None:
        _checkStack(state, 1)
        _lua.lua_pushnil(state)
        return

    t = type(value)

    if t is int:
        _checkStack(state, 1)
        _lua.lua_pushinteger(state, value)

    elif t is float:
        _checkStack(state, 1)
        _lua.lua_pushnumber(state, value)

    elif t is bool:
        _checkStack(state, 1)
        _lua.lua_pushboolean(state, value)

    elif t is str:
        _checkStack(state, 1)
        bytes: bytes = value.encode("UTF-8")
        _lua.lua_pushlstring(state, bytes, len(bytes))

    elif isinstance(value, dict):
        _checkStack(state, 3)
        prev: int = _lua.lua_gettop(state)
        _lua.lua_newtable(state)

        try:
            for k, v in value.items():
                _pushValue(state, k)
                _pushValue(state, v)
                _lua.lua_rawset(state, -3)
        except:
            _lua.lua_settop(state, prev)
            raise

    elif t is _lua_cfun_cb:
        _checkStack(state, 1)
        _lua.lua_pushcfunction(state, value)

    else:
        try:
            iter(value)
        except TypeError:
            raise Exception(
                "Unable to convert python type %s to LUA value" % t.__name__
            )

        _checkStack(state, 2)
        prev: int = _lua.lua_gettop(state)
        _lua.lua_newtable(state)
        try:
            i: int = 1
            for v in value:
                _pushValue(state, v)
                _lua.lua_rawseti(state, -2, i)
                i += 1

        except:
            _lua.lua_settop(state, prev)
            raise


def _handleLuaCallError(
    state: _lua_state,
    res: int,
    prevTop: int = None,
    msg: str = None,
    converter: Callable[[_lua_state], str] = None,
):
    if res != _LUA_OK:
        if msg is None:
            msg = "Error from LUA call: "
        else:
            msg += ": "

        msgBytes: bytes = _lua.lua_tostring(state, -1)
        if msgBytes is None:
            decoded: str = None

            if converter is not None:
                decoded = converter(state)

            if decoded is None:
                msg += "<LUA %s>" % _lua.luaL_typename(state, -1).decode("UTF-8")
            else:
                msg += decoded
        else:
            msg += msgBytes.decode("UTF-8")

        if prevTop is None:
            _lua.lua_pop(state, 1)
        else:
            _lua.lua_settop(state, prevTop)

        raise Exception(msg)


class LuaState:
    """A LUA engine to run your code"""

    def __init__(self):
        self._state: _lua_state = _lua.luaL_newstate()
        self._lastStart: float = None
        self._timeout: float = None
        self._mainIndex: int = None
        self._hostIndex: int = None
        self._callbackWrapperIndex: int = None
        self._callables: List[_lua_cfun_cb] = []

        # Load safe standard libraries
        for lib in _libs:
            _lua.luaL_requiref(
                self._state, lib.encode("UTF-8"), getattr(_lua, "luaopen_" + lib), 1
            )
            _lua.lua_pop(self._state, 1)

        _lua.luaL_requiref(self._state, "_G".encode("UTF-8"), _lua.luaopen_base, 1)

        for field in ["dofile", "loadfile"]:
            _pushValue(self._state, field)
            _lua.lua_pushnil(self._state)
            _lua.lua_rawset(self._state, -3)

        _lua.lua_pop(self._state, 1)

        def checkTimeout(state):
            if self._timeout is None or self._lastStart is None:
                _pushValue(state, False)
            else:
                _pushValue(state, monotonic() - self._lastStart >= self._timeout)
            return 1

        checkFunc: _lua_cfun_cb = _lua_cfun_cb(checkTimeout)
        self._callables.append(checkFunc)

        printFunc: _lua_cfun_cb = _createCallback(lambda *args: print(*args), True)
        self._callables.append(printFunc)

        _pushValue(self._state, {"isTimeout": checkFunc})

        _pushValue(self._state, "print")
        self._pushCallback(printFunc)
        _lua.lua_rawset(self._state, -3)

        _pushValue(self._state, "debug")
        _lua.luaopen_debug(self._state)
        _lua.lua_rawset(self._state, -3)

        nres: int = self._doString(_engineCode, 1, "<base engine code>")

        if nres != 1:
            raise Exception("Unexpected number of return values")

        _pushValue(self._state, "setTimeout")
        _lua.lua_rawget(self._state, -2)
        self._setTimeoutIndex: int = _lua.luaL_ref(self._state, _LUA_REGISTRYINDEX)

        _pushValue(self._state, "tostring")
        _lua.lua_rawget(self._state, -2)
        self._toStringIndex: int = _lua.luaL_ref(self._state, _LUA_REGISTRYINDEX)

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        if self._state is not None:
            _lua.lua_close(self._state)
        self._state = None

    def __del__(self):
        if self._state is not None:
            print(
                "Warning: LUA state is discarded by finalizer, this should be done by the with statement"
            )
        self.__exit__(None, None, None)

    def _toString(self, _: _lua_state):
        _lua.lua_rawgeti(self._state, _LUA_REGISTRYINDEX, self._toStringIndex)

        # put the function before the arguments
        _lua.lua_rotate(self._state, -2, 1)

        res: int = _lua.lua_pcall(self._state, 1, 1, 0)
        if res != _LUA_OK:
            _lua.lua_pop(self._state, 1)
            return None
        else:
            msg: bytes = _lua.lua_tostring(self._state, -1)

            _lua.lua_pop(self._state, 1)
            return None if msg is None else msg.decode("UTF-8")

    def _handleLuaCallError(self, res: int, prevTop: int = None, msg: str = None):
        _handleLuaCallError(self._state, res, prevTop, msg, self._toString)

    def _pushCallback(self, func: _lua_cfun_cb, argStringFallback: bool = False):
        if self._callbackWrapperIndex is None:
            self._loadString(
                """
                local func = ...
                return function(...)
                    local res = {func(...)}
                    if res[1] then
                        error(res[1])
                    end

                    return select(2, table.unpack(res))
                end
                """
            )

            _lua.lua_pushvalue(self._state, -1)
            self._callbackWrapperIndex = _lua.luaL_ref(self._state, _LUA_REGISTRYINDEX)

        else:
            _lua.lua_rawgeti(
                self._state, _LUA_REGISTRYINDEX, self._callbackWrapperIndex
            )

        _pushValue(self._state, func)
        res: int = _lua.lua_pcall(self._state, 1, 1, 0)
        self._handleLuaCallError(
            res, None, "Error while calling LUA callback wrapper script"
        )

    def _doString(self, code: str, nargs: int = 0, chunkName: str = None):
        """Runs the given LUA code and returns the number of return values"""

        prev: int = _lua.lua_gettop(self._state) - nargs
        self._loadString(code, chunkName)

        if nargs > 0:
            # put the function before the arguments
            _lua.lua_rotate(self._state, -nargs - 1, 1)

        res: int = _lua.lua_pcall(self._state, nargs, _LUA_MULTRET, 0)
        self._handleLuaCallError(res, prev, "Error while executing LUA script")

        return _lua.lua_gettop(self._state) - prev

    def _loadString(self, code: str, chunkName: str = None):
        codeBytes: bytes = code.encode("UTF-8")
        nameBytes: bytes = codeBytes if chunkName is None else chunkName.encode("UTF-8")

        res: int = _lua.luaL_loadbuffer(
            self._state, codeBytes, len(codeBytes), nameBytes
        )
        self._handleLuaCallError(res, None, "Error while loading LUA script")

    def setTimeout(self, seconds: float):
        """Set the timout for LUA code in secods"""
        self._timeout = seconds

    def setTimeoutCheckInterval(self, numInstructions: int):
        """Set the interval at which the timeout gets checked while running LUA code"""
        prev: int = _lua.lua_gettop(self._state)

        _lua.lua_rawgeti(self._state, _LUA_REGISTRYINDEX, self._setTimeoutIndex)
        _pushValue(self._state, numInstructions)

        res: int = _lua.lua_pcall(self._state, 1, 0, 0)
        self._handleLuaCallError(
            res, prev, "Error while setting timeout check interval"
        )

    def loadMain(self, code: str):
        """Load the main script code"""
        self._loadString(code)

        if self._mainIndex is None:
            self._mainIndex = _lua.luaL_ref(self._state, _LUA_REGISTRYINDEX)
        else:
            _lua.rawseti(self._state, _LUA_REGISTRYINDEX, self._mainIndex)

    def runMain(self) -> tuple:
        """Run the previously loaded main script"""
        if self._mainIndex is None:
            raise Exception("No main LUA script loaded")

        if self._lastStart is not None:
            raise Exception("Running multiple scripts simultaneously is not supported")
        self._lastStart = monotonic()

        try:
            prev: int = _lua.lua_gettop(self._state)
            _lua.lua_rawgeti(self._state, _LUA_REGISTRYINDEX, self._mainIndex)
            res: Any = _lua.lua_pcall(self._state, 0, _LUA_MULTRET, 0)

            self._handleLuaCallError(res, None, "Error while executing main LUA script")

            num: int = _lua.lua_gettop(self._state) - prev
            res = tuple(_getLuaVarAt(self._state, prev + i + 1) for i in range(num))
            _lua.lua_pop(self._state, num)

        finally:
            self._lastStart = None

        return res

    def runString(self, code: str, chunkName: str = None):
        """Run the given LUA code (ignores return values)"""
        if self._lastStart is not None:
            raise Exception("Running multiple scripts simultaneously is not supported")
        self._lastStart = monotonic()

        try:
            _lua.lua_pop(self._state, self._doString(code, 0, chunkName))
        finally:
            self._lastStart = None

    def doString(self, code: str, chunkName: str = None) -> tuple:
        """Run the given LUA code and return its result values"""
        if self._lastStart is not None:
            raise Exception("Running multiple scripts simultaneously is not supported")
        self._lastStart = monotonic()

        try:
            num: int = self._doString(code, 0, chunkName)
            prev: int = _lua.lua_gettop(self._state) - num
            res: tuple = tuple(
                _getLuaVarAt(self._state, prev + i + 1) for i in range(num)
            )
            _lua.lua_pop(self._state, num)
        finally:
            self._lastStart = None

        return res

    def setHostField(self, name: str, value: Any):
        """Set the given field in the host table accessibly by the LUA code"""
        if self._hostIndex is None:
            _lua.lua_newtable(self._state)
            _lua.lua_pushvalue(self._state, -1)
            self._hostIndex = _lua.luaL_ref(self._state, _LUA_REGISTRYINDEX)

            _lua.lua_pushvalue(self._state, -1)
            _lua.lua_setglobal(self._state, "host".encode("UTF-8"))

        else:
            _lua.lua_rawgeti(self._state, _LUA_REGISTRYINDEX, self._hostIndex)

        _pushValue(self._state, name)

        if callable(value) and value is not _lua_cfun_cb:
            value = _createCallback(value)

            # prevent garbage collection
            self._callables.append(value)
            self._pushCallback(value)
        else:
            _pushValue(self._state, value)

        _lua.lua_rawset(self._state, -3)
        _lua.lua_pop(self._state, 1)

