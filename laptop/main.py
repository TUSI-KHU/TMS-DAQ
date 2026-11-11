from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from common.config import ConfigError, default_config, load_config, save_config
from laptop.gui.main_window import MainWindow
from laptop.operator_defaults import apply_field_connection


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TUSI TMS Dashboard")
    parser.add_argument("--config", default=None)
    parser.add_argument("--local-daq", action="store_true", help="run standalone on the DAQ PC without SSH")
    parser.add_argument("--agent-config", default="/etc/tusi-tms/config.yaml")
    parser.add_argument(
        "--direct-telemetry",
        action="store_true",
        help="connect directly without SSH for local development only",
    )
    parser.add_argument("--direct-host", default="127.0.0.1")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="validate bundled NumPy/calibration code and exit",
    )
    return parser


def _run_self_test() -> int:
    """Exercise the lazy NumPy imports used by the calibration path."""

    from laptop.calibration import PressureCalibrationReference, fit_pressure_calibration

    fit_pressure_calibration(
        (
            PressureCalibrationReference(0.0, 9000.0, 0.0, 100),
            PressureCalibrationReference(10.0, 10000.0, 0.0, 100),
        )
    )
    print("TUSI-TMS self-test: calibration path OK")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        return _run_self_test()
    config_path = Path(args.config) if args.config else (
        Path.home() / ".config/tusi-tms/dashboard-local.yaml" if args.local_daq else Path("config.yaml")
    )
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).parents[1]))
    example_path = bundle_root / "config.example.yaml"
    app = QApplication(sys.argv)
    try:
        if config_path.exists():
            config = load_config(config_path)
        elif example_path.exists():
            config = load_config(example_path)
        else:
            config = default_config()
        if args.local_daq:
            agent = load_config(args.agent_config)
            config = replace(
                config, system=replace(agent.system, pi_host="127.0.0.1"),
                daq=agent.daq, thrust=agent.thrust, pressure=agent.pressure,
                pressure_input=agent.pressure_input, low_pass=agent.low_pass,
                logging=replace(agent.logging, directory=(config.logging.directory
                    if config_path.exists() else Path.home() / "TUSI-TMS/logs")),
            )
            save_config(config, config_path)
        elif args.direct_telemetry:
            config = replace(
                config,
                system=replace(config.system, pi_host=args.direct_host),
            )
        else:
            config = apply_field_connection(config)
    except ConfigError as exc:
        QMessageBox.critical(None, "TUSI TMS 설정 오류", str(exc))
        return 1
    window = MainWindow(
        config,
        config_path,
        direct_telemetry=args.direct_telemetry or args.local_daq,
        local_daq=args.local_daq,
        fixed_connection=not (args.direct_telemetry or args.local_daq),
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
