#!/usr/bin/env python3
"""Weather CLI script that fetches current weather for a given city."""

import argparse
import json
import sys
import urllib.request
import urllib.error
import urllib.parse

API_URL = "https://wttr.in/{city}?format=j1"


def fetch_weather(city: str) -> dict:
    """Fetch weather data for a city from wttr.in."""
    url = API_URL.format(city=urllib.parse.quote(city))
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error: Could not fetch weather for '{city}' (HTTP {e.code})", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Network issue - {e.reason}", file=sys.stderr)
        sys.exit(1)


def format_weather(data: dict) -> str:
    """Format the raw JSON weather data into a human-readable string."""
    current = data["current_condition"][0]
    lines = []
    lines.append(f"City: {data['nearest_area'][0]['areaName'][0]['value']}, "
                 f"{data['nearest_area'][0]['country'][0]['value']}")
    lines.append(f"Condition: {current['weatherDesc'][0]['value']}")
    lines.append(f"Temperature: {current['temp_C']}°C (feels like {current['FeelsLikeC']}°C)")
    lines.append(f"Humidity: {current['humidity']}%")
    lines.append(f"Wind: {current['windspeedKmph']} km/h")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Get current weather for a city.")
    parser.add_argument("city", nargs="?", default="London", help="City name (default: London)")
    args = parser.parse_args()

    data = fetch_weather(args.city)
    print(format_weather(data))


if __name__ == "__main__":
    main()
