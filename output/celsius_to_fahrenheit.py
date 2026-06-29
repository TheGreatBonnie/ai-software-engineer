#!/usr/bin/env python3
"""Convert Celsius to Fahrenheit."""


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert a temperature from Celsius to Fahrenheit.

    Formula: F = C × 9/5 + 32

    Args:
        celsius: Temperature in degrees Celsius.

    Returns:
        Temperature in degrees Fahrenheit.
    """
    return celsius * 9 / 5 + 32


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert a temperature from Celsius to Fahrenheit."
    )
    parser.add_argument(
        "celsius",
        type=float,
        help="Temperature in degrees Celsius.",
    )
    args = parser.parse_args()

    fahrenheit = celsius_to_fahrenheit(args.celsius)
    print(f"{args.celsius}°C = {fahrenheit:.2f}°F")


if __name__ == "__main__":
    main()
