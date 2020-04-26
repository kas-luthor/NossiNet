helpers = {}

function helpers.chainMember(processor)
    return function(input)
        local gen = {}
        gen.get = processor(input, gen)
        return gen
    end
end

function helpers.getScalar(input)
    if type(input) == "function" then
        return input()
    elseif type(input) ~= "table" then
        return input
    elseif input.get then
        return helpers.getScalar(input:get())
    elseif input.generator then
        return input.value
    else
        return helpers.getScalar(input[1])
    end
end

function helpers.getValue(input)
    if type(input) == "function" then
        return input()
    elseif type(input) ~= "table" then
        return input
    elseif input.generator then
        return input.value
    elseif input.get then
        return helpers.getValue(input:get())
    else
        local res = {}

        for i, v in ipairs(input) do
            res[i] = helpers.getValue(v)
        end

        return res
    end
end

function helpers.reduce(values, start, reducer)
    if type(values) ~= "table" or values.generator then
        return reducer(start, values)
    else
        local stop
        for _, v in ipairs(values) do
            start, stop = helpers.reduce(v, start, reducer)
            if stop then
                break
            end
        end

        return start
    end
end

function helpers.scalarGenerator(gen, max)
    local res = {
        max = max
    }

    function res:get()
        return {
            value = gen(self),
            generator = self
        }
    end

    return res
end

function helpers.mapTop(value, mapper)
    if type(value) ~= "table" or value.generator then
        return mapper(value)
    else
        local res = {}

        for i, v in ipairs(value) do
            res[i] = mapper(v)
        end

        return res
    end
end

function helpers.mapScalars(value, mapper)
    if type(value) ~= "table" or value.generator then
        return mapper(value)
    else
        local res = {}

        for i, v in ipairs(value) do
            res[i] = helpers.mapScalars(v, mapper)
        end

        return res
    end
end

function helpers.mapLists(values, depthFirst, mapper)
    if value.generator then
        return value
    else
        if depthFirst then
            local newValues = {}

            for i, v in ipairs(values) do
                newValues[i] = helpers.mapLists(v, depthFirst, mapper)
            end

            value = newValues
        end

        values = mapper(values)

        if not depthFirst then
            local newValues = {}

            for i, v in ipairs(values) do
                newValues[i] = helpers.mapLists(v, depthFirst, mapper)
            end

            value = newValues
        end

        return values
    end
end

function helpers.scalarMapper(input, mapper, max)
    if type(max) ~= "function" then
        max = helpers.getScalar(max)
    end

    return function()
        return helpers.mapScalars(
            input:get(),
            function(value)
                local prevGen = value.generator
                local max = max
                if type(max) == "function" then
                    max = max(prevGen)
                end

                local gen =
                    helpers.scalarGenerator(
                    function()
                        return mapper(prevGen:get())
                    end,
                    max
                )

                return {
                    value = mapper(value),
                    generator = gen
                }
            end
        )
    end
end

function helpers.shuffle(values)
    local len = #values

    for i = 1, len - 2 do
        local j = i + host.random(n - i + 1)

        if i ~= j then
            values[i], values[j] = values[j], values[i]
        end
    end
end

function helpers.any(values, predicate)
    return helpers.reduce(
        values,
        false,
        function(prev, value)
            if prev or predicate(value) then
                return true, true
            end

            return false
        end
    )
end

local function helpers_doFlatten(dest, value)
    table.insert(dest, value)
    return dest
end
function helpers.flatten(values)
    return helpers.reduce(values, {}, helpers_doFlatten)
end

local function helpers_collectSum(prev, curr)
    if type(curr) == "table" then
        return prev + (curr.value or 0)
    else
        return prev + (curr or 0)
    end
end
function helpers.sum(values)
    return helpers.reduce(values, 0, helpers_collectSum)
end

function helpers.filter(values, predicate)
    if type(values) ~= "table" or values.generator then
        return predicate(values) and values
    else
        local res = {}

        for _, v in ipairs(values) do
            v = helpers.filter(v, predicate)

            if v then
                table.insert(res, v)
            end
        end

        return res
    end
end

function helpers.filterFlat(values, predicate)
    return helpers.reduce(
        values,
        {},
        function(prev, value)
            if predicate(value) then
                table.insert(prev, value)
            end
            return prev
        end
    )
end

function helpers.count(values, predicate)
    return helpers.reduce(
        values,
        0,
        function(prev, value)
            if predicate(value) then
                return prev + 1
            else
                return prev
            end
        end
    )
end

function helpers.sorter(op1, op2)
    if type(op1) == "table" then
        op1 = op1.value
    end
    if type(op2) == "table" then
        op2 = op2.value
    end

    return op1 < op2
end

function helpers.reverseSorter(op1, op2)
    if type(op1) == "table" then
        op1 = op1.value
    end
    if type(op2) == "table" then
        op2 = op2.value
    end

    return op1 > op2
end

function helpers.sorted(values, sorter)
    values = helpers.flatten(values)
    table.sort(values, sorter)
    return values
end

local function helpers_cloneScalar(value)
    if type(value) == "table" then
        return {
            value = value.value,
            generator = value.generator
        }
    else
        return value
    end
end
function helpers.clone(values)
    return helpers.mapScalars(values, helpers_cloneScalar)
end

function die(sides)
    sides = helpers.getScalar(sides)
    if type(sides) ~= "number" or sides <= 0 then
        error("Invalid number of die sides")
    end

    return helpers.scalarGenerator(
        function()
            return host.random(sides) + 1
        end,
        sides
    )
end

local function staticScalarValue(value, max)
    if type(value) == "table" then
        local res = {}

        for i, v in ipairs(value) do
            res[i] = staticScalarValue(v)
        end

        return res
    else
        return helpers.scalarGenerator(
            function()
                return value
            end,
            max or value
        ):get()
    end
end
function static(value)
    if type(value) == "table" and value.get then
        value = value:get().value
    end

    value = values(value)

    local gen = {}

    function gen:get()
        return staticScalarValue(value)
    end

    return gen
end

function empty()
    local gen = {}

    function gen:get()
        return {}
    end

    return gen
end

local function getGeneratedScalar(value)
    if value.generator then
        return value
    else
        return getGeneratedScalar(value[1])
    end
end
function scalar()
    return helpers.chainMember(
        function(input)
            return function()
                return getGeneratedScalar(input:get())
            end
        end
    )
end

function flatten()
    return helpers.chainMember(
        function(input)
            return function()
                return helpers.flatten(input:get())
            end
        end
    )
end

function rerollIf(predicate)
    return helpers.chainMember(
        function(input)
            return function()
                return helpers.mapScalars(
                    input:get(),
                    function(value)
                        local prevGen = value.generator

                        local gen =
                            helpers.scalarGenerator(
                            function()
                                local v = prevGen:get()
                                while predicate(v.value) do
                                    v = prevGen:get()
                                end

                                return v.value
                            end
                        )

                        while predicate(value.value) do
                            value = prevGen:get()
                        end

                        return {
                            value = value.value,
                            generator = gen
                        }
                    end
                )
            end
        end
    )
end

function multi(times)
    times = helpers.getScalar(times)

    return helpers.chainMember(
        function(input)
            return function()
                local res = {}

                for i = 1, times do
                    res[i] = input:get()
                end

                return res
            end
        end
    )
end

function dice(times, sides)
    return multi(times)(die(sides))
end

local function sumMax(prev, value)
    if value.max then
        return prev + value.max
    else
        return prev
    end
end
function sum()
    return helpers.chainMember(
        function(input, gen)
            return function()
                local values = input:get()

                return {
                    value = helpers.sum(values),
                    generator = gen,
                    max = helpers.reduce(values, 0, sumMax)
                }
            end
        end
    )
end

local function collectMin(prev, curr)
    if prev and curr.value then
        if curr.value < prev.value then
            return curr
        else
            return prev
        end
    else
        return curr.value
    end
end
function min()
    return helpers.chainMember(
        function(input, gen)
            return function()
                local value = helpers.reduce(input:get(), nil, collectMin)

                return {
                    value = value.value,
                    generator = gen,
                    max = value.max
                }
            end
        end
    )
end

local function collectMax(prev, curr)
    if prev and curr.value then
        if curr.value > prev.value then
            return curr
        else
            return prev
        end
    else
        return curr.value
    end
end
function max()
    return helpers.chainMember(
        function(input, gen)
            return function()
                local value = helpers.reduce(input:get(), nil, collectMax)

                return {
                    value = value.value,
                    generator = gen,
                    max = value.max
                }
            end
        end
    )
end

local function applyMapping(mapper, value)
    if value.generator then
    end
end
function map(mapper, max)
    max = helpers.getScalar(max)

    return helpers.chainMember(
        function(input)
            return helpers.scalarMapper(
                input,
                function(value)
                    return mapper(value.value)
                end,
                max
            )
        end
    )
end

function append(...)
    local args = {...}

    return helpers.chainMember(
        function(input)
            return function()
                local res = {input:get()}

                for i, gen in ipairs(args) do
                    if type(gen) ~= "table" or not gen.get then
                        res[i + 1] = static(gen):get()
                    else
                        res[i + 1] = gen:get()
                    end
                end

                return res
            end
        end
    )
end

function prepend(...)
    local args = {...}

    return helpers.chainMember(
        function(input)
            return function()
                local res = {}

                for i, gen in ipairs(args) do
                    if type(gen) ~= "table" or not gen.get then
                        res[i] = static(gen):get()
                    else
                        res[i] = gen:get()
                    end
                end

                table.insert(res, input:get())

                return res
            end
        end
    )
end

function concat(...)
    local args = {...}

    return helpers.chainMember(
        function(input)
            return function()
                local res = {}
                local i = 1

                local value = input:get()
                if value.generator then
                    res[i] = value
                    i = i + 1
                else
                    for _, v in ipairs(value) do
                        res[i] = v
                        i = i + 1
                    end
                end

                for _, gen in ipairs(args) do
                    local value
                    if type(gen) ~= "table" or not gen.get then
                        value = static(gen):get()
                    else
                        value = gen:get()
                    end

                    if value.generator then
                        res[i] = value
                        i = i + 1
                    else
                        for _, v in ipairs(value) do
                            res[i] = v
                            i = i + 1
                        end
                    end
                end

                return res
            end
        end
    )
end

function filter(predicate)
    return helpers.chainMember(
        function(input)
            return function()
                return helpers.filter(input:get(), predicate)
            end
        end
    )
end

function f(difficulty)
    difficulty = helpers.getScalar(difficulty)

    return helpers.chainMember(
        function(input, gen)
            return function()
                local values = helpers.flatten(input:get())

                return {
                    value = math.max(
                        helpers.sum(
                            helpers.mapScalars(
                                values,
                                function(x)
                                    return x.value >= helpers.getScalar(difficulty) and 1 or (x.value == 1 and -1 or 0)
                                end
                            )
                        ),
                        helpers.any(
                            values,
                            function(x)
                                return x.value >= 6
                            end
                        ) and
                            0 or
                            -(#values)
                    ),
                    generator = gen
                }
            end
        end
    )
end

function explosion(threshold)
    threshold = helpers.getScalar(threshold)

    local function checkThreshold(value)
        if not value.value or not value.max then
            return false
        end

        return value.value >= value.max - threshold
    end

    return helpers.chainMember(
        function(input)
            return function()
                local values = input:get()
                local newValues = {}
                local dice = helpers.filterFlat(values, checkThreshold)

                for _, die in ipairs(dice) do
                    while true do
                        local value = die.generator:get()
                        table.insert(newValues, value)

                        if not checkThreshold(value) then
                            break
                        end
                    end
                end

                return {values, newValues}
            end
        end
    )
end

function rerollLow(num)
    num = helpers.getScalar(num)

    return helpers.chainMember(
        function(input)
            return function()
                local values = helpers.clone(input:get())
                local sorted = helpers.sorted(values, helpers.sorter)

                for i = 1, num do
                    local value = sorted[i].generator:get()

                    if type(value) == "table" then
                        sorted[i].value = value.value
                        sorted[i].generator = value.generator
                    else
                        sorted[i].value = value
                    end
                end

                return values
            end
        end
    )
end

function rerollHigh(num)
    num = helpers.getScalar(num)

    return helpers.chainMember(
        function(input)
            return function()
                local values = helpers.clone(input:get())
                local sorted = helpers.sorted(values, helpers.reverseSorter)

                for i = 1, num do
                    local value = sorted[i].generator:get()

                    if type(value) == "table" then
                        sorted[i].value = value.value
                        sorted[i].generator = value.generator
                    else
                        sorted[i].value = value
                    end
                end
            end
        end
    )
end

function add(amount)
    amount = helpers.getScalar(amount)

    local function mapper(value, gen)
        if value.value == nil then
            return value
        else
            return value.value + amount
        end
    end

    local function maxMapper(value, gen)
        if value.value == nil then
            return value
        else
            return value + amount
        end
    end

    return helpers.chainMember(
        function(input)
            return helpers.scalarMapper(input, mapper, maxMapper)
        end
    )
end

function subtract(amount)
    amount = helpers.getScalar(amount)

    local function mapper(value, gen)
        if value.value == nil then
            return value
        else
            return value.value - amount
        end
    end

    local function maxMapper(value, gen)
        if value.value == nil then
            return value
        else
            return value - amount
        end
    end

    return helpers.chainMember(
        function(input)
            return helpers.scalarMapper(input, mapper, maxMapper)
        end
    )
end

function selectDice(...)
    local args = helpers.mapTop({...}, helpers.getScalar)

    return helpers.chainMember(
        function(input)
            return function()
                local values = helpers.flatten(input:get())
                local res = {}

                for _, i in ipairs(args) do
                    table.insert(res, values[i])
                end

                return res
            end
        end
    )
end

function chain(first, ...)
    local rest = {...}

    for _, i in ipairs(rest) do
        first = i(first)
    end

    return first
end

local function valueMapper(value)
    if type(value) ~= "table" then
        return value
    else
        return value.value
    end
end
function values(input)
    if input.get then
        return values(input:get())
    else
        return helpers.mapScalars(input, valueMapper)
    end
end

function iif(condition, trueValue, falseValue)
    if condition then
        return trueValue
    else
        return falseValue
    end
end
