#!/bin/python
"""This Module calculates the number of Raw Materials, Factories
   and Belts necessary to manufacture a product"""

import argparse
import math

from typing import Dict
from dataclasses import dataclass
from collections import defaultdict
from itertools import chain

from ruamel.yaml import YAML

yaml = YAML(typ="safe")  # pylint: disable=invalid-name

FLUIDS = [
    "CrudeOil",
    "HeavyOil",
    "LightOil",
    "Lubricant",
    "PetroleumGas",
    "SulfuricAcid",
    "Water",
    "Steam",
]


@dataclass
class Recipe:
    """The recipe for a product"""

    ingredients: Dict[str, int]
    time: int = 0
    output: int = 1
    production: str = "AssemblingMachine"


def get_recipes(recipes_filename, stone_furnace):
    """Read recipes file and overload furnace recipes and meta-recipes"""
    recipes = {}
    with open(recipes_filename, "r") as recipes_file:
        recipes_raw = yaml.load(recipes_file)
    for recipe_name, recipe_dict in recipes_raw.items():
        recipes[recipe_name] = Recipe(**recipe_dict)

    # Furnace Recipes
    furnace_time = 3.2 if stone_furnace else 1.6
    recipes["CopperPlate"] = Recipe(
        {"CopperOre": 1}, furnace_time, production="Furnace"
    )
    recipes["IronPlate"] = Recipe({"IronOre": 1}, furnace_time, production="Furnace")
    recipes["StoneBrick"] = Recipe({"Stone": 2}, furnace_time, production="Furnace")
    recipes["SteelPlate"] = Recipe(
        {"IronPlate": 5}, 5 * furnace_time, production="Furnace"
    )

    # Top-level Recipes
    recipes["Rocket"] = Recipe({"RocketPart": 100, "Satellite": 1})
    recipes["Research"] = Recipe(
        {
            "AutomationSciencePack": 1,
            "LogisticSciencePack": 1,
            "MilitarySciencePack": 1,
            "ChemicalSciencePack": 1,
            "ProductionSciencePack": 1,
            "UtilitySciencePack": 1,
        }
    )

    return recipes


def create_totals(product, count, recipes, products=None, raws=None):
    """Recursively calculate the Products and Raws"""
    if products is None:
        products = defaultdict(int)
    if raws is None:
        raws = defaultdict(int)

    if product in recipes.keys():
        products[product] += count
        for next_product, next_count in recipes[product].ingredients.items():
            products, raws = create_totals(
                next_product,
                count * next_count / recipes[product].output,
                recipes,
                products,
                raws,
            )
    else:
        raws[product] += count

    return products, raws


def print_section(title, header, content, totals):
    """Print one section of the results"""
    row_format = "{:<26}" + "{:<7}" * len(totals)
    print(title)
    underline = "=" * len(title)
    if header is None:
        print(underline)
    else:
        print(row_format.format(underline, *header))
    for line in content:
        print(row_format.format(*line))
    print(row_format.format("Total", *totals))
    print()


def print_results(raws, products, recipes):
    """Calculate and print the results"""
    print_sections = {
        "raw_materials": [],
        "assembling_machines": [],
        "chemical_plants": [],
        "furnaces": [],
        "belts": [],
    }

    total_raw = 0
    total_assemblers_1 = 0
    total_assemblers_2 = 0
    total_assemblers_3 = 0
    total_chemical_plants = 0
    total_belts_y = 0
    total_belts_r = 0
    total_belts_b = 0
    total_stone_furnaces = 0
    total_steel_furnaces = 0
    for product, count in chain(raws.items(), products.items()):
        if product not in recipes.keys():
            print_sections["raw_materials"].append((product, round(count, 2)))
            total_raw += math.ceil(count)
        elif recipes[product].production in [
            "AssemblingMachine",
            "AssemblingMachine2",
            "AssemblingMachine3",
        ]:
            assemblers_3 = (
                recipes[product].time * count / recipes[product].output / 1.25
            )
            total_assemblers_3 += math.ceil(assemblers_3)
            if recipes[product].production in [
                "AssemblingMachine",
                "AssemblingMachine2",
            ]:
                assemblers_2 = (
                    recipes[product].time * count / recipes[product].output / 0.75
                )
                total_assemblers_2 += math.ceil(assemblers_2)
                if recipes[product].production in ["AssemblingMachine"]:
                    assemblers_1 = (
                        recipes[product].time * count / recipes[product].output / 0.50
                    )
                    total_assemblers_1 += math.ceil(assemblers_1)
                else:
                    assemblers_1 = None
            else:
                assemblers_1 = None
                assemblers_2 = None
            print_sections["assembling_machines"].append(
                (
                    product,
                    "" if not assemblers_1 else str(round(assemblers_1, 2)),
                    "" if not assemblers_2 else str(round(assemblers_2, 2)),
                    "" if not assemblers_3 else str(round(assemblers_3, 2)),
                )
            )
        elif recipes[product].production in ["ChemicalPlant"]:
            chemical_plants = recipes[product].time * count / recipes[product].output
            total_chemical_plants += math.ceil(chemical_plants)
            print_sections["chemical_plants"].append(
                (product, str(round(chemical_plants, 2)))
            )
        elif recipes[product].production in ["Furnace"]:
            stone_furnaces = recipes[product].time * count / recipes[product].output * 2
            total_stone_furnaces += math.ceil(stone_furnaces)
            steel_furnaces = recipes[product].time * count / recipes[product].output
            total_steel_furnaces += math.ceil(steel_furnaces)
            print_sections["furnaces"].append(
                (product, str(round(stone_furnaces, 2)), str(round(steel_furnaces, 2)))
            )
        else:
            raise RuntimeError(f"Unknown production {recipes[product].production}")

        if product not in FLUIDS:
            belts_y = count * 3 / 45
            belts_r = count * 3 / 90
            belts_b = count * 3 / 135
            total_belts_y += math.ceil(belts_y)
            total_belts_r += math.ceil(belts_r)
            total_belts_b += math.ceil(belts_b)
            print_sections["belts"].append(
                (product, round(belts_y, 2), round(belts_r, 2), round(belts_b, 2))
            )

    for lst in print_sections.values():
        lst.sort(key=lambda x: x[-1], reverse=True)
    print_section("Raw Materials", None, print_sections["raw_materials"], (total_raw,))
    print_section(
        "Assembling Machines",
        ("1", "2", "3"),
        print_sections["assembling_machines"],
        (total_assemblers_1, total_assemblers_2, total_assemblers_3,),
    )
    print_section(
        "Chemical Plants",
        None,
        print_sections["chemical_plants"],
        (total_chemical_plants,),
    )
    print_section(
        "Furnaces",
        ("Stone", "Steel"),
        print_sections["furnaces"],
        (total_stone_furnaces, total_steel_furnaces,),
    )
    print_section(
        "Belts",
        ("Yellow", "Red", "Blue"),
        print_sections["belts"],
        (total_belts_y, total_belts_r, total_belts_b,),
    )


def parse_args():
    """Parse arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "top_product", nargs="?", default=None, help="Product to Calculate"
    )
    parser.add_argument(
        "top_count",
        type=float,
        nargs="?",
        default=None,
        help="Number of Products a Second",
    )
    parser.add_argument(
        "--recipes", default="recipes.yml", help="Location of recipe catalog"
    )
    parser.add_argument(
        "--stone_furnace", action="store_true", help="Using a Stone Furnace"
    )
    return parser.parse_args()


def main():
    """Read user input, calculate results, and print"""
    args = parse_args()
    if args.top_product is None:
        args.top_product = str(input("Product: ")).replace(" ", "")
    if args.top_count is None:
        args.top_count = eval(input("Products Per Second: "))

    recipes = get_recipes(args.recipes, args.stone_furnace)
    products, raws = create_totals(args.top_product, args.top_count, recipes)
    print_results(raws, products, recipes)


if __name__ == "__main__":
    main()
