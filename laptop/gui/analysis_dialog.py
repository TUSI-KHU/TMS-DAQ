"""Offline result viewer; plots the same 80-sample means saved to CSV."""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from laptop.analysis import AnalysisData
from laptop.gui.theme import AMBER, CYAN, apply_theme


class ResultAnalysisDialog(QDialog):
    def __init__(self, data: AnalysisData, parent=None) -> None:
        super().__init__(parent)
        apply_theme(self)
        self.setWindowTitle('결과 분석 · 이동평균')
        self.resize(1100, 740)
        layout = QVBoxLayout(self)
        label = QLabel(f'{data.path.name}\n{data.window_samples}샘플 이동평균 · {len(data.time_s):,} samples · {data.time_reference}')
        label.setWordWrap(True)
        layout.addWidget(label)
        self.curves = []
        gaps = np.flatnonzero(np.diff(data.sample_indices) != 1) + 1
        for title, unit, values, color in (
            ('추력', 'N', data.thrust_N, CYAN), ('압력', 'bar', data.pressure_bar, AMBER)
        ):
            plot = pg.PlotWidget()
            plot.setLabel('left', title, units=unit)
            plot.setLabel('bottom', '시간', units='s')
            plot.showGrid(x=True, y=True, alpha=.2)
            signal = values.copy()
            signal[gaps] = np.nan
            curve = plot.plot(data.time_s, signal, pen=pg.mkPen(color, width=2), connect='finite')
            curve.setDownsampling(auto=True, method='peak')
            self.curves.append(curve)
            layout.addWidget(plot, 1)
            finite = values[np.isfinite(values)]
            layout.addWidget(QLabel(f'{title} · 최대 {np.max(finite):.4g} {unit} · 평균 {np.mean(finite):.4g} {unit}'
                                    if len(finite) else f'{title}: 데이터 없음'))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
