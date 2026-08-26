function [DdeltaN,DdeltaE] = HEADINGHOLD(X, TIME)
    %% Оценка состояния ЛА
    Wx=X(1);    Wy=X(2);
    GAM=X(4);   PSI=X(5);
    Az=X(7);
    Vz=X(8);
    Z=X(9);

    %% Требуемое значение кгла курса
    PSITR = PSI;
    if (TIME > 100.0 && TIME < 300)
       PSITR = 45*Wy/180 - 45.0*Wy/180*(TIME - 100.0)/300;
    end
    if (TIME >= 400.0 && TIME < 550)
       PSITR = 45*Wy/180*(TIME - 400.0)/300;
    end
    if (TIME >= 700 && TIME<900)
       PSITR = 45*Wy/180 + 45*Wy/180*(TIME - 700)/300;
    end
    
    K_AIL_GAM = -0.295147;
    K_AIL_Wx = -4.501701;
    K_RUD_PSI = -0.124876;
    K_RUD_Wy = 2.706971;

    %Коррекция по элеронам
    dn = -1.5*K_AIL_Wx*Wx + K_AIL_GAM*GAM;% +K_AIL_Az * DX[2] + K_AIL_Vz * X[2] + K_AIL_Z * X[11] / 57.3;
    %Коррекция по рулю направления
    de = -1.5*K_RUD_Wy*Wy + K_RUD_PSI*(PSI - PSITR);% +K_RUD_Az * DX[2] + K_RUD_Vz * X[2] + K_RUD_Z * X[11] / 57.3;

    % %% Коэффициента автопилота
    % K_AIL_Z= -0.007852;
    % K_AIL_Vz = 0.008516;
    % K_AIL_Az = 0.323961;
    % K_AIL_GAM = -0.295147;
    % K_AIL_Wx = -4.501701;
    % K_RUD_Z = -0.010000;
    % K_RUD_Vz = -0.000950;
    % K_RUD_Az= 0.049556;
    % K_RUD_PSI= -0.124876;
    % K_RUD_Wy= 2.706971;
    % %% Законы управления
	% de=K_AIL_Wx*Wx+K_AIL_GAM*GAM+K_AIL_Az*Az+K_AIL_Vz*Vz+K_AIL_Z*Z/57.3;
	% dn=K_RUD_Wy*Wy+K_RUD_PSI*PSI+K_RUD_Az*Az+K_RUD_Vz*Vz+K_RUD_Z*Z/57.3;
    % 
	DdeltaN=dn;%*57.3;
	DdeltaE=de;%*57.3;
end