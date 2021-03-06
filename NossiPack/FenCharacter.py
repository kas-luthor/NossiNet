import pickle
import re
import time
from collections import OrderedDict

__author__ = "maric"


class FenCharacter(object):
    def __init__(self, name="", meta=None):
        self.Tags = ""
        self.Name = name
        self.Character = OrderedDict()
        self.Meta = meta or OrderedDict()

        def sublvl():
            return OrderedDict([("Attribute", OrderedDict()),
                                ("Fähigkeiten", OrderedDict()),
                                ("Vorteile", OrderedDict())])

        self.Categories = OrderedDict([("Stärke", sublvl()),
                                       ("Können", sublvl()),
                                       ("Magie", OrderedDict([("Quelle", {}),
                                                              ("Konzepte", {}),
                                                              ("Aspekte", {}),
                                                              ("Zauber", {}),
                                                              ("Vorteile", {})])),
                                       ("Weisheit", sublvl()),
                                       ("Charisma", sublvl()),
                                       ("Schicksal", sublvl())])
        self.Wounds = []
        self.Modifiers = OrderedDict()
        self.Inventory = OrderedDict()
        self.Notes = ""
        self.Timestamp = time.strftime("%Y/%m/%d-%H:%M:%S")

    def unify(self):
        unified = OrderedDict()
        for kind in self.Categories.keys():
            for cat in self.Categories[kind].keys():
                for spec in self.Categories[kind][cat].keys():
                    unified[spec] = self.Categories[kind][cat][spec]
        return unified

    def process_trigger(self, trigger):
        pass  # for when triggers are being built in

    @staticmethod
    def parse_part(s, parse_table):
        result = OrderedDict()
        categories = [x for x in re.split(r"\n##(?!#)", "\n" + s,
                                          maxsplit=1000, flags=re.MULTILINE) if x.strip()]
        for category in categories:
            firstline = category.find("\n")
            categoryname = category[:firstline].strip()
            category = category[firstline + 1:].strip()
            result[categoryname] = OrderedDict()
            for section in [x for x in re.split(r"\n###(?!#)", "\n" + category, 1000, re.MULTILINE) if x.strip()]:
                firstline = section.find("\n")
                sectionname = section[:firstline].strip()
                section = section[firstline + 1:].strip()
                li = []
                result[categoryname][sectionname] = OrderedDict()
                result[categoryname][sectionname]["_lines"] = []
                tablestate = 0
                for line in section.split("\n"):
                    line = line.strip()
                    candidate = line.split("|")
                    candidate = (candidate if len(candidate) == 2
                                 else line[1 if line.startswith("|") else 0:
                                           -1 if line.startswith("|") else len(line)].split("|"))
                    if parse_table and len(candidate) == 2:
                        tablestate += 1
                        if tablestate > 2:  # 1: header, 2: alignment
                            while candidate[0] in result[categoryname][sectionname]:
                                candidate[0] = "_" + candidate[0]
                            result[categoryname][sectionname][candidate[0]] = candidate[1]
                    else:
                        tablestate = 0
                        result[categoryname][sectionname]["_lines"].append(line)
                result[categoryname][sectionname]["_lines"].extend(li)
                if len(result[categoryname][sectionname]["_lines"]) == 0:
                    del result[categoryname][sectionname]["_lines"]
                if not sectionname:
                    for k, v in result[categoryname][sectionname].items():
                        result[categoryname][k] = v
                    del result[categoryname][sectionname]
            if len(result[categoryname].keys()) == 1 and "_lines" in result[categoryname].keys():
                result[categoryname] = list(result[categoryname].values())[0]
        for cn in list(result.keys()):
            if not cn:
                if isinstance(result[cn], dict):
                    for k, v in result[cn].items():
                        result[k] = v
                    del result[cn]
                else:
                    print("Wikiparse unnamed lines:", result[cn], "in", result)
            else:
                result.move_to_end(cn, True)
        return result

    def load_from_md(self, title, tags, body):
        self.Name = title
        self.Tags = tags

        sheetparts = re.split(r"\n#(?!#)", "\n" + body, re.MULTILINE)
        if len("sheetparts") == 0:
            sheetparts = [body]
        for s in sheetparts:
            firstline = s.find("\n")
            partname = s[:firstline]
            s = s[firstline:]
            if partname.strip().startswith("Werte") or len(sheetparts) == 1:
                parsed_parts = self.parse_part(s, True)
                self.Categories.update(parsed_parts)
            else:
                if partname.strip() in ["", "Charakter"]:
                    self.Character = self.parse_part(s, True)
                else:
                    parsed_parts = self.parse_part(s, False)
                    self.Meta[partname] = parsed_parts
        for cat, catv in self.Categories.items():
            for sec, secv in list(catv.items()):
                for itemn, itemv in list(secv.items()):
                    if itemn == "_lines":
                        secv[""] = "\n".join(itemv)
                        del secv["_lines"]
        return self.Categories

    def validate_char(self, ):
        comment = self.Name + "NOT IMPLEMENTED"
        return comment

    def setfromform(self, form):  # accesses internal dicts
        form = dict(form)
        self.Notes = form.pop("Notes")[0]
        self.Name = form.pop("Name")[0]
        self.Meta = [("Species", form.pop("Species", [""])[0]),
                     ("XP", form.pop("XP", [""])[0]),
                     ("Home", form.pop("Home", [""])[0]),
                     ("Story", form.pop("Story", [""])[0]),
                     ("Size", form.pop("Size", [""])[0]),
                     ("Weight", form.pop("Weight", [""])[0]),
                     ("Concept", form.pop("Concept", [""])[0]),
                     ("Player", form.pop("Player", [""])[0])]

        for key, val in form.items():
            s = key.split("_")
            if len(s) != 3:
                continue
            k = key.split("_")[0]
            sub_key = key.split("_")[1]
            if form.get(key + "_val"):
                if self.Categories.get(k, None) is None:
                    self.Categories[k] = OrderedDict()
                if self.Categories[k].get(sub_key, None) is None:
                    self.Categories[k][sub_key] = OrderedDict()
                self.Categories[k][sub_key][val[0]] = int(form.get(key + "_val")[0])

    def getdictrepr(self):
        character = OrderedDict([('Categories', self.Categories),
                                 ('Wounds', self.Wounds),
                                 ('Modifiers', self.Modifiers),
                                 ('Inventory', self.Inventory),
                                 ('Notes', self.Notes),
                                 ('Type', "FEN")])
        return character

    def serialize(self):
        return pickle.dumps(self)

    @staticmethod
    def deserialize(serialized):
        tmp = pickle.loads(serialized)
        return tmp
