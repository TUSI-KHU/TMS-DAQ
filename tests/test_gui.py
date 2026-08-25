import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtWidgets import QApplication, QComboBox, QGroupBox, QLineEdit, QTabWidget

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from common.protocol import TelemetryBlock
from laptop.gui.main_window import MainWindow


def test_dashboard_builds_with_required_tabs_and_masked_password(
    tmp_path, monkeypatch
) -> None:
    app = QApplication.instance() or QApplication([])
    config = TmsConfig(
        daq=DaqConfig(sample_rate=1000, block_ms=10),
        thrust=ChannelConfig(0, 1.0, 0.0),
        pressure=ChannelConfig(1, 1.0, 0.0),
        logging=LoggingConfig(directory=tmp_path),
    )
    monkeypatch.setattr(MainWindow, "_start_runtime", lambda self: None)
    window = MainWindow(config, tmp_path / "config.yaml")

    tabs = window.findChild(QTabWidget)
    assert tabs is not None
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Dashboard",
        "Setup",
        "System Test",
        "Logs",
    ]
    assert window.ssh_password.echoMode() == QLineEdit.EchoMode.Password
    assert window.config.system.pi_host == "192.168.0.214"
    assert window.config.ssh.username == "tms"
    assert window.config.ssh.password == "tms"
    assert not window.pi_host.isEnabled()
    assert not window.ssh_password.isEnabled()
    assert not window.start_button.isEnabled()
    window.close()
    app.processEvents()


def test_live_quadrants_select_channels_and_refresh_values(tmp_path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    config = TmsConfig(
        daq=DaqConfig(sample_rate=1000, block_ms=10),
        thrust=ChannelConfig(0, 1.0, 0.0),
        pressure=ChannelConfig(1, 1.0, 0.0),
        logging=LoggingConfig(directory=tmp_path),
    )
    monkeypatch.setattr(MainWindow, "_start_runtime", lambda self: None)
    window = MainWindow(config, tmp_path / "config.yaml")

    assert window.findChild(QGroupBox, "live-data-panel-0") is not None
    assert window.findChild(QGroupBox, "live-data-panel-1") is not None
    first = window.findChild(QComboBox, "signal-selector-0")
    second = window.findChild(QComboBox, "signal-selector-1")
    assert first is not None and second is not None
    assert first.currentData() == "thrust_N"
    assert second.currentData() == "pressure_bar"

    window._receive_block(
        TelemetryBlock(
            sequence=1,
            first_sample_index=0,
            sample_rate=1000,
            channel_names=("thrust_N", "pressure_bar"),
            values=np.asarray(((10.0, 1.2), (12.5, 1.4), (11.0, 1.3)), dtype=np.float32),
        )
    )
    assert window._signal_panels[0].current.text() == "0.400"
    assert window._signal_panels[0].peak.text() == "12.50 N"
    assert window._signal_panels[1].current.text() == "0.500"
    assert "10.00 N – 12.50 N" in window._signal_panels[0].range_label.text()
    assert "1.200 bar – 1.400 bar" in window._signal_panels[1].range_label.text()
    _, normalized_thrust = window._signal_panels[0].curve.getData()
    np.testing.assert_allclose(normalized_thrust, (0.0, 1.0, 0.4))

    first.setCurrentIndex(first.findData("pressure_bar"))
    app.processEvents()
    assert window._signal_panels[0].current.text() == "0.500"
    assert window._signal_panels[0].peak.text() == "1.400 bar"
    assert "압력" in window._signal_panels[0].plot.plotItem.titleLabel.text
    window._receive_health(
        {
            "state": "READY",
            "health": {"daq": "FAILED", "logger": "READY", "storage": "OK"},
            "daq_probe": {"reason": "USB-4704 start returned EIO"},
        }
    )
    assert "USB-4704 start returned EIO" in window.pipeline_message.text()
    window.close()
    app.processEvents()
