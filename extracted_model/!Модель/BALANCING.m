%% АЛГОРИТМ РЕШЕНИЯ ЗАДАЧИ БАЛАНСИРОВКИ ПОЛЕТА
function [BAL,J]=BALANCING(HTR,VTR,THETATR,GAMTR,BETATR)    
    %% Прототип функции критерия
    f = @(BAL)FCT(BAL,HTR,VTR,THETATR,GAMTR,BETATR); 
    %% Начальное значение поисковых параметров балансировки
    BAL0=[0.0,0.0,0.0,0.0,0.0];%FCT(BAL0,HTR,VTR,THETATR,GAMTR,BETATR);
%     options = optimset('fminunc');
%     options = optimset(options,'Display','iter','PlotFcns',@optimplotfval);
%     [BAL,J] = fminunc(f,BAL0,options);
    %% Оптимизация
   [BAL,J] = fminunc(f,BAL0);
end
