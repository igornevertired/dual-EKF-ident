"""
ОФК-2 — фильтр идентификации: расширенный фильтр Калмана с расширенным вектором состояния.

Модель — система (15) в обозначениях L/M/X/Θ (отклонения от балансировки)::

    ΔV̇  = Xα Δα + Xδe Δδe + Xv ΔV + Xθ Δθ + Xδt ΔδT      (ΔδT — известный вход тяги)
    Δα̇  = Lα Δα + Lq Δωz + Lδe Δδe + Lv ΔV + Lθ Δθ       (Lq ≡ 1)
    Δθ̇  = Θα Δα + Θδe Δδe + Θv ΔV + Θθ Δθ
    Δω̇z = Mα Δα + Mq Δωz + Mδe Δδe + Mv ΔV + Mθ Δθ + Mδė Δδ̇e

Вектор состояния x (24) = [20 коэффициентов (порядок PARAM_NAMES), Δα, Δωz, ΔV, Δθ].
Измерение Z = [Δα, Δωz, ΔV, Δθ] по выходам ОФК-1; θ — угол наклона траектории,
tg θ = Vy / √(Vx² + Vz²).

Шаг фильтра (``ekf_step``):
  1. замороженные коэффициенты ← значения балансировки;
  2. прогноз движения методом РК4 (4 подшага, δe и δT интерполируются внутри шага);
  3. матрица перехода F — центральными разностями оператора прогноза;
  4. коррекция по невязке, ковариация — в форме Джозефа.

Какие коэффициенты оцениваются, задаёт аргумент ``estimated`` (индексы в PARAM_NAMES);
по умолчанию — ESTIMATED_PARAM_INDICES из ofk2_theory.
"""

from __future__ import annotations

from typing import NamedTuple, Sequence

import numpy as np

from .ofk2_theory import ESTIMATED_PARAM_INDICES, N_L, N_M, N_TH, N_X, PARAM_NAMES, path_angle_from_nav

# --- размерности и индексы ---------------------------------------------------
N_PARAM = len(PARAM_NAMES)
N_MOTION = 4
N_STATE = N_PARAM + N_MOTION
N_MEAS = 4
I_DA, I_DQ, I_DV, I_DTH = N_PARAM, N_PARAM + 1, N_PARAM + 2, N_PARAM + 3
G0 = 9.80665

_I_L = slice(0, N_L)
_I_M = slice(N_L, N_L + N_M)
_I_X = slice(N_L + N_M, N_L + N_M + N_X)
_I_T = slice(N_L + N_M + N_X, N_L + N_M + N_X + N_TH)
_I_XDT = PARAM_NAMES.index("Xδt")
_N_SUB = 4  # подшагов РК4 на такт

# --- настройка фильтра -------------------------------------------------------
# начальные дисперсии и шум процесса переменных движения [Δα, Δωz, ΔV, Δθ]
_P0_MOTION = (0.03**2, 0.03**2, 1.0**2, 0.03**2)
_Q_MOTION = (1.0e-8, 1.0e-8, 1.0e-4, 1.0e-8)

# нижняя граница масштаба коэффициентов (для P₀ и стартового сдвига малых коэффициентов)
COEFF_ABS_FLOOR = np.array(
    [
        0.05, 0.05, 0.02, 0.01, 0.05,           # L
        0.05, 0.05, 0.05, 0.01, 0.05, 0.05,     # M
        0.05, 0.02, 0.01, 0.50,                 # X
        0.05, 0.02, 0.01, 0.05,                 # Θ
        0.05,                                   # Xδt
    ],
    dtype=float,
)
_ABS_FLOOR = COEFF_ABS_FLOOR  # прежнее имя


def frozen_indices(estimated: Sequence[int]) -> np.ndarray:
    """Индексы коэффициентов, которые не оцениваются (держатся на балансировке)."""
    est = set(int(i) for i in estimated)
    return np.array([i for i in range(N_PARAM) if i not in est], dtype=int)


# ---------------------------------------------------------------------------
# Начальные условия и шумы
# ---------------------------------------------------------------------------
def initial_state(param0: np.ndarray, da: float = 0.0, dq: float = 0.0, dv: float = 0.0, dth: float = 0.0) -> np.ndarray:
    x = np.zeros(N_STATE, dtype=float)
    x[:N_PARAM] = np.asarray(param0, dtype=float).reshape(N_PARAM)
    x[I_DA], x[I_DQ], x[I_DV], x[I_DTH] = float(da), float(dq), float(dv), float(dth)
    return x


def initial_covariance(
    param0: np.ndarray | None = None,
    *,
    coeff_start_err: float = 0.3,
    scale_ref: np.ndarray | None = None,
    estimated: Sequence[int] = ESTIMATED_PARAM_INDICES,
) -> np.ndarray:
    """P₀: для коэффициентов 1σ = ожидаемая стартовая ошибка (coeff_start_err·|эталон|)."""
    ref = scale_ref if scale_ref is not None else param0
    ref = np.asarray(ref, dtype=float).reshape(N_PARAM)
    sig = np.maximum(np.abs(ref) * float(coeff_start_err), COEFF_ABS_FLOOR * 0.2)
    sig[frozen_indices(estimated)] = 0.0
    p = np.zeros((N_STATE, N_STATE), dtype=float)
    p[:N_PARAM, :N_PARAM] = np.diag(sig**2)
    for k, var in enumerate(_P0_MOTION):
        p[N_PARAM + k, N_PARAM + k] = var
    return p


def process_noise(*, q_std: float = 0.0, estimated: Sequence[int] = ESTIMATED_PARAM_INDICES) -> np.ndarray:
    """Q: шум переменных движения + (опционально) шум q_std² по оцениваемым коэффициентам."""
    q = np.zeros((N_STATE, N_STATE), dtype=float)
    for k, var in enumerate(_Q_MOTION):
        q[N_PARAM + k, N_PARAM + k] = var
    qc = float(q_std)
    if qc > 0.0:
        for i in estimated:
            q[i, i] = qc * qc
    return q


def measurement_covariance(
    sigma_alpha: float = 1.0e-4,
    sigma_q: float = 5.0e-5,
    sigma_v: float = 0.01,
    sigma_theta: float = 1.0e-4,
) -> np.ndarray:
    """R: σ ≈ 3–5 × фактической ошибки сигналов после ОФК-1 (α 3e-5 рад, q 1e-5 рад/с, V 3e-3 м/с, θ 4e-5 рад)."""
    return np.diag(np.array([sigma_alpha, sigma_q, sigma_v, sigma_theta], dtype=float) ** 2)


def _pin_frozen(x: np.ndarray, p: np.ndarray, param_fixed: np.ndarray | None, frozen: np.ndarray):
    """Замороженные коэффициенты ← значения балансировки; их строки и столбцы P ← 0."""
    if param_fixed is None:
        return x, p
    fixed = np.asarray(param_fixed, dtype=float).reshape(N_PARAM)
    x = x.copy()
    x[frozen] = fixed[frozen]
    p = p.copy()
    p[frozen, :] = 0.0
    p[:, frozen] = 0.0
    return x, p


# ---------------------------------------------------------------------------
# Измерения
# ---------------------------------------------------------------------------
def reconstruct_alpha_from_nav(np_bins: np.ndarray, cbn: np.ndarray) -> tuple[float, float]:
    """Угол атаки и модуль скорости по навигационной скорости [Vn, Vh, Ve] и Cbn."""
    v_n = np.array([np_bins[0], np_bins[1], np_bins[2]], dtype=float)
    v_b = np.asarray(cbn, dtype=float).T @ v_n
    vx, vy = float(v_b[0]), float(v_b[1])
    v = max(float(np.linalg.norm(v_b)), 1.0)
    alpha = -np.arctan2(vy, vx if abs(vx) > 1e-9 else 1e-9)
    return float(alpha), v


def reconstruct_path_angle_from_nav(np_cons: np.ndarray) -> float:
    """Угол наклона траектории: tg θ = Vh / √(Vn² + Ve²)."""
    npv = np.asarray(np_cons, dtype=float).reshape(-1)
    return path_angle_from_nav(float(npv[0]), float(npv[1]), float(npv[2]))


class Ofk2Signals(NamedTuple):
    alpha: float
    v: float
    theta: float
    q: float
    az: float
    de: float
    da: float
    dq: float
    dde: float
    dv: float
    dtheta: float
    ddt: float = 0.0


def signals_from_sensors(
    np_cons: np.ndarray,
    cbn: np.ndarray,
    w_cons: np.ndarray,
    a_m: np.ndarray,
    de_deg: float,
    trim: dict[str, float],
    throttle: float | None = None,
) -> Ofk2Signals:
    """Сигналы ОФК-2: α, V из NP+Cbn; q из ДУС; θ из NP ОФК-1; δe, δT — приводы; и их отклонения от балансировки."""
    alpha, v = reconstruct_alpha_from_nav(np_cons, cbn)
    theta = reconstruct_path_angle_from_nav(np_cons)
    q = float(np.asarray(w_cons, dtype=float).reshape(3)[2])
    az = float(np.asarray(a_m, dtype=float).reshape(3)[1]) / G0
    de = float(de_deg) * np.pi / 180.0
    return Ofk2Signals(
        alpha=alpha, v=v, theta=theta, q=q, az=az, de=de,
        da=alpha - trim["alpha0"],
        dq=q - trim["q0"],
        dde=de - trim["delta_e0"],
        dv=v - trim["v0"],
        dtheta=theta - trim["theta0"],
        ddt=0.0 if throttle is None else float(throttle) - trim.get("delta_t0", 0.0),
    )


def build_z_kinematics(alpha: float, q: float, v: float, theta: float, delta_e: float, trim: dict[str, float]) -> np.ndarray:
    """Измерение Z = [Δα, Δωz, ΔV, Δθ] (delta_e не используется, оставлен для совместимости)."""
    del delta_e
    return np.array(
        [alpha - trim["alpha0"], q - trim["q0"], v - trim["v0"], theta - trim["theta0"]],
        dtype=float,
    )


def _predict_z(x: np.ndarray) -> np.ndarray:
    return np.array([x[I_DA], x[I_DQ], x[I_DV], x[I_DTH]], dtype=float)


def _meas_jacobian() -> np.ndarray:
    h = np.zeros((N_MEAS, N_STATE), dtype=float)
    h[0, I_DA] = h[1, I_DQ] = h[2, I_DV] = h[3, I_DTH] = 1.0
    return h


# ---------------------------------------------------------------------------
# Модель движения и прогноз
# ---------------------------------------------------------------------------
def _rhs(par: np.ndarray, s: np.ndarray, dde: float, dde_dot: float, ddt: float) -> np.ndarray:
    """Правая часть системы (15) + Xδt ΔδT. s = [Δα, Δωz, ΔV, Δθ]."""
    da, dq, dv, dth = s
    l, m, xx, tt = par[_I_L], par[_I_M], par[_I_X], par[_I_T]
    da_dot = l @ np.array([da, dq, dde, dv, dth])                      # Lα Lq Lδe Lv Lθ
    dq_dot = m @ np.array([da, dq, dde, dv, dth, dde_dot])             # Mα Mq Mδe Mv Mθ Mδė
    dv_dot = xx @ np.array([da, dde, dv, dth]) + par[_I_XDT] * ddt     # Xα Xδe Xv Xθ + тяга
    dth_dot = tt @ np.array([da, dde, dv, dth])                        # Θα Θδe Θv Θθ
    return np.array([da_dot, dq_dot, dv_dot, dth_dot], dtype=float)


def _propagate(x: np.ndarray, dt: float, dde0: float, dde1: float, ddt0: float, ddt1: float, dde_dot: float) -> np.ndarray:
    """Прогноз переменных движения на шаг dt: РК4 на _N_SUB подшагах, δe и δT — линейно между отсчётами k−1 и k.

    (Эйлер на dt = 0,2 с при |λ_КП| ≈ 0,8 1/с и δe на конце интервала давал смещение M*, L* на 10–20 %.)
    """
    par = x[:N_PARAM]
    s = x[N_PARAM:].copy()
    h = dt / _N_SUB
    for j in range(_N_SUB):
        ta, tm, tb = j / _N_SUB, (j + 0.5) / _N_SUB, (j + 1) / _N_SUB
        de_a, de_m, de_b = (dde0 + (dde1 - dde0) * c for c in (ta, tm, tb))
        dt_a, dt_m, dt_b = (ddt0 + (ddt1 - ddt0) * c for c in (ta, tm, tb))
        k1 = _rhs(par, s, de_a, dde_dot, dt_a)
        k2 = _rhs(par, s + 0.5 * h * k1, de_m, dde_dot, dt_m)
        k3 = _rhs(par, s + 0.5 * h * k2, de_m, dde_dot, dt_m)
        k4 = _rhs(par, s + h * k3, de_b, dde_dot, dt_b)
        s = s + h / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    x_pred = x.copy()
    x_pred[N_PARAM:] = s
    return x_pred


def _predict(x, dt, dde, dde_dot, dde_prev, ddt, ddt_prev, estimated):
    """Прогноз состояния и численная матрица перехода F (по оцениваемым коэффициентам и движению)."""
    dde0 = float(dde) if dde_prev is None else float(dde_prev)
    ddt0 = float(ddt) if ddt_prev is None else float(ddt_prev)
    args = (float(dt), dde0, float(dde), ddt0, float(ddt), float(dde_dot))
    x_pred = _propagate(x, *args)
    f = np.eye(N_STATE, dtype=float)
    for i in list(estimated) + [I_DA, I_DQ, I_DV, I_DTH]:
        e = 1.0e-6 * max(1.0, abs(float(x[i])))
        xp, xm = x.copy(), x.copy()
        xp[i] += e
        xm[i] -= e
        f[:, i] = (_propagate(xp, *args) - _propagate(xm, *args)) / (2.0 * e)
    return x_pred, f


# ---------------------------------------------------------------------------
# Шаг фильтра
# ---------------------------------------------------------------------------
def ekf_step(
    x: np.ndarray,
    p: np.ndarray,
    *,
    da: float,
    dq: float,
    dv: float,
    dde: float,
    dt: float,
    dtheta: float = 0.0,
    dde_dot: float = 0.0,
    dde_prev: float | None = None,
    ddt: float = 0.0,
    ddt_prev: float | None = None,
    param_fixed: np.ndarray | None = None,
    r: np.ndarray | None = None,
    q_std: float = 0.0,
    estimated: Sequence[int] = ESTIMATED_PARAM_INDICES,
):
    """Один такт ОФК-2. Возвращает (x, P, невязка после коррекции, невязка до коррекции, √diag S)."""
    estimated = np.asarray(estimated, dtype=int)
    frozen = frozen_indices(estimated)
    x = np.asarray(x, dtype=float).reshape(N_STATE)
    p = np.asarray(p, dtype=float)
    x, p = _pin_frozen(x, p, param_fixed, frozen)
    dt = float(dt)
    if r is None:
        r = measurement_covariance()

    innov_post = np.zeros(N_MEAS, dtype=float)
    innov_prior = np.full(N_MEAS, np.nan, dtype=float)
    sqrt_s = np.full(N_MEAS, np.nan, dtype=float)
    if dt <= 0.0:
        return x.copy(), 0.5 * (p + p.T), innov_post, innov_prior, sqrt_s

    # прогноз
    x_pred, f = _predict(x, dt, dde, dde_dot, dde_prev, ddt, ddt_prev, estimated)
    x_pred, _ = _pin_frozen(x_pred, p, param_fixed, frozen)
    p_pred = f @ p @ f.T + process_noise(q_std=q_std, estimated=estimated)
    p_pred = 0.5 * (p_pred + p_pred.T)
    _, p_pred = _pin_frozen(x_pred, p_pred, param_fixed, frozen)

    # коррекция
    z = np.array([float(da), float(dq), float(dv), float(dtheta)], dtype=float)
    h = _meas_jacobian()
    delta = z - _predict_z(x_pred)
    ph_t = p_pred @ h.T
    s = h @ ph_t + r
    s = 0.5 * (s + s.T)
    try:
        k = np.linalg.solve(s, ph_t.T).T
    except np.linalg.LinAlgError:  # вырожденная S — пропускаем коррекцию
        return x_pred, p_pred, innov_post, innov_prior, sqrt_s

    innov_prior = delta.copy()
    sqrt_s = np.sqrt(np.maximum(np.diag(s), 1e-30))
    x_new = x_pred + k @ delta
    ik = np.eye(N_STATE) - k @ h
    joseph = ik @ p_pred @ ik.T + k @ r @ k.T
    p_new = 0.5 * (joseph + joseph.T)
    x_new, p_new = _pin_frozen(x_new, p_new, param_fixed, frozen)
    innov_post = z - _predict_z(x_new)
    return x_new, p_new, innov_post, innov_prior, sqrt_s
