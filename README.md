# Моделирование полёта ЛА + БИНС + ГНСС + ОФК

Python-порт учебной MATLAB-модели пассажирского самолёта.  
Рабочая цепочка: нелинейная динамика ЛА (FX1) -> ошибки INS -> механизация БИНС -> GNSS -> EKF (ОФК).

## Запуск

```bash
python run_full_sim.py
```

Графики сохраняются в `src/plots/`.

---

## 1) Какие файлы за что отвечают

| Блок | Файл |
|---|---|
| Главный сценарий | `run_full_sim.py` |
| Цикл симуляции | `src/model_python_port/simulation/bins_gnss_simulation.py` |
| Динамика ЛА (FX1) | `src/model_python_port/dynamics/fx1.py` |
| Автопилот | `src/model_python_port/dynamics/autopilot_model.py` |
| RK4 + GNSS модель | `src/model_python_port/sensors/core.py` |
| Ошибки INS (ДУС/ДЛУ) | `src/model_python_port/sensors/imu_error_generator.py` |
| Механизация БИНС | `src/model_python_port/navigation/bins_common.py` |
| Матрицы EKF (F,G,H,Q) | `src/model_python_port/filtering/bins_ofk_2ch.py` |
| Шаг EKF-1 + feedback | `src/model_python_port/filtering/loosely_coupled_ofk.py` |
| EKF-2 (второй фильтр) | `src/model_python_port/filtering/ofk2_ekf.py` |
| Теория L*, M* для ОФК-2 | `src/model_python_port/filtering/ofk2_theory.py` |
| Инициализация сценария | `src/model_python_port/simulation/initsim.py` |
| Построение графиков | `src/model_python_port/output/full_sim_outputs.py` |

---

## 2) Входные параметры сценария и их значения

### Параметры запуска (`run_full_sim.py`)

| Параметр | Значение |
|---|---|
| `tmodel` | `30.0` с |
| `dt` | `1e-3` с |
| `dt_gnss` | `0.1` с |

### Начальные условия (`initsim`)

| Параметр | Значение |
|---|---|
| Высота `H0` | `500` м |
| Скорость `V0` | `80` м/с |
| Широта `fi0` | `0` рад |
| Долгота `lam0` | `0` рад |
| Начальные углы | `0` (горизонтальный режим) |
| Балансировка | `δT≈0.725`, `α≈0.212` рад, `δV≈-7.16°` |

### Начальное состояние БИНС

`np_bins = [Vn, Vh, Ve, h, fi, lam]`  
на старте берется из истинного состояния FX1 (`x`), без INS-ошибок.

### Начальные параметры EKF

`x_ofk = zeros(15)`  
`P0 = diag([1e3]*4 + [1e-2]*6 + [1e-4]*5)` с уточнениями:
- `P0[13] = 0.04` (для `δVh`)
- `P0[14] = 1.0` (для `δh`)

---

## 3) Что делает RK4 и что дает на выходе

На каждом шаге `dt`:

1. `rk4_step(fx1, ...)` интегрирует динамику ЛА.
2. Получаем:
   - `x` — истинное состояние ЛА (25),
   - `af_bi_b` — истинное удельное ускорение без `g` в body-frame,
   - `wbi_b` — истинная угловая скорость в body-frame.

Эти два вектора (`af_bi_b`, `wbi_b`) — «идеальные» входы инерциальных датчиков.

---

## 4) Какие ошибки генерируются по каждому параметру

Генерация в `InsErrorGen`:

### ДУС (гироскоп)
- bias (1 раз на прогон): `N(0, (0.5°/ч)^2)`,  
  `0.5°/ч = 2.424068e-6 рад/с`
- white noise (каждый шаг): `N(0, (1e-5)^2)` рад/с
- формула: `w_m = w_true + dw_bias + dw_noise`

### ДЛУ (акселерометр)
- bias (1 раз на прогон): `N(0, (5e-4)^2)` м/с²
- white noise (каждый шаг): `N(0, (5e-5)^2)` м/с²
- формула: `a_m = a_true + da_bias + da_noise`

### GNSS
Измерение строится как `truth + N(0, sigma^2)`:
- `σ_fi = 5e-6` рад
- `σ_lam = 5e-6` рад
- `σ_h = 1.0` м
- `σ_vn = σ_ve = σ_vh = 0.2` м/с

---

## 5) Как работает модель по шагам (что куда идет)

На каждом шаге `dt=1мс`:

1. **FX1 + RK4** -> `x, af_bi_b, wbi_b`
2. **INS errors** -> `w_m, a_m`
3. **БИНС (`bins_step`)**  
   вход: `a_m, w_m, np_bins, cbn, q, dt`  
   выход: `q, cbn, np_bins, a_last`
4. Каждые `dt_gnss=0.1с`:
   - `gnss(...)` -> `np_gnss, v_gnss`
   - инновация: `z = build_innovation(np_bins, np_gnss)` (`BINS - GNSS`)
   - EKF: `x_ofk, p_ofk = ofk_step(a_last, cbn, np_bins, z, x_ofk, p_ofk, v_gnss, dt_gnss)`
   - feedback: `apply_bins_feedback(np_bins, x_ofk)`
   - reset error-state: `x_ofk[:] = 0`
   - **ОФК-2 (второй фильтр):**  
     `Z₂ = [α, q, a_z, q̇]` из БИНС + навигации после ОФК-1;  
     `δ = Z₂ − h(x̂)` → update оценок `α, q, δe, L*, M*`.

---

## 6) Что идет на вход EKF и что выходит

### Вход EKF-1 (навигация)
- `a_last` (последнее зашумленное ускорение INS),
- `cbn`, `np_bins` (текущее решение БИНС),
- `z = BINS - GNSS`,
- `x_ofk`, `p_ofk` (предыдущее состояние/ковариация),
- `v_gnss` (СКО измерений GNSS),
- `dt_gnss`.

### Выход EKF-1
- `x_ofk` — оценка error-state,
- `p_ofk` — апостериорная ковариация.

После feedback получаем скорректированное `np_bins` (ОФК-решение).

### EKF-2 (второй фильтр, идентификация L*, M*)

Модель: `q̇ = M_α α + M_q q + M_δe δe` (и аналогично для `α̇` через `L*`).

| | |
|---|---|
| Состояние | `[α, q, δe, Lα, Lq, Lδe, Mα, Mq, Mδe]` |
| Теория | якобиан FX1 в точке балансировки (`filtering/ofk2_theory.py`) |
| Измерение Z | α из навигации после ОФК-1; q, a_z с ДУС/ДЛУ; q̇ — разностная производная ДУС |
| Дельта коэффициентов | `Δ = θ̂_ОФК2 − θ_theory` (`dM_alpha`, `dL_alpha`, …) |
| Выход | график `src/plots/ofk2_ekf.png` |

---

## 7) Как считаются ±3σ

На каждом GNSS-такте берется диагональ `p_ofk`:

- `sigma_fi = sqrt(P[5,5])`
- `sigma_lam = sqrt(P[6,6])`
- `sigma_h = sqrt(P[14,14])`
- `sigma_vn = sqrt(P[3,3])`
- `sigma_ve = sqrt(P[4,4])`
- `sigma_vh = sqrt(P[13,13])`

На графике строится полоса:

\[
\pm 3\sigma = \pm 3\sqrt{P_{ii}}
\]

и сравнивается с ошибкой `err_ofk_* = ofk_* - true_*`.

---

## 8) Какие графики строятся

Все в `src/plots/`:

| Файл | Что показывает |
|---|---|
| `bins_gnss_full.png` | Абсолютные φ, λ, h, V: истина / БИНС до ОФК / БИНС после ОФК-1 / ГНСС |
| `latitude_vs_longitude.png` | Истинная траектория полёта (`fi-lam`) |
| `ofk_error_vs_three_sigma_P.png` | Ошибка ОФК-1 vs полоса `±3√Pii` по 6 каналам |
| `ofk2_ekf.png` | ОФК-2: α, q, L*/M* vs теория, Δ и инновации |

---

## 9) Векторы и обозначения

- Истина ЛА: `x` (25)
- INS навигация: `np_bins = [Vn, Vh, Ve, h, fi, lam]`
- GNSS измерение: `np_gnss = [fi, lam, h, Vn, Ve, Vh]`
- EKF state: `x_ofk` (15, error-state)
- EKF covariance: `p_ofk` (15x15)

---

## Ссылки

- [Начальные значения и ошибки](docs/SIMULATION_INITIAL_VALUES_AND_ERRORS.md)
- [Математическая модель ЛА](docs/MATHEMATICAL_MODEL_AIRCRAFT.md)
- [EKF уравнения](docs/EKF1_NAVIGATION_EQUATIONS.docx)
- [Отчёт: модели, алгоритмы, результаты](docs/Отчёт_имитационное_моделирование.docx) — сборка: `docs/build_report_figures.py` → `docs/_report_stats.py` → `docs/build_report_docx.py`
- [Модели и алгоритмы (расширенная версия с формулами)](docs/Отчет_модели_и_алгоритмы_дополненный.docx) — сборка: `docs/build_report_models_docx.py`
