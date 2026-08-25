from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from common.config import (
    ChannelConfig,
    ConfigError,
    DaqConfig,
    LoggingConfig,
    NanoConfig,
    SshConfig,
    SystemConfig,
    TmsConfig,
    save_config,
)
from common.protocol import TelemetryBlock
from laptop.gui.runtime import BackendRuntime, BackendSignals
from laptop.logs import LogError, export_csv, list_sessions
from laptop.operator_defaults import apply_field_connection
from laptop.system_test import SystemTestResult

STATUS_COLORS = {
    "GREEN": "#24a148",
    "YELLOW": "#f1c21b",
    "RED": "#da1e28",
    "GRAY": "#8d8d8d",
}


@dataclass(frozen=True)
class ChannelDisplay:
    """Presentation metadata for a telemetry channel shown in the dashboard."""

    label: str
    unit: str
    color: str
    decimals: int


@dataclass
class SignalPanel:
    """Widgets and plot state for one selectable live-data quadrant."""

    selector: QComboBox
    plot: pg.PlotWidget
    curve: Any
    current: QLabel
    peak: QLabel
    range_label: QLabel


CHANNEL_DISPLAYS: dict[str, ChannelDisplay] = {
    "thrust_N": ChannelDisplay("추력", "N", "#0f62fe", 2),
    "pressure_bar": ChannelDisplay("압력", "bar", "#8a3ffc", 3),
    "raw_thrust": ChannelDisplay("추력 원시값", "ADC", "#42be65", 0),
    "raw_pressure": ChannelDisplay("압력 원시값", "ADC", "#ff832b", 0),
}
DEFAULT_LIVE_CHANNELS = ("thrust_N", "pressure_bar")
NORMALIZED_DECIMALS = 3


class MainWindow(QMainWindow):
    def __init__(
        self,
        config: TmsConfig,
        config_path: Path,
        *,
        direct_telemetry: bool = False,
        fixed_connection: bool = True,
    ) -> None:
        super().__init__()
        self.fixed_connection = fixed_connection
        self.config = apply_field_connection(config) if fixed_connection else config
        self.config_path = config_path
        self.direct_telemetry = direct_telemetry
        self.setWindowTitle("TUSI TMS")
        self.resize(1180, 850)
        self._signals = BackendSignals()
        self._runtime: BackendRuntime | None = None
        self._status_labels: dict[str, QLabel] = {}
        self._connection_states: dict[str, str] = {}
        self._sample_indices = np.empty(0, dtype=np.int64)
        self._channel_names: tuple[str, ...] = ()
        self._channel_values: dict[str, np.ndarray] = {}
        self._peak_values: dict[str, float] = {}
        self._channel_bounds: dict[str, tuple[float, float]] = {}
        self._signal_panels: list[SignalPanel] = []
        self._last_sample_rate = self.config.daq.sample_rate
        self._trigger_sample: int | None = None
        self._last_plot_update = 0.0
        self._sessions = []

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_dashboard(), "Dashboard")
        self.tabs.addTab(self._build_setup(), "Setup")
        self.tabs.addTab(self._build_system_test(), "System Test")
        self.tabs.addTab(self._build_logs(), "Logs")
        self.setCentralWidget(self.tabs)
        self._connect_signals()
        self._start_runtime()
        self._refresh_logs()

    def _build_dashboard(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("TUSI TMS · 통합 계측 콘솔")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 4px 0;")
        layout.addWidget(title)

        subtitle = QLabel(
            "좌측 상단과 우측 상단에서 표시할 실시간 채널을 선택할 수 있습니다. "
            "상태와 측정 제어는 하단 패널에 항상 표시됩니다."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #525252;")
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.addWidget(self._build_signal_panel(0, DEFAULT_LIVE_CHANNELS[0]), 0, 0)
        grid.addWidget(self._build_signal_panel(1, DEFAULT_LIVE_CHANNELS[1]), 0, 1)
        grid.addWidget(self._build_pipeline_status_panel(), 1, 0)
        grid.addWidget(self._build_session_control_panel(), 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 3)
        grid.setRowStretch(1, 2)
        layout.addLayout(grid, 1)

        # These aliases keep the original public widget names usable for
        # integrations while the panes themselves are now channel-selectable.
        self.thrust_plot = self._signal_panels[0].plot
        self.thrust_curve = self._signal_panels[0].curve
        self.pressure_plot = self._signal_panels[1].plot
        self.pressure_curve = self._signal_panels[1].curve
        self.current_thrust = self._signal_panels[0].current
        self.peak_thrust = self._signal_panels[0].peak
        self.current_pressure = self._signal_panels[1].current
        self.peak_pressure = self._signal_panels[1].peak
        return page

    def _build_signal_panel(self, index: int, default_channel: str) -> QGroupBox:
        box = QGroupBox(f"실시간 데이터 {index + 1}")
        box.setObjectName(f"live-data-panel-{index}")
        layout = QVBoxLayout(box)

        selection = QHBoxLayout()
        selection.addWidget(QLabel("표시 데이터"))
        selector = QComboBox()
        selector.setObjectName(f"signal-selector-{index}")
        for channel_name in DEFAULT_LIVE_CHANNELS:
            selector.addItem(self._channel_option_label(channel_name), channel_name)
        selector.setCurrentIndex(max(0, selector.findData(default_channel)))
        selection.addWidget(selector, 1)
        layout.addLayout(selection)

        pg.setConfigOptions(antialias=True)
        plot = pg.PlotWidget()
        plot.setMinimumHeight(235)
        plot.showGrid(x=True, y=True, alpha=0.22)
        curve = plot.plot(pen=pg.mkPen("#0f62fe", width=2))
        layout.addWidget(plot, 1)

        metrics = QGridLayout()
        current = QLabel("--")
        peak = QLabel("--")
        range_label = QLabel("자동 min–max: --")
        for value in (current, peak):
            value.setStyleSheet("font-size: 19px; font-weight: bold;")
        range_label.setStyleSheet("color: #525252;")
        metrics.addWidget(QLabel("정규화 현재 (0–1)"), 0, 0)
        metrics.addWidget(QLabel("세션 최대 (원본)"), 0, 1)
        metrics.addWidget(current, 1, 0)
        metrics.addWidget(peak, 1, 1)
        metrics.addWidget(range_label, 2, 0, 1, 2)
        layout.addLayout(metrics)

        panel = SignalPanel(selector, plot, curve, current, peak, range_label)
        self._signal_panels.append(panel)
        selector.currentIndexChanged.connect(
            lambda _selection, panel_index=index: self._plot_selection_changed(
                panel_index
            )
        )
        self._refresh_panel_presentation(panel)
        return box

    def _build_pipeline_status_panel(self) -> QGroupBox:
        status_box = QGroupBox("프로그램 / 파이프라인 상태")
        status_layout = QVBoxLayout(status_box)

        self.state_label = QLabel("STATUS: DISCONNECTED")
        self.state_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        status_layout.addWidget(self.state_label)

        self.pipeline_summary = QLabel(
            "SSH 터널과 Pi telemetry 연결을 기다리는 중입니다."
        )
        self.pipeline_summary.setWordWrap(True)
        self.pipeline_summary.setStyleSheet("color: #525252;")
        status_layout.addWidget(self.pipeline_summary)

        acquisition = QGridLayout()
        self.sample_rate = QLabel("-- S/s")
        self.t_plus = QLabel("Pre-trigger")
        self.data_window = QLabel("최근 데이터: --")
        for value in (self.sample_rate, self.t_plus, self.data_window):
            value.setStyleSheet("font-weight: bold;")
        acquisition.addWidget(QLabel("Sample Rate"), 0, 0)
        acquisition.addWidget(QLabel("T+"), 0, 1)
        acquisition.addWidget(QLabel("Buffer"), 0, 2)
        acquisition.addWidget(self.sample_rate, 1, 0)
        acquisition.addWidget(self.t_plus, 1, 1)
        acquisition.addWidget(self.data_window, 1, 2)
        status_layout.addLayout(acquisition)

        component_layout = QGridLayout()
        for index, name in enumerate(
            ("Nano", "LAN", "SSH", "Pi", "DAQ", "Logger", "Disk")
        ):
            label = QLabel()
            self._status_labels[name] = label
            self._set_status(name, "Inactive", "GRAY")
            row, column = divmod(index, 3)
            component_layout.addWidget(label, row, column)
        status_layout.addLayout(component_layout)

        self.pipeline_message = QLabel("최근 이벤트: 없음")
        self.pipeline_message.setWordWrap(True)
        self.pipeline_message.setStyleSheet(
            "background: #f4f4f4; border-radius: 4px; padding: 7px; color: #393939;"
        )
        status_layout.addWidget(self.pipeline_message)
        return status_box

    def _build_session_control_panel(self) -> QGroupBox:
        box = QGroupBox("측정 제어 / 설정")
        layout = QVBoxLayout(box)

        self.test_name = QLineEdit("KNSB_TEST_001")
        self.test_name.setPlaceholderText("시험명")
        layout.addWidget(QLabel("시험명"))
        layout.addWidget(self.test_name)

        controls = QHBoxLayout()
        self.start_button = QPushButton("측정 준비")
        self.start_button.setEnabled(False)
        self.stop_button = QPushButton("측정 종료")
        self.stop_button.setEnabled(False)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        layout.addLayout(controls)

        self.quick_settings_summary = QLabel()
        self.quick_settings_summary.setWordWrap(True)
        self.quick_settings_summary.setStyleSheet(
            "background: #edf5ff; border-radius: 4px; padding: 7px; color: #0043ce;"
        )
        layout.addWidget(self.quick_settings_summary)
        self._update_quick_settings_summary()

        navigation = QHBoxLayout()
        setup_button = QPushButton("설정 열기")
        system_test_button = QPushButton("시스템 점검")
        logs_button = QPushButton("로그")
        navigation.addWidget(setup_button)
        navigation.addWidget(system_test_button)
        navigation.addWidget(logs_button)
        layout.addLayout(navigation)

        safety_note = QLabel(
            "측정 준비는 Pi 수집 세션만 시작합니다. Trigger/AO/DO 동작은 이 화면에서 실행하지 않습니다."
        )
        safety_note.setWordWrap(True)
        safety_note.setStyleSheet("color: #6f6f6f;")
        layout.addWidget(safety_note)
        layout.addStretch(1)

        self.start_button.clicked.connect(self._start_session)
        self.stop_button.clicked.connect(self._stop_session)
        setup_button.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        system_test_button.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        logs_button.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        return box

    @staticmethod
    def _channel_display(channel_name: str) -> ChannelDisplay:
        known = CHANNEL_DISPLAYS.get(channel_name)
        if known is not None:
            return known
        normalized = channel_name.lower()
        if normalized.endswith("_bar"):
            unit = "bar"
            decimals = 3
        elif normalized.endswith("_n"):
            unit = "N"
            decimals = 2
        elif normalized.startswith("raw_"):
            unit = "ADC"
            decimals = 0
        else:
            unit = ""
            decimals = 3
        colors = ("#1192e8", "#198038", "#fa4d56", "#8a3ffc")
        color = colors[sum(ord(char) for char in channel_name) % len(colors)]
        return ChannelDisplay(channel_name.replace("_", " ").title(), unit, color, decimals)

    def _channel_option_label(self, channel_name: str) -> str:
        display = self._channel_display(channel_name)
        suffix = f" ({display.unit})" if display.unit else ""
        return f"{display.label}{suffix}"

    @staticmethod
    def _selected_channel(panel: SignalPanel) -> str:
        value = panel.selector.currentData()
        return str(value) if value is not None else ""

    def _refresh_panel_presentation(self, panel: SignalPanel) -> None:
        channel_name = self._selected_channel(panel)
        if not channel_name:
            return
        display = self._channel_display(channel_name)
        panel.plot.setTitle(f"{display.label} · AUTO MIN–MAX")
        panel.plot.setLabel("left", "정규화 값", units="0–1")
        panel.plot.setLabel("bottom", "시간", units="s")
        panel.curve.setPen(pg.mkPen(display.color, width=2))
        panel.range_label.setText(f"자동 min–max · {display.label}: 데이터 대기")

    def _sync_channel_selectors(self, channel_names: tuple[str, ...]) -> None:
        available = channel_names or DEFAULT_LIVE_CHANNELS
        for index, panel in enumerate(self._signal_panels):
            previous = self._selected_channel(panel)
            selected = previous if previous in available else available[index % len(available)]
            panel.selector.blockSignals(True)
            panel.selector.clear()
            for channel_name in available:
                panel.selector.addItem(
                    self._channel_option_label(channel_name), channel_name
                )
            panel.selector.setCurrentIndex(max(0, panel.selector.findData(selected)))
            panel.selector.blockSignals(False)
            self._refresh_panel_presentation(panel)

    def _plot_selection_changed(self, panel_index: int) -> None:
        if not 0 <= panel_index < len(self._signal_panels):
            return
        self._refresh_panel_presentation(self._signal_panels[panel_index])
        self._render_signal_panels()

    def _render_signal_panels(self) -> None:
        if self._last_sample_rate <= 0 or not len(self._sample_indices):
            for panel in self._signal_panels:
                panel.curve.clear()
                panel.current.setText("--")
                panel.peak.setText("--")
            return
        origin = self._trigger_sample if self._trigger_sample is not None else 0
        times = (self._sample_indices - origin) / self._last_sample_rate
        for panel in self._signal_panels:
            channel_name = self._selected_channel(panel)
            values = self._channel_values.get(channel_name)
            if values is None or len(values) != len(self._sample_indices):
                panel.curve.clear()
                panel.current.setText("--")
                panel.peak.setText("--")
                continue
            normalized = self._normalize_channel_values(channel_name, values)
            panel.curve.setData(times, normalized)
            self._update_signal_panel_metrics(panel, values, normalized)

    def _update_signal_panel_metrics(
        self,
        panel: SignalPanel,
        raw_values: np.ndarray,
        normalized_values: np.ndarray,
    ) -> None:
        channel_name = self._selected_channel(panel)
        display = self._channel_display(channel_name)
        finite = raw_values[np.isfinite(raw_values)]
        if not len(finite):
            panel.current.setText("--")
            panel.peak.setText("--")
            panel.range_label.setText(f"자동 min–max · {display.label}: 데이터 없음")
            return
        current = float(normalized_values[-1])
        peak = self._peak_values.get(channel_name, float(np.max(finite)))
        panel.current.setText(self._format_normalized_value(current))
        panel.peak.setText(self._format_channel_value(peak, display))
        minimum, maximum = self._channel_bounds.get(
            channel_name, (float(np.min(finite)), float(np.max(finite)))
        )
        panel.range_label.setText(
            "자동 min–max · "
            f"{self._format_channel_value(minimum, display)} – "
            f"{self._format_channel_value(maximum, display)}"
        )

    def _normalize_channel_values(
        self, channel_name: str, values: np.ndarray
    ) -> np.ndarray:
        normalized = np.full(values.shape, np.nan, dtype=np.float32)
        finite_mask = np.isfinite(values)
        if not np.any(finite_mask):
            return normalized
        minimum, maximum = self._channel_bounds.get(
            channel_name,
            (float(np.min(values[finite_mask])), float(np.max(values[finite_mask]))),
        )
        span = maximum - minimum
        if np.isclose(span, 0.0):
            normalized[finite_mask] = 0.5
            return normalized
        normalized[finite_mask] = np.clip(
            (values[finite_mask] - minimum) / span,
            0.0,
            1.0,
        )
        return normalized

    @staticmethod
    def _format_channel_value(value: float, display: ChannelDisplay) -> str:
        if not np.isfinite(value):
            return "--"
        suffix = f" {display.unit}" if display.unit else ""
        return f"{value:.{display.decimals}f}{suffix}"

    @staticmethod
    def _format_normalized_value(value: float) -> str:
        if not np.isfinite(value):
            return "--"
        return f"{value:.{NORMALIZED_DECIMALS}f}"

    def _update_quick_settings_summary(self) -> None:
        if not hasattr(self, "quick_settings_summary"):
            return
        self.quick_settings_summary.setText(
            f"Pi {self.config.system.pi_host}:{self.config.ssh.port} · "
            f"DAQ {self.config.daq.sample_rate:,} S/s · "
            f"AI{self.config.thrust.channel}=추력, AI{self.config.pressure.channel}=압력 · "
            "표시: 세션 min–max 자동 정규화"
        )

    def _build_setup(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.pi_host = QLineEdit(self.config.system.pi_host)
        self.telemetry_port = self._spin(1, 65535, self.config.system.telemetry_port)
        self.ssh_port = self._spin(1, 65535, self.config.ssh.port)
        self.ssh_id = QLineEdit(self.config.ssh.username)
        self.ssh_password = QLineEdit(self.config.ssh.password)
        self.ssh_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.remember_password = QCheckBox("비밀번호 저장")
        self.remember_password.setChecked(self.config.ssh.remember_password)
        self.nano_port = QLineEdit(self.config.nano.port)
        self.sample_rate_setup = self._spin(1, 47_619, self.config.daq.sample_rate)
        self.block_ms = self._spin(1, 1000, self.config.daq.block_ms)
        self.thrust_channel = self._spin(0, 7, self.config.thrust.channel)
        self.thrust_scale = self._double(self.config.thrust.scale)
        self.thrust_offset = self._double(self.config.thrust.offset)
        self.pressure_channel = self._spin(0, 7, self.config.pressure.channel)
        self.pressure_scale = self._double(self.config.pressure.scale)
        self.pressure_offset = self._double(self.config.pressure.offset)
        self.log_directory = QLineEdit(str(self.config.logging.directory))
        if self.fixed_connection:
            for widget in (
                self.pi_host,
                self.telemetry_port,
                self.ssh_port,
                self.ssh_id,
                self.ssh_password,
                self.remember_password,
            ):
                widget.setEnabled(False)
        normalization = QLabel(
            "세션 min–max 자동 정규화 (0–1) · 원본 범위는 그래프 하단에 표시"
        )
        normalization.setWordWrap(True)
        fields = (
            ("Pi IP Address (고정)", self.pi_host),
            ("Telemetry Port (고정)", self.telemetry_port),
            ("SSH Port (고정)", self.ssh_port),
            ("SSH ID (고정)", self.ssh_id),
            ("SSH Password (고정)", self.ssh_password),
            ("", self.remember_password),
            ("Nano Port", self.nano_port),
            ("Sample Rate", self.sample_rate_setup),
            ("Block ms", self.block_ms),
            ("Thrust Channel", self.thrust_channel),
            ("Pressure Channel", self.pressure_channel),
            ("Display Scale", normalization),
            ("Log Directory", self.log_directory),
        )
        for label, widget in fields:
            form.addRow(label, widget)
        save_button = QPushButton("설정 저장 및 재연결")
        save_button.clicked.connect(self._save_setup)
        form.addRow(save_button)
        return page

    def _build_system_test(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.system_test_button = QPushButton("전체 시스템 점검")
        self.system_test_table = QTableWidget(0, 3)
        self.system_test_table.setHorizontalHeaderLabels(("항목", "결과", "상세"))
        layout.addWidget(self.system_test_button)
        layout.addWidget(self.system_test_table)
        self.system_test_button.clicked.connect(self._run_system_test)
        return page

    def _build_logs(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.log_list = QListWidget()
        buttons = QHBoxLayout()
        refresh = QPushButton("새로고침")
        open_folder = QPushButton("폴더 열기")
        export = QPushButton("CSV 내보내기")
        fetch = QPushButton("Pi 최신 로그 가져오기")
        for button in (refresh, open_folder, export, fetch):
            buttons.addWidget(button)
        self.advanced_log = QTextEdit()
        self.advanced_log.setReadOnly(True)
        layout.addWidget(self.log_list, 1)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("Advanced Log"))
        layout.addWidget(self.advanced_log, 1)
        refresh.clicked.connect(self._refresh_logs)
        open_folder.clicked.connect(self._open_log_folder)
        export.clicked.connect(self._export_selected_log)
        fetch.clicked.connect(self._fetch_pi_log)
        return page

    def _connect_signals(self) -> None:
        self._signals.connection.connect(self._connection_changed)
        self._signals.block.connect(self._receive_block)
        self._signals.health.connect(self._receive_health)
        self._signals.error.connect(self._show_error)
        self._signals.session_started.connect(self._session_started)
        self._signals.session_stopped.connect(self._session_stopped)
        self._signals.system_test_finished.connect(self._system_test_finished)
        self._signals.remote_log_downloaded.connect(self._remote_log_downloaded)

    def _start_runtime(self) -> None:
        if not self.direct_telemetry and not self.config.ssh.password:
            self._set_status("SSH", "Setup Required", "GRAY")
            self.state_label.setText("STATUS: SSH PASSWORD REQUIRED")
            self._append_log("Setup에서 SSH Password를 입력하십시오.")
            self._runtime = None
            return
        self._runtime = BackendRuntime(
            self.config, self._signals, direct_telemetry=self.direct_telemetry
        )
        self._runtime.start()

    def _start_session(self) -> None:
        name = self.test_name.text().strip()
        if not name:
            QMessageBox.warning(self, "시험명 필요", "Test Name을 입력하십시오.")
            return
        assert self._runtime is not None
        self.start_button.setEnabled(False)
        self.state_label.setText("STATUS: STARTING")
        self._runtime.start_session(name)

    def _stop_session(self) -> None:
        assert self._runtime is not None
        self.stop_button.setEnabled(False)
        self.state_label.setText("STATUS: STOPPING")
        self._runtime.stop_session()

    def _session_started(self, result: dict[str, Any]) -> None:
        self._clear_graphs()
        self.state_label.setText("STATUS: RECORDING / ARMED")
        self.stop_button.setEnabled(True)
        self._append_log(f"Session started: {result.get('log_file', '')}")

    def _session_stopped(self, result: dict[str, Any]) -> None:
        self.state_label.setText("STATUS: COMPLETE")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._append_log(f"Session stopped: {result.get('log_file', '')}")
        self._refresh_logs()

    def _receive_block(self, block: TelemetryBlock) -> None:
        if (
            block.sample_count <= 0
            or block.sample_rate <= 0
            or not block.channel_names
            or block.values.ndim != 2
            or block.values.shape[1] != len(block.channel_names)
        ):
            self._append_log("DAQ block 형식이 유효하지 않아 표시하지 않았습니다.")
            return
        if block.channel_names != self._channel_names:
            if self._channel_names:
                self._append_log(
                    "DAQ channel 구성이 변경되어 실시간 그래프 기록을 새로 시작합니다."
                )
            self._channel_names = block.channel_names
            self._clear_graphs()
            self._sync_channel_selectors(block.channel_names)

        self._sample_indices = np.concatenate(
            (
                self._sample_indices,
                np.arange(
                    block.first_sample_index,
                    block.first_sample_index + block.sample_count,
                    dtype=np.int64,
                ),
            )
        )
        for channel_index, channel_name in enumerate(block.channel_names):
            values = np.asarray(block.values[:, channel_index], dtype=np.float32)
            previous = self._channel_values.get(
                channel_name, np.empty(0, dtype=np.float32)
            )
            self._channel_values[channel_name] = np.concatenate((previous, values))
            finite = values[np.isfinite(values)]
            if len(finite):
                self._peak_values[channel_name] = max(
                    self._peak_values.get(channel_name, float("-inf")),
                    float(np.max(finite)),
                )
                minimum = float(np.min(finite))
                maximum = float(np.max(finite))
                previous_bounds = self._channel_bounds.get(channel_name)
                if previous_bounds is not None:
                    minimum = min(minimum, previous_bounds[0])
                    maximum = max(maximum, previous_bounds[1])
                self._channel_bounds[channel_name] = (minimum, maximum)

        max_points = max(block.sample_rate * 10, block.sample_count)
        if len(self._sample_indices) > max_points:
            self._sample_indices = self._sample_indices[-max_points:]
            for channel_name in self._channel_names:
                self._channel_values[channel_name] = self._channel_values[
                    channel_name
                ][-max_points:]

        self._last_sample_rate = block.sample_rate
        self.sample_rate.setText(f"{block.sample_rate:,} S/s")
        self.data_window.setText(
            f"최근 데이터: {len(self._sample_indices):,} samples / "
            f"{len(self._sample_indices) / block.sample_rate:.1f} s"
        )
        if self._trigger_sample is not None:
            elapsed = int(self._sample_indices[-1]) - self._trigger_sample
            self.t_plus.setText(f"{elapsed / block.sample_rate:.3f} s")
        else:
            self.t_plus.setText("Pre-trigger")

        for panel in self._signal_panels:
            values = self._channel_values.get(self._selected_channel(panel))
            if values is not None:
                channel_name = self._selected_channel(panel)
                self._update_signal_panel_metrics(
                    panel,
                    values,
                    self._normalize_channel_values(channel_name, values),
                )

        now = time.monotonic()
        if now - self._last_plot_update >= 0.05:
            self._render_signal_panels()
            self._last_plot_update = now

    def _receive_health(self, status: dict[str, Any]) -> None:
        trigger_sample = status.get("trigger_sample")
        if trigger_sample != self._trigger_sample:
            self._trigger_sample = trigger_sample
            self._last_plot_update = 0.0
        state = str(status.get("state", "DISCONNECTED"))
        self.state_label.setText(f"STATUS: {state}")
        health = status.get("health", {})
        daq_state = str(health.get("daq", "UNKNOWN"))
        self._health_status("DAQ", daq_state)
        self._health_status("Logger", str(health.get("logger", "UNKNOWN")))
        self._health_status("Disk", str(health.get("storage", "UNKNOWN")))
        probe = status.get("daq_probe", {})
        if isinstance(probe, dict):
            reason = str(probe.get("reason", "")).strip()
            if reason and daq_state.upper() not in ("RUNNING", "AVAILABLE"):
                self.pipeline_message.setText(f"DAQ 상태: {reason}")
        if state in ("RECORDING", "TRIGGERED"):
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(self._runtime is not None)
        elif state in ("READY", "COMPLETE"):
            self.start_button.setEnabled(self._runtime is not None)
            self.stop_button.setEnabled(False)
        self._update_pipeline_summary()

    def _connection_changed(self, component: str, status: str) -> None:
        self._connection_states[component] = status
        name = "Pi" if component == "Trigger" else component
        if name in self._status_labels:
            self._health_status(name, status)
        if component == "Pi" and status == "CONNECTED":
            self.start_button.setEnabled(True)
            self._set_status("LAN", "Connected", "GREEN")
        elif component == "Pi":
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
        if component == "Trigger":
            self.state_label.setText(f"STATUS: TRIGGERED ({status})")
        self._append_log(f"{component}: {status}")
        self._update_pipeline_summary()

    def _update_pipeline_summary(self) -> None:
        if not hasattr(self, "pipeline_summary"):
            return
        pipeline_components = ("Nano", "SSH", "Pi")
        states = [
            f"{component}={self._connection_states[component]}"
            for component in pipeline_components
            if component in self._connection_states
        ]
        if states:
            self.pipeline_summary.setText(" · ".join(states))
        else:
            self.pipeline_summary.setText(
                "SSH 터널과 Pi telemetry 연결을 기다리는 중입니다."
            )

    def _health_status(self, component: str, value: str) -> None:
        upper = value.upper()
        if upper in (
            "CONNECTED",
            "RUNNING",
            "RECORDING",
            "READY",
            "AVAILABLE",
            "OK",
            "COMPLETE",
        ):
            color = "GREEN"
        elif (
            "RECONNECT" in upper
            or "TIMEOUT" in upper
            or upper in ("STARTING", "LOW", "BYPASSED")
        ):
            color = "YELLOW"
        elif upper in ("UNKNOWN", "INACTIVE"):
            color = "GRAY"
        else:
            color = "RED"
        self._set_status(component, value.title(), color)

    def _set_status(self, component: str, text: str, color: str) -> None:
        label = self._status_labels.get(component)
        if label is None:
            return
        label.setText(f"● {component}: {text}")
        label.setStyleSheet(
            f"color: {STATUS_COLORS[color]}; font-weight: bold; padding: 4px;"
        )

    def _save_setup(self) -> None:
        try:
            new_config = TmsConfig(
                system=SystemConfig(
                    self.pi_host.text().strip(), self.telemetry_port.value()
                ),
                ssh=SshConfig(
                    port=self.ssh_port.value(),
                    username=self.ssh_id.text().strip(),
                    password=self.ssh_password.text(),
                    remember_password=self.remember_password.isChecked(),
                    connect_timeout_sec=self.config.ssh.connect_timeout_sec,
                    keepalive_interval_sec=self.config.ssh.keepalive_interval_sec,
                ),
                nano=NanoConfig(
                    port=self.nano_port.text().strip() or "auto",
                    baudrate=self.config.nano.baudrate,
                    heartbeat_timeout_sec=self.config.nano.heartbeat_timeout_sec,
                ),
                daq=DaqConfig(
                    sample_rate=self.sample_rate_setup.value(),
                    block_ms=self.block_ms.value(),
                    device=self.config.daq.device,
                ),
                thrust=ChannelConfig(
                    self.thrust_channel.value(),
                    self.thrust_scale.value(),
                    self.thrust_offset.value(),
                ),
                pressure=ChannelConfig(
                    self.pressure_channel.value(),
                    self.pressure_scale.value(),
                    self.pressure_offset.value(),
                ),
                logging=LoggingConfig(
                    directory=Path(self.log_directory.text()),
                    ring_buffer_sec=self.config.logging.ring_buffer_sec,
                    flush_interval_sec=self.config.logging.flush_interval_sec,
                    pi_directory=self.config.logging.pi_directory,
                ),
            )
            if self.fixed_connection:
                new_config = apply_field_connection(new_config)
            save_config(new_config, self.config_path)
        except (ConfigError, ValueError) as exc:
            QMessageBox.critical(self, "설정 오류", str(exc))
            return
        if self._runtime is not None:
            self._runtime.stop()
        self.config = new_config
        self._last_sample_rate = new_config.daq.sample_rate
        self._update_quick_settings_summary()
        self._start_runtime()
        QMessageBox.information(self, "설정 저장", "설정을 저장하고 재연결합니다.")

    def _run_system_test(self) -> None:
        if self._runtime is None:
            QMessageBox.warning(
                self, "연결 대기", "Dashboard 백엔드가 아직 연결되지 않았습니다."
            )
            return
        self.system_test_button.setEnabled(False)
        self._runtime.run_system_test()

    def _system_test_finished(self, results: list[SystemTestResult]) -> None:
        self.system_test_table.setRowCount(len(results))
        for row, result in enumerate(results):
            self.system_test_table.setItem(row, 0, QTableWidgetItem(result.name))
            self.system_test_table.setItem(
                row, 1, QTableWidgetItem(result.status.value)
            )
            self.system_test_table.setItem(row, 2, QTableWidgetItem(result.details))
        self.system_test_button.setEnabled(True)

    def _refresh_logs(self) -> None:
        self._sessions = list_sessions(self.config.logging.directory)
        self.log_list.clear()
        for session in self._sessions:
            trigger = (
                f"trigger={session.trigger_sample}"
                if session.trigger_sample is not None
                else "no trigger"
            )
            self.log_list.addItem(
                f"{session.start_time} | {session.test_name} | "
                f"{session.sample_count:,} samples | {trigger}"
            )

    def _open_log_folder(self) -> None:
        self.config.logging.directory.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(self.config.logging.directory.resolve()))
        )

    def _export_selected_log(self) -> None:
        row = self.log_list.currentRow()
        if row < 0 or row >= len(self._sessions):
            QMessageBox.warning(self, "시험 선택", "내보낼 시험을 선택하십시오.")
            return
        session = self._sessions[row]
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "CSV 내보내기",
            str(session.path.with_suffix(".csv")),
            "CSV Files (*.csv)",
        )
        if not destination:
            return
        try:
            export_csv(session.path, destination)
        except LogError as exc:
            QMessageBox.critical(self, "CSV 오류", str(exc))
            return
        QMessageBox.information(self, "CSV 완료", destination)

    def _fetch_pi_log(self) -> None:
        if self._runtime is None:
            QMessageBox.warning(
                self, "연결 대기", "Dashboard 백엔드가 아직 연결되지 않았습니다."
            )
            return
        self._runtime.fetch_latest_remote_log()

    def _remote_log_downloaded(self, path: str) -> None:
        self._append_log(f"Pi log downloaded: {path}")
        self._refresh_logs()

    def _show_error(self, message: str) -> None:
        self._append_log(f"ERROR: {message}")
        QMessageBox.critical(self, "TUSI TMS 오류", message)
        if "Session" in message or "session" in message:
            self.start_button.setEnabled(True)

    def _append_log(self, message: str) -> None:
        if hasattr(self, "advanced_log"):
            self.advanced_log.append(message)
        if hasattr(self, "pipeline_message"):
            self.pipeline_message.setText(f"최근 이벤트: {message}")

    def _clear_graphs(self) -> None:
        self._sample_indices = np.empty(0, dtype=np.int64)
        self._channel_values = {
            channel_name: np.empty(0, dtype=np.float32)
            for channel_name in self._channel_names
        }
        self._trigger_sample = None
        self._peak_values = {}
        self._channel_bounds = {}
        self._last_plot_update = 0.0
        for panel in self._signal_panels:
            panel.curve.clear()
            panel.current.setText("--")
            panel.peak.setText("--")
        if hasattr(self, "t_plus"):
            self.t_plus.setText("Pre-trigger")
        if hasattr(self, "data_window"):
            self.data_window.setText("최근 데이터: --")

    @staticmethod
    def _spin(minimum: int, maximum: int, value: int) -> QSpinBox:
        widget = QSpinBox()
        widget.setRange(minimum, maximum)
        widget.setValue(value)
        return widget

    @staticmethod
    def _double(value: float) -> QDoubleSpinBox:
        widget = QDoubleSpinBox()
        widget.setRange(-1_000_000_000.0, 1_000_000_000.0)
        widget.setDecimals(9)
        widget.setValue(value)
        return widget

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._runtime is not None:
            self._runtime.stop()
        event.accept()
