from __future__ import annotations

import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
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
from common.filtering import DEFAULT_MOVING_WINDOW_SAMPLES
from laptop.analysis import read_analysis_data
from laptop.gui.analysis_dialog import ResultAnalysisDialog
from laptop.gui.calibration_dialog import (
    LoadCellCalibrationDialog,
    PressureCalibrationDialog,
)
from laptop.gui.runtime import BackendRuntime, BackendSignals
from laptop.gui.theme import AMBER, CYAN, MUTED, PLOT, apply_theme
from laptop.logs import LogError, list_sessions
from laptop.operator_defaults import apply_field_connection
from laptop.system_test import SystemTestResult
from laptop.storage import prepare_log_directory

STATUS_COLORS = {
    "GREEN": "#87d99b",
    "YELLOW": "#ffc43d",
    "RED": "#ff898d",
    "GRAY": "#afb4bf",
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
    "thrust_N": ChannelDisplay("추력", "N", CYAN, 2),
    "pressure_bar": ChannelDisplay("압력", "bar", AMBER, 3),
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
        local_daq: bool = False,
        fixed_connection: bool = True,
    ) -> None:
        super().__init__()
        self.fixed_connection = fixed_connection and not local_daq
        self.config = apply_field_connection(config) if self.fixed_connection else config
        if local_daq:
            self.config = replace(
                self.config, system=replace(self.config.system, pi_host="127.0.0.1")
            )
        self.config_path = config_path
        self.local_daq = local_daq
        self.direct_telemetry = direct_telemetry or local_daq
        self.setWindowTitle("TUSI TMS — DAQ PC 로컬" if local_daq else "TUSI TMS")
        self.resize(1440, 940)
        self.setMinimumSize(1100, 760)
        apply_theme(self)
        # Anti-aliasing is disproportionately expensive for continuously
        # redrawn time-series curves and does not improve operator readability
        # at the dashboard's live update rate.
        pg.setConfigOptions(antialias=False)
        self._signals = BackendSignals()
        self._runtime: BackendRuntime | None = None
        self._log_directory_buttons: list[QPushButton] = []
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
        self._session_operation: str | None = None
        self._agent_state = "DISCONNECTED"
        self._active_session_id: str | None = None
        self._daq_recovery_required = False
        self._error_dialog: QMessageBox | None = None

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_dashboard(), "Dashboard")
        self.tabs.addTab(self._build_setup(), "Setup")
        self.tabs.addTab(self._build_system_test(), "System Test")
        self.tabs.addTab(self._build_logs(), "Logs")
        self.tabs.tabBar().hide()
        self.setCentralWidget(self._build_workspace())
        self._connect_signals()
        self._start_runtime()
        self._refresh_logs()

    def _build_workspace(self) -> QWidget:
        shell = QWidget()
        shell.setObjectName("workspace-shell")
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("app-header")
        header.setFixedHeight(48)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        title = QLabel("TUSI / TMS")
        title.setObjectName("app-title")
        header_layout.addWidget(title)
        header_layout.addStretch()
        section = QLabel("계측")
        section.setObjectName("app-section")
        header_layout.addWidget(section)
        layout.addWidget(header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 12, 8, 10)
        sidebar_layout.setSpacing(4)
        outline = QLabel("작업")
        outline.setObjectName("sidebar-title")
        sidebar_layout.addWidget(outline)
        self.navigation = QTreeWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setHeaderHidden(True)
        self.navigation.setIndentation(17)
        self.navigation.setRootIsDecorated(True)
        self.navigation.setUniformRowHeights(True)
        self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._navigation_pages: dict[int, QTreeWidgetItem] = {}
        live = QTreeWidgetItem(self.navigation, ["실시간 계측"])
        live.setData(0, Qt.ItemDataRole.UserRole, 0)
        self._navigation_pages[0] = live
        for heading, entries in (
            ("설정", (("수집 · 연결", 1), ("로드셀 보정", "thrust"), ("압력 보정", "pressure"))),
            ("진단", (("시스템 점검", 2),)),
            ("기록", (("시험 로그", 3),)),
        ):
            parent = QTreeWidgetItem(self.navigation, [heading])
            parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            for label, target in entries:
                item = QTreeWidgetItem(parent, [label])
                item.setData(0, Qt.ItemDataRole.UserRole, target)
                if isinstance(target, int):
                    self._navigation_pages[target] = item
            parent.setExpanded(True)
        self.navigation.setCurrentItem(live)
        self.navigation.itemClicked.connect(self._navigate)
        sidebar_layout.addWidget(self.navigation, 1)
        body.addWidget(sidebar)

        workspace = QWidget()
        workspace.setObjectName("workspace")
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        toolbar = QFrame()
        toolbar.setObjectName("workspace-toolbar")
        toolbar.setFixedHeight(46)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(18, 0, 18, 0)
        self.page_title = QLabel("실시간 계측")
        self.page_title.setObjectName("page-title")
        toolbar_layout.addWidget(self.page_title)
        toolbar_layout.addStretch()
        device = QLabel("USB-4704")
        device.setObjectName("workspace-device")
        toolbar_layout.addWidget(device)
        workspace_layout.addWidget(toolbar)
        workspace_layout.addWidget(self.tabs, 1)

        # Keep the live console one click away without filling the work area
        # with repetitive transport messages or permanent explanatory text.
        self.console_toggle = QPushButton("▸ 콘솔")
        self.console_toggle.setObjectName("console-toggle")
        self.console_toggle.setCheckable(True)
        self.console_toggle.toggled.connect(self._toggle_console)
        workspace_layout.addWidget(self.console_toggle)
        self.event_console = QTextEdit()
        self.event_console.setObjectName("event-console")
        self.event_console.setReadOnly(True)
        self.event_console.document().setMaximumBlockCount(500)
        self.event_console.setFixedHeight(145)
        self.event_console.hide()
        workspace_layout.addWidget(self.event_console)
        body.addWidget(workspace, 1)
        layout.addLayout(body, 1)
        self.tabs.currentChanged.connect(self._workspace_page_changed)
        return shell

    def _navigate(self, item: QTreeWidgetItem, _column: int) -> None:
        target = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(target, int):
            self.tabs.setCurrentIndex(target)
        elif target == "thrust":
            self._open_calibration()
            self._workspace_page_changed(self.tabs.currentIndex())
        elif target == "pressure":
            self._open_pressure_calibration()
            self._workspace_page_changed(self.tabs.currentIndex())

    def _workspace_page_changed(self, index: int) -> None:
        item = self._navigation_pages.get(index)
        if item is not None:
            self.navigation.setCurrentItem(item)
            self.page_title.setText(item.text(0))

    def _toggle_console(self, expanded: bool) -> None:
        self.event_console.setVisible(expanded)
        self.console_toggle.setText("▾ 콘솔" if expanded else "▸ 콘솔")

    def _build_dashboard(self) -> QWidget:
        page = QWidget()
        page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        layout = QVBoxLayout(page)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        layout.setContentsMargins(14, 8, 14, 8)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        grid.addWidget(self._build_signal_panel(0, DEFAULT_LIVE_CHANNELS[0]), 0, 0)
        grid.addWidget(self._build_signal_panel(1, DEFAULT_LIVE_CHANNELS[1]), 0, 1)
        grid.addWidget(self._build_pipeline_status_panel(), 1, 0)
        grid.addWidget(self._build_session_control_panel(), 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 5)
        grid.setRowStretch(1, 3)
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
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        return scroll

    def _build_signal_panel(self, index: int, default_channel: str) -> QGroupBox:
        box = QGroupBox(f"신호 {index + 1:02d}")
        box.setObjectName(f"live-data-panel-{index}")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 6, 10, 8)

        selection = QHBoxLayout()
        selector = QComboBox()
        selector.setObjectName(f"signal-selector-{index}")
        for channel_name in DEFAULT_LIVE_CHANNELS:
            selector.addItem(self._channel_option_label(channel_name), channel_name)
        selector.setCurrentIndex(max(0, selector.findData(default_channel)))
        selector.setMinimumWidth(170)
        selection.addWidget(selector)
        selection.addStretch()
        layout.addLayout(selection)

        metrics = QHBoxLayout()
        current = QLabel("--")
        peak = QLabel("--")
        range_label = QLabel(box)
        range_label.hide()
        for caption, value in (("현재값", current), ("세션 최대", peak)):
            column = QVBoxLayout()
            column.setSpacing(0)
            label = QLabel(caption)
            label.setProperty("role", "metric-caption")
            value.setProperty("role", "metric")
            column.addWidget(label)
            column.addWidget(value)
            metrics.addLayout(column, 1)
        layout.addLayout(metrics)

        plot = pg.PlotWidget()
        plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        plot.setBackground(PLOT)
        plot.setMinimumHeight(125)
        plot.showGrid(x=True, y=True, alpha=0.14)
        plot.setMenuEnabled(False)
        plot.hideButtons()
        for position in ("left", "bottom"):
            axis = plot.getAxis(position)
            axis.setPen(pg.mkPen("#646975"))
            axis.setTextPen(pg.mkPen(MUTED))
            tick_font = QFont("Noto Sans", 10)
            tick_font.setPixelSize(13)
            axis.setTickFont(tick_font)
        plot.getAxis("left").setWidth(78)
        plot.getAxis("bottom").setHeight(44)
        # Keep the operator-facing clock in plain seconds.  Otherwise
        # pyqtgraph abbreviates an accidentally large sample index as Ts/Ys.
        plot.getAxis("bottom").enableAutoSIPrefix(False)
        plot.setXRange(0.0, PLOT_HISTORY_SECONDS, padding=0.0)
        curve = plot.plot(pen=pg.mkPen(CYAN, width=2))
        curve.setClipToView(True)
        curve.setDownsampling(auto=True, method="peak")
        layout.addWidget(plot, 1)

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
        status_box = QGroupBox("시스템 상태")
        status_layout = QVBoxLayout(status_box)
        status_layout.setContentsMargins(10, 6, 10, 8)

        self.state_label = QLabel("STATUS: DISCONNECTED")
        self.state_label.setObjectName("session-state")
        status_layout.addWidget(self.state_label)

        self.pipeline_summary = QLabel(status_box)
        self.pipeline_summary.hide()

        acquisition = QGridLayout()
        self.sample_rate = QLabel("-- S/s")
        self.t_plus = QLabel("Pre-trigger")
        self.data_window = QLabel("-- samples")
        for value in (self.sample_rate, self.t_plus, self.data_window):
            value.setStyleSheet("font-weight: bold;")
        acquisition.addWidget(QLabel("취득 속도"), 0, 0)
        acquisition.addWidget(QLabel("T+"), 0, 1)
        acquisition.addWidget(QLabel("버퍼"), 0, 2)
        acquisition.addWidget(self.sample_rate, 1, 0)
        acquisition.addWidget(self.t_plus, 1, 1)
        acquisition.addWidget(self.data_window, 1, 2)
        status_layout.addLayout(acquisition)

        component_layout = QGridLayout()
        for index, name in enumerate(
            ("Nano", "LAN", "SSH", "Pi", "DAQ", "Logger", "Disk")
        ):
            label = QLabel()
            label.setMinimumHeight(32)
            self._status_labels[name] = label
            self._set_status(name, "Inactive", "GRAY")
            row, column = divmod(index, 3)
            component_layout.addWidget(label, row, column)
        status_layout.addLayout(component_layout)

        self.pipeline_message = QLabel("")
        self.pipeline_message.setWordWrap(True)
        self.pipeline_message.setObjectName("pipeline-event")
        self.pipeline_message.setMaximumHeight(52)
        status_layout.addWidget(self.pipeline_message)
        status_layout.addStretch()
        return status_box

    def _build_session_control_panel(self) -> QGroupBox:
        box = QGroupBox("측정 제어")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 6, 10, 8)

        self.test_name = QLineEdit("KNSB_TEST_001")
        self.test_name.setPlaceholderText("시험명")
        layout.addWidget(QLabel("시험명"))
        layout.addWidget(self.test_name)

        controls = QHBoxLayout()
        self.start_button = QPushButton("측정 준비")
        self.start_button.setProperty("role", "primary")
        self.start_button.setMinimumHeight(30)
        self.start_button.setEnabled(False)
        self.stop_button = QPushButton("측정 종료")
        self.stop_button.setProperty("role", "stop")
        self.stop_button.setMinimumHeight(30)
        self.stop_button.setEnabled(False)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        layout.addLayout(controls)

        self.calibration_button = QPushButton("AI0 로드셀 보정")
        self.calibration_button.setToolTip(
            "실행 전 AI0 원시값을 취득해 2점 또는 3점 질량 보정을 저장합니다"
        )

        self.pressure_calibration_button = QPushButton("AI1 압력 보정")
        self.pressure_calibration_button.setToolTip(
            "실행 전 AI1 원시값을 취득해 2점 또는 3점 기준압력 보정을 저장합니다"
        )
        calibrations = QHBoxLayout()
        calibrations.addWidget(self.calibration_button)
        calibrations.addWidget(self.pressure_calibration_button)
        layout.addLayout(calibrations)

        self.daq_reset_button = QPushButton("DAQ 초기화")
        self.daq_reset_button.setEnabled(False)
        self.daq_reset_button.setToolTip(
            "측정 전 USB-4704 드라이버/USB 장치를 재초기화하고 /dev/daq0을 복구합니다"
        )
        layout.addWidget(self.daq_reset_button)
        layout.addWidget(self._make_log_directory_button())

        layout.addStretch(1)

        self.start_button.clicked.connect(self._start_session)
        self.stop_button.clicked.connect(self._stop_session)
        self.calibration_button.clicked.connect(self._open_calibration)
        self.pressure_calibration_button.clicked.connect(self._open_pressure_calibration)
        self.daq_reset_button.clicked.connect(self._reset_daq)
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
        panel.plot.setTitle(display.label, color=MUTED, size="13px")
        panel.plot.plotItem.titleLabel.hide()
        axis_style = {"color": MUTED, "font-size": "14px"}
        panel.plot.setLabel("left", display.unit, **axis_style)
        panel.plot.setLabel("bottom", "시간 (s)", **axis_style)
        panel.curve.setPen(pg.mkPen(display.color, width=2))
        panel.current.setStyleSheet(f"color: {display.color};")
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
        # Connection/calibration details belong in Setup, not the live view.
        if hasattr(self, "low_pass_info"):
            self.low_pass_info.setText(
                f"이동평균 {DEFAULT_MOVING_WINDOW_SAMPLES}샘플 "
                f"({DEFAULT_MOVING_WINDOW_SAMPLES / self.config.daq.sample_rate * 1000:g} ms)"
            )

    def _build_setup(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 12, 18, 18)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(18)
        network_box = QGroupBox("연결")
        network_form = QFormLayout(network_box)
        network_form.setVerticalSpacing(16)
        network_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        daq_box = QGroupBox("데이터 수집")
        daq_form = QFormLayout(daq_box)
        daq_form.setVerticalSpacing(16)
        storage_box = QGroupBox("저장")
        storage_form = QFormLayout(storage_box)
        storage_form.setVerticalSpacing(16)
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
        self.low_pass_info = QLabel()
        self._update_quick_settings_summary()
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
        if self.fixed_connection or self.local_daq:
            for widget in (
                self.pi_host,
                self.telemetry_port,
                self.ssh_port,
                self.ssh_id,
                self.ssh_password,
                self.remember_password,
            ):
                widget.setEnabled(False)
        for label, widget in (
            ("Pi 주소", self.pi_host),
            ("Telemetry 포트", self.telemetry_port),
            ("SSH 포트", self.ssh_port),
            ("사용자", self.ssh_id),
            ("비밀번호", self.ssh_password),
            ("", self.remember_password),
            ("Nano 포트", self.nano_port),
        ):
            if self.local_daq and widget in (self.ssh_port, self.ssh_id, self.ssh_password, self.remember_password):
                widget.hide()
                continue
            network_form.addRow("DAQ 주소" if self.local_daq and widget is self.pi_host else label, widget)
        self.sample_rate_setup.setSuffix(" S/s")
        self.block_ms.setSuffix(" ms")
        for label, widget in (
            ("취득 속도", self.sample_rate_setup),
            ("블록 시간", self.block_ms),
            ("표시 · CSV · 분석 필터", self.low_pass_info),
            ("로드셀 · AI0", self.thrust_channel),
            ("압력 · AI1", self.pressure_channel),
            ("션트 저항", QLabel(f"{self.config.pressure_input.shunt_ohms:g} Ω")),
        ):
            daq_form.addRow(label, widget)
        storage_form.addRow("저장 폴더", self.log_directory)
        storage_actions = QHBoxLayout()
        storage_actions.addWidget(self._make_log_directory_button())
        self.apply_log_directory_button = QPushButton("저장 위치 적용")
        self.apply_log_directory_button.clicked.connect(self._apply_log_directory)
        storage_actions.addWidget(self.apply_log_directory_button)
        storage_form.addRow(storage_actions)
        storage_form.addRow(QLabel("GUI가 실행되는 이 PC에 HDF5·CSV를 저장합니다."))
        storage_form.addRow("로그", QLabel("HDF5 · CSV · 원본 + 80샘플 이동평균"))
        grid.addWidget(network_box, 0, 0, 2, 1)
        grid.addWidget(daq_box, 0, 1)
        grid.addWidget(storage_box, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(2, 1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        save_button = QPushButton("설정 저장 및 재연결")
        save_button.setProperty("role", "primary")
        save_button.clicked.connect(self._save_setup)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(save_button)
        layout.addLayout(buttons)
        return page

    def _build_system_test(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.system_test_button = QPushButton("전체 시스템 점검")
        self.system_test_table = QTableWidget(0, 3)
        self.system_test_table.setHorizontalHeaderLabels(("항목", "결과", "상세"))
        self.system_test_table.verticalHeader().hide()
        self.system_test_table.verticalHeader().setDefaultSectionSize(42)
        self.system_test_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.system_test_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.system_test_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.system_test_button.setProperty("role", "primary")
        layout.addWidget(self.system_test_button)
        layout.addWidget(self.system_test_table)
        self.system_test_button.clicked.connect(self._run_system_test)
        return page

    def _build_logs(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.saved_log_directory = QLineEdit(str(self.config.logging.directory.resolve()))
        self.saved_log_directory.setReadOnly(True)
        location = QHBoxLayout()
        location.addWidget(QLabel("로그 저장 위치"))
        location.addWidget(self.saved_log_directory, 1)
        location.addWidget(self._make_log_directory_button())
        layout.addLayout(location)
        self.log_list = QListWidget()
        buttons = QHBoxLayout()
        refresh = QPushButton("새로고침")
        open_folder = QPushButton("폴더 열기")
        export = QPushButton("CSV 내보내기")
        self.analysis_button = QPushButton("결과 분석")
        fetch = QPushButton("DAQ 원본 로그 가져오기" if self.local_daq else "Pi 로그 가져오기")
        for button in (refresh, open_folder, export, fetch, self.analysis_button):
            buttons.addWidget(button)
        self.advanced_log = QTextEdit()
        self.advanced_log.setReadOnly(True)
        self.advanced_log.document().setMaximumBlockCount(500)
        layout.addWidget(self.log_list, 1)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("이벤트"))
        layout.addWidget(self.advanced_log, 1)
        refresh.clicked.connect(self._refresh_logs)
        open_folder.clicked.connect(self._open_log_folder)
        export.clicked.connect(self._export_selected_log)
        fetch.clicked.connect(self._fetch_pi_log)
        self.analysis_button.clicked.connect(self._analyze_selected_log)
        self.log_list.itemDoubleClicked.connect(self._analyze_selected_log)
        return page

    def _connect_signals(self) -> None:
        self._signals.connection.connect(self._connection_changed)
        self._signals.block.connect(self._receive_block)
        self._signals.health.connect(self._receive_health)
        self._signals.error.connect(self._show_error)
        self._signals.operation_failed.connect(self._operation_failed)
        self._signals.session_started.connect(self._session_started)
        self._signals.session_stopped.connect(self._session_stopped)
        self._signals.calibration_sampled.connect(self._calibration_sampled)
        self._signals.calibration_saved.connect(self._calibration_saved)
        self._signals.calibration_profile_loaded.connect(self._calibration_profile_loaded)
        self._signals.daq_reset_finished.connect(self._daq_reset_finished)
        self._signals.system_test_finished.connect(self._system_test_finished)
        self._signals.remote_log_downloaded.connect(self._remote_log_downloaded)
        self._signals.log_message.connect(self._append_log)
        self._signals.csv_exported.connect(self._csv_exported)

    def _start_runtime(self) -> None:
        if not self.direct_telemetry and not self.config.ssh.password:
            self._set_status("SSH", "Setup Required", "GRAY")
            self.state_label.setText("STATUS: SSH PASSWORD REQUIRED")
            self._append_log("Setup에서 SSH Password를 입력하십시오.")
            self._runtime = None
            return
        self._runtime = BackendRuntime(
            self.config, self._signals, direct_telemetry=self.direct_telemetry,
            local_daq=self.local_daq
        )
        self._runtime.start()

    def _start_session(self) -> None:
        if self._session_operation or self._daq_reset_in_progress or self._daq_recovery_required:
            return
        name = self.test_name.text().strip()
        if not name:
            QMessageBox.warning(self, "시험명 필요", "Test Name을 입력하십시오.")
            return
        assert self._runtime is not None
        # Clear immediately on the operator action, rather than waiting for
        # the asynchronous START_SESSION acknowledgement.
        self._clear_graphs()
        self._active_session_id = None
        self._session_operation = "start"
        self._update_daq_reset_button()
        self.state_label.setText("STATUS: STARTING")
        self._runtime.start_session(name)

    def _stop_session(self) -> None:
        if self._session_operation or self._daq_reset_in_progress:
            return
        assert self._runtime is not None
        self._session_operation = "stop"
        self._update_daq_reset_button()
        self.state_label.setText("STATUS: STOPPING")
        self._runtime.stop_session()

    def _open_calibration(self) -> None:
        if self._runtime is None:
            QMessageBox.warning(
                self, "연결 대기", "Pi telemetry 연결이 준비된 뒤 보정하십시오."
            )
            return
        if self._session_operation or self._daq_reset_in_progress or self._agent_state in ("RECORDING", "TRIGGERED"):
            QMessageBox.warning(
                self, "측정 중", "측정을 종료한 뒤에만 실행 전 캘리브레이션을 할 수 있습니다."
            )
            return
        dialog = LoadCellCalibrationDialog(
            current_scale=self.config.thrust.scale,
            current_offset=self.config.thrust.offset,
            parent=self,
        )
        dialog.load_requested.connect(self._load_calibration_profile)
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
        if self._session_operation or self._daq_reset_in_progress or self._agent_state in ("RECORDING", "TRIGGERED"):
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
        dialog.load_requested.connect(self._load_calibration_profile)
        dialog.capture_requested.connect(self._capture_calibration_sample)
        dialog.save_requested.connect(self._save_pressure_calibration)
        self._calibration_dialog = dialog
        dialog.exec()
        self._calibration_dialog = None

    def _reset_daq(self) -> None:
        if self._daq_reset_in_progress or self._session_operation:
            return
        if self._runtime is None:
            QMessageBox.warning(
                self, "연결 대기", "Dashboard 백엔드가 준비된 뒤 DAQ를 초기화하십시오."
            )
            return
        if self._agent_state in ("RECORDING", "TRIGGERED") and not self._daq_recovery_required:
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
        self._daq_recovery_required = not bool(result.get("daq_ready"))
        details = str(result.get("details", "")).strip()
        if bool(result.get("daq_ready")):
            self._agent_state = "READY"
            self.state_label.setText("STATUS: READY")
            self._append_log("DAQ 초기화 완료: 실제 입력 취득·종료 및 Pi 연결 검증 통과.")
        else:
            self.state_label.setText("STATUS: DAQ RECOVERY REQUIRED")
            self._append_log(
                "DAQ 초기화 실패: 입력 취득 검증을 통과하지 못했습니다. USB 전원·케이블을 확인하십시오."
            )
        if details:
            self.pipeline_message.setToolTip(details)
        self._update_daq_reset_button()

    def _capture_calibration_sample(self, row: int, duration_ms: int) -> None:
        if self._runtime is None:
            if self._calibration_dialog is not None:
                self._calibration_dialog.operation_failed("Pi telemetry 연결이 없습니다")
            return
        if self._session_operation or self._daq_reset_in_progress:
            return
        self._session_operation = "calibration"
        self._update_daq_reset_button()
        self._runtime.capture_calibration_sample(row=row, duration_ms=duration_ms)

    def _calibration_sampled(self, result: dict[str, Any]) -> None:
        self._session_operation = None
        self._update_daq_reset_button()
        if self._calibration_dialog is not None:
            self._calibration_dialog.record_capture(result)

    def _load_calibration_profile(self, kind: str, token: str) -> None:
        if self._runtime is None:
            if self._calibration_dialog is not None:
                self._calibration_dialog.operation_failed("DAQ PC 연결이 없습니다")
            return
        self._runtime.load_calibration_profile(kind, token)

    def _calibration_profile_loaded(self, result: dict[str, Any]) -> None:
        dialog = self._calibration_dialog
        if dialog is None or result.get("_profile_token") != dialog.profile_token:
            return
        if dialog.profile_loaded(result):
            self._calibration_saved(result, notify_dialog=False)

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

    def _calibration_saved(self, result: dict[str, Any], *, notify_dialog: bool = True) -> None:
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
        if notify_dialog and self._calibration_dialog is not None:
            self._calibration_dialog.calibration_saved(result)

    def _session_started(self, result: dict[str, Any]) -> None:
        self._session_operation = None
        self._agent_state = "RECORDING"
        self._active_session_id = result.get("session_id")
        self._clear_graphs()
        self.state_label.setText("STATUS: RECORDING")
        self.stop_button.setEnabled(True)
        self._update_daq_reset_button()
        self._append_log(f"Session started: {result.get('log_file', '')}")

    def _session_stopped(self, result: dict[str, Any]) -> None:
        self._session_operation = None
        self._agent_state = "COMPLETE"
        self.state_label.setText("STATUS: COMPLETE")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._update_daq_reset_button()
        self._append_log(f"Session stopped: {result.get('log_file', '')}")
        self._refresh_logs()

    def _receive_block(self, block: TelemetryBlock) -> None:
        if self._session_operation == "start" or self._daq_reset_in_progress:
            return
        if block.session_id is not None and block.session_id != self._active_session_id:
            return
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
            f"{len(self._sample_indices):,} samples"
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
        self._agent_state = state
        if status.get("recovery_required"):
            self._daq_recovery_required = True
        if not self._session_operation and not self._daq_reset_in_progress:
            self.state_label.setText(
                "STATUS: DAQ RECOVERY REQUIRED" if self._daq_recovery_required
                else f"STATUS: {state}"
            )
        if not self._session_operation and not self._daq_reset_in_progress:
            self._active_session_id = status.get("session_id")
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
        self._update_daq_reset_button()
        self._update_pipeline_summary()

    def _connection_changed(self, component: str, status: str) -> None:
        self._connection_states[component] = status
        if component in self._status_labels:
            self._health_status(component, status)
        if component == "Pi" and status == "CONNECTED":
            self._set_status("LAN", "Connected", "GREEN")
        self._update_daq_reset_button()
        if component == "Trigger":
            # Transport/arming notices are not proof that Pi stored an event.
            sample = status.removeprefix("SAMPLE ")
            if (
                status.startswith("SAMPLE ") and sample.isdecimal()
                and not self._session_operation and not self._daq_reset_in_progress
                and self._agent_state in ("RECORDING", "TRIGGERED")
            ):
                self._trigger_sample = int(sample)
                self._agent_state = "TRIGGERED"
                self._last_plot_update = 0.0
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
                "로컬 DAQ 서비스 연결을 기다리는 중입니다." if self.local_daq else "SSH 터널과 Pi telemetry 연결을 기다리는 중입니다."
            )

    def _update_daq_reset_button(self) -> None:
        if not hasattr(self, "daq_reset_button"):
            return
        busy = self._session_operation is not None or self._daq_reset_in_progress
        recording = self._agent_state in ("RECORDING", "TRIGGERED")
        connected = self._runtime is not None and self._connection_states.get("Pi") == "CONNECTED"
        self.start_button.setEnabled(
            connected and not busy and not recording and not self._daq_recovery_required
            and self._agent_state in ("READY", "COMPLETE")
        )
        self.stop_button.setEnabled(connected and not busy and recording and not self._daq_recovery_required)
        self.daq_reset_button.setEnabled(
            self._runtime is not None
            and not busy
            and (not recording or self._daq_recovery_required)
        )

    def _health_status(self, component: str, value: str) -> None:
        upper = value.upper().split(" / ", 1)[0]
        if upper in (
            "CONNECTED",
            "RUNNING",
            "RECORDING",
            "READY",
            "AVAILABLE",
            "OK",
            "COMPLETE",
            "ARMED",
            "TRIGGERED",
        ):
            color = "GREEN"
        elif (
            "RECONNECT" in upper
            or "TIMEOUT" in upper
            or upper in ("STARTING", "LOW", "BYPASSED", "ARMING", "IGNITION_HIGH")
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
        names = {"Pi": "DAQ PC" if self.local_daq else "Pi", "Logger": "기록", "Disk": "저장공간"}
        if self.local_daq:
            names.update(LAN="로컬 연결", SSH="연결 방식")
        states = {
            "CONNECTED": "연결됨", "DISCONNECTED": "연결 끊김",
            "CONNECTING": "연결 중", "RECONNECTING": "재연결 중",
            "RUNNING": "취득 중", "RECORDING": "기록 중", "READY": "준비됨",
            "AVAILABLE": "준비됨", "OK": "정상", "COMPLETE": "완료",
            "UNKNOWN": "대기", "INACTIVE": "대기", "NOT_FOUND": "미연결",
            "NOT FOUND": "미연결", "TIMEOUT": "시간 초과", "FAILED": "오류",
            "INITIALIZING": "초기화 중", "STARTING": "시작 중", "LOW": "부족",
            "BYPASSED": "로컬", "MISSING": "미연결", "ERROR": "오류",
            "ARMED": "점화 감지 대기", "ARMING": "점화 감지 준비 중",
            "IGNITION_HIGH": "점화 입력 HIGH",
        }
        state, separator, level = text.upper().partition(" / ")
        display = states.get(state, state.replace("_", " "))
        if separator:
            display += f" / {level}"
        label.setText(f"{names.get(component, component)}  {display}")
        label.setToolTip(f"{component}: {text}")
        label.setStyleSheet(
            f"color: {STATUS_COLORS[color]}; background: #2e3035; "
            f"border-left: 2px solid {STATUS_COLORS[color]}; padding: 5px 8px;"
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
                    directory=prepare_log_directory(self.log_directory.text()),
                    ring_buffer_sec=self.config.logging.ring_buffer_sec,
                    flush_interval_sec=self.config.logging.flush_interval_sec,
                    pi_directory=self.config.logging.pi_directory,
                ),
            )
            if self.local_daq:
                new_config = replace(new_config, system=replace(new_config.system, pi_host="127.0.0.1"))
            if self.fixed_connection:
                new_config = apply_field_connection(new_config)
            save_config(new_config, self.config_path)
        except (ConfigError, ValueError, OSError) as exc:
            QMessageBox.critical(self, "설정 오류", str(exc))
            return
        if self._runtime is not None:
            self._runtime.stop()
        self.config = new_config
        self._update_log_directory_display()
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

    def _make_log_directory_button(self) -> QPushButton:
        button = QPushButton("저장 폴더 선택")
        button.setToolTip(f"현재 로그 저장 위치: {self.config.logging.directory.resolve()}")
        button.clicked.connect(self._choose_log_directory)
        self._log_directory_buttons.append(button)
        return button

    def _choose_log_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "HDF5·CSV 로그 저장 폴더 선택", str(self.config.logging.directory.resolve())
        )
        if directory:
            self._save_log_directory(directory)

    def _apply_log_directory(self) -> None:
        self._save_log_directory(self.log_directory.text())

    def _save_log_directory(self, value: str | Path) -> None:
        try:
            directory = prepare_log_directory(value)
            updated = replace(self.config, logging=replace(self.config.logging, directory=directory))
            save_config(updated, self.config_path)
        except (ConfigError, OSError, ValueError) as exc:
            QMessageBox.warning(self, "로그 저장 위치", f"저장 위치를 변경할 수 없습니다: {exc}")
            return
        self.config = updated
        if self._runtime is not None:
            self._runtime.set_log_directory(directory)
        self._update_log_directory_display()
        self._refresh_logs()
        self._append_log(f"로그 저장 위치 설정 완료: {directory} · 다음 저장부터 적용")
        self.statusBar().showMessage(f"로그 저장 위치를 저장했습니다: {directory}", 8000)

    def _update_log_directory_display(self) -> None:
        directory = str(self.config.logging.directory.resolve())
        self.log_directory.setText(directory)
        self.saved_log_directory.setText(directory)
        for button in self._log_directory_buttons:
            button.setToolTip(f"현재 로그 저장 위치: {directory}")

    def _open_log_folder(self) -> None:
        self.config.logging.directory.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(self.config.logging.directory.resolve()))
        )

    def _analyze_selected_log(self, *_args: object) -> None:
        row = self.log_list.currentRow()
        if 0 <= row < len(self._sessions):
            source = self._sessions[row].path
        else:
            filename, _ = QFileDialog.getOpenFileName(
                self, "결과 분석 파일 열기", str(self.config.logging.directory),
                "TMS 로그 (*.h5 *.csv)",
            )
            if not filename:
                return
            source = Path(filename)
        try:
            data = read_analysis_data(source)
        except LogError as exc:
            QMessageBox.warning(self, "결과 분석", str(exc))
            return
        ResultAnalysisDialog(data, self).exec()

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
        if self._runtime is None:
            self._operation_failed("save", "Dashboard 백엔드가 아직 준비되지 않았습니다.")
            return
        self._runtime.export_log(session.path, destination)

    def _fetch_pi_log(self) -> None:
        if self._runtime is None:
            QMessageBox.warning(
                self, "연결 대기", "Dashboard 백엔드가 아직 연결되지 않았습니다."
            )
            return
        row = self.log_list.currentRow()
        selected = self._sessions[row].path.name if 0 <= row < len(self._sessions) else None
        self._runtime.fetch_latest_remote_log(selected)

    def _remote_log_downloaded(self, path: str) -> None:
        self._append_log(f"DAQ log saved: {path}")
        self._refresh_logs()

    def _csv_exported(self, path: str) -> None:
        self._append_log(f"CSV saved: {path}")

    def _show_error(self, message: str) -> None:
        # Background reconnects are status events, not modal operator actions.
        # In particular they must not end an in-flight DAQ recovery.
        self._append_log(f"ERROR: {message}")
        if "DAQ 초기화" in message and not self._daq_reset_in_progress:
            # A bounded Pi-side hardware operation has detected a wedged USB
            # ioctl. Keep Start disabled so a late command cannot surprise the
            # operator; the reset button remains available even if telemetry
            # itself is no longer responsive.
            self.state_label.setText("STATUS: DAQ RECOVERY REQUIRED")
            self._daq_recovery_required = True
            self._update_daq_reset_button()

    def _operation_failed(self, operation: str, message: str) -> None:
        if operation in ("start", "stop", "calibration"):
            self._session_operation = None
        if operation == "reset":
            self._daq_reset_in_progress = False
            self._daq_recovery_required = True
        if operation == "calibration" and self._calibration_dialog is not None:
            self._calibration_dialog.operation_failed(message)
        if operation in ("start", "stop", "calibration") and "timed out" in message.lower():
            self._daq_recovery_required = True
        self._show_error(message)
        self._update_daq_reset_button()
        if self._daq_recovery_required:
            self.state_label.setText("STATUS: DAQ RECOVERY REQUIRED")
        if operation == "calibration" and self._calibration_dialog is not None:
            # The calibration dialog is already modal and shows this error
            # inline. A second window parented to the main window would be
            # blocked by that dialog and appear impossible to dismiss.
            return
        # A single modeless dialog: no nested exec() loop, stacked alarms or
        # disabled X button. Closing it does not cancel the background command.
        if self._error_dialog is None:
            self._error_dialog = QMessageBox(self)
            self._error_dialog.setWindowTitle("TMS 오류")
            self._error_dialog.setIcon(QMessageBox.Icon.Critical)
            self._error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
            self._error_dialog.setModal(False)
        self._error_dialog.setText(message)
        self._error_dialog.show()

    def _append_log(self, message: str) -> None:
        if hasattr(self, "advanced_log"):
            self.advanced_log.append(message)
        if hasattr(self, "event_console"):
            self.event_console.append(message)
        if hasattr(self, "pipeline_message"):
            if message.startswith(("Nano:", "LAN:", "SSH:", "Pi:", "Trigger:")):
                return
            # The full text remains available in the console and tooltip.
            self.pipeline_message.setText(message.splitlines()[0][:110])
            self.pipeline_message.setToolTip(message)

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
            self.data_window.setText("-- samples")

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
