#!/bin/python
"""This Module calculates the number of Raw Materials, Factories
   and Belts necessary to manufacture a product"""

import argparse
import math

from pathlib import Path
from typing import Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from ruamel.yaml import YAML

yaml = YAML(typ="safe")  # pylint: disable=invalid-name


@dataclass
class Recipe:
    """The recipe for a product"""

    ingredients: Dict[str, int] = field(default_factory=dict)
    time: int = 0
    output: int = 1
    production: str = "AssemblingMachine"
    fluid: bool = False


def get_recipes(recipes_filename: Path) -> Dict[str, Recipe]:
    """Read recipes file and overload furnace recipes and meta-recipes"""
    recipes = {}
    with open(recipes_filename, "r") as recipes_file:
        recipes_raw = yaml.load(recipes_file)
    for recipe_name, recipe_dict in recipes_raw.items():
        recipes[recipe_name] = Recipe(**recipe_dict)

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


def create_totals(
    product: str,
    count: float,
    recipes: Dict[str, Recipe],
    products: Dict[str, float] = None,
) -> Dict[str, float]:
    """Recursively calculate the number of Products needed"""
    if products is None:
        products = defaultdict(int)

    products[product] += count
    if product in recipes.keys():
        for next_product, next_count in recipes[product].ingredients.items():
            products = create_totals(
                next_product,
                count * next_count / recipes[product].output,
                recipes,
                products,
            )

    return products


@dataclass
class ResultsSection:
    """A section of printed results"""

    title: str
    header: Optional[Tuple[str, ...]] = None
    products: Dict[str, Tuple[Optional[float], ...]] = field(default_factory=dict)


def generate_sections(
    products: Dict[str, int], recipes: Dict[str, Recipe]
) -> Dict[str, ResultsSection]:
    """Calculate the results"""
    sections: Dict[str, ResultsSection] = {
        "unknowns": ResultsSection("Unknowns"),
        "raw_materials": ResultsSection("Raw Materials"),
        "assembling_machines": ResultsSection("Assembling Machines", ("1", "2", "3")),
        "chemical_plants": ResultsSection("Chemical Plants"),
        "furnaces": ResultsSection("Furnaces", ("Stone", "Steel")),
        "pipes": ResultsSection("Pipes"),
        "belts": ResultsSection("Belts", ("Yellow", "Red", "Blue")),
        "rocket_silos": ResultsSection("Rocket Silos"),
    }

    for product, count in products.items():
        if product not in recipes.keys():
            sections["unknowns"].products[product] = (count,)
            continue

        if recipes[product].production == "Raw":
            sections["raw_materials"].products[product] = (count,)

        elif recipes[product].production == "AssemblingMachine":
            sections["assembling_machines"].products[product] = (
                recipes[product].time * count / recipes[product].output / 1.25,
                recipes[product].time * count / recipes[product].output / 0.75,
                recipes[product].time * count / recipes[product].output / 0.50,
            )
        elif recipes[product].production == "AssemblingMachine2":
            sections["assembling_machines"].products[product] = (
                None,
                recipes[product].time * count / recipes[product].output / 0.75,
                recipes[product].time * count / recipes[product].output / 0.50,
            )
        elif recipes[product].production == "AssemblingMachine3":
            sections["assembling_machines"].products[product] = (
                None,
                None,
                recipes[product].time * count / recipes[product].output / 0.50,
            )

        elif recipes[product].production == "ChemicalPlant":
            sections["chemical_plants"].products[product] = (
                recipes[product].time * count / recipes[product].output,
            )

        elif recipes[product].production == "Furnace":
            sections["furnaces"].products[product] = (
                recipes[product].time * count / recipes[product].output / 0.50,
                recipes[product].time * count / recipes[product].output,
            )

        elif recipes[product].production == "RocketSilo":
            sections["rocket_silos"].products[product] = (
                recipes[product].time * count / recipes[product].output,
            )

        else:
            raise RuntimeError(f"Unknown production {recipes[product].production}")

        if recipes[product].fluid:
            sections["pipes"].products[product] = (count / 12000,)
        else:
            sections["belts"].products[product] = (
                count * 3 / 45,
                count * 3 / 90,
                count * 3 / 135,
            )
    return sections


def print_section(section: ResultsSection) -> None:
    """Print one section of the results"""

    num_columns_set = set(len(counts) for product, counts in section.products.items())
    if len(num_columns_set) < 1:
        return
    if len(num_columns_set) > 1:
        raise ValueError("Inconsistent Column Counts")
    num_columns = num_columns_set.pop()

    totals = [0] * num_columns
    row_format = "{:<26}" + "{:<7}" * num_columns

    print(section.title)
    underline = "=" * len(section.title)
    if section.header is None:
        print(underline)
    else:
        print(row_format.format(underline, *section.header))

    for product, counts in sorted(
        section.products.items(), key=lambda x: x[1][-1], reverse=True
    ):
        for idx, count in enumerate(counts):
            if count is not None:
                totals[idx] += math.ceil(count)
        counts_str = ["" if count is None else str(round(count, 2)) for count in counts]
        print(row_format.format(product, *counts_str))
    print(row_format.format("", *totals))
    print()


def print_results(products: Dict[str, int], recipes: Dict[str, Recipe]) -> None:
    """Calculate and print the results"""
    sections = generate_sections(products, recipes)
    for section in sections.values():
        print_section(section)


def parse_args() -> argparse.Namespace:
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
        "--recipes", type=Path, default="recipes.yml", help="Location of recipe catalog"
    )
    return parser.parse_args()


def main():
    """Read user input, calculate results, and print"""
    args = parse_args()
    if args.top_product is None:
        args.top_product = str(input("Product: ")).replace(" ", "")
    if args.top_count is None:
        args.top_count = eval(input("Products Per Second: "))

    recipes = get_recipes(args.recipes)
    products = create_totals(args.top_product, args.top_count, recipes)
    print_results(products, recipes)


if __name__ == "__main__":
    main()
