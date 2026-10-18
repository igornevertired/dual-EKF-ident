"""
Главный цикл моделирования: ЛА → ДУС/ДЛУ → БИНС → СНС → ОФК-1 → ОФК-2.

Схема (шаг цикла 1 мс)::

  FX1 ──идеал ω, a──► ДУС/ДЛУ ──w_m, a_m──► БИНС ──NP, Cbn──┐
   │                                                       │
   └─ истинные φ, λ, h, V ──► СНС (10 Гц) ──► ε = БИНС − СНС ──► ОФК-1 (10 Гц)
                                                              │  x̂, P (в БИНС не пишется)
                     NP − δ̂, ω − Δω̂, a − Δâ, Cbn, δe, δT ◄────┘
                                        │
                                        └──► ОФК-2 (5 Гц): коэффициенты L*, M*, X*, Θ*

Частоты: модель ЛА и БИНС — 1/dt, автопилот — 100 Гц, СНС и ОФК-1 — 1/dt_gnss,
ОФК-2 — 1/dt_ofk2.

Основные переменные
-------------------
x          состояние FX1 (истина ЛА, 25 компонент), x[15] = δT, x[16] = δв (град)
u          управление [δT, δв, δн, δэ]
w_m, a_m   показания ДУС и ДЛУ с погрешностями
q, cbn     кватернион и матрица ориентации БИНС
np_bins    решение БИНС [Vn, Vh, Ve, h, φ, λ]
x_ofk      15 ошибок БИНС (ОФК-1), p_ofk — их ковариация
x_ofk2     20 коэффициентов + [Δα, Δωz, ΔV, Δθ] (ОФК-2), p_ofk2 — ковариация
"""

from __future__ import annotations

if __name__ == "__main__" and not __package__:
    import sys
    from pathlib import Path

    _root = Path(__file__).resolve().parents[2]
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    __package__ = "src.model_python_port"

import numpy as np

from ..dynamics.autopilot_model import autopilot
from ..dynamics.fx1 import c_gb
from ..dynamics.fx1 import fx1 as fx1_func
from ..dynamics.maneuvers import Maneuver, legacy_maneuver
from ..filtering.loosely_coupled_ofk import build_innovation, consumer_outputs, ofk_step
from ..filtering.loosely_coupled_ofk import initial_covariance as ofk1_initial_covariance
from ..filtering.loosely_coupled_ofk import initial_state as ofk1_initial_state
from ..filtering.ofk2_ekf import COEFF_ABS_FLOOR, G0, I_DA, I_DQ, I_DTH, I_DV, build_z_kinematics, frozen_indices
from ..filtering.ofk2_ekf import ekf_step as ofk2_step
from ..filtering.ofk2_ekf import initial_covariance as ofk2_initial_covariance
from ..filtering.ofk2_ekf import initial_state as ofk2_initial_state
from ..filtering.ofk2_ekf import signals_from_sensors
from ..filtering.ofk2_theory import ESTIMATED_PARAM_INDICES, PARAM_NAMES, ofk2_jacobian_at_trim, theory_vector
from ..navigation.bins_common import bins_step
from ..sensors.core import gnss, rk4_step
from ..sensors.imu_error_generator import InsErrorGen
from .initsim import initsim
from .sim_logs import SimLogs

_I_XDT = PARAM_NAMES.index("Xδt")


# ---------------------------------------------------------------------------
# Начальные условия
# ---------------------------------------------------------------------------
def _initial_bins(sim: dict):
    """Начальное решение БИНС = истинное состояние ЛА (точная выставка)."""
    x = sim["x0"]
    q = sim["ivk"]["Qu"].copy()
    cbn = sim["ivk"]["CBN0"].copy()
    v_nav0 = c_gb(x[8], x[6], x[7]).T @ np.array([x[0], x[1], x[2]])
    np_bins = np.array([v_nav0[0], v_nav0[1], v_nav0[2], x[10], x[12], x[13]], dtype=float)
    return q, cbn, np_bins


def _trim_point(theory: dict) -> dict:
    """Балансировочные значения, от которых ОФК-2 отсчитывает отклонения."""
    keys = ("alpha0", "q0", "delta_e0", "v0", "theta0", "h0", "delta_t0")
    return {k: float(theory[k]) for k in keys}


def _ofk2_start(th_vec, estimated, coeff_start_err: float, start_scale: float | None):
    """Стартовые коэффициенты: оцениваемые — эталон × (1 + ошибка), замороженные — эталон."""
    err = float(coeff_start_err)
    if start_scale is None:
        scale = 1.0 + err
    else:
        scale = float(start_scale)
        err = abs(scale - 1.0)
    param0 = th_vec.copy()
    for i in estimated:
        if abs(float(th_vec[i])) < 1e-9:  # нулевой эталон — сдвиг на долю характерного масштаба
            param0[i] = float(th_vec[i]) + err * float(COEFF_ABS_FLOOR[i])
        else:
            param0[i] = float(th_vec[i]) * scale
    for i in frozen_indices(estimated):
        param0[i] = float(th_vec[i])
    x_ofk2 = ofk2_initial_state(param0)
    p_ofk2 = ofk2_initial_covariance(param0, coeff_start_err=err, scale_ref=th_vec, estimated=estimated)
    return x_ofk2, p_ofk2, err


# ---------------------------------------------------------------------------
# Моделирование
# ---------------------------------------------------------------------------
def run_simulation(
    tmodel: float = 120.0,
    dt: float = 1e-3,
    dt_gnss: float = 0.1,
    dt_ofk2: float = 0.1,
    *,
    maneuver: Maneuver | None = None,
    estimated_params: tuple[int, ...] | None = None,
    ofk1_feedback: bool = True,
    coeff_start_err: float = 0.3,
    ofk2_start_scale: float | None = None,
    ofk2_q_std: float = 0.0,
    aero_step_t: float | None = None,
    aero_step_scale: dict[int, float] | None = None,
    # прежний способ задания манёвра (используется, если maneuver не задан)
    elevator_maneuver: str | None = "doublet",
    elevator_doublet_amp_deg: float = 5.0,
    elevator_extra_t0: tuple[float, ...] = (),
    elevator_3211_t0: float = 10.0,
    elevator_3211_unit: float = 1.0,
):
    """
    Моделирование контура на интервале tmodel.

    maneuver          — идентификационный манёвр (см. dynamics/maneuvers.py);
    estimated_params  — индексы оцениваемых коэффициентов (по умолчанию 9 из ofk2_theory;
                        если РУД на манёвре зафиксирован, X_δt исключается автоматически);
    ofk1_feedback     — подавать в ОФК-2 скорректированные выходы ОФК-1 (иначе сырые БИНС);
    coeff_start_err   — относительная начальная ошибка коэффициентов;
    ofk2_q_std        — СКО шума процесса по коэффициентам;
    aero_step_t       — момент скачкообразного изменения аэродинамики (для проверки слежения).

    Возвращает словарь зарегистрированных данных (см. SimLogs.finalize).
    """
    if maneuver is None:
        maneuver = legacy_maneuver(elevator_maneuver, elevator_doublet_amp_deg, elevator_extra_t0,
                                   elevator_3211_t0, elevator_3211_unit)
    if estimated_params is None:
        estimated_params = tuple(ESTIMATED_PARAM_INDICES)
        if maneuver.throttle_fixed:
            estimated_params = tuple(i for i in estimated_params if i != _I_XDT)
    estimated = tuple(int(i) for i in estimated_params)

    # ---------------- ЭТАП 0. Инициализация ----------------
    sim = initsim()
    la = dict(sim["la"])
    la["PAR"] = np.asarray(sim["la"]["PAR"], dtype=float).copy()
    htr, vtr, tettr = sim["htr"], sim["vtr"], sim["tettr"]
    x, u = sim["x0"].copy(), sim["u0"].copy()
    q, cbn, np_bins = _initial_bins(sim)

    imu = InsErrorGen(42)
    rng_gnss = np.random.default_rng(123)
    x_ofk, p_ofk = ofk1_initial_state(), ofk1_initial_covariance()

    theory = ofk2_jacobian_at_trim(sim["x0"], sim["u0"], la, thetatr=float(sim["thetatr"]))
    th_vec = theory_vector(theory)  # эталонные коэффициенты на балансировке
    trim = _trim_point(theory)
    x_ofk2, p_ofk2, start_err = _ofk2_start(th_vec, estimated, coeff_start_err, ofk2_start_scale)
    ofk2_seeded = False
    last_dde: float | None = None
    last_ddt: float | None = None
    alpha_gnss = 0.0

    dt_ofk2 = float(dt_ofk2)
    step_ofk2 = max(1, int(round(dt_ofk2 / dt)))
    step_gnss = max(1, int(round(dt_gnss / dt)))
    step_ap = int(0.01 / dt)  # автопилот 100 Гц
    n_steps = int(tmodel / dt)
    logs = SimLogs(int(tmodel / dt_gnss) + 1, n_steps // step_ofk2 + 1)

    ap_count = 0
    a_last = np.zeros(3, dtype=float)
    aero_applied = False
    aero_scale = aero_step_scale or {7: 1.4, 20: 1.4, 22: 1.4}
    fx1 = lambda xx, uu, tt: fx1_func(xx, uu, tt, la)  # noqa: E731

    for i in range(n_steps):
        t = (i + 1) * dt
        if aero_step_t is not None and not aero_applied and t >= float(aero_step_t):
            for idx, k in aero_scale.items():
                la["PAR"][int(idx)] *= float(k)
            aero_applied = True

        # ---------------- ЭТАП 1. Истинное движение ЛА (РК4, dt) ----------------
        result = rk4_step(fx1, t - dt, dt, x, u)
        x, af_bi_b, wbi_b = result[0], result[2], result[3]   # состояние, идеальные ДЛУ и ДУС
        v_nav = c_gb(x[8], x[6], x[7]).T @ np.array([x[0], x[1], x[2]])  # истинная скорость [N, H, E]

        ap_count += 1
        if ap_count >= step_ap:
            ap_count = 0
            u = autopilot(x, result[1], t, sim["u0"], htr, vtr, tettr, maneuver=maneuver)

        # ---------------- ЭТАП 2. Показания датчиков ----------------
        w_m, a_m = imu.generate(wbi_b, af_bi_b)

        # ---------------- ЭТАП 3. Механизация БИНС ----------------
        q, cbn, np_bins, a_last = bins_step(a_m, w_m, np_bins, cbn, q, dt)

        # ---------------- ЭТАП 4. СНС и ОФК-1 ----------------
        if (i + 1) % step_gnss == 0:
            np_gnss, v_gnss = gnss(x[12], x[13], x[10], v_nav[0], v_nav[2], v_nav[1], rng=rng_gnss)
            z = build_innovation(np_bins, np_gnss)
            x_ofk, p_ofk = ofk_step(a_last, cbn, np_bins, z, x_ofk, p_ofk, v_gnss, dt_gnss)
            np_cons, w_cons, cbn_cons, a_cons = consumer_outputs(np_bins, w_m, cbn, a_m, x_ofk, feedback=ofk1_feedback)
            alpha_gnss = signals_from_sensors(np_cons, cbn_cons, w_cons, a_cons, x[16], trim).alpha
            np_true = np.array([v_nav[0], v_nav[1], v_nav[2], x[10], x[12], x[13]], dtype=float)
            logs.write_gnss(
                t=t, x=x, v_nav=v_nav, np_bins=np_bins, np_cons=np_cons, np_gnss=np_gnss, p_ofk=p_ofk,
                nper_pre=np_bins - np_true, nper_post=np_cons - np_true,
                true_alpha=float(-np.arctan2(x[1], x[0] if abs(x[0]) > 1e-9 else 1e-9)),
                true_q=float(x[5]), true_az=float(af_bi_b[1]) / G0, u=u, z=z,
            )

        # ---------------- ЭТАП 5. ОФК-2 ----------------
        if logs.gnss_idx > 0 and (i + 1) % step_ofk2 == 0:
            np_cons, w_cons, cbn_cons, a_cons = consumer_outputs(np_bins, w_m, cbn, a_m, x_ofk, feedback=ofk1_feedback)
            sig = signals_from_sensors(np_cons, cbn_cons, w_cons, a_cons, x[16], trim, throttle=x[15])
            if not ofk2_seeded:  # начальные Δα, Δωz, ΔV, Δθ — из первого измерения
                x_ofk2[I_DA], x_ofk2[I_DQ], x_ofk2[I_DV], x_ofk2[I_DTH] = sig.da, sig.dq, sig.dv, sig.dtheta
                ofk2_seeded = True
            z_ofk2 = build_z_kinematics(sig.alpha, sig.q, sig.v, sig.theta, sig.de, trim)
            # эталон FX1(t): линеаризация полной модели в текущей точке (только для анализа)
            th_inst_vec = theory_vector(ofk2_jacobian_at_trim(x, u, la, thetatr=float(sim["thetatr"])))
            dde_dot = 0.0 if last_dde is None else (float(sig.dde) - last_dde) / dt_ofk2
            dde_prev, ddt_prev = last_dde, last_ddt
            last_dde, last_ddt = float(sig.dde), float(sig.ddt)

            x_ofk2, p_ofk2, innov_ofk2, innov_prior_ofk2, innov_std_ofk2 = ofk2_step(
                x_ofk2, p_ofk2,
                da=sig.da, dq=sig.dq, dv=sig.dv, dde=sig.dde, dt=dt_ofk2, dtheta=sig.dtheta,
                dde_dot=dde_dot, dde_prev=dde_prev, ddt=sig.ddt, ddt_prev=ddt_prev,
                param_fixed=th_vec, q_std=float(ofk2_q_std), estimated=estimated,
            )
            logs.write_ofk2(
                t=t, x=x, x_sp=x_ofk2, p_sp=p_ofk2, th_inst_vec=th_inst_vec, th_vec=th_vec,
                innov_prior_sp=innov_prior_ofk2, innov_std_sp=innov_std_ofk2,
                da=sig.da, q_meas=sig.dq, dde=sig.dde, dv=sig.dv, dtheta=sig.dtheta,
            )
            if (i + 1) % step_gnss == 0:
                logs.write_ofk2_on_last_gnss(
                    z_sp=z_ofk2, innov_sp=innov_ofk2, alpha_gnss=alpha_gnss, q_meas=sig.dq,
                    de_meas=sig.de, az_meas=sig.az, x_sp=x_ofk2, th_inst_vec=th_inst_vec,
                    th_vec=th_vec, p_sp=p_ofk2,
                )

        if i % 20000 == 0:
            v = np.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2)
            print(f"t={t:.1f}s  H={x[10]:.1f}m  V={v:.1f}m/s  Vn={v_nav[0]:.2f}m/s")

    data = logs.finalize(
        sim=sim, sp_theory=theory, th_vec=th_vec, elevator_doublet_amp_deg=maneuver.amp_deg,
        coeff_start_err=start_err, ofk2_start_scale=ofk2_start_scale, ofk2_q_std=ofk2_q_std,
        aero_step_t=aero_step_t, ofk1_feedback=ofk1_feedback,
    )
    data["maneuver"] = maneuver
    data["estimated_params"] = estimated
    return data


if __name__ == "__main__":
    out = run_simulation(tmodel=60.0, dt=1e-3, dt_gnss=0.1)
    print(f"Симуляция завершена: {len(out['time'])} точек лога")
