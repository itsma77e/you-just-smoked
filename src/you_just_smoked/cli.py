"""Command line entry point. Heavy modules are imported inside each command so that
`--help` and `status` stay instant and MediaPipe's native logging can be silenced first.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence

from you_just_smoked import __version__
from you_just_smoked.app.config import Config, ConfigError, load_config
from you_just_smoked.app.logs import configure_logging, quiet_native_logs
from you_just_smoked.app.paths import AppPaths

Command = Callable[[Config, AppPaths], None]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    paths = AppPaths.default()
    try:
        config = load_config(paths.config_file)
    except ConfigError as error:
        print(f"Invalid configuration: {error}", file=sys.stderr)
        return 2
    command: Command = args.command
    if command is not _paths:
        quiet_native_logs()
        configure_logging(paths.log_file, verbose=args.verbose)
    command(config, paths)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="you-just-smoked",
        description="A local webcam companion that helps you wait a little longer.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="log debug details")
    parser.set_defaults(command=_run)
    commands = parser.add_subparsers(title="commands")
    commands.add_parser("run", help="start in the system tray (default)").set_defaults(command=_run)
    commands.add_parser("status", help="print today's numbers").set_defaults(command=_status)
    commands.add_parser(
        "preview", help="show what the camera sees and which cues fire"
    ).set_defaults(command=_preview)
    commands.add_parser("paths", help="show where config and data live").set_defaults(
        command=_paths
    )
    return parser


def _run(config: Config, paths: AppPaths) -> None:
    from you_just_smoked.app.bootstrap import run_app  # noqa: PLC0415

    run_app(config, paths)


def _preview(config: Config, paths: AppPaths) -> None:
    from you_just_smoked.app.preview import run_preview  # noqa: PLC0415

    run_preview(config, paths)


def _status(config: Config, paths: AppPaths) -> None:
    from you_just_smoked.notify.messages import resolve_language, status_lines  # noqa: PLC0415
    from you_just_smoked.runtime.clock import SystemClock  # noqa: PLC0415
    from you_just_smoked.runtime.stats import load_stats  # noqa: PLC0415
    from you_just_smoked.storage.database import connect  # noqa: PLC0415
    from you_just_smoked.storage.episodes import EpisodeRepository  # noqa: PLC0415

    now = SystemClock().now()
    connection = connect(paths.database)
    try:
        stats = load_stats(EpisodeRepository(connection), now=now, session_start=now)
    finally:
        connection.close()
    for line in status_lines(stats, now, resolve_language(config.language)):
        print(line)


def _paths(config: Config, paths: AppPaths) -> None:
    for name, path in (
        ("config", paths.config_file),
        ("database", paths.database),
        ("models", paths.models),
        ("log", paths.log_file),
    ):
        print(f"{name:<9}{path}")
