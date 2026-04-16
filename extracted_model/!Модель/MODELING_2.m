function [X]=MODELING_2(X0, XB0, TMODEL, DT, U0, CBN0, Qu, Qu_1, Qu_2, Qu_3)
global dw_1 da0_1
    %% Формирование вывода в файл
    %%
    fOUT_er1 = fopen('OUTPUT_error_BINS1.txt','wt','s','KOI8-R');
    fprintf(fOUT_er1,'TIME(sec.)  dVn  dVh  dVe  dH  dFi  dLm\r\n');

    fOUT_er2 = fopen('OUTPUT_error_BINS2.txt','wt','s','KOI8-R');
    fprintf(fOUT_er2,'TIME(sec.)  dVn  dVh  dVe  dH  dFi  dLm\r\n');

    fOUT_er3 = fopen('OUTPUT_error_BINS3.txt','wt','s','KOI8-R');
    fprintf(fOUT_er3,'TIME(sec.)  dVn  dVh  dVe  dH  dFi  dLm\r\n');

    fOUT_OFK1 = fopen('OUTPUT_OFK1.txt','wt','s','KOI8-R');
    fprintf(fOUT_OFK1,'TIME(sec.) SKO_Fi  SKO_Lm SKO_Vn SKO_Ve e_Fi_ofk e_Lm_ofk  e_Vn_ofk   e_Ve_ofk\r\n');
    
    fOUT = fopen('OUT_X.txt','wt','s','KOI8-R');
    fprintf(fOUT,'TIME Vx Vy Vz Wx Wy Wz GAM PSI TET L H Z FI LAMD d dT dV dN dE Vwx Vwy Vwz HFL EPS X1\r\n');

    fOUT_GNSS = fopen('OUTPUT_GNSS.txt','wt','s','KOI8-R');
    fprintf(fOUT_GNSS,'TIME(sec.)  dFi(rad)  dLm(rad) \r\n');

    fOUT_SRD = fopen('OUTPUT_SRD.txt','wt','s','KOI8-R');
    fprintf(fOUT_SRD,'TIME(sec.)  Fi_srd Lm_srd Vn_srd Ve_srd\r\n');

    fOUT_MD2 = fopen('OUT_MD2.txt','wt','s','KOI8-R');
    fprintf(fOUT_MD2,'TIME(sec.) Fi Lm Vn Ve SKO_Fi SKO_Lm SKO_Vn SKO_Ve\r\n');
    
    str = '%.12f   ';
    format1 = [];
    for i = 1:9
        format1 = [format1 str];
    end
    format1 = [format1 '\r\n'];

    str = '%.10f    ';
    format2 = [];
    for i = 1:26
        format2 = [format2 str];
    end
    format2 = [format2 '\r\n'];

    str = '%.10f    ';
    format3 = [];
    for i = 1:5
        format3 = [format3 str];
    end
    format3 = [format3 '\r\n'];
   
    str = '%.10f    ';
    format4 = [];
    for i = 1:3
        format4 = [format4 str];
    end
    format4 = [format4 '\r\n'];

    str = '%.10f    ';
    format5 = [];
    for i = 1:7
        format5 = [format5 str];
    end
    format5 = [format5 '\r\n'];

    str = '%.10f    ';
    format6 = [];
    for i = 1:9
        format6 = [format6 str];
    end
    format6 = [format6 '\r\n'];
    %% Входные данные
    %%
    count = 0;
    count1 = 0;
    m = 1000;% частота записи в файл
    mg = 10;% частота работы ОФК

    % Начальное время
    TIME = DT;
    TIME1 = DT*m;

    % Начальное состояние
    X = X0;
    U = U0;

    % Начальные значения для БИНС (выставка, из INITSIM - инициализация ИВК)
    NP1 = [XB0(10); XB0(11); XB0(12); X0(11); X0(13); X0(14)]; C1 = CBN0; Qu1 = Qu_1;
    NP2 = [XB0(10); XB0(11); XB0(12); X0(11); X0(13); X0(14)]; C2 = CBN0; Qu2 = Qu_2;
    NP3 = [XB0(10); XB0(11); XB0(12); X0(11); X0(13); X0(14)]; C3 = CBN0; Qu3 = Qu_3;

    % Начальные значения для ОФК
    Xref = [100; 100; 100; 50; 50; 50; 50; dw_1; da0_1];
    X_ofk = Xref;
    P_ofk = diag((Xref.^2));
    % Прототип функции динамики полета
    f = @(X,U,TIME)FX1(X,U,TIME);
   
    %% Моделирование
    %%
    while (TIME < TMODEL)
        % Интегрирование (работа модели динамики полета)
        [X, DX, A, W] = RK4(f, TIME, DT, X, U);

        % Закон управления
        [U] = AUTOPILOT(X,DX,TIME);

        % Формирование эталонного вектора навигационного решения БИНС
        NP_etalon = [DX(10); DX(11); DX(12); X(11); X(13); X(14)]; % - [Vn; Vh; Ve; H; Fi; Lm]
        
        % Генерация случайных возмущений
        GENERATOR_SV;

        % Работа БИНС
        [Qu1, C1, NP1, A1] = BINS1(A, W, NP1, C1, Qu1, DT, TIME, X(11), DX(11));
        [Qu2, C2, NP2, A2] = BINS2(A, W, NP2, C2, Qu2, DT, TIME, X(11), DX(11));
        [Qu3, C3, NP3, A3] = BINS3(A, W, NP3, C3, Qu3, DT, TIME, X(11), DX(11));
        
        % Ошибка вычисления БИНС
        NPer1 = NP1 - NP_etalon;
        NPer2 = NP2 - NP_etalon;
        NPer3 = NP3 - NP_etalon;
    
        % Работа ГНСС
        [NPgnss1, Vgnss1] = GNSS_1(X(13), X(14), DX(10), DX(12));
        GNSS_er = [X(13); X(14)] - NPgnss1(1:2);

        % Алгоритм осреднения SRD
        if TIME == DT % начальное значение для входа в SRD (из ГНСС)
            Fi_corr = NPgnss1(1);
            Lm_corr = NPgnss1(2);
        end

        FI = [NP1(5); NP2(5); NP3(5)];
        LM = [NP1(6); NP2(6); NP3(6)];
        A_c = [A1 A2 A3];
        Vn_c = [NP1(1); NP2(1); NP3(1)];
        Ve_c = [NP1(3); NP2(3); NP3(3)];

        [Fi_corr, Lm_corr, A_srd, Vn_srd, Ve_srd, C_srd] = MK_SRD_2(FI, LM, Fi_corr, Lm_corr, A_c, Vn_c, Ve_c, C1, C2, C3);
        SRD_er = [Fi_corr; Lm_corr; Vn_srd; Ve_srd] - [X(13); X(14); DX(10); DX(12)];

        % Формирование матриц F, G, H и Q для ОФК
        NP_srd = [Vn_srd; NP1(2); Ve_srd; NP1(4); Fi_corr; Lm_corr];
        [F1, G1, H1, Q1] = BINS_OFK_2ch(A_srd, C_srd, NP_srd, DT);
       
        % Формирование матриц Z, V и R для ОФК
        Z1 = [Fi_corr; Lm_corr; Vn_srd; Ve_srd] - NPgnss1; V1 = Vgnss1; R1 = diag((V1.^2)/DT);
        %Z1 = [Fi_corr; Lm_corr] - NPgnss1(1:2); V1 = Vgnss1(1:2); R1 = diag((V1.^2)/DT);

        % Работа ОФК
        if (count1 == mg) || (TIME == DT)
            count1 = 0;
            [X_ofk, P_ofk] = OFK(F1, G1, H1, Q1, R1, Z1, X_ofk, P_ofk, DT*mg);
        end
        %[X_ofk, P_ofk] = OFK(F1, G1, H1, Q1, R1, Z1, X_ofk, P_ofk, DT);

        e1 = [X_ofk(6:7); X_ofk(4:5)] - SRD_er;
        SKO_Fi1 = sqrt(P_ofk(6,6)); SKO_Lm1 = sqrt(P_ofk(7,7));
        SKO_Vn = sqrt(P_ofk(4,4)); SKO_Ve = sqrt(P_ofk(5,5));
        
        % Ошибка вычисления после оценки показаний SRD через ОФК
        Fi_out = Fi_corr - X_ofk(6) - X(13);
        Lm_out = Lm_corr - X_ofk(7) - X(14);
        Vn_out = Vn_srd - X_ofk(4) - DX(10);
        Ve_out = Ve_srd - X_ofk(5) - DX(12);
        Res_plot = [Fi_out; Lm_out; Vn_out; Ve_out];
        Res_sko = [SKO_Fi1; SKO_Lm1; SKO_Vn; SKO_Ve];

        % Запись в файл
        if (count == m) || (TIME == DT)
            count = 0;
            fprintf(fOUT_er1, format5, TIME1, NPer1);
            fprintf(fOUT_er2, format5, TIME1, NPer2);
            fprintf(fOUT_er3, format5, TIME1, NPer3);
            fprintf(fOUT, format2, TIME1, X);
            fprintf(fOUT_GNSS, format4, TIME1, GNSS_er);
            fprintf(fOUT_OFK1, format1, TIME1, SKO_Fi1, SKO_Lm1, SKO_Vn, SKO_Ve, e1);
            fprintf(fOUT_SRD, format3, TIME1, SRD_er);
            fprintf(fOUT_MD2, format6, TIME1, Res_plot, Res_sko);
            fprintf('%.1f\n', TIME1);
            TIME1 = TIME1 + DT*m;
        end

        % Обновление значений счетчиков
        count = count + 1;
        count1 = count1 + 1;
        TIME = TIME + DT;
    end
end