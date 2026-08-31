"""Диагностика ОФК-2: почему Δ = оценка − теория не идёт к нулю."""

import numpy as np

from src.model_python_port.simulation.bins_gnss_simulation import run_simulation

data = run_simulation(tmodel=60.0, dt=1e-3, dt_gnss=0.1, dt_ofk2=0.02)

t = data["ofk2_time"]
th = data["ofk2_theory"]
est = data["ofk2_params"]
d = data["ofk2_d_params"]
da, qm, dde = data["ofk2_reg"]
a_true, q_true, v_true, th_true = data["ofk2_true_aq"]
dt2 = 0.02

adot_fd = np.diff(da, prepend=da[0]) / dt2
adot_true = np.gradient(a_true, dt2)
qdot_true = np.gradient(q_true, dt2)

m = t > 10.0
dv = v_true - v_true[0]
dth = th_true - th_true[0]
phi3 = np.vstack([da[m], qm[m], dde[m]]).T
phi5 = np.vstack([da[m], qm[m], dde[m], dv[m], dth[m]]).T

print("\n== 1. lestnica alpha ==")
print(f"adot_fd == 0 : {100 * np.mean(np.abs(adot_fd) < 1e-12):.1f}%")
print(f"std(adot_fd)={adot_fd[m].std():.4f}  std(adot_true)={adot_true[m].std():.4f}")
print(f"corr(fd,true)={np.corrcoef(adot_fd[m], adot_true[m])[0, 1]:.3f}")

print("\n== 2. LS 3 regressora (istinnye proizvodnye) ==")
s3a, *_ = np.linalg.lstsq(phi3, adot_true[m], rcond=None)
s3q, *_ = np.linalg.lstsq(phi3, qdot_true[m], rcond=None)
print(f"adot: LS={np.round(s3a, 4)}  th={np.round(th[[0, 1, 2], -1], 4)}")
print(f"qdot: LS={np.round(s3q, 4)}  th={np.round(th[[3, 4, 5], -1], 4)}")

print("\n== 3. LS 5 regressorov (+dV, +dTheta) ==")
s5a, *_ = np.linalg.lstsq(phi5, adot_true[m], rcond=None)
s5q, *_ = np.linalg.lstsq(phi5, qdot_true[m], rcond=None)
print(f"adot: LS={np.round(s5a, 4)}  th={np.round(th[[0, 1, 2], -1], 4)}")
print(f"qdot: LS={np.round(s5q, 4)}  th={np.round(th[[3, 4, 5], -1], 4)}")

print("\n== 3b. LS na ISTINNYH regressorah (bez hold/shuma BNK) ==")
da_tr = a_true - a_true[0]
p3t = np.vstack([da_tr[m], q_true[m], dde[m]]).T
p5t = np.vstack([da_tr[m], q_true[m], dde[m], dv[m], dth[m]]).T
for p, lbl in ((p3t, "3reg"), (p5t, "5reg")):
    sa, *_ = np.linalg.lstsq(p, adot_true[m], rcond=None)
    sq, *_ = np.linalg.lstsq(p, qdot_true[m], rcond=None)
    print(f"{lbl} adot: LS={np.round(sa[:3], 4)}  th={np.round(th[[0, 1, 2], -1], 4)}")
    print(f"{lbl} qdot: LS={np.round(sq[:3], 4)}  th={np.round(th[[3, 4, 5], -1], 4)}")

print("\n== 3c. bazis [da, q, dde, dV, dGamma], gamma = theta - alpha ==")
# teoriya schitaet dL/dalpha pri POSTOYANNOM gamma (_set_alpha dvigaet theta vmeste s alpha)
gam = th_true - a_true
dgam = gam - gam[0]
p5g = np.vstack([da_tr[m], q_true[m], dde[m], dv[m], dgam[m]]).T
sa, *_ = np.linalg.lstsq(p5g, adot_true[m], rcond=None)
sq, *_ = np.linalg.lstsq(p5g, qdot_true[m], rcond=None)
print(f"adot: LS={np.round(sa, 4)}")
print(f"      th={np.round(th[[0, 1, 2], -1], 4)}  (sravnenie pervyh 3)")
print(f"qdot: LS={np.round(sq, 4)}")
print(f"      th={np.round(th[[3, 4, 5], -1], 4)}")

print("\n== 3d. tot zhe bazis, okno manevra 10..22 ==")
mw2 = (t > 10.0) & (t < 22.0)
p5w = np.vstack([da_tr[mw2], q_true[mw2], dde[mw2], dv[mw2], dgam[mw2]]).T
sa, *_ = np.linalg.lstsq(p5w, adot_true[mw2], rcond=None)
sq, *_ = np.linalg.lstsq(p5w, qdot_true[mw2], rcond=None)
print(f"adot: LS={np.round(sa, 4)}  th={np.round(th[[0, 1, 2], -1], 4)}")
print(f"qdot: LS={np.round(sq, 4)}  th={np.round(th[[3, 4, 5], -1], 4)}")

print("\n== 4. dinamika dV, dTheta ==")
print(f"std(dV)={dv[m].std():.4f} m/s  razmah={np.ptp(dv[m]):.3f}")
print(f"std(dTheta)={np.degrees(dth[m].std()):.4f} deg  razmah={np.degrees(np.ptp(dth[m])):.3f}")
print(f"std(da)={np.degrees(da[m].std()):.4f} deg")

print("\n== 5. korrelyacii ==")
c = np.corrcoef(np.vstack([da[m], qm[m], dde[m], dv[m], dth[m]]))
lbl = ("da", "q", "dde", "dV", "dTh")
print("     " + "".join(f"{n:>8s}" for n in lbl))
for i, n in enumerate(lbl):
    print(f"{n:>4s} " + "".join(f"{c[i, j]:8.3f}" for j in range(5)))

print("\n== 6. tol'ko okno manevra t=10..22 ==")
mw = (t > 10.0) & (t < 22.0)
pw = np.vstack([da[mw], qm[mw], dde[mw]]).T
sw_a, *_ = np.linalg.lstsq(pw, adot_true[mw], rcond=None)
sw_q, *_ = np.linalg.lstsq(pw, qdot_true[mw], rcond=None)
print(f"adot: LS={np.round(sw_a, 4)}  th={np.round(th[[0, 1, 2], -1], 4)}")
print(f"qdot: LS={np.round(sw_q, 4)}  th={np.round(th[[3, 4, 5], -1], 4)}")

print("\n== 7. EKF itog ==")
for k, n in enumerate(("La", "Lq", "Lde", "Ma", "Mq", "Mde")):
    rel = 100 * abs(d[k, -1]) / max(abs(th[k, -1]), 1e-9)
    print(f"{n:>4s} est={est[k, -1]:+.4f} th={th[k, -1]:+.4f} D={d[k, -1]:+.4f} ({rel:5.1f}%)")
