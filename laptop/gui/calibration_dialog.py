"""Operator dialog for an idle, fixed-AI0 load-cell calibration."""

from __future__ import annotations

from typing import Any
from math import isfinite
from uuid import uuid4

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from common.pressure import raw_code_to_current_mA, raw_code_to_voltage
from laptop.calibration import (
    CalibrationError,
    CalibrationReference,
    LoadCellCalibration,
    PressureCalibrationReference,
    fit_load_cell_calibration,
    fit_pressure_calibration,
)
from laptop.gui.theme import apply_theme


class LoadCellCalibrationDialog(QDialog):
    """Collect two or three stable AI0 references and persist their fit."""

    profile_kind = "thrust"
    load_requested = Signal(str, str)
    capture_requested = Signal(int, int)
    save_requested = Signal(float, float)

    def __init__(
        self, *, current_scale: float, current_offset: float, parent=None
    ) -> None:
        super().__init__(parent)
        apply_theme(self)
        self.setWindowTitle("AI0 로드셀 실행 전 캘리브레이션")
        self.setMinimumWidth(880)
        self.profile_token = uuid4().hex
        self._loaded_values = None
        self._current_scale = current_scale
        self._current_offset = current_offset
        self._captured: dict[int, dict[str, float | int]] = {}
        self._mass_fields: list[QDoubleSpinBox] = []
        self._mean_labels: list[QLabel] = []
        self._stddev_labels: list[QLabel] = []
        self._capture_buttons: list[QPushButton] = []
        self._pending_row: int | None = None
        self._saving = False
        self._fit: LoadCellCalibration | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        intro = QLabel(
            "AI0 · CAS BCL-50L  |  기준 질량을 올리고 안정화 후 취득"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        warning = QLabel(
            "취득 전 센서·앰프 전원을 켜십시오."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #ffc43d;")
        layout.addWidget(warning)

        settings = QFormLayout()
        self.point_count = QComboBox()
        self.point_count.addItem("2점 보정", 2)
        self.point_count.addItem("3점 보정", 3)
        self.capture_duration = QSpinBox()
        self.capture_duration.setRange(100, 10_000)
        self.capture_duration.setValue(1_000)
        self.capture_duration.setSuffix(" ms")
        settings.addRow("기준점 수", self.point_count)
        settings.addRow("각 기준점 취득 시간", self.capture_duration)
        layout.addLayout(settings)

        self.reference_table = QTableWidget(0, 5)
        self.reference_table.setHorizontalHeaderLabels(
            ("기준점", "질량", "AI0 평균", "AI0 표준편차", "원시값 취득")
        )
        self.reference_table.verticalHeader().setVisible(False)
        self.reference_table.verticalHeader().setDefaultSectionSize(54)
        self.reference_table.setMinimumHeight(220)
        self.reference_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.reference_table.horizontalHeader()
        header.setMinimumSectionSize(80)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.reference_table)

        action_layout = QGridLayout()
        self.calculate_button = QPushButton("보정값 계산")
        self.apply_button = QPushButton("설정 저장")
        self.apply_button.setProperty("role", "primary")
        self.apply_button.setEnabled(False)
        self.load_button = QPushButton("프로파일 불러오기")
        self.load_button.setToolTip("DAQ PC에 마지막 저장된 이 센서의 scale·offset을 불러옵니다")
        self.load_button.clicked.connect(self._request_load)
        action_layout.addWidget(self.load_button, 1, 0, 1, 2)
        action_layout.addWidget(self.calculate_button, 0, 0)
        action_layout.addWidget(self.apply_button, 0, 1)
        layout.addLayout(action_layout)

        self.result_label = QLabel(
            "현재 AI0 설정: "
            f"scale={current_scale:.9g} N/count, offset={current_offset:.9g} N"
        )
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet(
            "background: #252629; border: 1px solid #4a4c52; padding: 12px; color: #e8e9ed;"
        )
        layout.addWidget(self.result_label)

        self.status_label = QLabel("기준 질량을 입력하고 각 행에서 원시값 취득을 누르십시오.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.point_count.currentIndexChanged.connect(self._rebuild_reference_rows)
        self.calculate_button.clicked.connect(self._calculate)
        self.apply_button.clicked.connect(self._request_save)
        self._rebuild_reference_rows()

    @property
    def fit(self) -> LoadCellCalibration | None:
        return self._fit

    def _rebuild_reference_rows(self) -> None:
        point_count = int(self.point_count.currentData())
        defaults = (0.0, 3908.0) if point_count == 2 else (0.0, 550.0, 3908.0)
        self._loaded_values = None
        self._captured.clear()
        self._fit = None
        self._pending_row = None
        self._mass_fields.clear()
        self._mean_labels.clear()
        self._stddev_labels.clear()
        self._capture_buttons.clear()
        self.reference_table.setRowCount(0)
        self.reference_table.setRowCount(point_count)
        for row, mass_g in enumerate(defaults):
            label = QTableWidgetItem(f"기준 {row + 1}")
            self.reference_table.setItem(row, 0, label)
            mass = QDoubleSpinBox()
            mass.setRange(0.0, 100_000.0)
            mass.setDecimals(1)
            mass.setSingleStep(10.0)
            mass.setValue(mass_g)
            mass.setSuffix(" g")
            mass.valueChanged.connect(self._invalidate_fit)
            self.reference_table.setCellWidget(row, 1, mass)
            self._mass_fields.append(mass)

            mean = QLabel("미취득")
            stddev = QLabel("-")
            self.reference_table.setCellWidget(row, 2, mean)
            self.reference_table.setCellWidget(row, 3, stddev)
            self._mean_labels.append(mean)
            self._stddev_labels.append(stddev)

            capture = QPushButton("원시값 취득")
            capture.clicked.connect(
                lambda _checked=False, selected_row=row: self._request_capture(
                    selected_row
                )
            )
            self.reference_table.setCellWidget(row, 4, capture)
            self._capture_buttons.append(capture)
        self.apply_button.setEnabled(False)
        self.result_label.setText(
            "현재 AI0 설정: "
            f"scale={self._current_scale:.9g} N/count, "
            f"offset={self._current_offset:.9g} N"
        )
        self.status_label.setText("질량을 확인하고 각 행의 원시값을 취득하십시오.")

    def _invalidate_fit(self) -> None:
        self._loaded_values = None
        self._fit = None
        self.apply_button.setEnabled(False)

    def _request_capture(self, row: int) -> None:
        if self._pending_row is not None or self._saving:
            return
        self._pending_row = row
        self._capture_buttons[row].setEnabled(False)
        self.status_label.setText(
            f"기준 {row + 1} 취득 중… 물체를 움직이지 마십시오."
        )
        self.capture_requested.emit(row, self.capture_duration.value())

    def record_capture(self, result: dict[str, Any]) -> None:
        row = int(result.get("_ui_row", -1))
        if row != self._pending_row or not 0 <= row < len(self._mass_fields):
            return
        try:
            ai0 = result["channels"]["ai0"]
            sample_count = int(ai0["sample_count"])
            mean = float(ai0["mean"])
            stddev = float(ai0["stddev"])
        except (KeyError, TypeError, ValueError) as exc:
            self.operation_failed(f"AI0 취득 결과가 올바르지 않습니다: {exc}")
            return
        self._captured[row] = {
            "sample_count": sample_count,
            "mean": mean,
            "stddev": stddev,
        }
        self._mean_labels[row].setText(f"{mean:.3f} count")
        self._mean_labels[row].setToolTip(f"{sample_count:,} samples")
        self._stddev_labels[row].setText(f"σ {stddev:.3f} count")
        self._capture_buttons[row].setEnabled(True)
        self._pending_row = None
        self._invalidate_fit()
        self.status_label.setText(
            f"기준 {row + 1} 취득 완료. 다음 기준점을 취득하거나 보정값을 계산하십시오."
        )

    def _references(self) -> tuple[CalibrationReference, ...]:
        required = range(len(self._mass_fields))
        missing = [str(index + 1) for index in required if index not in self._captured]
        if missing:
            raise CalibrationError("기준점 " + ", ".join(missing) + "의 원시값이 없습니다")
        return tuple(
            CalibrationReference(
                mass_g=field.value(),
                raw_mean=float(self._captured[index]["mean"]),
                raw_stddev=float(self._captured[index]["stddev"]),
                sample_count=int(self._captured[index]["sample_count"]),
            )
            for index, field in enumerate(self._mass_fields)
        )

    def _calculate(self) -> None:
        try:
            self._fit = fit_load_cell_calibration(self._references())
        except CalibrationError as exc:
            self._fit = None
            self.apply_button.setEnabled(False)
            self.status_label.setText(f"계산 불가: {exc}")
            return
        residuals = ", ".join(f"{value:+.4f} N" for value in self._fit.residuals_N)
        r_squared = "n/a" if self._fit.r_squared is None else f"{self._fit.r_squared:.6f}"
        self.result_label.setText(
            "새 AI0 보정값: "
            f"scale={self._fit.scale_N_per_count:.9g} N/count, "
            f"offset={self._fit.offset_N:.9g} N · "
            f"RMSE={self._fit.rmse_N:.4f} N · R²={r_squared} · "
            f"잔차: {residuals}"
        )
        self.apply_button.setEnabled(True)
        self.status_label.setText(
            "계산 완료. 정상 장착·안정된 상태인지 확인한 뒤 설정 저장을 누르십시오."
        )

    def _set_busy(self, busy: bool) -> None:
        self._saving = busy
        self.load_button.setEnabled(not busy)
        self.calculate_button.setEnabled(not busy)
        self.point_count.setEnabled(not busy)
        self.reference_table.setEnabled(not busy)
        self.apply_button.setEnabled(not busy and (self._fit is not None or self._loaded_values is not None))

    def _request_load(self) -> None:
        if self._saving or self._pending_row is not None:
            return
        self._set_busy(True)
        self.status_label.setText("DAQ PC의 저장된 보정 프로파일을 불러오는 중…")
        self.load_requested.emit(self.profile_kind, self.profile_token)

    def profile_loaded(self, result: dict[str, Any]) -> bool:
        try:
            channel = result[self.profile_kind]
            scale, offset = float(channel["scale"]), float(channel["offset"])
            if not isfinite(scale) or not isfinite(offset) or scale == 0:
                raise ValueError("유효하지 않은 보정 계수")
            expected = 1 if self.profile_kind == "pressure" else 0
            if int(channel["channel"]) != expected:
                raise ValueError("센서 채널이 일치하지 않습니다")
        except (KeyError, TypeError, ValueError) as exc:
            self.operation_failed(str(exc))
            return False
        self._current_scale, self._current_offset = scale, offset
        self._rebuild_reference_rows()
        self._loaded_values = (scale, offset)
        self._set_busy(False)
        self.status_label.setText("DAQ PC의 마지막 저장 프로파일을 불러왔습니다. 기준점 재취득 없이 사용할 수 있습니다.")
        return True

    def _request_save(self) -> None:
        if self._saving or self._pending_row is not None:
            return
        if self._loaded_values is not None:
            values = self._loaded_values
        elif self._fit is not None:
            values = ((self._fit.scale_bar_per_count, self._fit.offset_bar)
                      if self.profile_kind == "pressure"
                      else (self._fit.scale_N_per_count, self._fit.offset_N))
        else:
            return
        self._set_busy(True)
        self.status_label.setText("DAQ PC에 보정 프로파일을 영구 저장하는 중…")
        self.save_requested.emit(*values)

    def calibration_saved(self, result: dict[str, Any]) -> None:
        if not self.profile_loaded(result):
            return
        self.status_label.setText("DAQ PC에 영구 저장 완료. 재시작 후에도 유지되며 다음 측정에 적용됩니다.")

    def operation_failed(self, message: str) -> None:
        if self._pending_row is not None:
            self._capture_buttons[self._pending_row].setEnabled(True)
        self._pending_row = None
        self._set_busy(False)
        self.status_label.setText(f"작업 실패: {message}")


class PressureCalibrationDialog(LoadCellCalibrationDialog):
    """Collect two or three stable AI1 pressure references and persist their fit."""

    profile_kind = "pressure"

    def __init__(
        self,
        *,
        current_scale: float,
        current_offset: float,
        shunt_ohms: float = 100.0,
        loop_min_mA: float = 4.0,
        loop_max_mA: float = 20.0,
        parent=None,
    ) -> None:
        self._shunt_ohms = float(shunt_ohms)
        self._loop_min_mA = float(loop_min_mA)
        self._loop_max_mA = float(loop_max_mA)
        super().__init__(
            current_scale=current_scale, current_offset=current_offset, parent=parent
        )
        self.setWindowTitle("AI1 압력 실행 전 캘리브레이션")
        intro = self.layout().itemAt(0).widget()
        if isinstance(intro, QLabel):
            intro.setText(
                f"AI1 · {self._loop_min_mA:g}–{self._loop_max_mA:g} mA · "
                f"{self._shunt_ohms:g} Ω  |  "
                f"{self._loop_min_mA / 1000.0 * self._shunt_ohms:.3f} V – "
                f"{self._loop_max_mA / 1000.0 * self._shunt_ohms:.3f} V"
            )
        self.reference_table.setHorizontalHeaderLabels(
            ("기준점", "기준압력", "AI1 평균 (전압/전류)", "AI1 표준편차", "원시값 취득")
        )
        self.setMinimumWidth(1000)
        self.apply_button.setText("설정 저장")

    def _rebuild_reference_rows(self) -> None:
        point_count = int(self.point_count.currentData())
        defaults = (0.0, 1.0) if point_count == 2 else (0.0, 0.5, 1.0)
        self._loaded_values = None
        self._captured.clear()
        self._fit = None
        self._pending_row = None
        self._mass_fields.clear()
        self._mean_labels.clear()
        self._stddev_labels.clear()
        self._capture_buttons.clear()
        self.reference_table.setRowCount(0)
        self.reference_table.setRowCount(point_count)
        for row, pressure_bar in enumerate(defaults):
            self.reference_table.setItem(row, 0, QTableWidgetItem(f"기준 {row + 1}"))
            pressure = QDoubleSpinBox()
            pressure.setRange(-100_000.0, 100_000.0)
            pressure.setDecimals(4)
            pressure.setSingleStep(0.1)
            pressure.setValue(pressure_bar)
            pressure.setSuffix(" bar")
            pressure.valueChanged.connect(self._invalidate_fit)
            self.reference_table.setCellWidget(row, 1, pressure)
            self._mass_fields.append(pressure)
            mean = QLabel("미취득")
            stddev = QLabel("-")
            self.reference_table.setCellWidget(row, 2, mean)
            self.reference_table.setCellWidget(row, 3, stddev)
            self._mean_labels.append(mean)
            self._stddev_labels.append(stddev)
            capture = QPushButton("원시값 취득")
            capture.clicked.connect(
                lambda _checked=False, selected_row=row: self._request_capture(selected_row)
            )
            self.reference_table.setCellWidget(row, 4, capture)
            self._capture_buttons.append(capture)
        self.apply_button.setEnabled(False)
        self.result_label.setText(
            "현재 AI1 설정: "
            f"scale={self._current_scale:.9g} bar/count, "
            f"offset={self._current_offset:.9g} bar"
        )
        self.status_label.setText("기준압력을 확인하고 각 행의 원시값을 취득하십시오.")

    def record_capture(self, result: dict[str, Any]) -> None:
        row = int(result.get("_ui_row", -1))
        if row != self._pending_row or not 0 <= row < len(self._mass_fields):
            return
        try:
            sample = result["channels"]["ai1"]
            sample_count = int(sample["sample_count"])
            mean = float(sample["mean"])
            stddev = float(sample["stddev"])
        except (KeyError, TypeError, ValueError) as exc:
            self.operation_failed(f"AI1 취득 결과가 올바르지 않습니다: {exc}")
            return
        self._captured[row] = {
            "sample_count": sample_count,
            "mean": mean,
            "stddev": stddev,
        }
        voltage = raw_code_to_voltage(mean)
        current = raw_code_to_current_mA(mean, self._shunt_ohms)
        self._mean_labels[row].setText(
            f"{mean:.3f} count\n{voltage:.4f} V / {current:.3f} mA"
        )
        self._mean_labels[row].setToolTip(f"{sample_count:,} samples")
        self._stddev_labels[row].setText(f"σ {stddev:.3f} count")
        self._capture_buttons[row].setEnabled(True)
        self._pending_row = None
        self._invalidate_fit()
        expected_min_v = self._loop_min_mA / 1000.0 * self._shunt_ohms
        expected_max_v = self._loop_max_mA / 1000.0 * self._shunt_ohms
        if not expected_min_v <= voltage <= expected_max_v:
            self.status_label.setText(
                f"기준 {row + 1} 취득 완료. 경고: {voltage:.4f} V가 "
                f"예상 {expected_min_v:.3f}–{expected_max_v:.3f} V 범위를 벗어났습니다. "
                "배선·전원·AI 입력 범위를 확인하십시오."
            )
        else:
            self.status_label.setText(
                f"기준 {row + 1} 취득 완료. 다음 기준점을 취득하거나 계산하십시오."
            )

    def _references(self) -> tuple[PressureCalibrationReference, ...]:
        missing = [
            str(index + 1)
            for index in range(len(self._mass_fields))
            if index not in self._captured
        ]
        if missing:
            raise CalibrationError("기준점 " + ", ".join(missing) + "의 원시값이 없습니다")
        return tuple(
            PressureCalibrationReference(
                pressure_bar=field.value(),
                raw_mean=float(self._captured[index]["mean"]),
                raw_stddev=float(self._captured[index]["stddev"]),
                sample_count=int(self._captured[index]["sample_count"]),
            )
            for index, field in enumerate(self._mass_fields)
        )

    def _calculate(self) -> None:
        try:
            self._fit = fit_pressure_calibration(self._references())
        except CalibrationError as exc:
            self._fit = None
            self.apply_button.setEnabled(False)
            self.status_label.setText(f"계산 불가: {exc}")
            return
        residuals = ", ".join(f"{value:+.4f} bar" for value in self._fit.residuals_bar)
        r_squared = "n/a" if self._fit.r_squared is None else f"{self._fit.r_squared:.6f}"
        self.result_label.setText(
            "새 AI1 보정값: "
            f"scale={self._fit.scale_bar_per_count:.9g} bar/count, "
            f"offset={self._fit.offset_bar:.9g} bar · "
            f"RMSE={self._fit.rmse_bar:.4f} bar · R²={r_squared} · 잔차: {residuals}"
        )
        self.apply_button.setEnabled(True)
        self.status_label.setText("계산 완료. 기준압력과 배선을 확인한 뒤 설정 저장을 누르십시오.")
