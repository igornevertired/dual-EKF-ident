"""
Сценарий симуляции: ЛА + БИНС + ГНСС + ОФК-1 + ОФК-2 (второй фильтр).

Поэтапный поток (на каждом шаге dt = 1 мс):

  ЭТАП 0 (один раз при старте)
    initsim / initivk → начальные q, Cbn, np_bins без ошибок датчиков

  ЭТАП 1 — «истинные» показания инерциальных датчиков (FX1, без ошибок)
    wbi_b  — истинная угловая скорость ЛА в связанной СК (то, что измерил бы идеальный ДУС)
    af_bi_b — истинное ускорение без гравитации (то, что измерил бы идеальный ДЛУ)

  ЭТАП 2 — ошибки датчиков (InsErrorGen, аналог GENERATOR_SV.m)
    w_m = wbi_b + bias_ДУС + белый_шум_ДУС   ← «сырой» выход гироскопа
    a_m = af_bi_b + bias_ДЛУ + белый_шум_ДЛУ ← «сырой» выход акселерометра

  ЭТАП 3 — механизация БИНС (bins_step)
    из (w_m, a_m) интегрируются скорость, h, φ, λ и ориентация (q, Cbn)

  ЭТАП 4 — каждые dt_gnss = 0.1 с: ГНСС + ОФК-1 (навигация)
    gnss() добавляет ошибки к истинным координатам/скоростям;
    z = np_bins − np_gnss → фильтр → поправка np_bins

  ЭТАП 5 — ОФК-2 short-period (часто чаще ГНСС, dt_ofk2 ≈ 0.02 с)
    входы α,V с последнего такта ОФК-1; q, az с ДУС/ДЛУ; δe с привода;
    оценка Lα,Lq,Lδe,Mα,Mq,Mδe (equation-error по α̇, q̇, az).
"""

from __future__ import annotations

# Прямой запуск: python src/model_python_port/bins_gnss_simulation.py
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
from ..filtering.loosely_coupled_ofk import apply_bins_feedback, build_innovation, ofk_step
from ..filtering.ofk2_ekf import (
    G0,
    N_PARAM,
    build_z_kinematics,
    ekf_step as sp_ekf_step,
    initial_covariance as sp_initial_covariance,
    initial_state as sp_initial_state,
    reconstruct_alpha_from_nav,
)
from ..filtering.ofk2_theory import (
    coeff_delta_ekf_minus_theory,
    ofk2_jacobian_at_trim,
    theory_vector,
)


def run_simulation(
    tmodel: float = 120.0,
    dt: float = 1e-3,
    dt_gnss: float = 0.1,
    dt_ofk2: float = 0.02,
):
    # ------------------------------------------------------------------
    # Манёвр руля высоты внутри автопилота (канал δV на интервале заморожен).
    # Выключить: ELEVATOR_MANEUVER = None
    # ------------------------------------------------------------------
    ELEVATOR_MANEUVER = "doublet"  # "doublet" | "3211" | None
    # ------------------------------------------------------------------

    sim = initsim()
    la = sim["la"]
    htr, vtr, tettr = sim["htr"], sim["vtr"], sim["tettr"]
    ivk = sim["ivk"]

    x = sim["x0"].copy()
    u = sim["u0"].copy()
    # ------------------------------------------------------------------
    # ЭТАП 0. Инициализация БИНС (до цикла, ошибок датчиков ещё нет)
    # ------------------------------------------------------------------
    # initivk: начальный кватернион Qu и матрица CBN0 из углов FX1 (γ, ψ, θ)
    q = ivk["Qu"].copy()
    cbn = ivk["CBN0"].copy()

    # np_bins = [Vn, Vh, Ve, h, φ, λ] — из истинного состояния FX1, без INS-ошибок
    cgb0 = c_gb(x[8], x[6], x[7])
    v_nav0 = cgb0.T @ np.array([x[0], x[1], x[2]])
    np_bins = np.array([v_nav0[0], v_nav0[1], v_nav0[2], x[10], x[12], x[13]], dtype=float)

    # Генератор ошибок ДУС/ДЛУ: bias задаётся один раз при создании, шум — каждый шаг
    gen = InsErrorGen(42)
    rng_gnss = np.random.default_rng(123)

    x_ofk = np.zeros(15, dtype=float)
    p0_diag = np.array([1e3] * 4 + [1e-2] * 6 + [1e-4] * 5, dtype=float)
    p0_diag[13] = 0.04  # σ_Vh ГНСС ≈ 0.2 м/с
    p0_diag[14] = 1.0  # σ_h ГНСС ≈ 1 м
    p_ofk = np.diag(p0_diag)

    # Теория: якобиан FX1 → эталон L*, M* короткопериода
    sp_theory = ofk2_jacobian_at_trim(
        sim["x0"], sim["u0"], la, thetatr=float(sim["thetatr"])
    )
    th_vec = theory_vector(sp_theory)
    trim = {
        "alpha0": float(sp_theory["alpha0"]),
        "q0": float(sp_theory["q0"]),
        "delta_e0": float(sp_theory["delta_e0"]),
    }
    # ОФК-2: [Lα,Lq,Lδe,Mα,Mq,Mδe] со смещением +50 % (без theory-anchor)
    _coeff_start_err = 0.5
    param0 = th_vec * (1.0 + _coeff_start_err)
    x_sp = sp_initial_state(param0)
    p_sp = sp_initial_covariance()
    a_smooth: float | None = None
    a_smooth_prev: float | None = None
    q_smooth: float | None = None
    q_smooth_prev: float | None = None
    alpha_hold: float | None = None
    v_hold: float | None = None
    az0: float | None = None
    delta_sp = np.zeros(3, dtype=float)
    z_sp = np.zeros(4, dtype=float)
    dt_ofk2 = float(dt_ofk2)
    step_ofk2 = max(1, int(round(dt_ofk2 / dt)))

    step_gnss = max(1, int(round(dt_gnss / dt)))
    n_gnss = int(tmodel / dt_gnss) + 1

    log = {
        "time": np.zeros(n_gnss),
        "true_h": np.zeros(n_gnss),
        "true_fi": np.zeros(n_gnss),
        "true_lam": np.zeros(n_gnss),
        "true_vn": np.zeros(n_gnss),
        "true_ve": np.zeros(n_gnss),
        "true_vh": np.zeros(n_gnss),
        "bins_h": np.zeros(n_gnss),
        "bins_fi": np.zeros(n_gnss),
        "bins_lam": np.zeros(n_gnss),
        "bins_vn": np.zeros(n_gnss),
        "bins_ve": np.zeros(n_gnss),
        "bins_vh": np.zeros(n_gnss),
        "ofk_h": np.zeros(n_gnss),
        "ofk_fi": np.zeros(n_gnss),
        "ofk_lam": np.zeros(n_gnss),
        "ofk_vn": np.zeros(n_gnss),
        "ofk_ve": np.zeros(n_gnss),
        "ofk_vh": np.zeros(n_gnss),
        "gnss_fi": np.full(n_gnss, np.nan),
        "gnss_lam": np.full(n_gnss, np.nan),
        "gnss_h": np.full(n_gnss, np.nan),
        "gnss_vn": np.full(n_gnss, np.nan),
        "gnss_ve": np.full(n_gnss, np.nan),
        "gnss_vh": np.full(n_gnss, np.nan),
        "ofk_std_fi": np.zeros(n_gnss),
        "ofk_std_lam": np.zeros(n_gnss),
        "ofk_std_h": np.zeros(n_gnss),
        "ofk_std_vn": np.zeros(n_gnss),
        "ofk_std_ve": np.zeros(n_gnss),
        "ofk_std_vh": np.zeros(n_gnss),
        "err_bins_fi": np.zeros(n_gnss),
        "err_bins_lam": np.zeros(n_gnss),
        "err_bins_vn": np.zeros(n_gnss),
        "err_bins_ve": np.zeros(n_gnss),
        "err_bins_vh": np.zeros(n_gnss),
        "err_bins_h": np.zeros(n_gnss),
        "err_ofk_fi": np.zeros(n_gnss),
        "err_ofk_lam": np.zeros(n_gnss),
        "err_ofk_vn": np.zeros(n_gnss),
        "err_ofk_ve": np.zeros(n_gnss),
        "err_ofk_vh": np.zeros(n_gnss),
        "err_ofk_h": np.zeros(n_gnss),
        "u": np.zeros((4, n_gnss)),
        # --- ОФК-2 (короткопериод α–q–az, L*/M*) ---
        "sp_alpha": np.zeros(n_gnss),
        "sp_q": np.zeros(n_gnss),
        "sp_de": np.zeros(n_gnss),
        "sp_az": np.zeros(n_gnss),
        "sp_params": np.zeros((N_PARAM, n_gnss)),
        "sp_delta": np.zeros((3, n_gnss)),
        "sp_z": np.zeros((4, n_gnss)),
        "z_nav": np.zeros((6, n_gnss)),
        "true_alpha": np.zeros(n_gnss),
        "true_q": np.zeros(n_gnss),
        "true_az": np.zeros(n_gnss),
        "d_params": np.zeros((N_PARAM, n_gnss)),
    }

    ap_count = 0
    ap_steps = int(0.01 / dt)
    gnss_idx = 0
    a_last = np.zeros(3, dtype=float)
    n_steps = int(tmodel / dt)

    for i in range(n_steps):
        t = (i + 1) * dt
        # --------------------------------------------------------------
        # ЭТАП 1. Модель полёта FX1 → «идеальные» выходы инерциальных датчиков
        # --------------------------------------------------------------
        # x — истинное состояние ЛА (25 компонент)
        # wbi_b  — ω истинная, связанная СК  → вход идеального ДУС
        # af_bi_b — a без g, связанная СК     → вход идеального ДЛУ
        fx1 = lambda x, u, t: fx1_func(x, u, t, la)
        result = rk4_step(fx1, t - dt, dt, x, u)
        x = result[0]
        af_bi_b = result[2]
        wbi_b = result[3]

        # Эталон для сравнения с решением БИНС
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
            )

        # --------------------------------------------------------------
        # ЭТАП 2. Ошибки приборов (ДУС + ДЛУ) — InsErrorGen.generate
        # --------------------------------------------------------------
        # w_m, a_m — то, что «видит» алгоритм БИНС на этом шаге
        w_m, a_m = gen.generate(wbi_b, af_bi_b)

        # --------------------------------------------------------------
        # ЭТАП 3. Механизация БИНС — bins_step (интегрирование INS)
        # --------------------------------------------------------------
        # Вход:  зашумлённые w_m, a_m + текущие q, Cbn, np_bins
        # Выход: обновлённые q, Cbn, np_bins = [Vn,Vh,Ve,h,φ,λ]
        # a_last сохраняется для матриц ОФК на такте ГНСС
        q, cbn, np_bins, a_last = bins_step(a_m, w_m, np_bins, cbn, q, dt)

        if (i + 1) % step_gnss == 0:
            # ----------------------------------------------------------
            # ЭТАП 4a. Снимок БИНС ДО коррекции ОФК (для лога err_bins_*)
            # ----------------------------------------------------------
            np_pre = np_bins.copy()

            # ----------------------------------------------------------
            # ЭТАП 4b. ГНСС — ошибки на измерениях PVT (отдельно от INS!)
            # ----------------------------------------------------------
            # Истина: x[12],x[13],x[10] и v_nav → добавляется гауссов шум
            np_gnss, v_gnss = gnss(
                x[12], x[13], x[10], v_nav[0], v_nav[2], v_nav[1], rng=rng_gnss
            )

            # Первый такт: грубое выравнивание БИНС по ГНСС (скорости + высота)
            if gnss_idx == 0:
                np_bins[0] = np_gnss[3]  # Vn
                np_bins[2] = np_gnss[4]  # Ve
                np_bins[1] = np_gnss[5]  # Vh
                np_bins[3] = np_gnss[2]  # h
                np_pre = np_bins.copy()

            # ----------------------------------------------------------
            # ЭТАП 4c. ОФК-1: z = BINS − GNSS → поправка np_bins
            # ----------------------------------------------------------
            z = build_innovation(np_bins, np_gnss)
            x_ofk, p_ofk = ofk_step(
                a_last, cbn, np_bins, z, x_ofk, p_ofk, v_gnss, dt_gnss
            )
            apply_bins_feedback(np_bins, x_ofk)
            x_ofk[:] = 0.0  # error-state reset после обратной связи

            # α, V из БНК после ОФК-1 — входы ОФК-2
            alpha_hold, v_hold = reconstruct_alpha_from_nav(np_bins, cbn)
            q_meas = float(w_m[2])
            az_meas = float(a_m[1]) / G0
            de_meas = float(x[16]) * np.pi / 180.0
            if az0 is None:
                az0 = az_meas
            z_sp = build_z_kinematics(alpha_hold, q_meas, de_meas, az_meas, trim)

            np_etalon = np.array(
                [v_nav[0], v_nav[1], v_nav[2], x[10], x[12], x[13]], dtype=float
            )
            nper_pre = np_pre - np_etalon
            nper_post = np_bins - np_etalon

            true_alpha = float(-np.arctan2(x[1], x[0] if abs(x[0]) > 1e-9 else 1e-9))
            true_q = float(x[5])
            true_az = float(af_bi_b[1]) / G0

            log["time"][gnss_idx] = t
            log["true_h"][gnss_idx] = x[10]
            log["true_fi"][gnss_idx] = x[12]
            log["true_lam"][gnss_idx] = x[13]
            log["true_vn"][gnss_idx] = v_nav[0]
            log["true_ve"][gnss_idx] = v_nav[2]
            log["true_vh"][gnss_idx] = v_nav[1]
            log["bins_h"][gnss_idx] = np_pre[3]
            log["bins_fi"][gnss_idx] = np_pre[4]
            log["bins_lam"][gnss_idx] = np_pre[5]
            log["bins_vn"][gnss_idx] = np_pre[0]
            log["bins_ve"][gnss_idx] = np_pre[2]
            log["bins_vh"][gnss_idx] = np_pre[1]
            log["ofk_h"][gnss_idx] = np_bins[3]
            log["ofk_fi"][gnss_idx] = np_bins[4]
            log["ofk_lam"][gnss_idx] = np_bins[5]
            log["ofk_vn"][gnss_idx] = np_bins[0]
            log["ofk_ve"][gnss_idx] = np_bins[2]
            log["ofk_vh"][gnss_idx] = np_bins[1]
            log["gnss_fi"][gnss_idx] = np_gnss[0]
            log["gnss_lam"][gnss_idx] = np_gnss[1]
            log["gnss_h"][gnss_idx] = np_gnss[2]
            log["gnss_vn"][gnss_idx] = np_gnss[3]
            log["gnss_ve"][gnss_idx] = np_gnss[4]
            log["gnss_vh"][gnss_idx] = np_gnss[5]
            log["ofk_std_fi"][gnss_idx] = np.sqrt(p_ofk[5, 5])
            log["ofk_std_lam"][gnss_idx] = np.sqrt(p_ofk[6, 6])
            log["ofk_std_h"][gnss_idx] = np.sqrt(p_ofk[14, 14])
            log["ofk_std_vn"][gnss_idx] = np.sqrt(p_ofk[3, 3])
            log["ofk_std_ve"][gnss_idx] = np.sqrt(p_ofk[4, 4])
            log["ofk_std_vh"][gnss_idx] = np.sqrt(p_ofk[13, 13])
            log["err_bins_fi"][gnss_idx] = nper_pre[4]
            log["err_bins_lam"][gnss_idx] = nper_pre[5]
            log["err_bins_h"][gnss_idx] = nper_pre[3]
            log["err_bins_vn"][gnss_idx] = nper_pre[0]
            log["err_bins_ve"][gnss_idx] = nper_pre[2]
            log["err_bins_vh"][gnss_idx] = nper_pre[1]
            log["err_ofk_fi"][gnss_idx] = nper_post[4]
            log["err_ofk_lam"][gnss_idx] = nper_post[5]
            log["err_ofk_h"][gnss_idx] = nper_post[3]
            log["err_ofk_vn"][gnss_idx] = nper_post[0]
            log["err_ofk_ve"][gnss_idx] = nper_post[2]
            log["err_ofk_vh"][gnss_idx] = nper_post[1]
            log["u"][:, gnss_idx] = u
            log["z_nav"][:, gnss_idx] = z
            log["sp_z"][:, gnss_idx] = z_sp
            log["sp_delta"][:, gnss_idx] = delta_sp
            log["sp_alpha"][gnss_idx] = alpha_hold
            log["sp_q"][gnss_idx] = q_meas
            log["sp_de"][gnss_idx] = de_meas
            log["sp_az"][gnss_idx] = az_meas
            log["sp_params"][:, gnss_idx] = x_sp[:N_PARAM]
            log["true_alpha"][gnss_idx] = true_alpha
            log["true_q"][gnss_idx] = true_q
            log["true_az"][gnss_idx] = true_az
            d_coeff = coeff_delta_ekf_minus_theory(x_sp, th_vec)
            log["d_params"][:, gnss_idx] = d_coeff
            gnss_idx += 1

        # --------------------------------------------------------------
        # ЭТАП 5. ОФК-2 short-period @ dt_ofk2 (после ОФК-1, если он был)
        # α,V — hold с последнего ГНСС/ОФК-1; q, az — ДУС/ДЛУ; δe — привод
        # --------------------------------------------------------------
        if alpha_hold is not None and (i + 1) % step_ofk2 == 0:
            q_meas = float(w_m[2])
            az_meas = float(a_m[1]) / G0
            de_meas = float(x[16]) * np.pi / 180.0
            da = float(alpha_hold) - trim["alpha0"]
            dde = de_meas - trim["delta_e0"]
            if az0 is None:
                az0 = az_meas
            z_sp = build_z_kinematics(alpha_hold, q_meas, de_meas, az_meas, trim)
            (
                x_sp,
                p_sp,
                delta_sp,
                a_smooth,
                a_smooth_prev,
                q_smooth,
                q_smooth_prev,
            ) = sp_ekf_step(
                x_sp,
                p_sp,
                da=da,
                q=q_meas,
                dde=dde,
                az=az_meas,
                v=float(v_hold),
                az0=float(az0),
                dt=dt_ofk2,
                alpha_smooth=a_smooth,
                alpha_smooth_prev=a_smooth_prev,
                q_smooth=q_smooth,
                q_smooth_prev=q_smooth_prev,
            )
            # на такте ГНСС лог уже записан до шага ОФК-2 — обновить оценки
            if (i + 1) % step_gnss == 0 and gnss_idx > 0:
                j = gnss_idx - 1
                log["sp_params"][:, j] = x_sp[:N_PARAM]
                log["sp_delta"][:, j] = delta_sp
                log["sp_z"][:, j] = z_sp
                log["d_params"][:, j] = coeff_delta_ekf_minus_theory(x_sp, th_vec)

        if i % 20000 == 0:
            v = np.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2)
            print(f"t={t:.1f}s  H={x[10]:.1f}m  V={v:.1f}m/s  Vn={v_nav[0]:.2f}m/s")

    out = {}
    for k, v in log.items():
        arr = np.asarray(v)
        if arr.ndim == 2:
            out[k] = arr[:, :gnss_idx].copy()
        else:
            out[k] = arr[:gnss_idx]
    out["u0"] = np.asarray(sim["u0"], dtype=float).copy()
    out["bal"] = np.asarray(sim["bal"], dtype=float).copy()
    out["sp_theory"] = {k: float(v) for k, v in sp_theory.items()}
    out["sp_theory_vec"] = th_vec.copy()
    return out


if __name__ == "__main__":
    data = run_simulation(tmodel=60.0, dt=1e-3, dt_gnss=0.1)
    print(f"Симуляция завершена: {len(data['time'])} точек лога")
