function [U]=AUTOPILOT(X,DX,TIME)
global TGLIDE U0_HORIZ U0_GLIDE 
    %% Предельные положения органов управления
    UMAX=[0.85;30;25;25];
    UMIN=[0.1;-25;-25;-25];
    %% Формирование вектора обратной связи
    Wx=X(4);    Wy=X(5);    Wz=X(6);
    GAM=X(7);   PSI=X(8);   TET=X(9);
    V=sqrt(X(1)^2+X(2)^2+X(3)^2);
    DV=sqrt(DX(1)^2+DX(2)^2+DX(3)^2);
    H=X(11); 
    Z=X(12);
    Az=DX(3);
    Vxg=DX(10);
    Vyg=DX(11);
    Vzg=DX(12);
    d=X(15); 
    THETA=asin(Vyg/sqrt(Vxg^2+Vzg^2));
    HFL=X(23);
    EPS=X(24);
    X1=X(25);
    XFEEDBACK=[Wx Wy Wz GAM PSI TET Az Vzg Z V DV H THETA d HFL EPS X1];
    %% Правило переключения между режимами
    % if (TIME<TGLIDE && H>400)
    %     KEY=0;
    % elseif (H>15.0)
    %     KEY=1;
    % else
    %     KEY=2;
    % end
    KEY = 0;
    %% Программное управление
    U0 = PROGCNTRL(KEY,U0_HORIZ,U0_GLIDE);
    %% Продольный канал
    DdeltaT=0.0;
    DdeltaV=0.0;
    % Режим горизонтального полета
    if (KEY==0)
        [DdeltaT,DdeltaV] = VHHOLD(XFEEDBACK);
    end
    % Режим захвата глиссады
    % if (KEY==1)
    %     [DdeltaT,DdeltaV] = GLCAPTURE(XFEEDBACK);
    % end
    % % Режим выравнивания
    % if (KEY==2)
    %     [DdeltaT,DdeltaV] = AUTOFLARE(XFEEDBACK);
    % end
    %% Боковой канал
    [DdeltaN,DdeltaE] = HEADINGHOLD(XFEEDBACK, TIME);
    %% Добавка по управления
    DU=[DdeltaT;DdeltaV;DdeltaN;DdeltaE];
    %% Вырабатыввемые сигналы управления
    U=U0+DU;
    %% Учет ограничения органов управления
    for i=1:4
        if (U(i)<UMIN(i))
            U(i)=UMIN(i);
        end
        if (U(i)>UMAX(i))
            U(i)=UMAX(i);
        end
    end
end

%% Программное управление
function U0 = PROGCNTRL(KEY,U0_HORIZ,U0_GLIDE)
persistent TFLARE
    U0=[0;0;0;0];
    %% Время отсчитанное от начала выравнивания	
    if isempty(TFLARE)
        TFLARE=0.0;
    end
    %DT=1.E-3;    
    %% Законы управления
    % Для горизонтального полета
    if (KEY==0)
        U0=U0_HORIZ;
    end
    % Для захвата глиссады
    % if (KEY==1)
    %     U0=U0_GLIDE;
    % end
    % % Для выравнивания
    % if (KEY==2)
    %     TFLARE=TFLARE+DT; 
    %     DRGR_BAL=U0_GLIDE(1);
    %     if (TFLARE<=10.0)
		% 	deltaDT=DRGR_BAL-(DRGR_BAL-0.1)/10.0*TFLARE;
	% 	else
		% 	deltaDT=0.1;
    %     end
    %     U0=[deltaDT;U0_GLIDE(2);U0_GLIDE(3);U0_GLIDE(4)];
    % end
end