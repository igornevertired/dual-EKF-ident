# БИНС / ГНСС — куда смотреть

Реализация **БИНС по файлам**, механизация, ошибки ДУС/ДЛУ — **[BINS_NAVIGATION_IMPLEMENTATION.md](BINS_NAVIGATION_IMPLEMENTATION.md)**.

Реализация **ГНСС** (генератор измерений, σ, порядок каналов, **R**) — **[GNSS_MODEL_IMPLEMENTATION.md](GNSS_MODEL_IMPLEMENTATION.md)**.

Параметры ошибок приборов, поток симулятора, описание модели ЛА (**FX1**, автопилот, состояние 25-й размерности) — **[BINS_GNSS_PARAMETERS_AND_AIRCRAFT.md](BINS_GNSS_PARAMETERS_AND_AIRCRAFT.md)**.

Полное описание приборов, ОФК и выходов симуляции (кратко по сценарию) — в **[SIMULATION_BINS_GNSS.md](SIMULATION_BINS_GNSS.md)**.

Код разнесён по пакету `src/model_python_port` (структура — в **`SIMULATION_BINS_GNSS.md`**); сценарий запуска — **`run_full_sim.py`**.
