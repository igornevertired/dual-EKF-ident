%% ФУНКЦИЯ АЛГОРИТМА SRD для 1 схемы
% FI - вектор значений Fi трек БИНС с оценкой ОФК
% LM - вектор значений Lm трек БИНС с оценкой ОФК

%% MAIN
%%
function [Fi_SRD, LM_SRD, Vn_SRD, Ve_SRD] = MK_SRD_1 (FIrad, LMrad, Fi_fms, Lm_fms, V_N, V_E)
    % рад. -> град. (SRD рботает с градусами)
    FIdeg = FIrad.*180/pi;
    LMdeg = LMrad.*180/pi;
    Fi_fms = Fi_fms*180/pi;
    Lm_fms = Lm_fms*180/pi;

    % Настроечные параметры SRD
    koeff = zeros(3, 1);
    rsi_nav = [1; 1; 1]; % 1 - работает / 0 - отказ [IRS1; IRS2; IRS3]
    Mode = rsi_nav(1)*rsi_nav(2)*rsi_nav(3); % Для выбора режима работы SRD
    
    % Переключение режимов работы SRD
    if Mode == 0
        [koeff] = DUALMIX (FIdeg, LMdeg, koeff, rsi_nav, Fi_fms, Lm_fms);
    else
        [koeff] = TRIPLEMIX (FIdeg, LMdeg, koeff);
    end

    % Нормализация (для перенастройки коэффициентов при отказе одной БИНС)
    kSUM = koeff(1) + koeff(2) + koeff(3);
    if kSUM > 10^-5
       koeff(1) = koeff(1)/kSUM;
       koeff(2) = koeff(2)/kSUM;
       koeff(3) = koeff(3)/kSUM;
    end

    % Вычисление взвешенного среднего значения парамтеров
    Fi_SRD = koeff(1)*FIrad(1) + koeff(2)*FIrad(2) + koeff(3)*FIrad(3);
    LM_SRD = koeff(1)*LMrad(1) + koeff(2)*LMrad(2) + koeff(3)*LMrad(3);
    Vn_SRD = koeff(1)*V_N(1) + koeff(2)*V_N(2) + koeff(3)*V_N(3);
    Ve_SRD = koeff(1)*V_E(1) + koeff(2)*V_E(2) + koeff(3)*V_E(3);
end

%% Subprogramm's
%%

% Выбор источника по Heading source
function [koeff] = HEADINGSOURCE_LOGIC(rsi_nav, indx1, indx2, indx3, koeff)
    if (rsi_nav(indx1) == 1)
       koeff(1) = 0;
       koeff(2) = 0;
       koeff(3) = 0;
       koeff(indx1) = 1;
    elseif (rsi_nav(indx2) == 1)
       koeff(1) = 0;
       koeff(2) = 0;
       koeff(3) = 0;
       koeff(indx2) = 1;
    elseif (rsi_nav(indx3) == 1)
       koeff(1) = 0;
       koeff(2) = 0;
       koeff(3) = 0;
       koeff(indx3) = 1;
    end
end

% Алгоритм осреднения в режиме triple-mix (3 БИНС рабочие)
function [koeff] = TRIPLEMIX (FI, LM, koeff)
    K = 0.001; % deg^2

    % Квадрат расстояния между тремя БИНС
    AB2 = (FI(1) - FI(2))^2 + (LM(1) - LM(2))^2 * cos(FI(1)*pi/180) * cos(FI(2)*pi/180);
    AC2 = (FI(1) - FI(3))^2 + (LM(1) - LM(3))^2 * cos(FI(1)*pi/180) * cos(FI(3)*pi/180);
    BC2 = (FI(2) - FI(3))^2 + (LM(2) - LM(3))^2 * cos(FI(2)*pi/180) * cos(FI(3)*pi/180);

    % Вспомогательные коэффициенты
    DA = AB2 + AC2 + 2*K;
    DB = AB2 + BC2 + 2*K;
    DC = AC2 + BC2 + 2*K;
    D = AB2 + AC2 + BC2 + 3*K;

    % Весовые коэффициенты
    koeff(1) = (D - DA)/D;
    koeff(2) = (D - DB)/D;
    koeff(3) = (D - DC)/D;
end

% Алгоритм осреднения в режиме dual-mix (2 БИНС рабочие)
function [koeff] = DUALMIX (FI, LM, koeff, rsi_nav, Fi_FMS, Lm_FMS)
    K = 0.001; % deg^2
    GPS = 1; % Признак доступности ГНСС (1 - доступен, 0 - нет)

    MODE = 1; % (0 - synchronized mode; 1 - independent mode)
    DIR_FMS = 1; % По таблице правил выбора из теории (1, 2 или 3)
    
    if (abs(koeff(1)) + abs(koeff(2)) + abs(koeff(3)) == 0) && (GPS == 1)
        if (MODE == 0)
            indx1 = 1; indx2 = 2; indx3 = 3;
            koeff = HEADINGSOURCE_LOGIC(rsi_nav, indx1, indx2, indx3);
        else
            if (DIR_FMS == 1)
                indx1 = 1; indx2 = 3; indx3 = 2;
                koeff = HEADINGSOURCE_LOGIC(rsi_nav, indx1, indx2, indx3);
            else
                if (DIR_FMS == 2)
                    indx1 = 2; indx2 = 3; indx3 = 1;
                    koeff = HEADINGSOURCE_LOGIC(rsi_nav, indx1, indx2, indx3);
                else
                    indx1 = 3; indx2 = 1; indx3 = 2;
                    koeff = HEADINGSOURCE_LOGIC(rsi_nav, indx1, indx2, indx3);
                end
            end
        end
    end

    % При переходе из triple-mix
%     if (GPS == 1)
%         % квадрат расстояния между БИНС и FMS
%         DA = (FI(1) - Fi_FMS)^2 + (LM(1) - Lm_FMS)^2 * cos(FI(1)*pi/180) * cos(Fi_FMS*pi/180);
%         DB = (FI(2) - Fi_FMS)^2 + (LM(2) - Lm_FMS)^2 * cos(FI(2)*pi/180) * cos(Fi_FMS*pi/180);
%         DC = (FI(3) - Fi_FMS)^2 + (LM(3) - Lm_FMS)^2 * cos(FI(3)*pi/180) * cos(Fi_FMS*pi/180);
% 
%         % Учет исправности БИНС
%         DA = DA*rsi_nav(1);
%         DB = DB*rsi_nav(2);
%         DC = DC*rsi_nav(3);
%         D = DA + DB + 2*K;
% 
%         % ВЫесовые коэффициенты
%         koeff(1) = rsi_nav(1) * (DB + DC + K)/D;
%         koeff(2) = rsi_nav(2) * (DA + DC + K)/D;
%         koeff(3) = rsi_nav(3) * (DA + DB + K)/D;
%     else
%         koeff(1) = rsi_nav(1)*koeff(1);
%         koeff(2) = rsi_nav(2)*koeff(2);
%         koeff(3) = rsi_nav(3)*koeff(3);
%     end
end