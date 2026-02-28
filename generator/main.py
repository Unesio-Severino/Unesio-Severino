"""Entry point for the Galaxy Profile README generator."""

import logging
import os
import sys
from pathlib import Path

import requests
import yaml

from generator.config import ConfigError, validate_config
from generator.github_api import GitHubAPI
from generator.svg_builder import SVGBuilder

logger = logging.getLogger(__name__)


def _placeholder_projects_svg(theme: dict, width: int = 850, height: int = 220) -> str:
    """Simple placeholder SVG used when projects are not configured or rendering fails."""
    nebula = theme.get("nebula", "#0f1623")
    star_dust = theme.get("star_dust", "#1a2332")
    text_bright = theme.get("text_bright", "#f1f5f9")
    text_dim = theme.get("text_dim", "#94a3b8")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="12" ry="12"
        fill="{nebula}" stroke="{star_dust}" stroke-width="1"/>
  <text x="30" y="38" fill="{text_dim}" font-size="11" font-family="monospace" letter-spacing="3">
    FEATURED SYSTEMS
  </text>
  <text x="30" y="105" fill="{text_bright}" font-size="16" font-family="sans-serif" font-weight="700">
    No projects configured
  </text>
  <text x="30" y="130" fill="{text_dim}" font-size="12" font-family="sans-serif">
    Add a "projects:" list in config.yml to enable this card.
  </text>
  <text x="{width-30}" y="38" fill="{text_dim}" font-size="10" font-family="monospace" text-anchor="end" opacity="0.6">
    SYS 0/0 ONLINE
  </text>
</svg>'''


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    repo_root = Path(__file__).resolve().parent.parent
    config_path = repo_root / "config.yml"

    # Load config
    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config.yml not found at %s. Copy config.example.yml to config.yml and edit it.", config_path)
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

    output_dir = repo_root / "assets" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    svgs = {
        "galaxy-header.svg": builder.render_galaxy_header(),
        "stats-card.svg": builder.render_stats_card(),
        "tech-stack.svg": builder.render_tech_stack(),
    }

    # Projects constellation: robust handling when projects are missing/empty or template has bugs
    projects = config.get("projects") or []
    if not projects:
        logger.info('No "projects" configured in config.yml. Writing placeholder projects-constellation.svg')
        svgs["projects-constellation.svg"] = _placeholder_projects_svg(builder.theme)
    else:
        try:
            svgs["projects-constellation.svg"] = builder.render_projects_constellation()
        except Exception as e:
            logger.warning("Could not render projects constellation (%s). Writing placeholder instead.", e)
            svgs["projects-constellation.svg"] = _placeholder_projects_svg(builder.theme)

    # Write files
    for filename, content in svgs.items():
        path = output_dir / filename
        path.write_text(content, encoding="utf-8")
        logger.info("Wrote %s", path)

    logger.info("Done! %d SVGs generated.", len(svgs))


if __name__ == "__main__":
    main()