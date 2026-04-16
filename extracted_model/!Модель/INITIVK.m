%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Программа инициализации начального состаяния ИВК %%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% Без погрешностей начальной выставки
%%

TET0    = X0(9);        % Точное значение угла тангажа
GAM0    = X0(7);        % Точное значение угла крена
PSI0    = X0(8);        % Точное значение угла курса
% Без погрешностей выставки
XB0(1)  = cos(PSI0)*cos(TET0);
XB0(2)  =-cos(PSI0)*sin(TET0)*cos(GAM0)+sin(PSI0)*sin(GAM0);
XB0(3)  = cos(PSI0)*sin(TET0)*sin(GAM0)+sin(PSI0)*cos(GAM0);
XB0(4)  = sin(TET0);
XB0(5)  = cos(TET0)*cos(GAM0);
XB0(6)  =-cos(TET0)*sin(GAM0);
XB0(7)  =-cos(TET0)*sin(PSI0);	
XB0(8)  = cos(PSI0)*sin(GAM0)+sin(PSI0)*sin(TET0)*cos(GAM0);	
XB0(9)  = cos(PSI0)*cos(GAM0)-sin(PSI0)*sin(TET0)*sin(GAM0);
CBN0    = [XB0(1) XB0(2) XB0(3); XB0(4) XB0(5) XB0(6); XB0(7) XB0(8) XB0(9)];
% Инициализация начального состояняи кватерниона
q0 = cos(TET0/2)*cos(PSI0/2)*cos(GAM0/2) - sin(TET0/2)*sin(PSI0/2)*sin(GAM0/2);
q1 = cos(TET0/2)*cos(PSI0/2)*sin(GAM0/2) + sin(TET0/2)*sin(PSI0/2)*cos(GAM0/2);
q2 = cos(TET0/2)*sin(PSI0/2)*cos(GAM0/2) + sin(TET0/2)*cos(PSI0/2)*sin(GAM0/2);
q3 = sin(TET0/2)*cos(PSI0/2)*cos(GAM0/2) - cos(TET0/2)*sin(PSI0/2)*sin(GAM0/2);
Qu = [q0;q1;q2;q3];

% Проекции земной скорости в ССК
Vx1     = X0(1);        
Vy1     = X0(2);  
Vz1     = X0(3);
% Оценка земной скорости в НСК
XB0(10)=Vx1*cos(PSI0)*cos(TET0)-Vy1*(cos(PSI0)*sin(TET0)*cos(GAM0)-sin(PSI0)*sin(GAM0))+Vz1*(sin(PSI0)*cos(GAM0)+cos(PSI0)*sin(TET0)*sin(GAM0));
XB0(11)=Vx1*sin(TET0)+Vy1*cos(TET0)*cos(GAM0)-Vz1*cos(TET0)*sin(GAM0);
XB0(12)=-Vx1*sin(PSI0)*cos(TET0)+Vy1*(cos(PSI0)*sin(GAM0)+sin(PSI0)*sin(TET0)*cos(GAM0))+Vz1*(cos(PSI0)*cos(GAM0)-sin(PSI0)*sin(TET0)*sin(GAM0));
% Оценка координат
XB0(13) = X0(10);
XB0(14) = X0(11);
XB0(15) = X0(12);

X01     = [XB0(10);XB0(11);XB0(12);XB0(13);XB0(14);XB0(15)];

%% Инициализация БИНС 1
%%
SIGVYST = 0.1*pi/180/3600.0;        % СКО ошибок начальной выставки
DTET    = (-1+2*rand())*SIGVYST;    % Погрешность выставки в горизонт
DPH     = (-1+2*rand())*SIGVYST;	
DPSI    = (-1+2*rand())*SIGVYST;    % Погрешность выставки по азимуту
TETB    = TET0+DTET;    % Оценка угла тангажа
GAMB    = GAM0+DPH;     % Оценка угла крена
PSIB    = PSI0+DPSI;    % Оценка угла курса    
% Элементы матрицы направляющих косинусов (Cbn)
XB01(1)  = cos(PSIB)*cos(TETB);
XB01(2)  =-cos(PSIB)*sin(TETB)*cos(GAMB)+sin(PSIB)*sin(GAMB);
XB01(3)  = cos(PSIB)*sin(TETB)*sin(GAMB)+sin(PSIB)*cos(GAMB);
XB01(4)  = sin(TETB);
XB01(5)  = cos(TETB)*cos(GAMB);
XB01(6)  =-cos(TETB)*sin(GAMB);
XB01(7)  =-cos(TETB)*sin(PSIB);	
XB01(8)  = cos(PSIB)*sin(GAMB)+sin(PSIB)*sin(TETB)*cos(GAMB);	
XB01(9)  = cos(PSIB)*cos(GAMB)-sin(PSIB)*sin(TETB)*sin(GAMB);
CBN01    = [XB01(1) XB01(2) XB01(3); XB01(4) XB01(5) XB01(6); XB01(7) XB01(8) XB01(9)];
% Инициализация начального состояняи кватерниона
q0_1 = cos(TETB/2)*cos(PSIB/2)*cos(GAMB/2) - sin(TETB/2)*sin(PSIB/2)*sin(GAMB/2);
q1_1 = cos(TETB/2)*cos(PSIB/2)*sin(GAMB/2) + sin(TETB/2)*sin(PSIB/2)*cos(GAMB/2);
q2_1 = cos(TETB/2)*sin(PSIB/2)*cos(GAMB/2) + sin(TETB/2)*cos(PSIB/2)*sin(GAMB/2);
q3_1 = sin(TETB/2)*cos(PSIB/2)*cos(GAMB/2) - cos(TETB/2)*sin(PSIB/2)*sin(GAMB/2);
Qu1 = [q0_1;q1_1;q2_1;q3_1];

% Характеристики датчиков БИНС 1
global dw_1 kmw_1 fiw_1 da0_1 kma_1 fia_1
% Характеристики ДУС %
SIGW0   = 0.016*pi/180*1/3600; % Станд. смещение нуля (рад/сек)
SIGKMW  = 1.E-13;
SIGFIW  = 0.001*pi/180/3600.0; % угл. сек. ->рад

% Смещения нуля
dw_1 = [ SIGW0*sign(randn());
       SIGW0*sign(randn());
       SIGW0*sign(randn())];
% Погрешности масш. коэфф.
kmw_1 = [ SIGKMW*sign(randn()) 0                    0;
          0                    SIGKMW*sign(randn()) 0;
          0                    0                    SIGKMW*sign(randn())];
% Неортогональности
fixy = SIGFIW*sign(randn());
fixz = SIGFIW*sign(randn());
fiyx = SIGFIW*sign(randn());
fiyz = SIGFIW*sign(randn());
fizx = SIGFIW*sign(randn());
fizy = SIGFIW*sign(randn());
fiw_1 = [sqrt(1 - fixy^2 - fixz^2) fixy                      fixz;
         fiyx                      sqrt(1 - fiyx^2 - fiyz^2) fiyz;
         fizx                      fizy                      sqrt(1 - fizx^2 - fizy^2)];

% Характеристика ДЛУ %
SIGA0   = 0.00035; % Станд. смещение нуля
SIGKMA  = 1.E-7;
SIGFIA  = 0.001*pi/180/3600.0; % угл. сек. ->рад

% Смещения нуля
da0_1 = [SIGA0*sign(randn());
         SIGA0*sign(randn());
         SIGA0*sign(randn())];
% Погрешности масш. коэфф.
kma_1 = [ SIGKMA*sign(randn()) 0                    0;
          0                    SIGKMA*sign(randn()) 0;
          0                    0                    SIGKMA*sign(randn())];
% Неортогональности
fixy = SIGFIA*sign(randn());
fixz = SIGFIA*sign(randn());
fiyx = SIGFIA*sign(randn());
fiyz = SIGFIA*sign(randn());
fizx = SIGFIA*sign(randn());
fizy = SIGFIA*sign(randn());
fia_1 = [sqrt(1 - fixy^2 - fixz^2) fixy                      fixz;
         fiyx                      sqrt(1 - fiyx^2 - fiyz^2) fiyz;
         fizx                      fizy                      sqrt(1 - fizx^2 - fizy^2)];




%% Инициализация БИНС 2
%%
SIGVYST = 0.1*pi/180/3600.0;        % СКО ошибок начальной выставки (град/час)
DTET    = (-1+2*rand())*SIGVYST;    % Погрешность выставки в горизонт
DPH     = (-1+2*rand())*SIGVYST;	
DPSI    = (-1+2*rand())*SIGVYST;    % Погрешность выставки по азимуту
TETB    = TET0+DTET;    % Оценка угла тангажа
GAMB    = GAM0+DPH;     % Оценка угла крена
PSIB    = PSI0+DPSI;    % Оценка угла курса    
% Элементы матрицы направляющих косинусов (Cbn)
XB02(1)  = cos(PSIB)*cos(TETB);
XB02(2)  =-cos(PSIB)*sin(TETB)*cos(GAMB)+sin(PSIB)*sin(GAMB);
XB02(3)  = cos(PSIB)*sin(TETB)*sin(GAMB)+sin(PSIB)*cos(GAMB);
XB02(4)  = sin(TETB);
XB02(5)  = cos(TETB)*cos(GAMB);
XB02(6)  =-cos(TETB)*sin(GAMB);
XB02(7)  =-cos(TETB)*sin(PSIB);	
XB02(8)  = cos(PSIB)*sin(GAMB)+sin(PSIB)*sin(TETB)*cos(GAMB);	
XB02(9)  = cos(PSIB)*cos(GAMB)-sin(PSIB)*sin(TETB)*sin(GAMB);
CBN02    = [XB02(1) XB02(2) XB02(3); XB02(4) XB02(5) XB02(6); XB02(7) XB02(8) XB02(9)];
% Инициализация начального состояняи кватерниона
q0_2 = cos(TETB/2)*cos(PSIB/2)*cos(GAMB/2) - sin(TETB/2)*sin(PSIB/2)*sin(GAMB/2);
q1_2 = cos(TETB/2)*cos(PSIB/2)*sin(GAMB/2) + sin(TETB/2)*sin(PSIB/2)*cos(GAMB/2);
q2_2 = cos(TETB/2)*sin(PSIB/2)*cos(GAMB/2) + sin(TETB/2)*cos(PSIB/2)*sin(GAMB/2);
q3_2 = sin(TETB/2)*cos(PSIB/2)*cos(GAMB/2) - cos(TETB/2)*sin(PSIB/2)*sin(GAMB/2);
Qu2 = [q0_2;q1_2;q2_2;q3_2];

% Характеристики датчиков БИНС 2
global dw_2 kmw_2 fiw_2 da0_2 kma_2 fia_2
% Характеристики ДУС %
SIGW0   = 0.016*pi/180*1/3600; % Станд. смещение нуля
SIGKMW  = 1.E-13;
SIGFIW  = 0.001*pi/180/3600.0; % угл. сек. ->рад

% Смещения нуля
dw_2 = [ SIGW0*sign(randn());
       SIGW0*sign(randn());
       SIGW0*sign(randn())];
% Погрешности масш. коэфф.
kmw_2 = [ SIGKMW*sign(randn()) 0                    0;
          0                    SIGKMW*sign(randn()) 0;
          0                    0                    SIGKMW*sign(randn())];
% Неортогональности
fixy = SIGFIW*sign(randn());
fixz = SIGFIW*sign(randn());
fiyx = SIGFIW*sign(randn());
fiyz = SIGFIW*sign(randn());
fizx = SIGFIW*sign(randn());
fizy = SIGFIW*sign(randn());
fiw_2 = [sqrt(1 - fixy^2 - fixz^2) fixy                      fixz;
         fiyx                      sqrt(1 - fiyx^2 - fiyz^2) fiyz;
         fizx                      fizy                      sqrt(1 - fizx^2 - fizy^2)];

% Характеристика ДЛУ %
SIGA0   = 0.00035; % Станд. смещение нуля
SIGKMA  = 1.E-7;
SIGFIA  = 0.001*pi/180/3600.0; % угл. сек. ->рад

% Смещения нуля
da0_2 = [SIGA0*sign(randn());
         SIGA0*sign(randn());
         SIGA0*sign(randn())];
% Погрешности масш. коэфф.
kma_2 = [ SIGKMA*sign(randn()) 0                    0;
          0                    SIGKMA*sign(randn()) 0;
          0                    0                    SIGKMA*sign(randn())];
% Неортогональности
fixy = SIGFIA*sign(randn());
fixz = SIGFIA*sign(randn());
fiyx = SIGFIA*sign(randn());
fiyz = SIGFIA*sign(randn());
fizx = SIGFIA*sign(randn());
fizy = SIGFIA*sign(randn());
fia_2 = [sqrt(1 - fixy^2 - fixz^2) fixy                      fixz;
         fiyx                      sqrt(1 - fiyx^2 - fiyz^2) fiyz;
         fizx                      fizy                      sqrt(1 - fizx^2 - fizy^2)];





%% Инициализация БИНС 3
%%
SIGVYST = 0.1*pi/180/3600.0;        % СКО ошибок начальной выставки
DTET    = (-1+2*rand())*SIGVYST;    % Погрешность выставки в горизонт
DPH     = (-1+2*rand())*SIGVYST;	
DPSI    = (-1+2*rand())*SIGVYST;    % Погрешность выставки по азимуту
TETB    = TET0+DTET;    % Оценка угла тангажа
GAMB    = GAM0+DPH;     % Оценка угла крена
PSIB    = PSI0+DPSI;    % Оценка угла курса    
% Элементы матрицы направляющих косинусов (Cbn)
XB03(1)  = cos(PSIB)*cos(TETB);
XB03(2)  =-cos(PSIB)*sin(TETB)*cos(GAMB)+sin(PSIB)*sin(GAMB);
XB03(3)  = cos(PSIB)*sin(TETB)*sin(GAMB)+sin(PSIB)*cos(GAMB);
XB03(4)  = sin(TETB);
XB03(5)  = cos(TETB)*cos(GAMB);
XB03(6)  =-cos(TETB)*sin(GAMB);
XB03(7)  =-cos(TETB)*sin(PSIB);	
XB03(8)  = cos(PSIB)*sin(GAMB)+sin(PSIB)*sin(TETB)*cos(GAMB);	
XB03(9)  = cos(PSIB)*cos(GAMB)-sin(PSIB)*sin(TETB)*sin(GAMB);
CBN03    = [XB03(1) XB03(2) XB03(3); XB03(4) XB03(5) XB03(6); XB03(7) XB03(8) XB03(9)];
% Инициализация начального состояняи кватерниона
q0_3 = cos(TETB/2)*cos(PSIB/2)*cos(GAMB/2) - sin(TETB/2)*sin(PSIB/2)*sin(GAMB/2);
q1_3 = cos(TETB/2)*cos(PSIB/2)*sin(GAMB/2) + sin(TETB/2)*sin(PSIB/2)*cos(GAMB/2);
q2_3 = cos(TETB/2)*sin(PSIB/2)*cos(GAMB/2) + sin(TETB/2)*cos(PSIB/2)*sin(GAMB/2);
q3_3 = sin(TETB/2)*cos(PSIB/2)*cos(GAMB/2) - cos(TETB/2)*sin(PSIB/2)*sin(GAMB/2);
Qu3 = [q0_3;q1_3;q2_3;q3_3];

% Характеристики датчиков БИНС 3
global dw_3 kmw_3 fiw_3 da0_3 kma_3 fia_3
% Характеристики ДУС %
SIGW0   = 0.016*pi/180*1/3600; % Станд. смещение нуля
SIGKMW  = 1.E-13;
SIGFIW  = 0.001*pi/180/3600.0; % угл. сек. ->рад

% Смещения нуля
dw_3 = [ SIGW0*sign(randn());
       SIGW0*sign(randn());
       SIGW0*sign(randn())];
% Погрешности масш. коэфф.
kmw_3 = [ SIGKMW*sign(randn()) 0                    0;
          0                    SIGKMW*sign(randn()) 0;
          0                    0                    SIGKMW*sign(randn())];
% Неортогональности
fixy = SIGFIW*sign(randn());
fixz = SIGFIW*sign(randn());
fiyx = SIGFIW*sign(randn());
fiyz = SIGFIW*sign(randn());
fizx = SIGFIW*sign(randn());
fizy = SIGFIW*sign(randn());
fiw_3 = [sqrt(1 - fixy^2 - fixz^2) fixy                      fixz;
         fiyx                      sqrt(1 - fiyx^2 - fiyz^2) fiyz;
         fizx                      fizy                      sqrt(1 - fizx^2 - fizy^2)];

% Характеристика ДЛУ %
SIGA0   = 0.00035; % Станд. смещение нуля
SIGKMA  = 1.E-7;
SIGFIA  = 0.001*pi/180/3600.0; % угл. сек. ->рад

% Смещения нуля
da0_3 = [SIGA0*sign(randn());
         SIGA0*sign(randn());
         SIGA0*sign(randn())];
% Погрешности масш. коэфф.
kma_3 = [ SIGKMA*sign(randn()) 0                    0;
          0                    SIGKMA*sign(randn()) 0;
          0                    0                    SIGKMA*sign(randn())];
% Неортогональности
fixy = SIGFIA*sign(randn());
fixz = SIGFIA*sign(randn());
fiyx = SIGFIA*sign(randn());
fiyz = SIGFIA*sign(randn());
fizx = SIGFIA*sign(randn());
fizy = SIGFIA*sign(randn());
fia_3 = [sqrt(1 - fixy^2 - fixz^2) fixy                      fixz;
         fiyx                      sqrt(1 - fiyx^2 - fiyz^2) fiyz;
         fizx                      fizy                      sqrt(1 - fizx^2 - fizy^2)];