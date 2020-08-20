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


def get_recipes(recipes_filename, stone_furnace):
    """Read recipes file and overload furnace recipes and meta-recipes"""
    recipes = {}
    with open(recipes_filename, "r") as recipes_file:
        recipes_raw = yaml.load(recipes_file)
    for recipe_name, recipe_dict in recipes_raw.items():
        recipes[recipe_name] = Recipe(**recipe_dict)

    # Furnace Recipes
    furnace_time = 3.2 if stone_furnace else 1.6
    recipes["CopperPlate"] = Recipe({"CopperOre": 1}, furnace_time)
    recipes["IronPlate"] = Recipe({"IronOre": 1}, furnace_time)
    recipes["StoneBrick"] = Recipe({"Stone": 2}, furnace_time)
    recipes["SteelPlate"] = Recipe({"IronPlate": 5}, 5 * furnace_time)

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


def print_underline(string, underline):
    """Print with an underline"""
    print(string)
    print(underline * len(string))


def print_results(raws, products, recipes):
    """Print the results"""
    print()
    print_underline("Raw Materials", "=")
    row_format = "{:<26}{:<7}"
    for product, count in raws.items():
        print(row_format.format(product, round(count, 2)))

    print()
    print_underline("Factories", "=")
    row_format = "{:<26}{:<7}"
    total_factories = 0
    for product, count in products.items():
        factories = recipes[product].time * count / recipes[product].output
        total_factories += math.ceil(factories)
        print(row_format.format(product, round(factories, 2)))
    print(row_format.format("Total", total_factories))

    print()
    print_underline("Belts", "=")
    row_format = "{:<26}{:<7}{:<7}{:<7}"
    total_belts_y = 0
    total_belts_r = 0
    total_belts_b = 0
    print(row_format.format("", "Yellow", "Red", "Blue"))
    for product, count in chain(raws.items(), products.items()):
        if product not in FLUIDS:
            belts_y = count * 3 / 40
            belts_r = count * 3 / 80
            belts_b = count * 3 / 120
            total_belts_y += math.ceil(belts_y)
            total_belts_r += math.ceil(belts_r)
            total_belts_b += math.ceil(belts_b)
            print(
                row_format.format(
                    product, round(belts_y, 2), round(belts_r, 2), round(belts_b, 2)
                )
            )
    print(row_format.format("Total", total_belts_y, total_belts_r, total_belts_b))


def parse_args():
    """Parse arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "top_product", nargs="?", default=None, help="Product to Calculate"
    )
    parser.add_argument(
        "top_count", type=float, nargs="?", default=None, help="Number of Products a Second"
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
