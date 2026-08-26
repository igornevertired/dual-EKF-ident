function [X]=MODELING_1(X0, XB0, TMODEL, DT, U0, CBN0, Qu, Qu_1, Qu_2, Qu_3)
global dw_1 da0_1 dw_2 da0_2 dw_3 da0_3
    %% Формирование вывода в файл
    %%
    fOUT_er1 = fopen('OUTPUT_error_BINS1.txt','wt','s','KOI8-R');
    fprintf(fOUT_er1,'TIME(sec.)  dVn  dVh  dVe  dH(m)  dFi(rad)  dLm(rad)\r\n');
    fOUT_er11 = fopen('OUTPUT_error_BINS11.txt','wt','s','KOI8-R');
    fprintf(fOUT_er11,'TIME(sec.)  dFi(rad)  dLm(rad)\r\n');
    fOUT_er2 = fopen('OUTPUT_error_BINS2.txt','wt','s','KOI8-R');
    fprintf(fOUT_er2,'TIME(sec.)  dVn  dVh  dVe  dH(m)  dFi(rad)  dLm(rad)\r\n');
    fOUT_er3 = fopen('OUTPUT_error_BINS3.txt','wt','s','KOI8-R');
    fprintf(fOUT_er3,'TIME(sec.)  dVn  dVh  dVe  dH(m)  dFi(rad)  dLm(rad)\r\n');
    fOUT_OFK1 = fopen('OUTPUT_OFK1.txt','wt','s','KOI8-R');
    fprintf(fOUT_OFK1,'TIME(sec.)  SKO_Fi  SKO_Lm  SKO_Vn  SKO_Ve  e_Fi_ofk  e_Lm_ofk  e_Vn  e_Ve\r\n');
    fOUT_OFK2 = fopen('OUTPUT_OFK2.txt','wt','s','KOI8-R');
    fprintf(fOUT_OFK2,'TIME(sec.)  SKO_Fi  SKO_Lm  SKO_Vn  SKO_Ve  e_Fi_ofk  e_Lm_ofk  e_Vn  e_Ve\r\n');
    fOUT_OFK3 = fopen('OUTPUT_OFK3.txt','wt','s','KOI8-R');
    fprintf(fOUT_OFK3,'TIME(sec.)  SKO_Fi  SKO_Lm  SKO_Vn  SKO_Ve  e_Fi_ofk  e_Lm_ofk  e_Vn  e_Ve\r\n');
    fOUT = fopen('OUT_X.txt','wt','s','KOI8-R');
    fprintf(fOUT,'TIME Vx Vy Vz Wx Wy Wz GAM PSI TET L H Z FI LAMD d dT dV dN dE Vwx Vwy Vwz HFL EPS X1\r\n');
    fOUT_GNSS = fopen('OUTPUT_GNSS.txt','wt','s','KOI8-R');
    fprintf(fOUT_GNSS,'TIME(sec.)  dFi2(rad)  dLm2(rad)\r\n');
    fOUT_SRD = fopen('OUTPUT_SRD.txt','wt','s','KOI8-R');
    fprintf(fOUT_SRD,'TIME(sec.)  dFi_corr(rad)  dLm_corr(rad) dVn_corr dVe_corr\r\n');
    fOUT_STATOFK = fopen('OUTPUT_STATOFK.txt','wt','s','KOI8-R');
    fprintf(fOUT_STATOFK,'dwcx   dwcy   dwcz  dacx  dacy   dacz  skowx   skowy   skowz   skoax   skoay   skoaz \r\n');
    fOUT_OCEN = fopen('OUTPUT_OCEN.txt','wt','s','KOI8-R');
    fprintf(fOUT_OCEN,'Vn1 Ve1 Fi1 Lm1 Vn2 Ve2 Fi2 Lm2 Vn3 Ve3 Fi3 Lm3 Fi_s Lm_s Vn_s Ve_s \r\n');

    % Для записи траектории
    % fOUT_AW = fopen('fOUT_AW.txt', 'wt','s','KOI8-R');
    % fprintf(fOUT_AW, 'TIME(sec.)  A1  A2  A3  W1  W2  W3\r\n');
    % fOUT_DX = fopen('OUT_DX.txt','wt','s','KOI8-R');
    % fprintf(fOUT_DX,'TIME Vx Vy Vz Wx Wy Wz GAM PSI TET L H Z FI LAMD d dT dV dN dE Vwx Vwy Vwz HFL EPS X1\r\n');

    str1 = '%.12f   ';
    format1 = [];
    for i = 1:7
        format1 = [format1 str1];
    end
    format1 = [format1 '\r\n'];

    str2 = '%.10f    ';
    format2 = [];
    for i = 1:26
        format2 = [format2 str2];
    end
    format2 = [format2 '\r\n'];

    str3 = '%.10f    ';
    format3 = [];
    for i = 1:3
        format3 = [format3 str3];
    end
    format3 = [format3 '\r\n'];

    str4 = '%.12f   ';
    format4 = [];
    for i = 1:9
        format4 = [format4 str4];
    end
    format4 = [format4 '\r\n'];

    str5 = '%.10f    ';
    format5 = [];
    for i = 1:5
        format5 = [format5 str5];
    end
    format5 = [format5 '\r\n'];

    str6 = '%.10f    ';
    format6 = [];
    for i = 1:16
        format6 = [format6 str6];
    end
    format6 = [format6 '\r\n'];
    
    %% Входные данные
    %%
    count = 0;
    count1 = 0;
    m = 1000;% частота записи в файл (Гц)
    mg = 10;% частота работы ОФК (Гц)

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
    Xref1 = [100; 100; 100; 50; 50; 50; 50; dw_1; da0_1];
    Xref2 = [100; 100; 100; 50; 50; 50; 50; dw_2; da0_2];
    Xref3 = [100; 100; 100; 50; 50; 50; 50; dw_3; da0_3];
    X_ofk1 = Xref1;
    X_ofk2 = Xref2;
    X_ofk3 = Xref3;
    P_ofk1 = diag(Xref1.^2);
    P_ofk2 = diag(Xref2.^2);
    P_ofk3 = diag(Xref3.^2);

    % Прототип функции динамики полета
    f = @(X,U,TIME)FX1(X,U,TIME);
   
    %% Моделирование
    %%
    while (TIME < TMODEL)
        % Интегрирование (работа модели динамики полета)
        [X, DX, A, W] = RK4(f, TIME, DT, X, U);

        % % Закон управления
        % [U] = AUTOPILOT(X,DX,TIME);

        % Формирование эталонного вектора навигационного решения БИНС
        NP_etalon = [DX(10); DX(11); DX(12); X(11); X(13); X(14)]; % - [Vn; Vh; Ve; H; Fi; Lm]

        % Генерация случайных возмущений
        GENERATOR_SV;

        % Работа БИНС 1,2,3
        [Qu1, C1, NP1, A1] = BINS1(A, W, NP1, C1, Qu1, DT, TIME, X(11), DX(11));
        [Qu2, C2, NP2, A2] = BINS2(A, W, NP2, C2, Qu2, DT, TIME, X(11), DX(11));
        [Qu3, C3, NP3, A3] = BINS3(A, W, NP3, C3, Qu3, DT, TIME, X(11), DX(11));
        
        % Сравнение навигационных решений БИНС 1,2,3 с эталонными значениями
        NPer1 = NP1 - NP_etalon;
        NPer2 = NP2 - NP_etalon;
        NPer3 = NP3 - NP_etalon;

        % Работа ГНСС 1 и ГНСС 2
        [NPgnss1, Vgnss1] = GNSS_1(X(13), X(14), DX(10), DX(12));
        GNSS_er1 = [X(13), X(14)] - NPgnss1(1:2);
        % [NPgnss2, Vgnss2] = GNSS_2(X(13), X(14), X(11), DX(10), DX(12));
        % GNSS_er2 = [X(13), X(14)] - NPgnss2(1:2);

        % Линейная модель БИНС для ОФК
        [F1, G1, H1, Q1] = BINS_OFK_2ch(A1, C1, NP1, DT);
        [F2, G2, H2, Q2] = BINS_OFK_2ch(A2, C2, NP2, DT);
        [F3, G3, H3, Q3] = BINS_OFK_2ch(A3, C3, NP3, DT);

        % Формирование матриц Z, V и R для ОФК
        Z1 = [NP1(5); NP1(6); NP1(1); NP1(3)] - NPgnss1; V1 = Vgnss1; R1 = diag((V1.^2)/DT);
        Z2 = [NP2(5); NP2(6); NP2(1); NP2(3)] - NPgnss1; V2 = Vgnss1; R2 = diag((V2.^2)/DT);
        Z3 = [NP3(5); NP3(6); NP3(1); NP3(3)] - NPgnss1; V3 = Vgnss1; R3 = diag((V3.^2)/DT);

        % Работа ОФК
        if (count1 == mg) || (TIME == DT)
            count1 = 0;
            [X_ofk1, P_ofk1] = OFK(F1, G1, H1, Q1, R1, Z1, X_ofk1, P_ofk1, DT*mg);
            [X_ofk2, P_ofk2] = OFK(F2, G2, H2, Q2, R2, Z2, X_ofk2, P_ofk2, DT*mg);
            [X_ofk3, P_ofk3] = OFK(F3, G3, H3, Q3, R3, Z3, X_ofk3, P_ofk3, DT*mg);
        end
        %[X_ofk1, P_ofk1] = OFK(F1, G1, H1, Q1, R1, Z1, X_ofk1, P_ofk1, DT);
        %[X_ofk2, P_ofk2] = OFK(F2, G2, H2, Q2, R2, Z2, X_ofk2, P_ofk2, DT);
        %[X_ofk3, P_ofk3] = OFK(F3, G3, H3, Q3, R3, Z3, X_ofk3, P_ofk3, DT);
        
        % Сравнение результата работы ОФК с эталонными значениями
        e1 = [X_ofk1(6:7); X_ofk1(4:5)] - [NPer1(5); NPer1(6); NPer1(1); NPer1(3)];
        e2 = [X_ofk2(6:7); X_ofk2(4:5)] - [NPer2(5); NPer2(6); NPer2(1); NPer2(3)];
        e3 = [X_ofk3(6:7); X_ofk3(4:5)] - [NPer3(5); NPer3(6); NPer3(1); NPer3(3)];
        SKO_Fi1 = sqrt(P_ofk1(6,6)); SKO_Lm1 = sqrt(P_ofk1(7,7));
        SKO_Vn1 = sqrt(P_ofk1(4,4)); SKO_Ve1 = sqrt(P_ofk1(5,5));
        SKO_Fi2 = sqrt(P_ofk2(6,6)); SKO_Lm2 = sqrt(P_ofk2(7,7));
        SKO_Vn2 = sqrt(P_ofk2(4,4)); SKO_Ve2 = sqrt(P_ofk2(5,5));
        SKO_Fi3 = sqrt(P_ofk3(6,6)); SKO_Lm3 = sqrt(P_ofk3(7,7));
        SKO_Vn3 = sqrt(P_ofk3(4,4)); SKO_Ve3 = sqrt(P_ofk3(5,5));

        % Оцененные показания БИНС
        % if (count1 == mg) || (TIME == DT)
        %     del1 = [NP1(1); NP1(3); NP1(5); NP1(6)] - [X_ofk1(4:7)]; % [Vn1; Ve1; Fi1; Lm1]
        %     del2 = [NP2(1); NP2(3); NP2(5); NP2(6)] - [X_ofk2(4:7)]; % [Vn2; Ve2; Fi2; Lm2]
        %     del3 = [NP3(1); NP3(3); NP3(5); NP3(6)] - [X_ofk3(4:7)]; % [Vn3; Ve3; Fi3; Lm3]
        % end
        del1 = [NP1(1); NP1(3); NP1(5); NP1(6)] - [X_ofk1(4:7)]; % [Vn1; Ve1; Fi1; Lm1]
        del2 = [NP2(1); NP2(3); NP2(5); NP2(6)] - [X_ofk2(4:7)]; % [Vn2; Ve2; Fi2; Lm2]
        del3 = [NP3(1); NP3(3); NP3(5); NP3(6)] - [X_ofk3(4:7)]; % [Vn3; Ve3; Fi3; Lm3]

        % Алгоритм осреднения
        if TIME == DT % начальное значение для входа в SRD (из ГНСС)
            Fi_corr = NPgnss1(1);
            Lm_corr = NPgnss1(2);
        end
        FI = [del1(3); del2(3); del3(3)]; V_N = [del1(1); del2(1); del3(1)];
        LM = [del1(4); del2(4); del3(4)]; V_E = [del1(2); del2(2); del3(2)];
        [Fi_corr, Lm_corr, Vn_corr, Ve_corr] = MK_SRD_1(FI, LM, Fi_corr, Lm_corr, V_N, V_E);
        SRD_er = [Fi_corr; Lm_corr; Vn_corr; Ve_corr] - [X(13); X(14); DX(10); DX(12)];
        
        % Закон управления
        X(13:14) = [Fi_corr; Lm_corr];
        DX(10) = Vn_corr; DX(12) = Ve_corr;
        [U] = AUTOPILOT(X,DX,TIME);

        % Запись в файл
        if (count == m) || (TIME == DT)
            count = 0;
            fprintf(fOUT_er1, format1, TIME1, NPer1);
            fprintf(fOUT_er2, format1, TIME1, NPer2);
            fprintf(fOUT_er3, format1, TIME1, NPer3);
            fprintf(fOUT, format2, TIME1, X);
            fprintf(fOUT_OFK1, format4, TIME1, SKO_Fi1, SKO_Lm1, SKO_Vn1, SKO_Ve1, e1);
            fprintf(fOUT_OFK2, format4, TIME1, SKO_Fi2, SKO_Lm2, SKO_Vn2, SKO_Ve2, e2);
            fprintf(fOUT_OFK3, format4, TIME1, SKO_Fi3, SKO_Lm3, SKO_Vn3, SKO_Ve3, e3);
            fprintf(fOUT_GNSS, format3, TIME1, GNSS_er1(1:2));
            fprintf(fOUT_SRD, format5, TIME1, SRD_er);
            fprintf(fOUT_OCEN, format6, del1, del2, del3, Fi_corr, Lm_corr, Vn_corr, Ve_corr);
            fprintf('%.1f\n', TIME1);
            TIME1 = TIME1 + DT*m;
        end
        % Обновление значений счетчиков
        count = count + 1;
        count1 = count1 + 1;
        TIME = TIME + DT;
    end
end