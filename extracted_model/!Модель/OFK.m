function [x_est, P_est] = OFK(F, G, H, Q, R, Z, x_est_prev, P_est_prev, dt)
    % Переход к дискретной форме
    F_rus = eye(size(F)) + F*dt+((F*dt)^2)/2;
    G_rus = G*dt;

    % Вычисление промежуточных переменных
    S_intermediate = F_rus*P_est_prev*transpose(F_rus) + G_rus*Q*transpose(G_rus);
    K_intermediate = S_intermediate*transpose(H)*inv(H*S_intermediate*transpose(H) + R);

    % Коррекция
    P_est = (eye(size(F)) - K_intermediate*H)*S_intermediate;
    x_est = F_rus*x_est_prev + K_intermediate*(Z - H*F_rus*x_est_prev);
end