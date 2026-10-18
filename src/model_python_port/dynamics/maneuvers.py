"""
Идентификационные манёвры: программа отклонения руля высоты и (опционально) РУД.

Один объект ``Maneuver`` описывает весь эксперимент:

    Maneuver("doublet", amp_deg=5, pulse_s=2.5)            # дублет ±5°, импульсы по 2,5 с
    Maneuver("3211", amp_deg=5, unit_s=1.0)                # 3-2-1-1, такт 1 с
    Maneuver("multisine", amp_deg=5, duration_s=10)        # 6 гармоник 0,1–0,6 Гц
    Maneuver("chirp", amp_deg=3, duration_s=20)            # развертка 0,05→0,6 Гц
    Maneuver("pulse", amp_deg=5, pulse_s=2.5)              # одиночный импульс
    Maneuver("none", throttle_amp=0.15)                    # только дублет РУД
    Maneuver("doublet", hold_throttle=False)               # автомат тяги работает во время манёвра

Протокол эксперимента по умолчанию: на интервале манёвра рулём (и ``hold_after_s``
секунд после него) канал руля высоты автопилота и автомат тяги отключены; руль —
балансировка плюс программа, РУД — на балансировке.

Почему РУД фиксируется: тяга влияет на угол атаки (L_δt ≈ −0,0054 1/с на основном
режиме), а во время дублета автомат тяги уводит РУД до упоров (ΔδT до −0,54). Вклад
L_δt·ΔδT в Δα̇ равен вкладу самого руля, а в модели ОФК-2 этого члена нет — без
фиксации РУД оценка L_δe смещается на ~15 %. При фиксированном РУД коэффициент
X_δt ненаблюдаем и исключается из оцениваемых (см. ``throttle_fixed``).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ELEVATOR_KINDS = ("none", "doublet", "3211", "pulse", "multisine", "chirp")


@dataclass(frozen=True)
class Maneuver:
    kind: str = "doublet"
    amp_deg: float = 5.0
    t0: float = 10.0
    pulse_s: float = 2.5          # дублет / импульс: длительность одного импульса
    unit_s: float = 1.0           # 3-2-1-1: длительность такта
    duration_s: float = 10.0      # мультисинус / развертка
    f_min_hz: float = 0.1         # мультисинус: первая гармоника = 1/duration; развертка: начальная частота
    f_max_hz: float = 0.6
    extra_t0: tuple[float, ...] = ()   # повторные дублеты
    # РУД
    throttle_amp: float = 0.0     # амплитуда дублета РУД (доли хода); 0 — нет
    throttle_t0: float | None = None   # начало дублета РУД (по умолчанию — после манёвра рулём)
    throttle_pulse_s: float = 10.0
    hold_throttle: bool = True    # зафиксировать РУД на балансировке на время манёвра рулём
    hold_after_s: float = 15.0    # и ещё столько секунд после него

    def __post_init__(self):
        if self.kind not in ELEVATOR_KINDS:
            raise ValueError(f"неизвестный вид манёвра {self.kind!r}; допустимо: {ELEVATOR_KINDS}")

    # ------------------------------------------------------------------ руль
    def elevator_window(self) -> tuple[float, float]:
        """Интервал [начало, конец) программы руля высоты (без повторных дублетов)."""
        k, t0 = self.kind, self.t0
        if k == "doublet":
            return t0, t0 + 2.0 * self.pulse_s
        if k == "pulse":
            return t0, t0 + self.pulse_s
        if k == "3211":
            return t0, t0 + 7.0 * self.unit_s
        if k in ("multisine", "chirp"):
            return t0, t0 + self.duration_s
        return t0, t0

    def elevator_active(self, t: float) -> bool:
        if self.kind == "none":
            return False
        if self.kind == "doublet":
            return any(s <= t < s + 2.0 * self.pulse_s for s in (self.t0, *self.extra_t0))
        a, b = self.elevator_window()
        return a <= t < b

    def elevator_deg(self, t: float) -> float:
        """Приращение руля высоты к балансировке, градусы."""
        k, A = self.kind, float(self.amp_deg)
        if k == "doublet":
            for s in (self.t0, *self.extra_t0):
                if s <= t < s + self.pulse_s:
                    return A
                if s + self.pulse_s <= t < s + 2.0 * self.pulse_s:
                    return -A
            return 0.0
        if not self.elevator_active(t):
            return 0.0
        tau = t - self.t0
        if k == "pulse":
            return A
        if k == "3211":
            edges = np.array([0.0, 3.0, 5.0, 6.0, 7.0]) * self.unit_s
            signs = (1.0, -1.0, 1.0, -1.0)
            for j in range(4):
                if edges[j] <= tau < edges[j + 1]:
                    return signs[j] * A
            return 0.0
        if k == "multisine":
            f, ph, scale = self._multisine()
            return float(scale * np.sum(np.sin(2.0 * np.pi * f * tau + ph)))
        if k == "chirp":
            rate = (self.f_max_hz - 0.05) / self.duration_s
            return float(A * np.sin(2.0 * np.pi * (0.05 * tau + 0.5 * rate * tau * tau)))
        return 0.0

    def _multisine(self):
        """Гармоники k/T, k = 1..N (до f_max), фазы Шредера, нормировка на пиковое значение amp_deg."""
        n = max(1, int(round(self.f_max_hz * self.duration_s)))
        k = np.arange(1, n + 1)
        f = k / self.duration_s
        ph = -np.pi * k * (k - 1) / n
        tt = np.linspace(0.0, self.duration_s, 4001)
        peak = np.max(np.abs(np.sum(np.sin(2.0 * np.pi * np.outer(tt, f) + ph), axis=1)))
        return f, ph, float(self.amp_deg) / peak

    # ------------------------------------------------------------------ РУД
    def throttle_offset(self, t: float) -> float | None:
        """Приращение РУД к балансировке или None, если работает автомат тяги."""
        if self.throttle_amp:
            ts = self.throttle_t0 if self.throttle_t0 is not None else self.elevator_window()[1]
            if ts <= t < ts + self.throttle_pulse_s:
                return float(self.throttle_amp)
            if ts + self.throttle_pulse_s <= t < ts + 2.0 * self.throttle_pulse_s:
                return -float(self.throttle_amp)
        if self.hold_throttle and self.kind != "none":
            a, b = self.elevator_window()
            starts = (a, *self.extra_t0) if self.kind == "doublet" else (a,)
            for s in starts:  # для повторных дублетов РУД фиксируется на каждом
                if s <= t < s + (b - a) + self.hold_after_s:
                    return 0.0
        return None

    @property
    def throttle_fixed(self) -> bool:
        """РУД на интервалах манёвра не меняется — коэффициент X_δt ненаблюдаем."""
        return self.hold_throttle and not self.throttle_amp and self.kind != "none"


def legacy_maneuver(kind: str | None, amp_deg: float = 5.0, extra_t0=(), t0_3211: float = 10.0,
                    unit_3211: float = 1.0) -> Maneuver:
    """Перевод старых аргументов run_simulation (elevator_maneuver=...) в Maneuver."""
    if not kind:
        return Maneuver("none")
    if kind == "doublet":
        return Maneuver("doublet", amp_deg=amp_deg, extra_t0=tuple(extra_t0))
    if kind == "3211":
        return Maneuver("3211", amp_deg=amp_deg, t0=t0_3211, unit_s=unit_3211)
    raise ValueError(f"неизвестный манёвр {kind!r}")
