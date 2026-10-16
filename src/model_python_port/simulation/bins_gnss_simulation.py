"""
Цикл 1 мс. Читать этот файл сверху вниз: на каждом этапе написано, что пришло и что получили.

  FX1 ──идеал ω,a──► ДУС/ДЛУ ──сырые w_m,a_m──► БИНС ──NP, Cbn──►
        │                                                      │
        │ истинные φ,λ,h,V ──► ГНСС ──NP_гнсс──►               │
        │                              ε=БИНС−ГНСС ──► ОФК-1   │
        │                              ◄── x̂,P (не в БИНС)     │
        └── δe ──┐                                             │
                 └── NP−δ, ω−Δω̂, Cbn с БИНС, a−Δâ, δe ──► ОФК-2

Что лежит в переменных
----------------------
x          состояние FX1 (истина ЛА). x[16] = δe, град
u          рули автопилота
wbi_b, af_bi_b   идеальные ДУС, ДЛУ из FX1
w_m, a_m   сырые ДУС, ДЛУ (ошибки приборов)
q          кватернион БИНС (не тангажная скорость)
cbn        ориентация БИНС, связанная ← географическая
np_bins    счисление БИНС [Vn, Vh, Ve, h, φ, λ]
np_gnss    ГНСС [φ, λ, h, Vn, Ve, Vh]
z          невязка ОФК-1 = БИНС − ГНСС
x_ofk, p_ofk     15 ошибок навигации и смещений, ковариация
np_cons, w_cons  то же NP и ω, что отдаём потребителю (ОФК-2)
sig        входы ОФК-2: α,V,θ (наклон траектории),q,az,δe и отклонения от trim
x_ofk2     коэффициенты (15) + δα, δq, δV, δθ
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
from ..navigation.bins_common import bins_step
from ..sensors.core import gnss, rk4_step
from ..dynamics.fx1 import c_gb
from ..dynamics.fx1 import fx1 as fx1_func
from ..sensors.imu_error_generator import InsErrorGen
from .initsim import initsim
from .sim_logs import SimLogs
from ..filtering.loosely_coupled_ofk import (
    build_innovation,
    consumer_outputs,
    initial_covariance as ofk1_initial_covariance,
    initial_state as ofk1_initial_state,
    ofk_step,
)
from ..filtering.ofk2_ekf import (
    G0,
    I_DA,
    I_DQ,
    I_DTH,
    I_DV,
    _ABS_FLOOR,
    build_z_kinematics,
    ekf_step as ofk2_step,
    initial_covariance as ofk2_initial_covariance,
    initial_state as ofk2_initial_state,
    signals_from_sensors,
)
from ..filtering.ofk2_theory import (
    ESTIMATED_PARAM_INDICES,
    FROZEN_PARAM_INDICES,
    ofk2_jacobian_at_trim,
    theory_vector,
)


def run_simulation(
    tmodel: float = 120.0,
    dt: float = 1e-3,
    dt_gnss: float = 0.1,
    dt_ofk2: float = 0.1,
    elevator_doublet_amp_deg: float = 5.0,
    elevator_maneuver: str | None = "doublet",
    elevator_3211_t0: float = 10.0,
    elevator_3211_unit: float = 1.0,
    ofk1_feedback: bool = True,
    coeff_start_err: float = 0.3,
    ofk2_start_scale: float | None = None,
    ofk2_q_std: float = 0.0,
    elevator_extra_t0: tuple[float, ...] = (),
    aero_step_t: float | None = None,
    aero_step_scale: dict[int, float] | None = None,
):
    # ------------------------------------------------------------------
    # ЭТАП 0. Старт (один раз)
    # Получаем: x, u, q, cbn, np_bins, x_ofk=0, P₀ ОФК-1, trim и x_ofk2.
    # ------------------------------------------------------------------
    ELEVATOR_MANEUVER = elevator_maneuver
    sim = initsim()
    la = dict(sim["la"])
    la["PAR"] = np.asarray(sim["la"]["PAR"], dtype=float).copy()
    htr, vtr, tettr = sim["htr"], sim["vtr"], sim["tettr"]
    ivk = sim["ivk"]

    x = sim["x0"].copy()
    u = sim["u0"].copy()
    q = ivk["Qu"].copy()
    cbn = ivk["CBN0"].copy()
    cgb0 = c_gb(x[8], x[6], x[7])
    v_nav0 = cgb0.T @ np.array([x[0], x[1], x[2]])
    np_bins = np.array(
        [v_nav0[0], v_nav0[1], v_nav0[2], x[10], x[12], x[13]], dtype=float
    )

    gen = InsErrorGen(42)
    rng_gnss = np.random.default_rng(123)

    x_ofk = ofk1_initial_state()
    p_ofk = ofk1_initial_covariance()

    ofk2_theory = ofk2_jacobian_at_trim(
        sim["x0"], sim["u0"], la, thetatr=float(sim["thetatr"])
    )
    th_vec = theory_vector(ofk2_theory)
    trim = {
        "alpha0": float(ofk2_theory["alpha0"]),
        "q0": float(ofk2_theory["q0"]),
        "delta_e0": float(ofk2_theory["delta_e0"]),
        "v0": float(ofk2_theory["v0"]),
        "theta0": float(ofk2_theory["theta0"]),
        "h0": float(ofk2_theory["h0"]),
        "delta_t0": float(ofk2_theory["delta_t0"]),
    }
    _coeff_start_err = float(coeff_start_err)
    if ofk2_start_scale is None:
        _scale = 1.0 + _coeff_start_err
    else:
        _scale = float(ofk2_start_scale)
        _coeff_start_err = abs(_scale - 1.0)
    # Стартовый сдвиг только у оцениваемых; Lv — сразу trim.
    _abs_floor = _ABS_FLOOR
    param0 = th_vec.copy()
    for _i in ESTIMATED_PARAM_INDICES:
        if abs(float(th_vec[_i])) < 1e-9:
            param0[_i] = float(th_vec[_i]) + _coeff_start_err * float(_abs_floor[_i])
        else:
            param0[_i] = float(th_vec[_i]) * _scale
    for _i in FROZEN_PARAM_INDICES:
        param0[_i] = float(th_vec[_i])
    x_ofk2 = ofk2_initial_state(param0)
    p_ofk2 = ofk2_initial_covariance(
        param0, coeff_start_err=_coeff_start_err, scale_ref=th_vec
    )
    ofk2_seeded = False
    last_dde: float | None = None
    last_ddt: float | None = None
    az0 = None
    alpha_gnss = 0.0

    dt_ofk2 = float(dt_ofk2)
    step_ofk2 = max(1, int(round(dt_ofk2 / dt)))
    step_gnss = max(1, int(round(dt_gnss / dt)))
    n_steps = int(tmodel / dt)
    logs = SimLogs(int(tmodel / dt_gnss) + 1, n_steps // step_ofk2 + 1)

    ap_count = 0
    ap_steps = int(0.01 / dt)
    a_last = np.zeros(3, dtype=float)
    aero_applied = False
    aero_scale = aero_step_scale or {7: 1.4, 20: 1.4, 22: 1.4}

    for i in range(n_steps):
        t = (i + 1) * dt
        if (
            aero_step_t is not None
            and not aero_applied
            and t >= float(aero_step_t)
        ):
            for idx, k in aero_scale.items():
                la["PAR"][int(idx)] *= float(k)
            aero_applied = True

        # --------------------------------------------------------------
        # ЭТАП 1. Истина FX1 за 1 мс
        # Вход: x, u. Выход: новый x; идеал ДЛУ af_bi_b; идеал ДУС wbi_b;
        #       истинные скорости в географии v_nav (для ГНСС).
        # --------------------------------------------------------------
        fx1 = lambda xx, uu, tt: fx1_func(xx, uu, tt, la)
        result = rk4_step(fx1, t - dt, dt, x, u)
        x = result[0]
        af_bi_b = result[2]
        wbi_b = result[3]
        cgb = c_gb(x[8], x[6], x[7])
        v_nav = cgb.T @ np.array([x[0], x[1], x[2]])

        ap_count += 1
        if ap_count >= ap_steps:
            ap_count = 0
            u = autopilot(
                x,
                result[1],
                t,
                sim["u0"],
                htr,
                vtr,
                tettr,
                elevator_maneuver=ELEVATOR_MANEUVER,
                elevator_doublet_amp_deg=float(elevator_doublet_amp_deg),
                elevator_extra_t0=tuple(elevator_extra_t0),
                elevator_3211_t0=float(elevator_3211_t0),
                elevator_3211_unit=float(elevator_3211_unit),
            )

        # --------------------------------------------------------------
        # ЭТАП 2. Сырые ДУС и ДЛУ
        # Вход: идеал wbi_b, af_bi_b. Выход: приборы w_m, a_m.
        # --------------------------------------------------------------
        w_m, a_m = gen.generate(wbi_b, af_bi_b)

        # --------------------------------------------------------------
        # ЭТАП 3. БИНС по сырым приборам (ОФК-1 сюда не заходит)
        # Вход: a_m, w_m. Выход: q, cbn, np_bins=[Vn,Vh,Ve,h,φ,λ], a_last=a_m.
        # --------------------------------------------------------------
        q, cbn, np_bins, a_last = bins_step(a_m, w_m, np_bins, cbn, q, dt)

        # --------------------------------------------------------------
        # ЭТАП 4. ГНСС + ОФК-1, 10 Гц. В БИНС не пишем.
        # Вход ОФК-1: a_last, cbn, np_bins, z=БИНС−ГНСС, σ ГНСС.
        # Выход: x_ofk (15 дельт), p_ofk.
        # Потребителю: NP−δ, ω−Δω̂, Cbn с БИНС (без φ̂), a−Δâ.
        # --------------------------------------------------------------
        if (i + 1) % step_gnss == 0:
            np_gnss, v_gnss = gnss(
                x[12], x[13], x[10], v_nav[0], v_nav[2], v_nav[1], rng=rng_gnss
            )
            z = build_innovation(np_bins, np_gnss)
            x_ofk, p_ofk = ofk_step(
                a_last, cbn, np_bins, z, x_ofk, p_ofk, v_gnss, dt_gnss
            )
            np_cons, w_cons, cbn_cons, a_cons = consumer_outputs(
                np_bins, w_m, cbn, a_m, x_ofk, feedback=ofk1_feedback
            )
            sig = signals_from_sensors(np_cons, cbn_cons, w_cons, a_cons, x[16], trim)
            alpha_gnss = sig.alpha
            if az0 is None:
                az0 = sig.az
            np_etalon = np.array(
                [v_nav[0], v_nav[1], v_nav[2], x[10], x[12], x[13]], dtype=float
            )
            logs.write_gnss(
                t=t,
                x=x,
                v_nav=v_nav,
                np_bins=np_bins,
                np_cons=np_cons,
                np_gnss=np_gnss,
                p_ofk=p_ofk,
                nper_pre=np_bins - np_etalon,
                nper_post=np_cons - np_etalon,
                true_alpha=float(
                    -np.arctan2(x[1], x[0] if abs(x[0]) > 1e-9 else 1e-9)
                ),
                true_q=float(x[5]),
                true_az=float(af_bi_b[1]) / G0,
                u=u,
                z=z,
            )

        # --------------------------------------------------------------
        # ЭТАП 5. ОФК-2, та же частота что ОФК-1 (10 Гц).
        # Прогноз: интеграл α̇,q̇,V̇,θ̇. Коррекция: Z=[δα,δq,δV,δθ] после ОФК-1.
        # Cbn — напрямую с БИНС (научрук: поправка φ̂ почти не даёт).
        # --------------------------------------------------------------
        if logs.gnss_idx > 0 and (i + 1) % step_ofk2 == 0:
            np_cons, w_cons, cbn_cons, a_cons = consumer_outputs(
                np_bins, w_m, cbn, a_m, x_ofk, feedback=ofk1_feedback
            )
            sig = signals_from_sensors(
                np_cons, cbn_cons, w_cons, a_cons, x[16], trim, throttle=x[15]
            )
            if az0 is None:
                az0 = sig.az
            if not ofk2_seeded:
                x_ofk2[I_DA] = sig.da
                x_ofk2[I_DQ] = sig.dq
                x_ofk2[I_DV] = sig.dv
                x_ofk2[I_DTH] = sig.dtheta
                ofk2_seeded = True
            z_ofk2 = build_z_kinematics(
                sig.alpha, sig.q, sig.v, sig.theta, sig.de, trim
            )
            th_inst_vec = theory_vector(
                ofk2_jacobian_at_trim(x, u, la, thetatr=float(sim["thetatr"]))
            )
            if last_dde is None:
                dde_dot = 0.0
            else:
                dde_dot = (float(sig.dde) - last_dde) / dt_ofk2
            dde_prev, ddt_prev = last_dde, last_ddt
            last_dde = float(sig.dde)
            last_ddt = float(sig.ddt)
            (
                x_ofk2,
                p_ofk2,
                innov_ofk2,
                innov_prior_ofk2,
                innov_std_ofk2,
            ) = ofk2_step(
                x_ofk2,
                p_ofk2,
                da=sig.da,
                dq=sig.dq,
                dv=sig.dv,
                dde=sig.dde,
                dt=dt_ofk2,
                dtheta=sig.dtheta,
                dde_dot=dde_dot,
                dde_prev=dde_prev,
                ddt=sig.ddt,
                ddt_prev=ddt_prev,
                param_fixed=th_vec,
                q_std=float(ofk2_q_std),
            )
            logs.write_ofk2(
                t=t,
                x=x,
                x_sp=x_ofk2,
                p_sp=p_ofk2,
                th_inst_vec=th_inst_vec,
                th_vec=th_vec,
                innov_prior_sp=innov_prior_ofk2,
                innov_std_sp=innov_std_ofk2,
                da=sig.da,
                q_meas=sig.dq,
                dde=sig.dde,
                dv=sig.dv,
                dtheta=sig.dtheta,
            )
            if (i + 1) % step_gnss == 0 and logs.gnss_idx > 0:
                logs.write_ofk2_on_last_gnss(
                    z_sp=z_ofk2,
                    innov_sp=innov_ofk2,
                    alpha_gnss=alpha_gnss,
                    q_meas=sig.dq,
                    de_meas=sig.de,
                    az_meas=sig.az,
                    x_sp=x_ofk2,
                    th_inst_vec=th_inst_vec,
                    th_vec=th_vec,
                    p_sp=p_ofk2,
                )

        if i % 20000 == 0:
            v = np.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2)
            print(f"t={t:.1f}s  H={x[10]:.1f}m  V={v:.1f}m/s  Vn={v_nav[0]:.2f}m/s")

    return logs.finalize(
        sim=sim,
        sp_theory=ofk2_theory,
        th_vec=th_vec,
        elevator_doublet_amp_deg=elevator_doublet_amp_deg,
        coeff_start_err=_coeff_start_err,
        ofk2_start_scale=ofk2_start_scale,
        ofk2_q_std=ofk2_q_std,
        aero_step_t=aero_step_t,
        ofk1_feedback=ofk1_feedback,
    )


if __name__ == "__main__":
    data = run_simulation(tmodel=60.0, dt=1e-3, dt_gnss=0.1)
    print(f"Симуляция завершена: {len(data['time'])} точек лога")
