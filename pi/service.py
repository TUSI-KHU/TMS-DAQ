from __future__ import annotations

import argparse
import asyncio
import signal
from pathlib import Path

from common.config import ConfigError, load_config
from pi.daq import DaqError, SimulatedDaqSource, Usb4704DaqSource
from pi.telemetry import TelemetryServer
from pi.tms_agent import AgentState, SessionError, TmsAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TUSI TMS Raspberry Pi service")
    parser.add_argument("--config", default="/etc/tusi-tms/config.yaml")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int)
    parser.add_argument("--log-dir", type=Path)
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="use generated DAQ data for development without USB-4704",
    )
    return parser


async def run_service(args: argparse.Namespace) -> None:
    config_path = Path(args.config)
    if not config_path.exists() and args.config == "/etc/tusi-tms/config.yaml":
        config_path = Path("config.example.yaml")
    config = load_config(config_path)

    if args.simulate:
        daq = SimulatedDaqSource(
            config.daq, (config.thrust.channel, config.pressure.channel)
        )
        output_directory = args.log_dir or config.logging.directory
    else:
        daq = Usb4704DaqSource(
            config.daq,
            (config.thrust.channel, config.pressure.channel),
            buffer_seconds=config.logging.ring_buffer_sec,
        )
        output_directory = args.log_dir or config.logging.pi_directory

    agent = TmsAgent(config, daq, output_directory=output_directory)
    server = TelemetryServer(
        agent,
        config,
        host=args.bind,
        port=args.port if args.port is not None else config.system.telemetry_port,
    )
    await server.start()
    print(f"tms-agent READY on {args.bind}:{server.port}")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except (NotImplementedError, RuntimeError):
            pass

    try:
        await stop_event.wait()
    finally:
        await server.close()
        if agent.state in (AgentState.RECORDING, AgentState.TRIGGERED):
            await asyncio.to_thread(agent.stop_session)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        asyncio.run(run_service(args))
    except (ConfigError, DaqError, SessionError, OSError, ValueError) as exc:
        parser.exit(1, f"tms-agent: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
