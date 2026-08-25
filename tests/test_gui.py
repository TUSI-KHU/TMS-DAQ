import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtWidgets import QApplication, QComboBox, QGroupBox, QLineEdit, QTabWidget

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from common.protocol import TelemetryBlock
from laptop.gui.calibration_dialog import LoadCellCalibrationDialog
from laptop.gui.main_window import MainWindow, PLOT_MAX_POINTS


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
    assert window.config.system.pi_host == "10.47.0.2"
    assert window.config.ssh.username == "tms"
    assert window.config.ssh.password == "tms"
    assert not window.pi_host.isEnabled()
    assert not window.ssh_password.isEnabled()
    assert not window.start_button.isEnabled()
    assert window.calibration_button.text() == "AI0 로드셀 보정"
    assert window.daq_reset_button.text() == "DAQ 초기화"
    assert not window.daq_reset_button.isEnabled()
    assert window.thrust_channel.value() == 0
    assert window.pressure_channel.value() == 1
    assert not window.thrust_channel.isEnabled()
    assert not window.pressure_channel.isEnabled()
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
    assert window._signal_panels[0].current.text() == "11.00 N"
    assert window._signal_panels[0].peak.text() == "12.50 N"
    assert window._signal_panels[1].current.text() == "1.300 bar"
    assert "10.00 N – 12.50 N" in window._signal_panels[0].range_label.text()
    assert "1.200 bar – 1.400 bar" in window._signal_panels[1].range_label.text()
    _, physical_thrust = window._signal_panels[0].curve.getData()
    np.testing.assert_allclose(physical_thrust, (10.0, 12.5, 11.0))
    y_min, y_max = window._signal_panels[0].plot.getViewBox().viewRange()[1]
    assert y_min < 10.0 < 12.5 < y_max

    first.setCurrentIndex(first.findData("pressure_bar"))
    app.processEvents()
    assert window._signal_panels[0].current.text() == "1.300 bar"
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


def test_live_plot_envelope_is_bounded_and_keeps_local_extrema() -> None:
    values = np.zeros(PLOT_MAX_POINTS * 3 + 17, dtype=np.float32)
    values[25] = 42.0
    values[values.size // 2] = -17.0
    values[-10] = 9.0

    indices = MainWindow._peak_display_indices(values)

    assert len(indices) <= PLOT_MAX_POINTS
    assert np.all(np.diff(indices) >= 0)
    assert 25 in indices
    assert values.size // 2 in indices
    assert values.size - 10 in indices


def test_load_cell_calibration_dialog_collects_two_points_and_fits() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = LoadCellCalibrationDialog(current_scale=0.01, current_offset=0.0)
    assert dialog.reference_table.rowCount() == 2

    dialog._request_capture(0)
    dialog.record_capture(
        {
            "_ui_row": 0,
            "channels": {"ai0": {"sample_count": 5000, "mean": 10239.0, "stddev": 2.0}},
        }
    )
    dialog._request_capture(1)
    dialog.record_capture(
        {
            "_ui_row": 1,
            "channels": {"ai0": {"sample_count": 5000, "mean": 10111.0, "stddev": 2.0}},
        }
    )
    dialog._calculate()
    assert dialog.fit is not None
    assert dialog.fit.scale_N_per_count < 0.0
    assert dialog.apply_button.isEnabled()

    dialog.point_count.setCurrentIndex(1)
    app.processEvents()
    assert dialog.reference_table.rowCount() == 3
    dialog.close()
