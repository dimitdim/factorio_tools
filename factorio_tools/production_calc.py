#!/bin/python
"""This Module calculates the number of Raw Materials, Factories
   and Belts necessary to manufacture a product"""

import argparse
import math
import csv

from pathlib import Path
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict

import numpy
from ruamel.yaml import YAML

yaml = YAML(typ="safe")  # pylint: disable=invalid-name


OIL_PROCESSING_RECIPES = [
    "BasicOilProcessing",
    "AdvancedOilProcessing",
    "HeavyOilCracking",
    "LightOilCracking",
    # "CoalLiquefaction",
    "HeavyOil2SolidFuel",
    "LightOil2SolidFuel",
    "PetroleumGas2SolidFuel",
]


@dataclass
class Recipe:
    """The recipe for a product"""

    ingredients: Dict[str, int] = field(default_factory=dict)
    time: int = 0
    output: int = 1
    production: str = "AssemblingMachine"
    fluid: bool = False
    breakdown: Optional[Dict[str, int]] = None


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


def create_recipe_matrices(
    available_recipes: Dict[str, Recipe], output_products: List[str]
) -> List[Tuple[List[str], numpy.ndarray]]:
    """List all invertible recipe vs product matrices"""

    recipe_matrices = []
    for mask in range(2 ** len(available_recipes)):
        partial_recipe_list = {
            recipe_name: recipe
            for idx, (recipe_name, recipe) in enumerate(available_recipes.items())
            if (mask // (2 ** idx)) % 2
        }
        if len(partial_recipe_list) != len(output_products):
            continue  # Ignore non-square matrices

        inv_recipe_matrix = []
        for output_product in output_products:
            inv_recipe_row = []
            for recipe in partial_recipe_list.values():
                if recipe.breakdown is None:
                    raise ValueError("Not a valid Oil Processing recipe")
                element = 0
                if output_product in recipe.ingredients:
                    element -= recipe.ingredients[output_product]
                if output_product in recipe.breakdown:
                    element += recipe.breakdown[output_product]
                inv_recipe_row.append(element)
            inv_recipe_matrix.append(inv_recipe_row)

        try:
            recipe_matrices.append(
                (list(partial_recipe_list.keys()), numpy.linalg.inv(inv_recipe_matrix))
            )
        except numpy.linalg.LinAlgError:
            pass  # Ignore singular matrices

    return recipe_matrices


def rank_recipe_combo(recipe_counts: Dict[str, float]) -> float:
    """Rank recipe combo (0 is best)"""
    rank = 0.0
    if "BasicOilProcessing" in recipe_counts:
        rank += recipe_counts["BasicOilProcessing"]
    if "AdvancedOilProcessing" in recipe_counts:
        rank += recipe_counts["AdvancedOilProcessing"]
    return rank


def process_oil(
    products: Dict[str, float], recipes: Dict[str, Recipe]
) -> Dict[str, float]:
    """Calculate best oil processing recipe combination"""

    output_products = []
    output_counts = []
    for recipe_name, recipe in recipes.items():
        if recipe.production != "OilProcessing":
            continue
        output_products.append(recipe_name)
        if recipe_name in products:
            output_counts.append(products[recipe_name])
        else:
            output_counts.append(0)

    available_recipes = {
        recipe_name: recipe
        for recipe_name, recipe in recipes.items()
        if recipe_name in OIL_PROCESSING_RECIPES
    }
    recipe_matrices = create_recipe_matrices(available_recipes, output_products)

    best_recipe_combo = None
    best_rank = None
    for recipe_list, recipe_matrix in recipe_matrices:
        recipe_counts = dict(zip(recipe_list, recipe_matrix.dot(output_counts)))
        if min(recipe_counts.values()) >= 0:
            rank = rank_recipe_combo(recipe_counts)
            if best_rank is None or rank < best_rank:
                best_recipe_combo = recipe_counts
                best_rank = rank
    if best_recipe_combo is None:
        raise RuntimeError("No valid recipe combination found!")

    for product, count in best_recipe_combo.items():
        if count != 0:
            products = create_totals(product, count, recipes, products)

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
        "oil_refineries": ResultsSection("Oil Refineries"),
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

        elif recipes[product].production == "OilRefinery":
            sections["oil_refineries"].products[product] = (
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

        elif recipes[product].production == "OilProcessing":
            pass  # Expressed as recipes instead

        else:
            raise RuntimeError(f"Unknown production {recipes[product].production}")

        if recipes[product].breakdown is not None:
            pass  # Expressed as individual products instead
        elif recipes[product].fluid:
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


def write_section(section: ResultsSection, base_csvfilename: Path) -> None:
    """Write one section of the results to a csv"""
    csvfilename = (
        base_csvfilename.stem
        + "_"
        + section.title.lower().replace(" ", "_")
        + base_csvfilename.suffix
    )
    with open(csvfilename, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        if section.header is None:
            csvwriter.writerow([section.title])
        else:
            csvwriter.writerow([section.title] + list(section.header))
        for product, counts in sorted(
            section.products.items(), key=lambda x: x[1][-1], reverse=True
        ):
            counts_str = ["" if count is None else str(count) for count in counts]
            csvwriter.writerow([product] + counts_str)


def print_results(
    products: Dict[str, int],
    recipes: Dict[str, Recipe],
    base_csvfilename: Optional[Path] = None,
) -> None:
    """Calculate and print the results"""
    sections = generate_sections(products, recipes)
    for section in sections.values():
        print_section(section)
        if base_csvfilename is not None:
            write_section(section, base_csvfilename)


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
    parser.add_argument("--csv", type=Path, default=None, help="Write results to csv")
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
    products = process_oil(products, recipes)
    print_results(products, recipes, args.csv)


if __name__ == "__main__":
    main()
