from __future__ import annotations

import time
from dataclasses import dataclass, replace
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
    SECOND_SENSOR_AI_CHANNEL,
    SshConfig,
    SystemConfig,
    THRUST_AI_CHANNEL,
    TmsConfig,
    save_config,
)
from common.protocol import TelemetryBlock
from laptop.gui.calibration_dialog import (
    LoadCellCalibrationDialog,
    PressureCalibrationDialog,
)
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
    "thrust_N": ChannelDisplay("추력 (LPF)", "N", "#0f62fe", 2),
    "pressure_bar": ChannelDisplay("압력 (LPF)", "bar", "#8a3ffc", 3),
    "raw_thrust": ChannelDisplay("추력 원시값", "ADC", "#42be65", 0),
    "raw_pressure": ChannelDisplay("압력 원시값", "ADC", "#ff832b", 0),
}
DEFAULT_LIVE_CHANNELS = ("thrust_N", "pressure_bar")

# Retain a full 10-second physical-value history for metrics and log context,
# but draw only a peak-preserving envelope.  Rendering the whole 50,000 point
# window for two panels on every 10 ms DAQ block is what made the UI sluggish.
PLOT_HISTORY_SECONDS = 10.0
PLOT_MAX_POINTS = 2_000
PLOT_REFRESH_INTERVAL_SEC = 0.10


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
        # Anti-aliasing is disproportionately expensive for continuously
        # redrawn time-series curves and does not improve operator readability
        # at the dashboard's live update rate.
        pg.setConfigOptions(antialias=False)
        self._signals = BackendSignals()
        self._runtime: BackendRuntime | None = None
        self._status_labels: dict[str, QLabel] = {}
        self._connection_states: dict[str, str] = {}
        self._sample_indices = np.empty(0, dtype=np.int64)
        self._channel_names: tuple[str, ...] = ()
        self._channel_values: dict[str, np.ndarray] = {}
        self._peak_values: dict[str, float] = {}
        self._signal_panels: list[SignalPanel] = []
        self._last_sample_rate = self.config.daq.sample_rate
        self._trigger_sample: int | None = None
        # DAQ sample indexes need not start at zero after a reconnect.  Keep
        # the plot clock independent of them so every measurement starts at
        # 0 s on screen.
        self._plot_time_origin: int | None = None
        self._last_plot_update = 0.0
        self._sessions = []
        self._calibration_dialog: LoadCellCalibrationDialog | PressureCalibrationDialog | None = None
        self._daq_reset_in_progress = False

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

        plot = pg.PlotWidget()
        plot.setMinimumHeight(235)
        plot.showGrid(x=True, y=True, alpha=0.22)
        # Keep the operator-facing clock in plain seconds.  Otherwise
        # pyqtgraph abbreviates an accidentally large sample index as Ts/Ys.
        plot.getAxis("bottom").enableAutoSIPrefix(False)
        plot.setXRange(0.0, PLOT_HISTORY_SECONDS, padding=0.0)
        curve = plot.plot(pen=pg.mkPen("#0f62fe", width=2))
        curve.setClipToView(True)
        curve.setDownsampling(auto=True, method="peak")
        layout.addWidget(plot, 1)

        metrics = QGridLayout()
        current = QLabel("--")
        peak = QLabel("--")
        range_label = QLabel("Y축 자동 범위: --")
        for value in (current, peak):
            value.setStyleSheet("font-size: 19px; font-weight: bold;")
        range_label.setStyleSheet("color: #525252;")
        metrics.addWidget(QLabel("현재값"), 0, 0)
        metrics.addWidget(QLabel("세션 최대"), 0, 1)
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

        self.calibration_button = QPushButton("AI0 로드셀 보정")
        self.calibration_button.setToolTip(
            "실행 전 AI0 원시값을 취득해 2점 또는 3점 질량 보정을 저장합니다"
        )
        layout.addWidget(self.calibration_button)

        self.pressure_calibration_button = QPushButton("AI1 압력 보정")
        self.pressure_calibration_button.setToolTip(
            "실행 전 AI1 원시값을 취득해 2점 또는 3점 기준압력 보정을 저장합니다"
        )
        layout.addWidget(self.pressure_calibration_button)

        self.daq_reset_button = QPushButton("DAQ 초기화")
        self.daq_reset_button.setEnabled(False)
        self.daq_reset_button.setToolTip(
            "측정 전 USB-4704 드라이버/USB 장치를 재초기화하고 /dev/daq0을 복구합니다"
        )
        layout.addWidget(self.daq_reset_button)

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
        self.calibration_button.clicked.connect(self._open_calibration)
        self.pressure_calibration_button.clicked.connect(self._open_pressure_calibration)
        self.daq_reset_button.clicked.connect(self._reset_daq)
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
        panel.plot.setTitle(f"{display.label} · Y축 자동 범위")
        panel.plot.setLabel("left", display.label, units=display.unit)
        panel.plot.setLabel("bottom", "측정 시작 후 시간", units="s")
        panel.curve.setPen(pg.mkPen(display.color, width=2))
        panel.range_label.setText(f"Y축 자동 범위 · {display.label}: 데이터 대기")

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
        if self._plot_time_origin is None:
            self._plot_time_origin = int(self._sample_indices[0])
        # Subtract while the indexes are still int64.  Converting a large
        # absolute DAQ index to float first can round adjacent samples into
        # the same x-coordinate.
        times = (self._sample_indices - self._plot_time_origin).astype(
            np.float64
        ) / float(self._last_sample_rate)
        latest_time = max(0.0, float(times[-1]))
        x_min = max(0.0, latest_time - PLOT_HISTORY_SECONDS)
        x_max = max(PLOT_HISTORY_SECONDS, latest_time)
        for panel in self._signal_panels:
            panel.plot.setXRange(x_min, x_max, padding=0.0)
            channel_name = self._selected_channel(panel)
            values = self._channel_values.get(channel_name)
            if values is None or len(values) != len(self._sample_indices):
                panel.curve.clear()
                panel.current.setText("--")
                panel.peak.setText("--")
                continue
            display_indices = self._peak_display_indices(values)
            panel.curve.setData(times[display_indices], values[display_indices])
            self._autoscale_panel_y(panel, values)
            self._update_signal_panel_metrics(panel, values)

    @staticmethod
    def _peak_display_indices(values: np.ndarray) -> np.ndarray:
        """Return an ordered, bounded-size envelope that retains local peaks.

        The data acquisition path continues to hold every sample.  This only
        controls the number of points passed to pyqtgraph for screen drawing,
        using the minimum and maximum of each time bucket so short pressure or
        thrust peaks do not disappear from the operator view.
        """
        sample_count = len(values)
        if sample_count <= PLOT_MAX_POINTS:
            return np.arange(sample_count, dtype=np.intp)

        bucket_limit = max(1, PLOT_MAX_POINTS // 2)
        bucket_size = int(np.ceil(sample_count / bucket_limit))
        bucket_count = int(np.ceil(sample_count / bucket_size))
        padded_count = bucket_count * bucket_size
        padded = np.full(padded_count, np.nan, dtype=np.float32)
        padded[:sample_count] = values
        buckets = padded.reshape(bucket_count, bucket_size)
        finite = np.isfinite(buckets)
        valid_buckets = np.any(finite, axis=1)
        if not np.any(valid_buckets):
            return np.linspace(
                0, sample_count - 1, PLOT_MAX_POINTS, dtype=np.intp
            )

        starts = np.arange(bucket_count, dtype=np.intp) * bucket_size
        minimum_offsets = np.argmin(
            np.where(finite, buckets, np.inf), axis=1
        ).astype(np.intp)
        maximum_offsets = np.argmax(
            np.where(finite, buckets, -np.inf), axis=1
        ).astype(np.intp)
        minimum_indices = starts + minimum_offsets
        maximum_indices = starts + maximum_offsets
        ordered = np.empty(bucket_count * 2, dtype=np.intp)
        ordered[0::2] = np.minimum(minimum_indices, maximum_indices)
        ordered[1::2] = np.maximum(minimum_indices, maximum_indices)
        return ordered[np.repeat(valid_buckets, 2)]

    def _update_signal_panel_metrics(
        self,
        panel: SignalPanel,
        values: np.ndarray,
    ) -> None:
        channel_name = self._selected_channel(panel)
        display = self._channel_display(channel_name)
        finite = values[np.isfinite(values)]
        if not len(finite):
            panel.current.setText("--")
            panel.peak.setText("--")
            panel.range_label.setText(f"Y축 자동 범위 · {display.label}: 데이터 없음")
            return
        current = float(values[-1])
        peak = self._peak_values.get(channel_name, float(np.max(finite)))
        panel.current.setText(self._format_channel_value(current, display))
        panel.peak.setText(self._format_channel_value(peak, display))
        minimum, maximum = float(np.min(finite)), float(np.max(finite))
        panel.range_label.setText(
            "Y축 자동 범위 · "
            f"{self._format_channel_value(minimum, display)} – "
            f"{self._format_channel_value(maximum, display)}"
        )

    @staticmethod
    def _autoscale_panel_y(panel: SignalPanel, values: np.ndarray) -> None:
        """Fit the plot height to physical values without changing those values."""
        finite_mask = np.isfinite(values)
        if not np.any(finite_mask):
            return
        minimum = float(np.min(values[finite_mask]))
        maximum = float(np.max(values[finite_mask]))
        span = maximum - minimum
        if np.isclose(span, 0.0):
            span = max(abs(minimum), 1.0) * 0.05
        padding = span * 0.08
        panel.plot.setYRange(minimum - padding, maximum + padding, padding=0.0)

    @staticmethod
    def _format_channel_value(value: float, display: ChannelDisplay) -> str:
        if not np.isfinite(value):
            return "--"
        suffix = f" {display.unit}" if display.unit else ""
        return f"{value:.{display.decimals}f}{suffix}"

    def _update_quick_settings_summary(self) -> None:
        if not hasattr(self, "quick_settings_summary"):
            return
        self.quick_settings_summary.setText(
            f"Pi {self.config.system.pi_host}:{self.config.ssh.port} · "
            f"DAQ {self.config.daq.sample_rate:,} S/s · "
            f"AI{self.config.thrust.channel}=로드셀, "
            f"AI{self.config.pressure.channel}=두번째 센서 · "
            f"압력 입력 {self.config.pressure_input.shunt_ohms:g} Ω "
            f"({self.config.pressure_input.signal_voltage_min_v:.3f}–"
            f"{self.config.pressure_input.signal_voltage_max_v:.3f} V) · "
            f"압력 보정 scale={self.config.pressure.scale:.6g}, "
            f"offset={self.config.pressure.offset:.6g} bar · "
            f"표시/저장 LPF={'ON' if self.config.low_pass.enabled else 'OFF'} "
            f"({self.config.low_pass.cutoff_hz:g} Hz) · "
            "원본 raw/비필터 물리값도 함께 저장"
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
        low_pass_info = QLabel(
            f"화면/로그 LPF: "
            f"{'사용' if self.config.low_pass.enabled else '사용 안 함'} · "
            f"차단주파수 {self.config.low_pass.cutoff_hz:g} Hz "
            "(Pi와 동일 설정)"
        )
        low_pass_info.setWordWrap(True)
        self.thrust_channel = self._spin(
            THRUST_AI_CHANNEL, THRUST_AI_CHANNEL, THRUST_AI_CHANNEL
        )
        self.thrust_channel.setEnabled(False)
        self.pressure_channel = self._spin(
            SECOND_SENSOR_AI_CHANNEL,
            SECOND_SENSOR_AI_CHANNEL,
            SECOND_SENSOR_AI_CHANNEL,
        )
        self.pressure_channel.setEnabled(False)
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
        display_filter = (
            f"{self.config.low_pass.cutoff_hz:g} Hz LPF 처리된"
            if self.config.low_pass.enabled
            else "비필터"
        )
        display_scale = QLabel(
            f"실시간 추력/압력은 Pi에서 {display_filter} 물리값을 표시합니다. "
            "원본 raw와 비필터 물리값은 로그에 함께 저장합니다."
        )
        display_scale.setWordWrap(True)
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
            ("Low-pass filter", low_pass_info),
            ("AI0 (로드셀 · 고정)", self.thrust_channel),
            ("AI1 (두번째 센서 · 고정)", self.pressure_channel),
            ("Display Scale", display_scale),
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
        self._signals.calibration_sampled.connect(self._calibration_sampled)
        self._signals.calibration_saved.connect(self._calibration_saved)
        self._signals.daq_reset_finished.connect(self._daq_reset_finished)
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
        # Clear immediately on the operator action, rather than waiting for
        # the asynchronous START_SESSION acknowledgement.
        self._clear_graphs()
        self.start_button.setEnabled(False)
        self.state_label.setText("STATUS: STARTING")
        self._runtime.start_session(name)

    def _stop_session(self) -> None:
        assert self._runtime is not None
        self.stop_button.setEnabled(False)
        self.state_label.setText("STATUS: STOPPING")
        self._runtime.stop_session()

    def _open_calibration(self) -> None:
        if self._runtime is None:
            QMessageBox.warning(
                self, "연결 대기", "Pi telemetry 연결이 준비된 뒤 보정하십시오."
            )
            return
        if self.stop_button.isEnabled():
            QMessageBox.warning(
                self, "측정 중", "측정을 종료한 뒤에만 실행 전 캘리브레이션을 할 수 있습니다."
            )
            return
        dialog = LoadCellCalibrationDialog(
            current_scale=self.config.thrust.scale,
            current_offset=self.config.thrust.offset,
            parent=self,
        )
        dialog.capture_requested.connect(self._capture_calibration_sample)
        dialog.save_requested.connect(self._save_thrust_calibration)
        self._calibration_dialog = dialog
        dialog.exec()
        self._calibration_dialog = None

    def _open_pressure_calibration(self) -> None:
        if self._runtime is None:
            QMessageBox.warning(
                self, "연결 대기", "Pi telemetry 연결이 준비된 뒤 보정하십시오."
            )
            return
        if self.stop_button.isEnabled():
            QMessageBox.warning(
                self, "측정 중", "측정을 종료한 뒤에만 실행 전 캘리브레이션을 할 수 있습니다."
            )
            return
        dialog = PressureCalibrationDialog(
            current_scale=self.config.pressure.scale,
            current_offset=self.config.pressure.offset,
            shunt_ohms=self.config.pressure_input.shunt_ohms,
            loop_min_mA=self.config.pressure_input.loop_min_mA,
            loop_max_mA=self.config.pressure_input.loop_max_mA,
            parent=self,
        )
        dialog.capture_requested.connect(self._capture_calibration_sample)
        dialog.save_requested.connect(self._save_pressure_calibration)
        self._calibration_dialog = dialog
        dialog.exec()
        self._calibration_dialog = None

    def _reset_daq(self) -> None:
        if self._runtime is None:
            QMessageBox.warning(
                self, "연결 대기", "Dashboard 백엔드가 준비된 뒤 DAQ를 초기화하십시오."
            )
            return
        if self.stop_button.isEnabled():
            QMessageBox.warning(
                self, "측정 중", "측정을 종료한 뒤에만 DAQ 초기화를 실행할 수 있습니다."
            )
            return
        self._daq_reset_in_progress = True
        self._update_daq_reset_button()
        self.start_button.setEnabled(False)
        self.state_label.setText("STATUS: DAQ INITIALIZING")
        self._append_log("DAQ 초기화: USB-4704 복구를 시작합니다.")
        self._runtime.reset_daq()

    def _daq_reset_finished(self, result: dict[str, object]) -> None:
        self._daq_reset_in_progress = False
        details = str(result.get("details", "")).strip()
        if bool(result.get("daq_ready")):
            self._append_log("DAQ 초기화 완료: /dev/daq0 준비됨. Pi 재연결 중입니다.")
        else:
            self._append_log(
                "DAQ 초기화는 끝났지만 /dev/daq0이 없습니다. USB 전원·케이블을 확인하십시오."
            )
        if details:
            self.pipeline_message.setText(f"DAQ 초기화: {details}")
        self._update_daq_reset_button()

    def _capture_calibration_sample(self, row: int, duration_ms: int) -> None:
        if self._runtime is None:
            if self._calibration_dialog is not None:
                self._calibration_dialog.operation_failed("Pi telemetry 연결이 없습니다")
            return
        self._runtime.capture_calibration_sample(row=row, duration_ms=duration_ms)

    def _calibration_sampled(self, result: dict[str, Any]) -> None:
        if self._calibration_dialog is not None:
            self._calibration_dialog.record_capture(result)

    def _save_thrust_calibration(
        self, scale_N_per_count: float, offset_N: float
    ) -> None:
        if self._runtime is None:
            if self._calibration_dialog is not None:
                self._calibration_dialog.operation_failed("Pi telemetry 연결이 없습니다")
            return
        self._runtime.save_thrust_calibration(
            scale_N_per_count=scale_N_per_count,
            offset_N=offset_N,
        )

    def _save_pressure_calibration(
        self, scale_bar_per_count: float, offset_bar: float
    ) -> None:
        if self._runtime is None:
            if self._calibration_dialog is not None:
                self._calibration_dialog.operation_failed("Pi telemetry 연결이 없습니다")
            return
        self._runtime.save_pressure_calibration(
            scale_bar_per_count=scale_bar_per_count,
            offset_bar=offset_bar,
        )

    def _calibration_saved(self, result: dict[str, Any]) -> None:
        try:
            if "thrust" in result:
                thrust = result["thrust"]
                updated = ChannelConfig(
                    channel=THRUST_AI_CHANNEL,
                    scale=float(thrust["scale"]),
                    offset=float(thrust["offset"]),
                )
                self.config = replace(self.config, thrust=updated)
            elif "pressure" in result:
                pressure = result["pressure"]
                updated = ChannelConfig(
                    channel=SECOND_SENSOR_AI_CHANNEL,
                    scale=float(pressure["scale"]),
                    offset=float(pressure["offset"]),
                )
                self.config = replace(self.config, pressure=updated)
            else:
                raise KeyError("thrust or pressure")
            save_config(self.config, self.config_path)
            self._update_quick_settings_summary()
        except (ConfigError, KeyError, TypeError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "로컬 설정 경고",
                "Pi에는 보정값이 저장됐지만 노트북 설정 파일 반영에 실패했습니다: "
                f"{exc}",
            )
        if self._calibration_dialog is not None:
            self._calibration_dialog.calibration_saved(result)

    def _session_started(self, result: dict[str, Any]) -> None:
        self._clear_graphs()
        self.state_label.setText("STATUS: RECORDING / ARMED")
        self.stop_button.setEnabled(True)
        self._update_daq_reset_button()
        self._append_log(f"Session started: {result.get('log_file', '')}")

    def _session_stopped(self, result: dict[str, Any]) -> None:
        self.state_label.setText("STATUS: COMPLETE")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._update_daq_reset_button()
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

        if self._plot_time_origin is None:
            self._plot_time_origin = int(block.first_sample_index)
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

        max_points = max(
            int(block.sample_rate * PLOT_HISTORY_SECONDS), block.sample_count
        )
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
                self._update_signal_panel_metrics(panel, values)

        now = time.monotonic()
        if now - self._last_plot_update >= PLOT_REFRESH_INTERVAL_SEC:
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
        self._update_daq_reset_button()
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
        self._update_daq_reset_button()
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

    def _update_daq_reset_button(self) -> None:
        if not hasattr(self, "daq_reset_button"):
            return
        idle = not self.stop_button.isEnabled()
        self.daq_reset_button.setEnabled(
            self._runtime is not None
            and idle
            and not self._daq_reset_in_progress
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
                    THRUST_AI_CHANNEL,
                    self.config.thrust.scale,
                    self.config.thrust.offset,
                ),
                pressure=ChannelConfig(
                    SECOND_SENSOR_AI_CHANNEL,
                    self.config.pressure.scale,
                    self.config.pressure.offset,
                ),
                pressure_input=self.config.pressure_input,
                low_pass=self.config.low_pass,
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
        if self._daq_reset_in_progress:
            self._daq_reset_in_progress = False
            self._update_daq_reset_button()
        if self._calibration_dialog is not None:
            self._calibration_dialog.operation_failed(message)
        if "DAQ 초기화" in message:
            # A bounded Pi-side hardware operation has detected a wedged USB
            # ioctl. Keep Start disabled so a late command cannot surprise the
            # operator; the reset button remains available even if telemetry
            # itself is no longer responsive.
            self.state_label.setText("STATUS: DAQ RECOVERY REQUIRED")
            self.start_button.setEnabled(False)
            self._update_daq_reset_button()
        QMessageBox.critical(self, "TUSI TMS 오류", message)
        if "session" in message.lower() and "DAQ 초기화" not in message:
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
        self._plot_time_origin = None
        self._peak_values = {}
        self._last_plot_update = 0.0
        for panel in self._signal_panels:
            panel.curve.clear()
            panel.current.setText("--")
            panel.peak.setText("--")
            panel.range_label.setText(
                f"Y축 자동 범위 · {self._channel_display(self._selected_channel(panel)).label}: "
                "데이터 대기"
            )
            panel.plot.setXRange(0.0, PLOT_HISTORY_SECONDS, padding=0.0)
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
