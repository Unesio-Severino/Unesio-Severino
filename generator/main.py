"""Entry point for the Galaxy Profile README generator."""

import logging
import os
import sys

import requests
import yaml

from generator.config import ConfigError, validate_config
from generator.github_api import GitHubAPI
from generator.svg_builder import SVGBuilder

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.yml")
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config.yml not found. Copy config.example.yml to config.yml and edit it.")
        sys.exit(1)

    try:
        config = validate_config(config)
    except ConfigError as e:
        logger.error("Invalid config: %s", e)
        sys.exit(1)

    username = config["username"]

    logger.info("Generating profile SVGs for @%s...", username)

    # Fetch GitHub data
    api = GitHubAPI(username)

    logger.info("Fetching stats...")
    try:
        stats = api.fetch_stats()
    except (requests.exceptions.RequestException, ValueError, KeyError) as e:
        logger.warning("Could not fetch stats (%s). Using defaults.", e)
        stats = {"commits": 0, "stars": 0, "prs": 0, "issues": 0, "repos": 0}

    logger.info("Fetching languages...")
    try:
        languages = api.fetch_languages()
    except (requests.exceptions.RequestException, ValueError, KeyError) as e:
        logger.warning("Could not fetch languages (%s). Using defaults.", e)
        languages = {}

    logger.info("Stats: %s", stats)
    logger.info("Languages: %d found", len(languages))

    # Build SVGs
    builder = SVGBuilder(config, stats, languages)
    output_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "generated")
    os.makedirs(output_dir, exist_ok=True)

    svgs = {
        "galaxy-header.svg": builder.render_galaxy_header(),
        "stats-card.svg": builder.render_stats_card(),
        "tech-stack.svg": builder.render_tech_stack(),
        "projects-constellation.svg": builder.render_projects_constellation(),
    }

    for filename, content in svgs.items():
        path = os.path.join(output_dir, filename)
        with open(path, "w") as f:
            f.write(content)
        logger.info("Wrote %s", path)

    logger.info("Done! 4 SVGs generated.")


if __name__ == "__main__":
    main()
