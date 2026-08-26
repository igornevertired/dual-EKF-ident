function [DdeltaT,DdeltaV] = VHHOLD(X)
global HTR VTR TETTR 
    %% Оценка состояния ЛА
    V=X(10);
    DV=X(11);
    H=X(12);
    Wz=X(3);
    TET=X(6);  
    %% Коэффициента автопилота
    K_ELEV_W= 1.339591;
    K_ELEV_THETA = -1.332765;
    K_ELEV_H = -0.127573;
    K_THROTTLE_V = 0.145670;
    K_THROTTLE_DV = -0.307940;
    K_ELEV_V = -0.148772;
    K_THROTTLE_H = 0.006174;
    %% Законы управления
    DdeltaT = K_THROTTLE_V * (VTR - V) + K_THROTTLE_DV * DV+K_THROTTLE_H*(HTR - H);
    DdeltaV = K_ELEV_W * Wz * 57.3 + K_ELEV_THETA * (TETTR-TET)*57.3 + K_ELEV_H*(HTR - H)+ K_ELEV_V*(VTR - V);
end