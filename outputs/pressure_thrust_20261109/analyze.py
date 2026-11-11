"""Analyze the supplied calibrated CSV without modifying the source.

Run: python3 analyze.py [source.csv]
Requires numpy, pandas, matplotlib. Times are acquisition-relative.
"""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/run/media/sb/bf4774dd-ff52-48ac-833f-348d007da982/home/sb/usb-4704 porting project/logs/2026-11-09_pin_control_6e7eeb77.csv')
OUT = Path(__file__).resolve().parent
d = pd.read_csv(SOURCE)
cols = ['time_s', 'thrust_N', 'pressure_bar', 'thrust_N_lpf', 'pressure_bar_lpf']
assert np.isfinite(d[cols].to_numpy()).all(), 'Non-finite measurement'
t = d.time_s.to_numpy()
dt = float(np.median(np.diff(t)))
assert (np.diff(t) > 0).all(), 'Non-increasing timestamps'
baseline = d[(d.time_s >= 18) & (d.time_s < 21)]
f0 = float(baseline.thrust_N_lpf.mean())
p0 = float(baseline.pressure_bar_lpf.mean())
f = d.thrust_N_lpf.to_numpy() - f0
p = d.pressure_bar_lpf.to_numpy() - p0
threshold = .05 * f.max()
edges = np.diff(np.r_[False, f > threshold, False].astype(int))
intervals = list(zip(np.where(edges == 1)[0], np.where(edges == -1)[0] - 1))
merged = []
for a, b in intervals:
    if merged and t[a] - t[merged[-1][1]] <= .03:
        merged[-1][1] = int(b)
    else:
        merged.append([int(a), int(b)])
events = []
for a, b in merged:
    if t[b] - t[a] < .02:
        continue
    sl = slice(a, b + 1)
    events.append(dict(start_s=float(t[a]), end_s=float(t[b]), duration_s=float(t[b]-t[a]),
                       peak_thrust_N=float(f[sl].max()), peak_pressure_bar=float(p[sl].max()),
                       impulse_Ns=float(np.trapezoid(f[sl], t[sl])),
                       mean_thrust_N=float(np.trapezoid(f[sl], t[sl])/(t[b]-t[a]))))
main = max(events, key=lambda e: e['impulse_Ns'])
sel = (t >= main['start_s']) & (t <= main['end_s'])
peaks = {c: {'value': float(d[c].max()), 'time_s': float(t[d[c].argmax()])} for c in cols[1:]}
summary = dict(source=str(SOURCE), samples=len(d), duration_s=float(t[-1]-t[0]),
               sample_rate_Hz=1/dt, missing_sample_indices=int((np.diff(d.sample_index)!=1).sum()),
               max_time_step_s=float(np.diff(t).max()), ignition_recorded=bool(d.ignition_recorded.any()),
               baseline_window_s=[18, 21], baseline_thrust_N=f0, baseline_pressure_bar=p0,
               baseline_std=baseline[cols[1:]].std().to_dict(), recorded_peaks=peaks,
               event_threshold_N=float(threshold), merge_gap_s=.03, minimum_event_duration_s=.02,
               events=events, main_event=main,
               main_event_lpf_correlation=float(np.corrcoef(f[sel],p[sel])[0,1]))
(OUT/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
pd.DataFrame(events).to_csv(OUT/'events.csv', index=False)

plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
fig, axs = plt.subplots(2, 2, figsize=(14, 8), layout='constrained')
for row, (raw, smooth, unit, color) in enumerate([
    ('thrust_N', 'thrust_N_lpf', 'Thrust (N)', '#1565c0'),
    ('pressure_bar', 'pressure_bar_lpf', 'Pressure (bar)', '#c04c12')]):
    for col in range(2):
        ax = axs[row, col]
        mask = np.ones(len(d), dtype=bool) if col == 0 else (t >= 20.5) & (t <= 32)
        ax.plot(t[mask], d[raw].to_numpy()[mask], color='#a8b0ba', alpha=.45, lw=.35, label='Calibrated raw', rasterized=True)
        ax.plot(t[mask], d[smooth].to_numpy()[mask], color=color, lw=1.15, label='Recorded LPF')
        ax.axvspan(main['start_s'], main['end_s'], color='#eedda5', alpha=.3, label='Main event (5% threshold)')
        peak = peaks[smooth]
        ax.plot(peak['time_s'], peak['value'], 'o', color=color, ms=4)
        ax.set(ylabel=unit, xlabel='Time since acquisition start (s)')
        ax.grid(alpha=.2)
        if row == 0:
            ax.set_title('Full recording' if col == 0 else 'Event detail')
        if col == 1:
            ax.legend(fontsize=8, loc='upper right')
            ax.text(.02, .95, f"LPF peak: {peak['value']:.2f} {unit.split('(')[1][:-1]} @ {peak['time_s']:.4f} s", transform=ax.transAxes, va='top', fontsize=10)
fig.suptitle('Pressure & thrust | 2026-11-09 | 5,000 samples/s', fontsize=17)
fig.savefig(OUT/'pressure_thrust.png', dpi=180)
fig.savefig(OUT/'pressure_thrust.svg')
plt.close(fig)
print(json.dumps(summary, indent=2))
