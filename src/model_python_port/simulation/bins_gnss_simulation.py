"""
Цикл 1 мс. Читать этот файл сверху вниз: на каждом этапе написано, что пришло и что получили.

  FX1 ──идеал ω,a──► ДУС/ДЛУ ──сырые w_m,a_m──► БИНС ──NP, Cbn──►
        │                                                      │
        │ истинные φ,λ,h,V ──► ГНСС ──NP_гнсс──►               │
        │                              ε=БИНС−ГНСС ──► ОФК-1   │
        │                              ◄── x̂,P (не в БИНС)     │
        └── δe ──┐                                             │
                 └── NP−δ, ω−Δω̂, Cbn, a_m, δe ──► ОФК-2 (L*M*X*)

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
sig        входы ОФК-2: α,V,θ,q,az,δe и отклонения от trim
x_ofk2     15 коэффициентов L*, M*, X*
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
    build_z_kinematics,
    ekf_step as ofk2_step,
    initial_covariance as ofk2_initial_covariance,
    initial_state as ofk2_initial_state,
    signals_from_sensors,
)
from ..filtering.ofk2_theory import ofk2_jacobian_at_trim, theory_vector


def run_simulation(
    tmodel: float = 120.0,
    dt: float = 1e-3,
    dt_gnss: float = 0.1,
    dt_ofk2: float = 0.02,
    elevator_doublet_amp_deg: float = 5.0,
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
    ELEVATOR_MANEUVER = "doublet"
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
    }
    _coeff_start_err = float(coeff_start_err)
    if ofk2_start_scale is None:
        _scale = 1.0 + _coeff_start_err
    else:
        _scale = float(ofk2_start_scale)
        _coeff_start_err = abs(_scale - 1.0)
    x_ofk2 = ofk2_initial_state(th_vec * _scale)
    p_ofk2 = ofk2_initial_covariance(
        th_vec * _scale, coeff_start_err=_coeff_start_err, scale_ref=th_vec
    )
    da_prev = None
    q_prev = None
    v_prev = None
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
        # Потребителю: np_cons = NP−δV/δr, w_cons = w_m−Δω̂.
        # --------------------------------------------------------------
        if (i + 1) % step_gnss == 0:
            np_gnss, v_gnss = gnss(
                x[12], x[13], x[10], v_nav[0], v_nav[2], v_nav[1], rng=rng_gnss
            )
            z = build_innovation(np_bins, np_gnss)
            x_ofk, p_ofk = ofk_step(
                a_last, cbn, np_bins, z, x_ofk, p_ofk, v_gnss, dt_gnss
            )
            np_cons, w_cons = consumer_outputs(
                np_bins, w_m, x_ofk, feedback=ofk1_feedback
            )
            sig = signals_from_sensors(np_cons, cbn, w_cons, a_m, x[16], trim)
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
        # ЭТАП 5. ОФК-2, 50 Гц. x_ofk держим с последнего ГНСС.
        # Вход sig: α,V из np_cons+cbn; q=w_cons[2]; θ из сырой cbn;
        #           az сырой ДЛУ; δe из FX1 x[16].
        # Выход: x_ofk2 — 15 коэффициентов L*, M*, X*.
        # --------------------------------------------------------------
        if logs.gnss_idx > 0 and (i + 1) % step_ofk2 == 0:
            np_cons, w_cons = consumer_outputs(
                np_bins, w_m, x_ofk, feedback=ofk1_feedback
            )
            sig = signals_from_sensors(np_cons, cbn, w_cons, a_m, x[16], trim)
            if az0 is None:
                az0 = sig.az
            z_ofk2 = build_z_kinematics(
                sig.alpha, sig.q, sig.de, sig.v, sig.theta, sig.az, trim
            )
            th_inst_vec = theory_vector(
                ofk2_jacobian_at_trim(x, u, la, thetatr=float(sim["thetatr"]))
            )
            (
                x_ofk2,
                p_ofk2,
                innov_ofk2,
                innov_prior_ofk2,
                innov_std_ofk2,
                da_prev,
                q_prev,
            ) = ofk2_step(
                x_ofk2,
                p_ofk2,
                da=sig.da,
                q=sig.q,
                dde=sig.dde,
                dv=sig.dv,
                dtheta=sig.dtheta,
                az=sig.az,
                v=sig.v,
                az0=float(az0),
                dt=dt_ofk2,
                da_prev=da_prev,
                q_prev=q_prev,
                v_prev=v_prev,
                q_std=float(ofk2_q_std),
            )
            v_prev = sig.v
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
                q_meas=sig.q,
                dde=sig.dde,
                dv=sig.dv,
                dtheta=sig.dtheta,
            )
            if (i + 1) % step_gnss == 0 and logs.gnss_idx > 0:
                logs.write_ofk2_on_last_gnss(
                    z_sp=z_ofk2,
                    innov_sp=innov_ofk2,
                    alpha_gnss=alpha_gnss,
                    q_meas=sig.q,
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
