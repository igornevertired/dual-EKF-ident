%% ФУНКЦИЯ АЛГОРИТМА SRD для 2 схемы

%% MAIN
%%
function [Fi_SRD, Lm_SRD, A_srd, Vn_srd, Ve_srd, C_srd] = MK_SRD_2(FIrad, LMrad, Fi_fms, Lm_fms, A_c, Vn_c, Ve_c, C1, C2, C3)
    % рад. -> град. (SRD рботает с градусами)
    FIdeg = FIrad.*180/pi;
    LMdeg = LMrad.*180/pi;
    Fi_fms = Fi_fms*180/pi;
    Lm_fms = Lm_fms*180/pi;
    [Psi1, Theta1, Gamma1] = C_ANG(C1);
    [Psi2, Theta2, Gamma2] = C_ANG(C2);
    [Psi3, Theta3, Gamma3] = C_ANG(C3);
    PSI = [Psi1; Psi2; Psi3];
    THETA = [Theta1; Theta2; Theta3];
    GAMMA = [Gamma1; Gamma2; Gamma3];

    % Настроечные параметры SRD
    koeff = zeros(3, 1);
    rsi_nav = [1; 1; 1]; % 1 - работает / 0 - отказ [IRS1; IRS2; IRS3]
    Mode = rsi_nav(1)*rsi_nav(2)*rsi_nav(3); % Для выбора режима работы SRD
    
    % Переключение режимов работы SRD
    if Mode == 0
        [koeff] = DUALMIX (FIdeg, LMdeg, rsi_nav, koeff, Fi_fms, Lm_fms, A_c, W_c, Vn_c, Ve_c);
    elseif Mode == 1
        [koeff] = TRIPLEMIX (FIdeg, LMdeg, Vn_c, Ve_c, PSI, THETA, GAMMA);
    end

    % Нормализация (для перенастройки коэффициентов при отказе одной БИНС)
    kSUM = koeff(1) + koeff(2) + koeff(3);
    if kSUM > 10^-5
       koeff(1) = koeff(1)/kSUM;
       koeff(2) = koeff(2)/kSUM;
       koeff(3) = koeff(3)/kSUM;
    end
    
    % Осреднение углов ориентации и получение осредненной матрицы С
    Psi = koeff(1)*Psi1 + koeff(2)*Psi2 + koeff(3)*Psi3;
    Theta = koeff(1)*Theta1 + koeff(2)*Theta2 + koeff(3)*Theta3;
    Gamma = koeff(1)*Gamma1 + koeff(2)*Gamma2 + koeff(3)*Gamma3;
        C_srd = zeros(3);
        C_srd(1,1)  = cos(Psi)*cos(Theta);
        C_srd(1,2)  =-cos(Psi)*sin(Theta)*cos(Gamma)+sin(Psi)*sin(Gamma);
        C_srd(1,3)  = cos(Psi)*sin(Theta)*sin(Gamma)+sin(Psi)*cos(Gamma);
        C_srd(2,1)  = sin(Theta);
        C_srd(2,2)  = cos(Theta)*cos(Gamma);
        C_srd(2,3)  =-cos(Theta)*sin(Gamma);
        C_srd(3,1)  =-cos(Theta)*sin(Psi);
        C_srd(3,2)  = cos(Psi)*sin(Gamma)+sin(Psi)*sin(Theta)*cos(Gamma);	
        C_srd(3,3)  = cos(Psi)*cos(Gamma)-sin(Psi)*sin(Theta)*sin(Gamma);

    % Вычисление взвешенного среднего значения парамтеров
    Fi_SRD = koeff(1)*FIrad(1) + koeff(2)*FIrad(2) + koeff(3)*FIrad(3);
    Lm_SRD = koeff(1)*LMrad(1) + koeff(2)*LMrad(2) + koeff(3)*LMrad(3);
    % Fi_SRD = koeff_coord(1)*FIrad(1) + koeff_coord(2)*FIrad(2) + koeff_coord(3)*FIrad(3);
    % Lm_SRD = koeff_coord(1)*LMrad(1) + koeff_coord(2)*LMrad(2) + koeff_coord(3)*LMrad(3);
    A_srd = [koeff(1)*A_c(1, 1) + koeff(2)*A_c(2, 1) + koeff(3)*A_c(3, 1);
             koeff(1)*A_c(1, 2) + koeff(2)*A_c(2, 2) + koeff(3)*A_c(3, 2);
             koeff(1)*A_c(1, 3) + koeff(2)*A_c(2, 3) + koeff(3)*A_c(3, 3)];
    Vn_srd = koeff(1)*Vn_c(1) + koeff(2)*Vn_c(2) + koeff(3)*Vn_c(3);
    Ve_srd = koeff(1)*Ve_c(1) + koeff(2)*Ve_c(2) + koeff(3)*Ve_c(3);
    % Vn_srd = koeff_veloc(1)*Vn_c(1) + koeff_veloc(2)*Vn_c(2) + koeff_veloc(3)*Vn_c(3);
    % Ve_srd = koeff_veloc(1)*Ve_c(1) + koeff_veloc(2)*Ve_c(2) + koeff_veloc(3)*Ve_c(3);
    %Vn_srd = (Vn_c(1) + Vn_c(2) + Vn_c(3))/3;
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
% function [koeff] = TRIPLEMIX (FI, LM, Vn_c, Ve_c)
function [koeff] = TRIPLEMIX (FI, LM, Vn_c, Ve_c, PSI, THETA, GAMMA)
     K = 0.001; % deg^2
% %Расчет весовых коэффициентов по координатам
%     %Квадрат расстояния между тремя БИНС
%     AB2 = (FI(1) - FI(2))^2 + (LM(1) - LM(2))^2 * cos(FI(1)*pi/180) * cos(FI(2)*pi/180);
%     AC2 = (FI(1) - FI(3))^2 + (LM(1) - LM(3))^2 * cos(FI(1)*pi/180) * cos(FI(3)*pi/180);
%     BC2 = (FI(2) - FI(3))^2 + (LM(2) - LM(3))^2 * cos(FI(2)*pi/180) * cos(FI(3)*pi/180);
% 
%     %Вспомогательные коэффициенты
%     DA = AB2 + AC2 + 2*K;
%     DB = AB2 + BC2 + 2*K;
%     DC = AC2 + BC2 + 2*K;
%     D = AB2 + AC2 + BC2 + 3*K;
% 
%     %Весовые коэффициенты по координатам
%     koeff_coord = zeros(3, 1);
%     koeff_coord(1) = (D - DA)/D;
%     koeff_coord(2) = (D - DB)/D;
%     koeff_coord(3) = (D - DC)/D;

%Расчет весовых коэффициентов по скоростям
    %Квадрат расстояния между тремя БИНС
    AB2 = (Vn_c(1) - Vn_c(2))^2 + (Ve_c(1) - Ve_c(2))^2;
    AC2 = (Vn_c(1) - Vn_c(3))^2 + (Ve_c(1) - Ve_c(3))^2;
    BC2 = (Vn_c(2) - Vn_c(3))^2 + (Ve_c(2) - Ve_c(3))^2;

    %Вспомогательные коэффициенты
    DA = AB2 + AC2 + 2*K;
    DB = AB2 + BC2 + 2*K;
    DC = AC2 + BC2 + 2*K;
    D = AB2 + AC2 + BC2 + 3*K;

    %Весовые коэффициенты по скоростям
    koeff_veloc = zeros(3, 1);
    koeff_veloc(1) = (D - DA)/D;
    koeff_veloc(2) = (D - DB)/D;
    koeff_veloc(3) = (D - DC)/D;


 % %Расчет весовых коэффициентов по углам
 %    %Квадрат расстояния между тремя БИНС
 %    AB2 = (GAMMA(1) - GAMMA(2))^2 + (THETA(1) - THETA(2))^2 + (PSI(1) - PSI(2))^2;
 %    AC2 = (GAMMA(1) - GAMMA(3))^2 + (THETA(1) - THETA(3))^2 + (PSI(1) - PSI(3))^2;
 %    BC2 = (GAMMA(2) - GAMMA(3))^2 + (THETA(2) - THETA(3))^2 + (PSI(2) - PSI(3))^2;
 % 
 %    %Вспомогательные коэффициенты
 %    DA = AB2 + AC2 + 2*K;
 %    DB = AB2 + BC2 + 2*K;
 %    DC = AC2 + BC2 + 2*K;
 %    D = AB2 + AC2 + BC2 + 3*K;
 % 
 %    %Весовые коэффициенты по крену
 %    koeff_angle = zeros(3, 1);
 %    koeff_angle(1) = (D - DA)/D;
 %    koeff_angle(2) = (D - DB)/D;
 %    koeff_angle(3) = (D - DC)/D;
% 
        
      koeff = koeff_veloc;

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