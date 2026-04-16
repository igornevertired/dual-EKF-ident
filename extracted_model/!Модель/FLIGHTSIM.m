clc
clear
close all
%% Инициализация симмуляции
INITSIM;
%% Выбор схемы комплексирования
Scheme = 1; % 1 - косвенное осреднение; 2 - прямое осреднение
%% Цикл моделирования
if Scheme == 1
    [X] = MODELING_1(X0, XB0, TMODEL, DT, U0, CBN0, Qu, Qu1, Qu2, Qu3);
elseif Scheme == 2
    [X] = MODELING_2(X0, XB0, TMODEL, DT, U0, CBN0, Qu, Qu1, Qu2, Qu3);
end
%% Вывод графиков
X_file = readtable('OUT_X.txt');
GNSS = readtable('OUTPUT_GNSS.txt');
BINS1 = readtable('OUTPUT_error_BINS1.txt');
BINS2 = readtable('OUTPUT_error_BINS2.txt');
BINS3 = readtable('OUTPUT_error_BINS3.txt');
SRD = readtable('OUTPUT_SRD.txt');
Time = BINS1.TIME_sec__(:);
k = 180/pi*111000;

if Scheme == 1
    OFK1 = readtable('OUTPUT_OFK1.txt');
    OFK2 = readtable('OUTPUT_OFK2.txt');
    OFK3 = readtable('OUTPUT_OFK3.txt');
    OCEN = readtable('OUTPUT_OCEN.txt');

    % График оценки погрешности БИНС параметра Fi (ОФК)
    figure();
    plot(Time, OFK1.e_Fi_ofk(:)*k, '-c', 'LineWidth', 2);
    hold on
    plot(Time, OFK2.e_Fi_ofk(:)*k, '-g', 'LineWidth', 2);
    hold on
    plot(Time, OFK3.e_Fi_ofk(:)*k, '-m', 'LineWidth', 2);
    hold on
    plot(Time, 2*OFK1.SKO_Fi(:)*k, '-b', 'LineWidth', 2);
    hold on
    plot(Time, 2*OFK2.SKO_Fi(:)*k, '-b', 'LineWidth', 2);
    hold on
    plot(Time, 2*OFK3.SKO_Fi(:)*k, '-b', 'LineWidth', 2);
    hold on
    plot(Time, -2*OFK1.SKO_Fi(:)*k, '-b', 'LineWidth', 2); 
    hold on
    plot(Time, -2*OFK2.SKO_Fi(:)*k, '-b', 'LineWidth', 2);
    hold on
    plot(Time, -2*OFK3.SKO_Fi(:)*k, '-b', 'LineWidth', 2);
    grid on
    title('ОФК - график ошибки оценки по параметру Fi', 'FontSize', 14);
    legend('Fi_1', 'Fi_2', 'Fi_3', '3 СКО Fi_1', '3 СКО Fi_2', '3 СКО Fi_3', 'FontSize', 14);
    xlabel('Время (сек.)', 'FontSize', 14);
    ylabel('Ошибка оценки по Fi (м.)', 'FontSize', 14);

    % График оценки погрешности БИНС параметра Lm (ОФК)
    figure();
    plot(Time, OFK1.e_Lm_ofk(:)*k, '-c', 'LineWidth', 2);
    hold on
    plot(Time, OFK2.e_Lm_ofk(:)*k, '-g', 'LineWidth', 2);
    hold on
    plot(Time, OFK3.e_Lm_ofk(:)*k, '-m', 'LineWidth', 2);
    hold on
    plot(Time, 2*OFK1.SKO_Lm(:)*k, '-b', 'LineWidth', 2);
    hold on
    plot(Time, 2*OFK2.SKO_Lm(:)*k, '-b', 'LineWidth', 2);
    hold on
    plot(Time, 2*OFK3.SKO_Lm(:)*k, '-b', 'LineWidth', 2);
    hold on
    plot(Time, -2*OFK1.SKO_Lm(:)*k, '-b', 'LineWidth', 2); 
    hold on
    plot(Time, -2*OFK2.SKO_Lm(:)*k, '-b', 'LineWidth', 2);
    hold on
    plot(Time, -2*OFK3.SKO_Lm(:)*k, '-b', 'LineWidth', 2);
    grid on
    title('ОФК - график ошибки оценки по параметру Lm', 'FontSize', 14);
    legend('Lm_1', 'Lm_2', 'Lm_3', '3 СКО Lm_1', '3 СКО Lm_2', '3 СКО Lm_3', 'FontSize', 14);
    xlabel('Время (сек.)', 'FontSize', 14);
    ylabel('Ошибка оценки по Lm (м.)', 'FontSize', 14);

    % График оценки погрешности БИНС параметра Vn (ОФК)
    figure();
    plot(Time, OFK1.e_Vn(:), '-c','LineWidth', 2);
    hold on
    plot(Time, OFK2.e_Vn(:), '-g','LineWidth', 2);
    hold on
    plot(Time, OFK3.e_Vn(:), '-m','LineWidth', 2);
    hold on
    plot(Time, 2*OFK1.SKO_Vn(:), '-b', 'LineWidth', 2); 
    hold on
    plot(Time, 2*OFK2.SKO_Vn(:), '-b', 'LineWidth', 2);
    hold on
    plot(Time, 2*OFK3.SKO_Vn(:), '-b', 'LineWidth', 2);
    hold on
    plot(Time, -2*OFK1.SKO_Vn(:), '-b', 'LineWidth', 2); 
    hold on
    plot(Time, -2*OFK2.SKO_Vn(:), '-b', 'LineWidth', 2);
    hold on
    plot(Time, -2*OFK3.SKO_Vn(:), '-b', 'LineWidth', 2);
    grid on
    title('ОФК - график ошибки оценки по параметру V_N', 'FontSize', 14);
    legend('Vn_1', 'Vn_2', 'Vn_3', '3 СКО Vn_1', '3 СКО Vn_2', '3 СКО Vn_3', 'FontSize', 14)
    xlabel('Время (сек.)', 'FontSize', 14);
    ylabel('Ошибка оценки по V_N (м/с)', 'FontSize', 14);

    % График оценки погрешности БИНС параметра Ve (ОФК)
    figure();
    plot(Time, OFK1.e_Ve(:), '-c','LineWidth', 2);
    hold on
    plot(Time, OFK2.e_Ve(:), '-g','LineWidth', 2);
    hold on
    plot(Time, OFK3.e_Ve(:), '-m','LineWidth', 2);
    hold on
    plot(Time, 2*OFK1.SKO_Ve(:), '-b', 'LineWidth', 2); 
    hold on
    plot(Time, 2*OFK2.SKO_Ve(:), '-b', 'LineWidth', 2);
    hold on
    plot(Time, 2*OFK3.SKO_Ve(:), '-b', 'LineWidth', 2);
    hold on
    plot(Time, -2*OFK1.SKO_Ve(:), '-b', 'LineWidth', 2); 
    hold on
    plot(Time, -2*OFK2.SKO_Ve(:), '-b', 'LineWidth', 2);
    hold on
    plot(Time, -2*OFK3.SKO_Ve(:), '-b', 'LineWidth', 2);
    grid on
    title('ОФК - график ошибки оценки по параметру V_E', 'FontSize', 14);
    legend('Ve_1', 'Ve_2', 'Ve_3', '3 СКО Ve_1', '3 СКО Ve_2', '3 СКО Ve_3', 'FontSize', 14)
    xlabel('Время (сек.)', 'FontSize', 14);
    ylabel('Ошибка оценки по V_E (м/с)', 'FontSize', 14);

    % Графики работы алгоритма осреднения
    figure();
    plot(Time, OCEN.Fi1(:)*k, 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, OCEN.Fi2(:)*k, 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, OCEN.Fi3(:)*k, 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, OCEN.Fi_s(:)*k, 'LineWidth', 2)
    grid on
    title('График оцененных параметров Fi всех БИНС и средневзвешенное');
    legend('Fi_1', 'Fi_2', 'Fi_3', 'Fi ср.вз.');
    xlabel('Время (сек.)');
    ylabel('Широта (м.)');

    figure();
    plot(Time, OCEN.Lm1(:)*k, 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, OCEN.Lm2(:)*k, 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, OCEN.Lm3(:)*k, 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, OCEN.Lm_s(:)*k, 'LineWidth', 2)
    grid on
    title('График оцененных параметров Lm всех БИНС и средневзвешенное');
    legend('Lm_1', 'Lm_2', 'Lm_3', 'Lm ср.вз.');
    xlabel('Время (сек.)');
    ylabel('Долгота (м.)');

    figure();
    plot(Time, OCEN.Vn1(:), 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, OCEN.Vn2(:), 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, OCEN.Vn3(:), 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, OCEN.Vn_s(:), 'LineWidth', 2)
    grid on
    title('График оцененных параметров V_N всех БИНС и средневзвешенное');
    legend('Vn_1', 'Vn_2', 'Vn_3', 'Vn ср.вз.');
    xlabel('Время (сек.)');
    ylabel('Северная проекция путевой скорости (м/с)');

    figure();
    plot(Time, OCEN.Ve1(:), 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, OCEN.Ve2(:), 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, OCEN.Ve3(:), 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, OCEN.Ve_s(:), 'LineWidth', 2)
    grid on
    title('График оцененных параметров V_E всех БИНС и средневзвешенное');
    legend('Ve_1', 'Ve_2', 'Ve_3', 'Ve ср.вз.');
    xlabel('Время (сек.)');
    ylabel('Восточная проекция путевой скорости (м/с)');
    % 
    % % Итоговая ошибка НК
    % % По координатам
    % figure()
    % plot(Time, SRD.dFi_corr_rad_(:)*k, 'LineWidth', 2);
    % hold on
    % plot(Time, 2*OFK1.SKO_Fi(:)*k, '-b', 'LineWidth', 2);
    % hold on
    % plot(Time, -2*OFK1.SKO_Fi(:)*k, '-b', 'LineWidth', 2);
    % hold on
    % plot(Time, SRD.dLm_corr_rad_(:)*k, 'LineWidth', 2);
    % hold on
    % plot(Time, 2*OFK1.SKO_Lm(:)*k, '-g', 'LineWidth', 2);
    % hold on
    % plot(Time, -2*OFK1.SKO_Lm(:)*k, '-g', 'LineWidth', 2);
    % grid on
    % title('Итоговая ошибка вычисления координат навигационного комплекса');
    % legend('Fi_e', '2 СКО Fi', '-2 СКО Fi', 'Lm_e', '2 СКО Lm', '-2 СКО Lm');
    % xlabel('Время (сек.)');
    % ylabel('Ошибка по координатам (м.)');
    % 
    % % По скоростям
    % figure()
    % plot(Time, SRD.dVn_corr(:), 'LineWidth', 2);
    % hold on
    % plot(Time, 2*OFK1.SKO_Vn(:), '-b', 'LineWidth', 2);
    % hold on
    % plot(Time, -2*OFK1.SKO_Vn(:), '-b', 'LineWidth', 2);
    % hold on
    % plot(Time, SRD.dVe_corr(:), 'LineWidth', 2);
    % hold on
    % plot(Time, 2*OFK1.SKO_Ve(:), '-g', 'LineWidth', 2);
    % hold on
    % plot(Time, -2*OFK1.SKO_Ve(:), '-g', 'LineWidth', 2);
    % grid on
    % title('Итоговая ошибка вычисления скоростей навигационного комплекса');
    % legend('Vn', '2 СКО Vn', '-2 СКО Vn', 'Ve', '2 СКО Ve', '-2 СКО Ve');
    % xlabel('Время (сек.)');
    % ylabel('Ошибка по скоростям (м/с)');

    % Графики ошибки Fi всех БИНС
    figure();
    plot(Time, BINS1.dFi_rad_(:)*k, 'LineWidth', 2);
    hold on
    plot(Time, BINS2.dFi_rad_(:)*k, 'LineWidth', 2);
    hold on
    plot(Time, BINS3.dFi_rad_(:)*k, 'LineWidth', 2);
    grid on
    title('График ошибки автномной работы всех БИНС по параметру Fi');
    legend('Fi BINS1', 'Fi BINS2', 'Fi BINS3');
    xlabel('Время (сек.)');
    ylabel('Ошибка по широте (м.)');
    
    % Графики ошибки Lm всех БИНС
    figure();
    plot(Time, BINS1.dLm_rad_(:)*k, 'LineWidth', 2);
    hold on
    plot(Time, BINS2.dLm_rad_(:)*k, 'LineWidth', 2);
    hold on
    plot(Time, BINS3.dLm_rad_(:)*k, 'LineWidth', 2);
    grid on
    title('График ошибки автномной работы всех БИНС по параметру Lm');
    legend('Lm BINS1', 'Lm BINS2', 'Lm BINS3');
    xlabel('Время (сек.)');
    ylabel('Ошибка по долготе (м.)');
    
    % Графики ошибки Vn всех БИНС
    figure();
    plot(Time, BINS1.dVn(:), 'LineWidth', 2);
    hold on
    plot(Time, BINS2.dVn(:), 'LineWidth', 2);
    hold on
    plot(Time, BINS3.dVn(:), 'LineWidth', 2);
    grid on
    title('График ошибки автномной работы всех БИНС по параметру V_N');
    legend('V_N BINS1', 'V_N BINS2', 'V_N BINS3');
    xlabel('Время (сек.)');
    ylabel('Ошибка по северной скорости (м/с)');
    
    % Графики ошибки Ve всех БИНС
    figure();
    plot(Time, BINS1.dVe(:), 'LineWidth', 2);
    hold on
    plot(Time, BINS2.dVe(:), 'LineWidth', 2);
    hold on
    plot(Time, BINS3.dVe(:), 'LineWidth', 2); 
    grid on
    title('График ошибки автномной работы всех БИНС по параметру V_E');
    legend('V_E BINS1', 'V_E BINS2', 'V_E BINS3');
    xlabel('Время (сек.)');
    ylabel('Ошибка по восточной скорости (м/с)');

elseif Scheme == 2
    OFK1 = readtable('OUTPUT_OFK1.txt');
    RES = readtable('OUT_MD2.txt');

    % График ОФК оценки Fi и Lm
    figure();
    plot(Time, OFK1.e_Fi_ofk(:)*k, 'LineWidth', 2);
    hold on
    plot(Time, OFK1.e_Lm_ofk(:)*k, 'LineWidth', 2);
    hold on
    plot(Time, 3*OFK1.SKO_Fi(:)*k, '-b', 'LineWidth', 2);
    hold on
    plot(Time, -3*OFK1.SKO_Fi(:)*k, '-b', 'LineWidth', 2);
    hold on
    plot(Time, 3*OFK1.SKO_Lm(:)*k, '-g', 'LineWidth', 2);
    hold on
    plot(Time, -3*OFK1.SKO_Lm(:)*k, '-g', 'LineWidth', 2);
    grid on
    title('ОФК 1 - график ошибки оценки координат');
    legend('Fi_e', 'Lm_e', '3 СКО Fi', '-3 СКО Fi', '3 СКО Lm', '-3 СКО Lm');
    xlabel('Время (сек.)');
    ylabel('Ошибка по координатам (м.)');

    % График ОФК оценки Vn и Ve
    figure();
    plot(Time, OFK1.e_Vn_ofk(:), 'LineWidth', 2);
    hold on
    plot(Time, OFK1.e_Ve_ofk(:), 'LineWidth', 2);
    hold on
    plot(Time, 3*OFK1.SKO_Vn(:), '-b', 'LineWidth', 2);
    hold on
    plot(Time, -3*OFK1.SKO_Vn(:), '-b', 'LineWidth', 2);
    hold on
    plot(Time, 3*OFK1.SKO_Ve(:), '-g', 'LineWidth', 2);
    hold on
    plot(Time, -3*OFK1.SKO_Ve(:), '-g', 'LineWidth', 2);
    grid on
    title('ОФК 1 - график ошибки оценки скоростей');
    legend('Vn_e', 'Ve_e', '3 СКО Vn', '-3 СКО Vn', '3 СКО Ve', '-3 СКО Ve');
    xlabel('Время (сек.)');
    ylabel('Ошибка по скоростям (м/с)');

    % Графики ошибки Fi всех БИНС
    figure();
    plot(Time, BINS1.dFi(:)*k, 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, BINS2.dFi(:)*k, 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, BINS3.dFi(:)*k, 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, SRD.Fi_srd(:)*k, 'LineWidth', 2)
    grid on
    title('График ошибки автномной работы всех БИНС по параметру Fi и среднее');
    legend('Fi BINS1', 'Fi BINS2', 'Fi BINS3', 'Fi средневзвешанное');
    xlabel('Время (сек.)');
    ylabel('Ошибка по широте (м.)');
    
    % Графики ошибки Lm всех БИНС
    figure();
    plot(Time, BINS1.dLm(:)*k, 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, BINS2.dLm(:)*k, 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, BINS3.dLm(:)*k, 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, SRD.Lm_srd(:)*k, 'LineWidth', 2)
    grid on
    title('График ошибки автномной работы всех БИНС по параметру Lm и среднее');
    legend('Lm BINS1', 'Lm BINS2', 'Lm BINS3', 'Lm средневзвешанное');
    xlabel('Время (сек.)');
    ylabel('Ошибка по долготе (м.)');
    
    % Графики ошибки Vn всех БИНС
    figure();
    plot(Time, BINS1.dVn(:), 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, BINS2.dVn(:), 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, BINS3.dVn(:), 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, SRD.Vn_srd(:), 'LineWidth', 2)
    grid on
    title('График ошибки автномной работы всех БИНС по параметру V_N');
    legend('V_N BINS1', 'V_N BINS2', 'V_N BINS3', 'V_N средневзвешанное');
    xlabel('Время (сек.)');
    ylabel('Ошибка по северной проекции путевой скорости (м/с)');
    
    % Графики ошибки Ve всех БИНС
    figure();
    plot(Time, BINS1.dVe(:), 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, BINS2.dVe(:), 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, BINS3.dVe(:), 'LineWidth', 2, 'LineStyle', '--');
    hold on
    plot(Time, SRD.Ve_srd(:), 'LineWidth', 2)
    grid on
    title('График ошибки автномной работы всех БИНС по параметру V_E');
    legend('V_E BINS1', 'V_E BINS2', 'V_E BINS3', 'V_E средневзвешанное');
    xlabel('Время (сек.)');
    ylabel('Ошибка по восточной проекции путевой скорости (м/с)');

end

%% Temp
%%
figure();
plot(X_file.FI(:), X_file.LAMD(:), 'LineWidth', 2);
grid on
title('Траектория полета');
xlabel('Долгота (рад.)');
ylabel('Широта (рад.)');
% 
% STAT = readtable('OUTPUT_STATOFK.txt');
% figure()
% plot(Time, STAT.dwcx(:), '-g', 'LineWidth', 2);
% hold on
% plot(Time, STAT.skowx(:), '-r', 'LineWidth', 2);
% hold on
% plot(Time, -STAT.skowx(:), '-r', 'LineWidth', 2);
% hold on
% plot(Time, STAT.dwcy(:), '-g', 'LineWidth', 2);
% hold on
% plot(Time, STAT.skowy(:), '-r', 'LineWidth', 2);
% hold on
% plot(Time, -STAT.skowy(:), '-r', 'LineWidth', 2);
% hold on
% plot(Time, STAT.dwcz(:), '-g', 'LineWidth', 2);
% hold on
% plot(Time, STAT.skowz(:), '-r', 'LineWidth', 2);
% hold on
% plot(Time, -STAT.skowz(:), '-r', 'LineWidth', 2);
% title('Смещение нуля гироскопов - ОФК');
% 
% figure()
% plot(Time, STAT.dacx(:), '-g', 'LineWidth', 2);
% hold on
% plot(Time, STAT.skoax(:), '-r', 'LineWidth', 2);
% hold on
% plot(Time, -STAT.skoax(:), '-r', 'LineWidth', 2);
% hold on
% plot(Time, STAT.dacy(:), '-g', 'LineWidth', 2);
% hold on
% plot(Time, STAT.skoay(:), '-r', 'LineWidth', 2);
% hold on
% plot(Time, -STAT.skoay(:), '-r', 'LineWidth', 2);
% hold on
% plot(Time, STAT.dacz(:), '-g', 'LineWidth', 2);
% hold on
% plot(Time, STAT.skoaz(:), '-r', 'LineWidth', 2);
% hold on
% plot(Time, -STAT.skoaz(:), '-r', 'LineWidth', 2);
% title('Смещение нуля аклесерометров - ОФК');

% BINS11 = readtable('OUTPUT_error_BINS11.txt');
% 
% figure();
% plot(Time, BINS1.dFi_rad_(:)*k, 'LineWidth', 2);
% hold on
% plot(Time, BINS11.dFi_rad_(:), 'LineWidth', 2);
% grid on
% title('БИНС Fi');
% legend('Fi BINS1', 'Fi BINS1 - модель');
% xlabel('Time, sec.');
% ylabel('dFi, m.');
% 
% figure();
% plot(Time, BINS1.dLm_rad_(:)*k, 'LineWidth', 2);
% hold on
% plot(Time, BINS11.dLm_rad_(:), 'LineWidth', 2);
% grid on
% title('БИНС Lm');
% legend('Lm BINS1', 'Lm BINS1 - модель');
% xlabel('Time, sec.');
% ylabel('dLm, m.');

% % Графики ошибки Vn всех БИНС
% figure();
% plot(Time, BINS1.dVn(:), 'LineWidth', 2);
% hold on
% plot(Time, BINS2.dVn(:), 'LineWidth', 2);
% hold on
% plot(Time, BINS3.dVn(:), 'LineWidth', 2);
% grid on
% title('БИНС Vn');
% legend('Vn BINS1', 'Vn BINS2', 'Vn BINS3');
% xlabel('Time, sec.');
% ylabel('dVn, m/s^2');
% 
% % Графики ошибки Ve всех БИНС
% figure();
% plot(Time, BINS1.dVe(:), 'LineWidth', 2);
% hold on
% plot(Time, BINS2.dVe(:), 'LineWidth', 2);
% hold on
% plot(Time, BINS3.dVe(:), 'LineWidth', 2);
% grid on
% title('БИНС Ve');
% legend('Ve BINS1', 'Ve BINS2', 'Ve BINS3');
% xlabel('Time, sec.');
% ylabel('dVe, m/s^2');

% Графики погрешностей вычисления координат от ГНСС
% figure();
% plot(Time, abs(GNSS.dFi_rad_(:)), 'LineWidth', 2);
% hold on
% plot(Time, abs(GNSS.dLm_rad_(:)), 'LineWidth', 2);
% grid on
% title('ГНСС');
% legend('Fi Error', 'Lm Error');
% xlabel('Time, sec.');
% ylabel('Error coord. GNSS 1, rad.');

% figure();
% plot(Time, GNSS.dFi_rad_(:)*k, 'LineWidth', 2);
% hold on
% plot(Time, GNSS.dLm_rad_(:)*k, 'LineWidth', 2);
% grid on
% title('ГНСС');
% legend('Fi Error', 'Lm Error');
% xlabel('Time, sec.');
% ylabel('Error coord. GNSS 2, rad.');