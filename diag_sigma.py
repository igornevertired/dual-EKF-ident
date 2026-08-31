"""Почему ±3σ ОФК-2 такая широкая: разложение по вкладам P0, R, Q, возбуждения."""

import numpy as np

from src.model_python_port.filtering.ofk2_ekf import (
    initial_covariance,
    measurement_covariance,
    process_noise,
)
from src.model_python_port.simulation.bins_gnss_simulation import run_simulation

data = run_simulation(tmodel=60.0, dt=1e-3, dt_gnss=0.1, dt_ofk2=0.02)

t = data["ofk2_time"]
th = data["ofk2_theory"]
std = data["ofk2_std"]
da, qm, dde = data["ofk2_reg"]
a_true, q_true, v_true, th_true = data["ofk2_true_aq"]
names = ("La", "Lq", "Lde", "Ma", "Mq", "Mde")
dt2 = 0.02

p0 = initial_covariance(th[:, 0] * 1.3, coeff_start_err=0.3)
r = measurement_covariance()
qd = process_noise(dt2, adapt=True)

print("\n== 1. 3sigma: start -> konec ==")
print(f"{'':>5s} {'3sig0':>9s} {'3sigN':>9s} {'szhatie':>9s} {'|theta|':>9s} {'3sigN/|th|':>11s}")
for k, n in enumerate(names):
    s0 = 3 * np.sqrt(p0[k, k])
    sn = 3 * std[k, -1]
    base = abs(th[k, -1])
    print(f"{n:>5s} {s0:9.4f} {sn:9.4f} {s0 / sn:9.2f} {base:9.4f} {100 * sn / base:10.1f}%")

print("\n== 2. R protiv real'nogo signala ==")
adot = np.gradient(a_true, dt2)
qdot = np.gradient(q_true, dt2)
m = t > 10.0
sig_r = np.sqrt(np.diag(r))
for i, (lbl, sg) in enumerate(
    (("adot", adot[m].std()), ("qdot", qdot[m].std()), ("az", 0.0))
):
    if i < 2:
        print(f"{lbl:>5s}: sigma_R={sig_r[i]:.4f}  std(signal)={sg:.4f}  R/signal={sig_r[i] / sg:.1f}x")
print(f"{'az':>5s}: sigma_R={sig_r[2]:.4f}")

print("\n== 3. informaciya na odno izmerenie ==")
phi = np.vstack([da[m], qm[m], dde[m]]).T
gram = phi.T @ phi / len(phi)
print(f"std(da)={da[m].std():.5f}  std(q)={qm[m].std():.5f}  std(dde)={dde[m].std():.5f}")
print(f"diag(Gram)={np.round(np.diag(gram), 8)}")
n_upd = len(phi)
print(f"n_updates={n_upd}")

print("\n== 4. predskazannaya sigma po informacii Fishera (stroka L) ==")
for lbl, rows, sg2 in (("L", (0, 1, 2), r[0, 0]), ("M", (3, 4, 5), r[1, 1])):
    fim = n_upd * (phi.T @ phi / n_upd) / sg2
    cov = np.linalg.inv(fim)
    pred = 3 * np.sqrt(np.diag(cov))
    fact = 3 * std[list(rows), -1]
    print(f"{lbl}: 3sig_pred={np.round(pred, 4)}  3sig_fakt={np.round(fact, 4)}")

print("\n== 5. pol EKF ot Q (nakoplenie za vse shagi) ==")
n_all = len(t)
for k, n in enumerate(names):
    var_q = qd[k, k] * n_all
    print(f"{n:>5s} 3sig_Q_floor={3 * np.sqrt(var_q):.4f}  3sig_fakt={3 * std[k, -1]:.4f}")

print("\n== 6. chto budet pri R/10 i R/100 (predskazanie) ==")
for scale in (1.0, 0.1, 0.01):
    out = []
    for rows, sg2 in (((0, 1, 2), r[0, 0] * scale), ((3, 4, 5), r[1, 1] * scale)):
        fim = phi.T @ phi / sg2
        out.append(3 * np.sqrt(np.diag(np.linalg.inv(fim))))
    print(f"R x{scale:<5g}: L={np.round(out[0], 4)}  M={np.round(out[1], 4)}")
