import time
import random


def roll(lvl):
    amt = lvl - 2 if lvl > 2 else lvl - 4
    x = [random.randint(1, 10) for i in range(abs(amt))]
    if amt > 0:
        for i in range(1, 12):
            if x.count(i) > 1:
                x.append(i + (x.count(i) - 1))
        return max(x)
    elif amt < 0:
        for i in reversed(range(11)):
            if x.count(i) > 1:
                x.append(i - (x.count(i) - 1))
        return min(x)
    else:
        return max(x)


class Gem:
    def __init__(self, current, maximum, quality, artifactattribute=2, characteristics=None, counters=None):
        self.Energy = current
        self.Maximum = maximum
        self.Quality = quality
        self.Characteristics = characteristics if characteristics is not None else {}
        self.Counters = counters if counters is not None else {}
        self.Artifactattribute = artifactattribute

    @staticmethod
    def possible_characteristics():
        # only the ones currently implemented, the possibilities are large
        return ['adamantine',
                # quality loss reduced
                'dull',
                # max loss causes quality loss
                'slick',
                # "greasy", min usage per use
                'metallic',
                # charge and discharge faster
                'pearly',
                # shifted towards passive uses
                'cloudy',
                # max usage per day
                'brittle',
                # diminishes max per empty
                'glowing',
                # passive energy usage per day
                'dragonglass',
                # diminishes quality per use
                'bristling',
                # looses/gains energy after spell use
                'peaceful',
                # looses max if harm is inflicted
                # https://en.wikipedia.org/wiki/Lustre_(mineralogy)
                ]

    def use(self, amount, context):
        self.process_characteristics(amount, context, "usepre")
        if self.Energy >= amount:
            self.Energy -= amount
            self.process_characteristics(amount, context, "usespend")
            return True
        self.process_characteristics(amount, context, "usefail")
        return False

    def recharge(self, amount, context):
        if self.process_characteristics(amount, context, "rechargepre"):
            self.Energy = min(self.Maximum, self.Energy + amount)
            self.process_characteristics(amount, context, "rechargepost")

    def tick(self, days):
        for i in range(days):
            for c in self.Characteristics.keys():
                if c == 'cloudy' and self.Counters.get(c, 0) < self.Characteristics[c]:
                    self.Counters[c] = self.Counters.get(c, 0) + 1
                if c == 'pearly' and self.Counters.get(c, 0) > self.Maximum:
                    self.Counters[c] -= 1

    def diminish(self, amount, context):
        if self.process_characteristics(amount, context, "diminishpre"):
            self.Maximum = max(self.Maximum - amount, 0)
            self.process_characteristics(amount, context, "diminishpost")

    def restore(self, amount, context):  # context here being the result of how much quality will be lowered by
        if self.process_characteristics(amount, context, "restorepre"):
            self.Maximum += amount
            self.Quality = max(0, self.Quality - int(context))
            self.Maximum = min(self.Maximum, self.Quality)
            self.process_characteristics(amount, context, "restorepost")

    def process_characteristics(self, amount, context, phase):
        for c in self.Characteristics.keys():
            if c == 'cloudy':
                # max usage replenishing 1 per day
                if phase == "usepre":
                    if self.Counters.get(c, 0) <= amount:
                        return False
                if phase == "usespend":
                    self.Counters[c] -= amount
            if c == 'adamantine':
                # quality loss reduced
                if phase == "restorepre":
                    self.Quality += min(amount, self.Characteristics[c])  # cancels up to adamantine-level qualityloss
            if c == 'dull':
                # max loss causes quality loss
                pass
            if c == 'slick':
                # "greasy", min usage per use
                if phase == "usespend":
                    self.Energy = max(0, self.Energy - max(0, self.Characteristics[c] - amount))
            if c == 'metallic':
                # charge and discharge faster
                if phase == "usespend":
                    self.Energy = max(0, self.Energy - self.Characteristics[c])
                if phase == "rechargepost":
                    self.Energy = round(min(self.Maximum, self.Energy + amount * self.Characteristics[c] / 2))
            if c == 'pearly':
                # shifted towards passive uses
                if phase == "usepre":
                    if context == "sustain" and amount > 0 and self.Counters.get(c, 0) > 0:
                        self.Energy += 1
                        self.Counters[c] -= 1
                elif phase == "usespend":
                    if context != "sustain" and self.Energy > 0:
                        self.Energy -= 1
                        self.Counters[c] = self.Counters.get(c, 0) + self.Characteristics[c]
            if c == 'brittle':
                # diminishes max per empty
                if phase == "usepre" and amount > 0 and self.Maximum >= amount > self.Energy > 0:
                    self.diminish(amount - self.Energy, "brittle")
                    self.Energy = amount
                if phase == "usespend" and amount > 0 and self.Energy == 0:
                    self.diminish(self.Characteristics[c], "brittle")
            if c == 'glowing':
                # passive energy usage per day
                pass
            if c == 'dragonglass':
                # diminishes quality per use
                # technically cancelled out by adamantine but that would be lame
                if phase == "usespend" and amount > 0:
                    self.Quality -= self.Characteristics[c]
            if c == 'bristling':
                # looses/gains energy after spell use
                if phase == "usespend" and amount > 0 and context != "sustain":
                    newcost = roll(self.Artifactattribute) - self.Characteristics[c]
                    self.Energy = max(0, self.Energy + min(amount, newcost))
            if c == 'peaceful':
                # looses max if harm is inflicted
                if phase == "usespend":
                    if context == "damage":
                        self.Maximum -= self.Characteristics[c]
        return True


# # # # # # # # # EXAMPLE/CONCEPTS/TEST # # # # # # # # #

class Character:
    def __init__(self):
        self.Gem = None
        self.Spells = {"fir3b4llerz": {"context": "damage", "cost": 2, "sustain": 0, "len": 0},
                       "gl0vvs7ickz": {"context": "pretty", "cost": 5, "sustain": 1, "len": 12}}

    @staticmethod
    def gemlist():
        return [Gem(100, 100, 100, -1),
                # Gem(100, 100, 100, -1, {"brittle": 1}),
                Gem(100, 100, 100, -1, {"bristling": 3}),
                # Gem(100, 100, 100, -1, {"pearly": 2})
                ]

    def test_gem(self):
        artifact_attribute = 5

        print("Artifactskill:", artifact_attribute)
        self.Gem.Artifactattribute = artifact_attribute
        totaldamage = 0
        totalpretty = 0
        t = time.time()
        for i in range(10000):
            if i % 100 == 0:
                if time.time() - t > 5:
                    t = time.time()
                    print(i / 100, "%")
            for s in self.Spells:
                damage = 0
                pretty = 0
                spell = self.Spells[s]
                self.Gem.Energy = self.Gem.Maximum
                while self.Gem.use(spell["cost"], spell["context"]):
                    for sustain in range(spell["len"]):
                        if self.Gem.use(spell["sustain"], "sustain"):
                            if spell["context"] == "pretty":
                                pretty += 1
                        else:
                            break
                    if spell["context"] == "damage":
                        damage += 1
                totaldamage += damage
                totalpretty += pretty
                # print(s, "D:", damage, "P:", pretty, "|", self.Gem.Energy, "/", self.Gem.Maximum)
        print(totaldamage / 10000, totalpretty / 10000, "\n\n\n")


if __name__ == "__main__":
    c = Character()
    for g in c.gemlist():
        print(g.Maximum, g.Characteristics)
        c.Gem = g
        c.test_gem()
