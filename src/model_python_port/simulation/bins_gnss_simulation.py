"""
Цикл 1 мс: FX1 → ДУС/ДЛУ → БИНС → при такте ГНСС ОФК-1 → при такте ОФК-2 идентификация.

ЭТАП 0  старт (один раз)
ЭТАП 1  истина FX1
ЭТАП 2  сырые ДУС, ДЛУ
ЭТАП 3  БИНС (без ОФК-1)
ЭТАП 4  ГНСС + ОФК-1, 10 Гц
ЭТАП 5  ОФК-2, 50 Гц

Запись массивов — sim_logs.py, на расчёт не влияет.
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
    correct_gyro_output,
    correct_nav_output,
    ofk_step,
)
from ..filtering.ofk2_ekf import (
    G0,
    build_z_kinematics,
    ekf_step as sp_ekf_step,
    initial_covariance as sp_initial_covariance,
    initial_state as sp_initial_state,
    reconstruct_alpha_from_nav,
    reconstruct_theta_from_nav,
)
from ..filtering.ofk2_theory import ofk2_jacobian_at_trim, theory_vector
from ..filtering.ofk2_ekf_legacy import (
    ekf_step as sp_ekf_step_legacy,
    initial_covariance as sp_initial_covariance_legacy,
    initial_state as sp_initial_state_legacy,
)


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
    # ЭТАП 0. Старт
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

    x_ofk = np.zeros(15, dtype=float)
    # P₀: квадраты σ из табл. 5 (смещения — σ из табл. 3). Без часов приёмника.
    _deg_hr = np.pi / 180.0 / 3600.0
    _sig_att = np.array([1.0e-5, 1.0e-5, 2.0e-5])  # рад
    _sig_v = 0.02  # м/с, в т.ч. Vh
    _sig_ll = 1.57e-7  # рад, φ и λ
    _sig_h = 1.0  # м
    _sig_gyro = 0.003 * _deg_hr  # 0.003 °/ч
    _sig_accel = 25.0e-6 * 9.80665  # 25 µg
    p0_diag = np.array(
        [
            _sig_att[0] ** 2,
            _sig_att[1] ** 2,
            _sig_att[2] ** 2,
            _sig_v ** 2,
            _sig_v ** 2,
            _sig_ll ** 2,
            _sig_ll ** 2,
            _sig_accel ** 2,
            _sig_accel ** 2,
            _sig_accel ** 2,
            _sig_gyro ** 2,
            _sig_gyro ** 2,
            _sig_gyro ** 2,
            _sig_v ** 2,
            _sig_h ** 2,
        ],
        dtype=float,
    )
    p_ofk = np.diag(p0_diag)

    sp_theory = ofk2_jacobian_at_trim(
        sim["x0"], sim["u0"], la, thetatr=float(sim["thetatr"])
    )
    th_vec = theory_vector(sp_theory)
    th_vec_legacy = np.array(
        [th_vec[0], th_vec[1], th_vec[2], th_vec[5], th_vec[6], th_vec[7]],
        dtype=float,
    )
    trim = {
        "alpha0": float(sp_theory["alpha0"]),
        "q0": float(sp_theory["q0"]),
        "delta_e0": float(sp_theory["delta_e0"]),
        "v0": float(sp_theory["v0"]),
        "theta0": float(sp_theory["theta0"]),
        "h0": float(sp_theory["h0"]),
    }
    _coeff_start_err = float(coeff_start_err)
    if ofk2_start_scale is None:
        _scale = 1.0 + _coeff_start_err
    else:
        _scale = float(ofk2_start_scale)
        _coeff_start_err = abs(_scale - 1.0)
    x_sp = sp_initial_state(th_vec * _scale)
    p_sp = sp_initial_covariance(
        th_vec * _scale, coeff_start_err=_coeff_start_err, scale_ref=th_vec
    )
    x_sp_legacy = sp_initial_state_legacy(th_vec_legacy * _scale)
    p_sp_legacy = sp_initial_covariance_legacy(
        th_vec_legacy * _scale,
        coeff_start_err=_coeff_start_err,
        scale_ref=th_vec_legacy,
    )
    da_prev = None
    q_prev = None
    v_prev = None
    da_prev_legacy = None
    q_prev_legacy = None
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
        # --------------------------------------------------------------
        w_m, a_m = gen.generate(wbi_b, af_bi_b)

        # --------------------------------------------------------------
        # ЭТАП 3. БИНС по сырым приборам
        # --------------------------------------------------------------
        q, cbn, np_bins, a_last = bins_step(a_m, w_m, np_bins, cbn, q, dt)

        # q — кватернион ориентации БИНС, четыре числа. Им интегрируют ДУС.
        # cbn — матрица направляющих косинусов, связанная ← географическая.
        # np_bins — навигационный вектор счисления, шесть чисел: [Vn, Vh, Ve, h, φ, λ]. 
        # a_last — то же удельное ускорение a_m с ДЛУ, которое только что ушло в bins_step. Его пробрасывают в ОФК-1, чтобы собрать матрицы F, G на такте ГНСС. На ориентацию и координаты это не ещё одна оценка, а копия входа ДЛУ.

        # --------------------------------------------------------------
        # ЭТАП 4. ГНСС + ОФК-1, только 10 Гц
        # x_ofk копится и держится до следующего ГНСС. В БИНС не пишем.
        # --------------------------------------------------------------
        if (i + 1) % step_gnss == 0:
            np_gnss, v_gnss = gnss(
                x[12], x[13], x[10], v_nav[0], v_nav[2], v_nav[1], rng=rng_gnss
            )
            z = build_innovation(np_bins, np_gnss)
            x_ofk, p_ofk = ofk_step(
                a_last, # ускорение из ДЛУ 
                cbn, # матрица ориентации БИНС
                np_bins, # [Vn, Vh, Ve, h, φ, λ]
                z, # БИНС - ГНСС
                x_ofk, # вектор из 15 оценок ошибок, которые корректирует ОФК-1. (в начальный момент - нули) 
                p_ofk, # ковариационная матрица 15×15, насколько фильтр уверен в этих оценках.
                v_gnss, # СКО каналов ГНСС, [σφ, σλ, σh, σVn, σVe, σVh]
                dt_gnss # 10 Гц
            )
            if ofk1_feedback:
                np_cons = correct_nav_output(np_bins, x_ofk) # угловая скорость и тангаж БИНС - ОФК-1.
                w_cons = correct_gyro_output(w_m, x_ofk) # ДУС - ошибка из ОФК-1.
            else:
                np_cons = np_bins.copy()
                w_cons = w_m

            alpha_gnss, v_gnss_sp = reconstruct_alpha_from_nav(np_cons, cbn) # угол атаки и скорость
            theta_gnss = reconstruct_theta_from_nav(cbn) # тангаж из той же Cbn, без поправки углами рассогласования.
            q_meas = float(w_cons[2])
            az_meas = float(a_m[1]) / G0
            de_meas = float(x[16]) * np.pi / 180.0
            if az0 is None:
                az0 = az_meas
            z_sp = build_z_kinematics(
                alpha_gnss, q_meas, de_meas, v_gnss_sp, theta_gnss, az_meas, trim
            )
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
        # ЭТАП 5. ОФК-2, 50 Гц. Берёт последний x_ofk (он обновляется на 10 Гц).
        # ДУС, ДЛУ, Cbn — с текущего миллисекундного шага.
        # --------------------------------------------------------------
        if logs.gnss_idx > 0 and (i + 1) % step_ofk2 == 0:
            if ofk1_feedback:
                np_cons = correct_nav_output(np_bins, x_ofk)
                w_cons = correct_gyro_output(w_m, x_ofk)
            else:
                np_cons = np_bins
                w_cons = w_m
            alpha_meas, v_meas = reconstruct_alpha_from_nav(np_cons, cbn)
            theta_meas = reconstruct_theta_from_nav(cbn)
            q_meas = float(w_cons[2])
            az_meas = float(a_m[1]) / G0
            de_meas = float(x[16]) * np.pi / 180.0
            da = float(alpha_meas) - trim["alpha0"]
            dde = de_meas - trim["delta_e0"]
            dv = float(v_meas) - trim["v0"]
            dtheta = float(theta_meas) - trim["theta0"]
            if az0 is None:
                az0 = az_meas
            z_sp = build_z_kinematics(
                alpha_meas, q_meas, de_meas, v_meas, theta_meas, az_meas, trim
            )
            th_inst_vec = theory_vector(
                ofk2_jacobian_at_trim(x, u, la, thetatr=float(sim["thetatr"]))
            )
            (
                x_sp,
                p_sp,
                innov_sp,
                innov_prior_sp,
                innov_std_sp,
                da_prev,
                q_prev,
            ) = sp_ekf_step(
                x_sp,
                p_sp,
                da=da,
                q=q_meas,
                dde=dde,
                dv=dv,
                dtheta=dtheta,
                az=az_meas,
                v=float(v_meas),
                az0=float(az0),
                dt=dt_ofk2,
                da_prev=da_prev,
                q_prev=q_prev,
                v_prev=v_prev,
                q_std=float(ofk2_q_std),
            )
            v_prev = float(v_meas)
            (
                x_sp_legacy,
                p_sp_legacy,
                _innov_legacy,
                _prior_legacy,
                _std_legacy,
                da_prev_legacy,
                q_prev_legacy,
            ) = sp_ekf_step_legacy(
                x_sp_legacy,
                p_sp_legacy,
                da=da,
                q=q_meas,
                dde=dde,
                az=az_meas,
                v=float(v_meas),
                az0=float(az0),
                dt=dt_ofk2,
                da_prev=da_prev_legacy,
                q_prev=q_prev_legacy,
            )
            logs.write_ofk2(
                t=t,
                x=x,
                x_sp=x_sp,
                p_sp=p_sp,
                th_inst_vec=th_inst_vec,
                th_vec=th_vec,
                x_sp_legacy=x_sp_legacy,
                p_sp_legacy=p_sp_legacy,
                th_vec_legacy=th_vec_legacy,
                innov_prior_sp=innov_prior_sp,
                innov_std_sp=innov_std_sp,
                da=da,
                q_meas=q_meas,
                dde=dde,
                dv=dv,
                dtheta=dtheta,
            )
            if (i + 1) % step_gnss == 0 and logs.gnss_idx > 0:
                logs.write_ofk2_on_last_gnss(
                    z_sp=z_sp,
                    innov_sp=innov_sp,
                    alpha_gnss=alpha_gnss,
                    q_meas=q_meas,
                    de_meas=de_meas,
                    az_meas=az_meas,
                    x_sp=x_sp,
                    th_inst_vec=th_inst_vec,
                    th_vec=th_vec,
                    p_sp=p_sp,
                )

        if i % 20000 == 0:
            v = np.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2)
            print(f"t={t:.1f}s  H={x[10]:.1f}m  V={v:.1f}m/s  Vn={v_nav[0]:.2f}m/s")

    return logs.finalize(
        sim=sim,
        sp_theory=sp_theory,
        th_vec=th_vec,
        th_vec_legacy=th_vec_legacy,
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
