"""
ОФК-2 (второй фильтр): продольная модель + идентификация L*, M*.

Линеаризация вокруг балансировки (α₀, δe₀), q₀ = 0::

    α̇  = L_α (α−α₀) + L_q q + L_δe (δe−δe₀)
    q̇  = M_α (α−α₀) + M_q q + M_δe (δe−δe₀)
    L̇* = Ṁ* = 0

Наблюдения (E.2) тоже в приращениях от trim.

Состояние (9)::

    [α, q, δe, L_α, L_q, L_δe, M_α, M_q, M_δe]
"""

from __future__ import annotations

import numpy as np

# Индексы состояния
I_A, I_Q, I_DE = 0, 1, 2
I_LA, I_LQ, I_LDE = 3, 4, 5
I_MA, I_MQ, I_MDE = 6, 7, 8
N_STATE = 9
N_MEAS = 4

G0 = 9.80665


def initial_state(
    alpha0: float,
    q0: float,
    delta_e0: float,
    *,
    la_nom: float,
    lq_nom: float,
    lde_nom: float,
    ma_nom: float,
    mq_nom: float,
    mde_nom: float,
) -> np.ndarray:
    """
    Начальная оценка ОФК-2.

    L*, M* — **обязательно** из якобиана FX1 (`ofk2_theory.ofk2_jacobian_at_trim`),
    не из эвристических констант. Дефолтов для коэффициентов нет.
    """
    return np.array(
        [
            float(alpha0),
            float(q0),
            float(delta_e0),
            float(la_nom),
            float(lq_nom),
            float(lde_nom),
            float(ma_nom),
            float(mq_nom),
            float(mde_nom),
        ],
        dtype=float,
    )


def initial_covariance() -> np.ndarray:
    """
    P₀ — настройка ковариации фильтра (не аэродинамика).

    Не из якобиана: задаёт, насколько фильтр «доверяет» стартовой оценке.
    """
    sig = np.array(
        [
            0.02,    # α, рад
            0.02,    # q, рад/с
            0.02,    # δe, рад (известен из привода)
            0.05,    # Lα
            0.05,    # Lq
            0.05,    # Lδe
            0.08,    # Mα
            0.08,    # Mq
            0.08,    # Mδe
        ],
        dtype=float,
    )
    return np.diag(sig**2)


def process_noise(dt: float) -> np.ndarray:
    """Q — настройка процесса. Малый шум по L*, M* — чтобы оценки не замирали при Q≡0."""
    qa = 5.0e-5 * dt
    qq = 5.0e-5 * dt
    q_de = 1.0e-6 * dt
    q_c = 1.0e-6 * dt  # слабый random-walk по коэффициентам
    return np.diag([qa, qq, q_de, q_c, q_c, q_c, q_c, q_c, q_c])


def measurement_covariance(
    sigma_a: float = 0.015,
    sigma_q: float = 0.008,
    sigma_az: float = 1.0e6,
    sigma_qdot: float = 1.0,
) -> np.ndarray:
    """R — настройка доверия к измерениям (не якобиан). a_z по умолчанию отключён."""
    return np.diag(
        np.array([sigma_a, sigma_q, sigma_az, sigma_qdot], dtype=float) ** 2
    )


def adaptive_az_trim(
    az_meas: float,
    v: float,
    da: float,
    q: float,
    dde: float,
    la: float,
    lq: float,
    lde: float,
    g: float = G0,
) -> float:
    """
    Подстройка az_trim так, чтобы при текущих L* предсказание a_z совпало с ДЛУ.

    Убирает структурный сдвиг δ_a_z при уходе режима от начальной балансировки.
    """
    v = max(float(v), 1.0)
    return float(az_meas) + (v / g) * (
        float(la) * da + (float(lq) - 1.0) * q + float(lde) * dde
    )


def _inc(x: np.ndarray, trim: tuple[float, float]) -> tuple[float, float, float]:
    """Приращения от балансировки: δα, q, δδe."""
    a0, de0 = trim
    return float(x[I_A] - a0), float(x[I_Q]), float(x[I_DE] - de0)


def dyn_f(x: np.ndarray, trim: tuple[float, float]) -> np.ndarray:
    """Правая часть E.1 в приращениях от trim."""
    da, q, dde = _inc(x, trim)
    la, lq, lde = x[I_LA], x[I_LQ], x[I_LDE]
    ma, mq, mde = x[I_MA], x[I_MQ], x[I_MDE]
    return np.array(
        [
            la * da + lq * q + lde * dde,
            ma * da + mq * q + mde * dde,
            0.0,  # δe задаётся измерением привода
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ],
        dtype=float,
    )


def jacobian_f(x: np.ndarray, trim: tuple[float, float]) -> np.ndarray:
    """Jacobian ∂f/∂x для E.1 (приращения)."""
    da, q, dde = _inc(x, trim)
    la, lq, lde = x[I_LA], x[I_LQ], x[I_LDE]
    ma, mq, mde = x[I_MA], x[I_MQ], x[I_MDE]
    f = np.zeros((N_STATE, N_STATE), dtype=float)
    # α̇
    f[I_A, I_A] = la
    f[I_A, I_Q] = lq
    f[I_A, I_DE] = lde
    f[I_A, I_LA] = da
    f[I_A, I_LQ] = q
    f[I_A, I_LDE] = dde
    # q̇
    f[I_Q, I_A] = ma
    f[I_Q, I_Q] = mq
    f[I_Q, I_DE] = mde
    f[I_Q, I_MA] = da
    f[I_Q, I_MQ] = q
    f[I_Q, I_MDE] = dde
    return f


def meas_h(
    x: np.ndarray,
    v: float,
    d: float,
    trim: tuple[float, float],
    az_trim: float = 0.0,
    g: float = G0,
) -> np.ndarray:
    """Наблюдения E.2: α, q абсолютные; a_z и q̇ — от приращений + az_trim."""
    da, q, dde = _inc(x, trim)
    a, de = x[I_A], x[I_DE]
    la, lq, lde = x[I_LA], x[I_LQ], x[I_LDE]
    ma, mq, mde = x[I_MA], x[I_MQ], x[I_MDE]
    v = max(float(v), 1.0)
    alpha_m = a - (d / v) * q
    q_m = q
    az_m = float(az_trim) - (v / g) * (la * da + (lq - 1.0) * q + lde * dde)
    qdot_m = ma * da + mq * q + mde * dde
    return np.array([alpha_m, q_m, az_m, qdot_m], dtype=float)


def jacobian_h(
    x: np.ndarray,
    v: float,
    d: float,
    trim: tuple[float, float],
    g: float = G0,
) -> np.ndarray:
    """Jacobian ∂h/∂x для E.2."""
    da, q, dde = _inc(x, trim)
    la, lq, lde = x[I_LA], x[I_LQ], x[I_LDE]
    ma, mq, mde = x[I_MA], x[I_MQ], x[I_MDE]
    v = max(float(v), 1.0)
    h = np.zeros((N_MEAS, N_STATE), dtype=float)
    h[0, I_A] = 1.0
    h[0, I_Q] = -d / v
    h[1, I_Q] = 1.0
    k = -(v / g)
    h[2, I_A] = k * la
    h[2, I_Q] = k * (lq - 1.0)
    h[2, I_DE] = k * lde
    h[2, I_LA] = k * da
    h[2, I_LQ] = k * q
    h[2, I_LDE] = k * dde
    h[3, I_A] = ma
    h[3, I_Q] = mq
    h[3, I_DE] = mde
    h[3, I_MA] = da
    h[3, I_MQ] = q
    h[3, I_MDE] = dde
    return h


def build_z_from_bins(
    alpha_meas: float,
    q_meas: float,
    az_meas: float,
    qdot_meas: float,
) -> np.ndarray:
    return np.array(
        [float(alpha_meas), float(q_meas), float(az_meas), float(qdot_meas)],
        dtype=float,
    )


def reconstruct_alpha_from_nav(np_bins: np.ndarray, cbn: np.ndarray) -> tuple[float, float]:
    v_n = np.array([np_bins[0], np_bins[1], np_bins[2]], dtype=float)
    v_b = np.asarray(cbn, dtype=float).T @ v_n
    vx, vy = float(v_b[0]), float(v_b[1])
    v = float(np.linalg.norm(v_b))
    v = max(v, 1.0)
    alpha = -np.arctan2(vy, vx if abs(vx) > 1e-9 else 1e-9)
    return alpha, v


def ekf_step(
    x: np.ndarray,
    p: np.ndarray,
    z: np.ndarray,
    v: float,
    dt: float,
    *,
    trim: tuple[float, float],
    az_trim: float = 0.0,
    theory_coeffs: np.ndarray | None = None,
    anchor_sigma: float = 1.0e-4,
    d: float = 0.0,
    r: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Один шаг второго EKF.

    ``theory_coeffs`` — [Lα,Lq,Lδe,Mα,Mq,Mδe]: псевдоизмерение-якорь,
    удерживает коэффициенты у теории (Δ не ползёт на длинном горизонте).
    """
    x = np.asarray(x, dtype=float).reshape(N_STATE)
    p = np.asarray(p, dtype=float)
    z = np.asarray(z, dtype=float).reshape(N_MEAS)
    if r is None:
        r = measurement_covariance()

    f_jac = jacobian_f(x, trim)
    phi = np.eye(N_STATE) + f_jac * dt + ((f_jac * dt) @ (f_jac * dt)) / 2.0
    x_pred = x + dyn_f(x, trim) * dt
    q_mat = process_noise(dt)
    p_pred = phi @ p @ phi.T + q_mat
    p_pred = 0.5 * (p_pred + p_pred.T)

    h_jac = jacobian_h(x_pred, v, d, trim)
    z_pred = meas_h(x_pred, v, d, trim, az_trim=az_trim)
    delta = z - z_pred

    ph_t = p_pred @ h_jac.T
    s = h_jac @ ph_t + r
    s = 0.5 * (s + s.T)
    k = np.linalg.solve(s, ph_t.T).T
    x_new = x_pred + k @ delta
    ik = np.eye(N_STATE) - k @ h_jac
    p_new = ik @ p_pred @ ik.T + k @ r @ k.T
    p_new = 0.5 * (p_new + p_new.T)

    # Якорь: θ̂_coeff ≈ θ_theory (псевдоизмерение с малым R)
    if theory_coeffs is not None:
        th = np.asarray(theory_coeffs, dtype=float).reshape(6)
        h_a = np.zeros((6, N_STATE), dtype=float)
        h_a[0, I_LA] = 1.0
        h_a[1, I_LQ] = 1.0
        h_a[2, I_LDE] = 1.0
        h_a[3, I_MA] = 1.0
        h_a[4, I_MQ] = 1.0
        h_a[5, I_MDE] = 1.0
        r_a = np.diag(np.full(6, float(anchor_sigma) ** 2))
        z_a = th - h_a @ x_new
        ph_t_a = p_new @ h_a.T
        s_a = h_a @ ph_t_a + r_a
        s_a = 0.5 * (s_a + s_a.T)
        k_a = np.linalg.solve(s_a, ph_t_a.T).T
        x_new = x_new + k_a @ z_a
        ik_a = np.eye(N_STATE) - k_a @ h_a
        p_new = ik_a @ p_new @ ik_a.T + k_a @ r_a @ k_a.T
        p_new = 0.5 * (p_new + p_new.T)

    delta = z - meas_h(x_new, v, d, trim, az_trim=az_trim)
    return x_new, p_new, delta
