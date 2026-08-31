"""Измерение фактических погрешностей измерений ОФК-2 для настройки R."""

import numpy as np

from src.model_python_port.simulation.bins_gnss_simulation import run_simulation

data = run_simulation(tmodel=60.0, dt=1e-3, dt_gnss=0.1, dt_ofk2=0.02)

t = data["ofk2_time"]
da, qm, dde = data["ofk2_reg"]
a_true, q_true, v_true, th_true = data["ofk2_true_aq"]
dt2 = 0.02
m = t > 10.0

adot_fd = np.diff(da, prepend=da[0]) / dt2
qdot_fd = np.diff(qm, prepend=qm[0]) / dt2
adot_true = np.gradient(a_true, dt2)
qdot_true = np.gradient(q_true, dt2)

print("\n== pogreshnost' proizvodnyh (t>10) ==")
e_a = adot_fd[m] - adot_true[m]
e_q = qdot_fd[m] - qdot_true[m]
print(f"adot: std(oshibka)={e_a.std():.5f}  bias={e_a.mean():+.5f}  std(signal)={adot_true[m].std():.5f}")
print(f"qdot: std(oshibka)={e_q.std():.5f}  bias={e_q.mean():+.5f}  std(signal)={qdot_true[m].std():.5f}")

print("\n== to zhe, no adot cherez shag 0.1 s (bez lestnicy) ==")
step = 5
idx = np.arange(0, len(da), step)
adot_dec = np.diff(da[idx], prepend=da[idx[0]]) / (dt2 * step)
adot_true_dec = adot_true[idx]
md = t[idx] > 10.0
e_ad = adot_dec[md] - adot_true_dec[md]
print(f"adot@0.1s: std(oshibka)={e_ad.std():.5f}  std(signal)={adot_true_dec[md].std():.5f}")

print("\n== az: DLU protiv istiny (takt GNSS) ==")
az_m = np.asarray(data["sp_az"], dtype=float)
az_t = np.asarray(data["true_az"], dtype=float)
tg = np.asarray(data["time"], dtype=float)
mg = tg > 10.0
e_az = az_m[mg] - az_t[mg]
print(f"std(oshibka)={e_az.std():.6f}  bias={e_az.mean():+.6f}  std(az)={az_t[mg].std():.5f}")

print("\n== oshibka MODELI az = az0 - (V/g)(La*da + (Lq-1)*q + Lde*dde) ==")
g0 = 9.80665
th = data["ofk2_theory"]
la_, lq_, lde_ = th[0], th[1], th[2]
az0 = az_m[0]
# na takte OFK-2 net az; ocenka po 10 Gc s peresborkoy regressorov
i50 = np.searchsorted(t, tg)
i50 = np.clip(i50, 0, len(t) - 1)
pred = az0 - (v_true[i50] / g0) * (
    la_[i50] * da[i50] + (lq_[i50] - 1.0) * qm[i50] + lde_[i50] * dde[i50]
)
e_mod = pred[mg] - az_t[mg]
print(f"std(oshibka modeli)={e_mod.std():.6f}  bias={e_mod.mean():+.6f}")

print("\n== regressory: shum BNK ==")
print(f"std(da - da_true) = {(da[m] - (a_true[m] - a_true[0])).std():.6f}")
print(f"std(q  - q_true)  = {(qm[m] - q_true[m]).std():.6f}")

print("\n== REKOMENDACIYA R ==")
print(f"sigma_adot = {e_a.std():.4f}   (seychas 0.0600)")
print(f"sigma_qdot = {e_q.std():.4f}   (seychas 0.0400)")
print(f"sigma_az   = {max(e_az.std(), e_mod.std()):.4f}   (seychas 0.0800)")
