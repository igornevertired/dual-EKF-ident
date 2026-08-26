%% Функция расчета углов ориентации из матрицы направляющих косинусов
function [Psi, Theta, Gamma] = C_ANG (C)
    % Расчет Psi
    if abs(C(2,1)) > sqrt(2)/2
       Psi = atan(-C(1,1)/C(2,1));
    else
       Psi = pi/2 - atan(-C(2,1)/C(1,1));
    end

    % Расчет Theta
    Theta = asin(C(3,1));

    % Расчет Gamma
    if abs(C(3, 2)) > sqrt(2)/2
       Gamma = atan(-C(3, 3)/C(3, 2));
    else
       Gamma = pi/2 - atan(-C(3, 2)/C(3, 3));
    end
end