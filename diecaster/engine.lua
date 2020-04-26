local api = ...
local timeoutToken = {}

local unpack = table.unpack
local select = select
local rawequal = rawequal
local pcall = pcall
local xpcall = xpcall
local error = error
local tostring = tostring
local setmetatable = setmetatable

setmetatable(
    timeoutToken,
    {
        __tostring = function()
            return "LUA execution timed out"
        end,
        __metatable = {}
    }
)

-- make the timeout error uncatchable
_G.pcall = function(...)
    local res = {pcall(...)}

    if not res[1] and rawequal(res[2], timeoutToken) then
        error(timeoutToken)
    else
        return unpack(res)
    end
end

_G.xpcall = function(...)
    local res = {xpcall(...)}

    if not res[1] and rawequal(res[2], timeoutToken) then
        error(timeoutToken)
    else
        return unpack(res)
    end
end

_G.print = api.print

return {
    setTimeout = function(count)
        api.debug.sethook(
            function()
                if api.isTimeout() then
                    error(timeoutToken)
                end
            end,
            "",
            count
        )
    end,
    tostring = tostring
}
