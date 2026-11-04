"""Verify real buffered input via the running agent; never drive any outputs."""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import time

from common.config import load_config
from common.protocol import MessageType, WireMessage, new_request_id, read_message, write_message


async def verify(port: int, *, startup_timeout: float = 10.0) -> None:
    deadline = time.monotonic() + startup_timeout
    while True:
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            break
        except OSError:
            if time.monotonic() >= deadline:
                raise RuntimeError("agent telemetry did not become ready") from None
            await asyncio.sleep(0.2)
    try:
        async def request(kind: MessageType, body: dict | None = None) -> dict:
            request_id = new_request_id()
            await write_message(writer, WireMessage(kind, body or {}, request_id=request_id))
            while True:
                reply = await read_message(reader)
                if reply.request_id != request_id:
                    continue
                if reply.message_type != MessageType.ACK:
                    raise RuntimeError(str(reply.body.get("message", reply.body)))
                return reply.body

        # Two consecutive open/read/stop/close cycles catch the specific case
        # where a node exists but cannot acquire again after its first close.
        for _ in range(2):
            capture = await asyncio.wait_for(
                request(MessageType.CALIBRATION_SAMPLE, {"duration_ms": 100}), 8.0
            )
            channels = capture.get("channels", {})
            if any(channels.get(name, {}).get("sample_count", 0) <= 0 for name in ("ai0", "ai1")):
                raise RuntimeError("buffered AI0/AI1 input verification returned no samples")
        status = (await asyncio.wait_for(request(MessageType.PING), 3.0))["status"]
        if status["state"] not in ("READY", "COMPLETE") or status["health"]["daq"] != "READY":
            raise RuntimeError("DAQ did not return to READY after input verification")
        print("BUFFERED_INPUT_VERIFIED=AI0,AI1 (two acquisition/stop cycles)", flush=True)
    finally:
        writer.close()
        with contextlib.suppress(ConnectionError):
            await writer.wait_closed()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="/etc/tusi-tms/config.yaml")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        asyncio.run(asyncio.wait_for(verify(config.system.telemetry_port), 28.0))
    except Exception as exc:
        print(f"BUFFERED_INPUT_VERIFICATION_FAILED: {exc}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
