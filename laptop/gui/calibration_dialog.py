"""Operator dialog for an idle, fixed-AI0 load-cell calibration."""

from __future__ import annotations

from typing import Any

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

from laptop.calibration import (
    CalibrationError,
    CalibrationReference,
    LoadCellCalibration,
    fit_load_cell_calibration,
)


class LoadCellCalibrationDialog(QDialog):
    """Collect two or three stable AI0 references and persist their fit."""

    capture_requested = Signal(int, int)
    save_requested = Signal(float, float)

    def __init__(
        self, *, current_scale: float, current_offset: float, parent=None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI0 로드셀 실행 전 캘리브레이션")
        self.setMinimumWidth(760)
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
        intro = QLabel(
            "AI0은 CAS BCL-50L 로드셀로 고정되어 있습니다. 실제 장착 지그를 "
            "포함한 상태에서, 각 기준 질량을 올린 뒤 안정화된 원시 ADC 평균을 "
            "취득합니다. 이 과정은 짧게 AI만 읽고 Trigger/AO/DO는 동작시키지 않습니다."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        warning = QLabel(
            "센서/앰프 전원이 켜지고 배선이 확인된 뒤 실행하십시오. "
            "전원이 꺼진 현재 상태의 값은 보정값으로 저장하면 안 됩니다."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #da1e28; font-weight: bold;")
        layout.addWidget(warning)

        settings = QFormLayout()
        self.point_count = QComboBox()
        self.point_count.addItem("2점 보정 (두 기준 질량)", 2)
        self.point_count.addItem("3점 보정 (세 기준 질량 · 최소제곱)", 3)
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
        self.reference_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.reference_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.reference_table)

        action_layout = QGridLayout()
        self.calculate_button = QPushButton("보정값 계산")
        self.apply_button = QPushButton("AI0 보정값을 Pi에 저장")
        self.apply_button.setEnabled(False)
        action_layout.addWidget(self.calculate_button, 0, 0)
        action_layout.addWidget(self.apply_button, 0, 1)
        layout.addLayout(action_layout)

        self.result_label = QLabel(
            "현재 AI0 설정: "
            f"scale={current_scale:.9g} N/count, offset={current_offset:.9g} N"
        )
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet(
            "background: #edf5ff; border-radius: 4px; padding: 8px; color: #0043ce;"
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
        self._captured.clear()
        self._fit = None
        self._pending_row = None
        self._mass_fields.clear()
        self._mean_labels.clear()
        self._stddev_labels.clear()
        self._capture_buttons.clear()
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
        self._mean_labels[row].setText(f"{mean:.3f} count ({sample_count:,} samples)")
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
            "계산 완료. 정상 장착·안정된 상태인지 확인한 뒤 Pi 저장을 누르십시오."
        )

    def _request_save(self) -> None:
        if self._fit is None or self._saving:
            return
        self._saving = True
        self.apply_button.setEnabled(False)
        self.status_label.setText("Pi 설정 파일에 AI0 보정값을 저장하는 중…")
        self.save_requested.emit(self._fit.scale_N_per_count, self._fit.offset_N)

    def calibration_saved(self, result: dict[str, Any]) -> None:
        self._saving = False
        thrust = result.get("thrust", {})
        self.status_label.setText(
            "저장 완료. 다음 측정 세션과 HDF5 로그에 이 AI0 보정값이 적용됩니다. "
            f"(AI{thrust.get('channel', 0)})"
        )
        self.apply_button.setEnabled(self._fit is not None)

    def operation_failed(self, message: str) -> None:
        if self._pending_row is not None:
            self._capture_buttons[self._pending_row].setEnabled(True)
        self._pending_row = None
        self._saving = False
        self.apply_button.setEnabled(self._fit is not None)
        self.status_label.setText(f"작업 실패: {message}")
