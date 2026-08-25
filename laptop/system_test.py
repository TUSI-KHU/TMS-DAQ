from __future__ import annotations

import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np

from laptop.nano import NanoSerialManager
from laptop.ssh_client import SshTunnelManager
from laptop.telemetry import TelemetryClient


class TestStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(frozen=True)
class SystemTestResult:
    name: str
    status: TestStatus
    details: str


class SystemTestRunner:
    def __init__(
        self,
        nano: NanoSerialManager,
        ssh: SshTunnelManager,
        telemetry: TelemetryClient,
        local_log_directory: Path,
    ) -> None:
        self.nano = nano
        self.ssh = ssh
        self.telemetry = telemetry
        self.local_log_directory = local_log_directory

    async def run(self) -> list[SystemTestResult]:
        results: list[SystemTestResult] = []
        nano_status = self.nano.status()
        results.append(
            SystemTestResult(
                "Nano",
                TestStatus.PASS if nano_status.connected else TestStatus.FAIL,
                nano_status.state,
            )
        )
        network_connected = self.ssh.connected or self.telemetry.connected
        results.append(
            SystemTestResult(
                "LAN",
                TestStatus.PASS if network_connected else TestStatus.FAIL,
                "Pi network path connected" if network_connected else "not connected",
            )
        )
        results.append(
            SystemTestResult(
                "SSH",
                (
                    TestStatus.PASS
                    if self.ssh.connected
                    else TestStatus.SKIP
                    if self.telemetry.connected
                    else TestStatus.FAIL
                ),
                "password authentication and tunnel connected"
                if self.ssh.connected
                else "direct development connection"
                if self.telemetry.connected
                else "not connected",
            )
        )
        try:
            response = await self.telemetry.ping(timeout=3.0)
            status = response.get("status", {})
            results.append(SystemTestResult("Pi Agent", TestStatus.PASS, "responding"))
            source = str(status.get("daq_source", "unknown"))
            probe = status.get("daq_probe", {})
            probe_available = bool(probe.get("available"))
            if source == "simulated":
                results.append(
                    SystemTestResult("USB4704", TestStatus.SKIP, "simulation mode")
                )
            else:
                probe_details = str(
                    probe.get("description") or probe.get("reason") or "not detected"
                )
                results.append(
                    SystemTestResult(
                        "USB4704",
                        TestStatus.PASS if probe_available else TestStatus.FAIL,
                        probe_details,
                    )
                )
            daq = str(status.get("health", {}).get("daq", "UNKNOWN"))
            logger = str(status.get("health", {}).get("logger", "UNKNOWN"))
            results.append(
                SystemTestResult(
                    "DAQ",
                    TestStatus.PASS
                    if daq in ("READY", "AVAILABLE", "RUNNING")
                    else TestStatus.FAIL,
                    daq,
                )
            )
            results.append(
                SystemTestResult(
                    "Logger",
                    TestStatus.PASS
                    if logger in ("READY", "RECORDING", "COMPLETE")
                    else TestStatus.FAIL,
                    logger,
                )
            )
            storage = str(status.get("health", {}).get("storage", "UNKNOWN"))
            free_bytes = status.get("storage_free_bytes")
            storage_details = storage
            if isinstance(free_bytes, int):
                storage_details += f", {free_bytes / 1024**3:.1f} GiB free"
            results.append(
                SystemTestResult(
                    "Pi Storage",
                    TestStatus.PASS if storage == "OK" else TestStatus.FAIL,
                    storage_details,
                )
            )
            results.extend(await self._test_stream(str(status.get("state", ""))))
        except Exception as exc:  # noqa: BLE001 - each diagnostic must become a result
            results.extend(
                (
                    SystemTestResult("Pi Agent", TestStatus.FAIL, str(exc)),
                    SystemTestResult(
                        "USB4704", TestStatus.SKIP, "Pi Agent unavailable"
                    ),
                    SystemTestResult("DAQ", TestStatus.SKIP, "Pi Agent unavailable"),
                    SystemTestResult("Logger", TestStatus.SKIP, "Pi Agent unavailable"),
                    SystemTestResult(
                        "Pi Storage", TestStatus.SKIP, "Pi Agent unavailable"
                    ),
                    SystemTestResult(
                        "DAQ Stream", TestStatus.SKIP, "Pi Agent unavailable"
                    ),
                    SystemTestResult(
                        "Thrust Channel", TestStatus.SKIP, "Pi Agent unavailable"
                    ),
                    SystemTestResult(
                        "Pressure Channel", TestStatus.SKIP, "Pi Agent unavailable"
                    ),
                )
            )
        results.append(self._test_local_storage())
        return results

    async def _test_stream(self, state: str) -> list[SystemTestResult]:
        started_check_session = False
        previous = self.telemetry.latest_block
        previous_sequence = previous.sequence if previous is not None else None
        results: list[SystemTestResult] = []
        try:
            if state in ("READY", "COMPLETE"):
                await self.telemetry.start_session("SYSTEM_CHECK", timeout=10.0)
                started_check_session = True
            elif state not in ("RECORDING", "TRIGGERED"):
                raise RuntimeError(f"agent state {state} cannot stream")

            block = await self.telemetry.wait_for_fresh_block(
                after_sequence=previous_sequence, timeout=5.0
            )
            if block.channel_names != ("thrust_N", "pressure_bar"):
                raise RuntimeError(f"unexpected channels: {block.channel_names}")
            stream_result = SystemTestResult(
                "DAQ Stream",
                TestStatus.PASS,
                f"{block.sample_rate} S/s, {block.sample_count} samples/block",
            )
            thrust_ok = bool(np.isfinite(block.values[:, 0]).all())
            pressure_ok = bool(np.isfinite(block.values[:, 1]).all())
            results = [
                stream_result,
                SystemTestResult(
                    "Thrust Channel",
                    TestStatus.PASS if thrust_ok else TestStatus.FAIL,
                    "finite samples" if thrust_ok else "invalid sample detected",
                ),
                SystemTestResult(
                    "Pressure Channel",
                    TestStatus.PASS if pressure_ok else TestStatus.FAIL,
                    "finite samples" if pressure_ok else "invalid sample detected",
                ),
            ]
        except Exception as exc:  # noqa: BLE001 - each diagnostic must become a result
            results = [
                SystemTestResult("DAQ Stream", TestStatus.FAIL, str(exc)),
                SystemTestResult(
                    "Thrust Channel", TestStatus.SKIP, "stream unavailable"
                ),
                SystemTestResult(
                    "Pressure Channel", TestStatus.SKIP, "stream unavailable"
                ),
            ]
        finally:
            if started_check_session:
                try:
                    await self.telemetry.stop_session(timeout=30.0)
                except Exception as exc:  # noqa: BLE001 - cleanup failure is reported
                    results.append(
                        SystemTestResult(
                            "System Check Cleanup", TestStatus.FAIL, str(exc)
                        )
                    )
        return results

    def _test_local_storage(self) -> SystemTestResult:
        try:
            self.local_log_directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=self.local_log_directory, prefix=".tms-write-test-", delete=True
            ) as test_file:
                test_file.write(b"ok")
                test_file.flush()
            return SystemTestResult("Local Storage", TestStatus.PASS, "writable")
        except OSError as exc:
            return SystemTestResult("Local Storage", TestStatus.FAIL, str(exc))
