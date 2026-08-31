from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from common.config import ConfigError, default_config, load_config
from laptop.gui.main_window import MainWindow
from laptop.operator_defaults import apply_field_connection


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TUSI TMS Dashboard")
    parser.add_argument("--config", default="config.yaml")
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
    config_path = Path(args.config)
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
        if args.direct_telemetry:
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
        direct_telemetry=args.direct_telemetry,
        fixed_connection=not args.direct_telemetry,
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
