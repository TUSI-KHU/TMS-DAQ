import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QGroupBox, QLineEdit, QMessageBox, QTabWidget

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from common.protocol import TelemetryBlock
from laptop.gui.calibration_dialog import LoadCellCalibrationDialog, PressureCalibrationDialog
from laptop.gui.main_window import MainWindow, PLOT_HISTORY_SECONDS, PLOT_MAX_POINTS


@pytest.fixture
def idle_window(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(MainWindow, "_start_runtime", lambda self: None)
    window = MainWindow(TmsConfig(
        daq=DaqConfig(sample_rate=1000, block_ms=10),
        thrust=ChannelConfig(0, 1.0, 0.0), pressure=ChannelConfig(1, 1.0, 0.0),
        logging=LoggingConfig(directory=tmp_path),
    ), tmp_path / "config.yaml")

    class Runtime:
        def start_session(self, name):
            pass

        def stop_session(self):
            pass

        def reset_daq(self):
            pass

        def stop(self):
            pass

    window._runtime = Runtime()
    window._connection_changed("Pi", "CONNECTED")
    window._receive_health({"state": "READY", "health": {}})
    yield window
    window.close()
    app.processEvents()


def test_session_transitions_cannot_be_unlocked_by_stale_health(idle_window):
    window = idle_window
    assert window.start_button.isEnabled()
    window._start_session()
    window._receive_health({"state": "READY", "health": {}})
    window._connection_changed("Pi", "CONNECTED")
    assert window.state_label.text() == "STATUS: STARTING"
    assert not window.start_button.isEnabled()
    assert not window.daq_reset_button.isEnabled()
    window._session_started({"session_id": "new"})
    assert window.stop_button.isEnabled()
    window._stop_session()
    window._receive_health({"state": "RECORDING", "health": {}})
    assert window.state_label.text() == "STATUS: STOPPING"
    assert not window.stop_button.isEnabled()
    assert not window.start_button.isEnabled()
    assert not window.daq_reset_button.isEnabled()
    window._session_stopped({})
    assert window.start_button.isEnabled()
    assert window.daq_reset_button.isEnabled()


def test_nano_and_trigger_ui_do_not_claim_unconfirmed_ignition(idle_window):
    window = idle_window
    window._session_started({"session_id": "new"})
    assert window.state_label.text() == "STATUS: RECORDING"
    pi_style = window._status_labels["Pi"].styleSheet()
    for notice in ("PENDING", "FAILED", "SAMPLE -1", "SAMPLE invalid"):
        window._connection_changed("Trigger", notice)
        assert window.state_label.text() == "STATUS: RECORDING"
        assert window._trigger_sample is None
        assert window._status_labels["Pi"].styleSheet() == pi_style
    window._connection_changed("Trigger", "SAMPLE 41")
    assert window.state_label.text() == "STATUS: TRIGGERED (SAMPLE 41)"
    assert window._trigger_sample == 41
    window._connection_changed("Nano", "ARMED")
    assert "점화 감지 대기" in window._status_labels["Nano"].text()
    window._connection_changed("Nano", "ARMING")
    assert "준비 중" in window._status_labels["Nano"].text()
    window._connection_changed("Nano", "IGNITION_HIGH")
    assert "입력 HIGH" in window._status_labels["Nano"].text()
    window._session_stopped({})
    window._connection_changed("Trigger", "SAMPLE 99")
    assert window.state_label.text() == "STATUS: COMPLETE"


def test_save_error_does_not_turn_complete_session_into_daq_failure(idle_window):
    window = idle_window
    window._session_stopped({"log_file": "session.h5"})
    window._operation_failed("save", "CSV 저장에 실패했습니다; Pi 로그 가져오기로 재시도")
    assert window.state_label.text() == "STATUS: COMPLETE"
    assert not window._daq_recovery_required
    assert window.start_button.isEnabled()
    assert window._error_dialog.isVisible()


def test_reset_suppresses_background_alarms_and_error_dialog_x_closes(idle_window):
    app = QApplication.instance()
    window = idle_window
    window._reset_daq()
    window._show_error("telemetry is not connected")
    window._receive_health({"state": "READY", "health": {}})
    window._connection_changed("Pi", "CONNECTED")
    assert window._daq_reset_in_progress
    assert not window.start_button.isEnabled()
    assert not window.daq_reset_button.isEnabled()
    assert window._error_dialog is None
    window._operation_failed("reset", "DAQ 초기화 실패")
    app.processEvents()
    dialog = window._error_dialog
    assert dialog is not None and dialog.isVisible() and not dialog.isModal()
    window._operation_failed("command", "another error")
    assert window.findChildren(QMessageBox) == [dialog]
    assert dialog.close()
    app.processEvents()
    assert not dialog.isVisible()
    window._show_error("cannot connect to telemetry")
    app.processEvents()
    assert not dialog.isVisible()
    assert not window.start_button.isEnabled()
    assert window.daq_reset_button.isEnabled()


def test_old_session_data_and_calibration_error_do_not_open_blocked_windows(idle_window):
    window = idle_window
    window._start_session()
    window._session_started({"session_id": "new"})
    block = TelemetryBlock(
        sequence=0, first_sample_index=0, sample_rate=1000,
        channel_names=("thrust_N", "pressure_bar"),
        values=np.ones((2, 2), dtype=np.float32), session_id="old",
    )
    window._receive_block(block)
    assert not len(window._sample_indices)
    dialog = LoadCellCalibrationDialog(current_scale=1, current_offset=0, parent=window)
    window._calibration_dialog = dialog
    window._operation_failed("calibration", "CALIBRATION_SAMPLE response timed out")
    assert "timed out" in dialog.status_label.text()
    assert window._error_dialog is None
    assert not window.start_button.isEnabled()
    dialog.close()
    window._calibration_dialog = None


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


def test_sidebar_navigation_and_console_preserve_the_live_workspace(
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
    window.resize(1100, 760)
    window.show()
    app.processEvents()

    assert not window.tabs.tabBar().isVisible()
    # Select actual visible tree rows, including return to the live plots.
    for label, expected_index in (("수집 · 연결", 1), ("시험 로그", 3), ("실시간 계측", 0)):
        item = window.navigation.findItems(
            label, Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchRecursive
        )[0]
        QTest.mouseClick(
            window.navigation.viewport(), Qt.MouseButton.LeftButton,
            pos=window.navigation.visualItemRect(item).center(),
        )
        app.processEvents()
        assert window.tabs.currentIndex() == expected_index
        assert window.page_title.text() == label

    window._append_log("test connection event")
    QTest.mouseClick(window.console_toggle, Qt.MouseButton.LeftButton)
    app.processEvents()
    assert window.event_console.isVisible()
    assert "test connection event" in window.event_console.toPlainText()
    for panel in window._signal_panels:
        assert panel.plot.geometry().bottom() < panel.plot.parentWidget().height()
    QTest.mouseClick(window.console_toggle, Qt.MouseButton.LeftButton)
    app.processEvents()
    assert not window.event_console.isVisible()
    for panel in window._signal_panels:
        group = panel.plot.parentWidget()
        assert panel.plot.geometry().bottom() < group.height()
        assert panel.plot.backgroundBrush().color().name() == "#1d1e20"
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
            # A resumed/reconnected DAQ can use a large absolute sample index;
            # the operator plot must still start its own clock at 0 s.
            first_sample_index=9_876_543_210_123,
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
    plotted_time, physical_thrust = window._signal_panels[0].curve.getOriginalDataset()
    np.testing.assert_allclose(plotted_time, (0.0, 0.001, 0.002))
    np.testing.assert_allclose(physical_thrust, (10.0, 12.5, 11.0))
    assert window._plot_time_origin == 9_876_543_210_123
    assert not window._signal_panels[0].plot.getAxis("bottom").autoSIPrefix
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


def test_start_session_immediately_clears_live_plot(tmp_path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    config = TmsConfig(
        daq=DaqConfig(sample_rate=1000, block_ms=10),
        thrust=ChannelConfig(0, 1.0, 0.0),
        pressure=ChannelConfig(1, 1.0, 0.0),
        logging=LoggingConfig(directory=tmp_path),
    )
    monkeypatch.setattr(MainWindow, "_start_runtime", lambda self: None)
    window = MainWindow(config, tmp_path / "config.yaml")
    window._receive_block(
        TelemetryBlock(
            sequence=1,
            first_sample_index=500,
            sample_rate=1000,
            channel_names=("thrust_N", "pressure_bar"),
            values=np.asarray(((10.0, 1.2),), dtype=np.float32),
        )
    )

    class RuntimeStub:
        def __init__(self) -> None:
            self.started: list[str] = []

        def start_session(self, name: str) -> None:
            self.started.append(name)

        def stop(self) -> None:
            pass

    runtime = RuntimeStub()
    window._runtime = runtime  # type: ignore[assignment]
    window.start_button.setEnabled(True)
    window._start_session()

    assert runtime.started == ["KNSB_TEST_001"]
    assert not len(window._sample_indices)
    assert window._plot_time_origin is None
    plotted_time, plotted_values = window._signal_panels[0].curve.getData()
    assert plotted_time is None and plotted_values is None
    x_min, x_max = window._signal_panels[0].plot.getViewBox().viewRange()[0]
    assert x_min == 0.0
    assert x_max == PLOT_HISTORY_SECONDS
    assert window.state_label.text() == "STATUS: STARTING"
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


def test_pressure_calibration_dialog_collects_ai1_points_and_fits() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = PressureCalibrationDialog(current_scale=0.001, current_offset=0.0)
    assert dialog.reference_table.rowCount() == 2
    assert "100 Ω" in dialog.layout().itemAt(0).widget().text()
    assert "0.400 V" in dialog.layout().itemAt(0).widget().text()
    dialog._request_capture(0)
    dialog.record_capture(
        {
            "_ui_row": 0,
            "channels": {"ai1": {"sample_count": 5000, "mean": 1000.0, "stddev": 2.0}},
        }
    )
    dialog._request_capture(1)
    dialog.record_capture(
        {
            "_ui_row": 1,
            "channels": {"ai1": {"sample_count": 5000, "mean": 3000.0, "stddev": 2.0}},
        }
    )
    assert "mA" in dialog._mean_labels[1].text()
    dialog._mass_fields[1].setValue(10.0)
    dialog._calculate()
    assert dialog._fit is not None
    assert dialog._fit.scale_bar_per_count == pytest.approx(0.005)
    assert dialog.apply_button.isEnabled()
    dialog.close()
