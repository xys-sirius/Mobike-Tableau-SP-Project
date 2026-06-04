% extract_ode_truth.m - 从MAT数据提取真实ODE概率值，用于修正表3和表5
clear; clc;

% 加载已有的仿真结果
load('C:/Users/33294/Desktop/paper_project/scripts/simulation_results.mat');

fprintf('=== 从 simulation_results.mat 提取真实ODE数据 ===\n\n');

% 检查P_CBD矩阵的维度
fprintf('P_CBD size: %d x %d\n', size(P_CBD,1), size(P_CBD,2));
fprintf('P_RES size: %d x %d\n', size(P_RES,1), size(P_RES,2));
fprintf('t_span length: %d\n', length(t_span));
K_CBD = size(P_CBD,1) - 1;
K_RES = size(P_RES,1) - 1;

%% 提取关键时间点的概率
key_hours = [0, 8, 12, 18, 23];
fprintf('\n--- 关键时间点概率 ---\n');
fprintf('Time  | CBD P(N=0) | CBD P(N=K) | RES P(N=0) | RES P(N=K)\n');
fprintf('------|------------|------------|------------|------------\n');

for h = key_hours
    idx = find(t_span >= h, 1, 'first');
    p0_cbd = P_CBD(1, idx) * 100;
    pk_cbd = P_CBD(K_CBD+1, idx) * 100;
    p0_res = P_RES(1, idx) * 100;
    pk_res = P_RES(K_RES+1, idx) * 100;
    fprintf('%02d:00 | %9.4f%% | %9.4f%% | %9.4f%% | %9.4f%%\n', ...
        h, p0_cbd, pk_cbd, p0_res, pk_res);
end

%% 找CBD双风险的峰值
[P0_CBD_max, idx_P0_CBD] = max(P_CBD(1,:));
[PK_CBD_max, idx_PK_CBD] = max(P_CBD(K_CBD+1,:));
[P0_RES_max, idx_P0_RES] = max(P_RES(1,:));
[PK_RES_max, idx_PK_RES] = max(P_RES(K_RES+1,:));

fprintf('\n--- 极限参数 ---\n');
fprintf('CBD 空站绝对峰值: %.4f%% @ t=%.2fh\n', P0_CBD_max*100, t_span(idx_P0_CBD));
fprintf('CBD 满站绝对峰值: %.4f%% @ t=%.2fh\n', PK_CBD_max*100, t_span(idx_PK_CBD));
fprintf('RES 空站绝对峰值: %.4f%% @ t=%.2fh\n', P0_RES_max*100, t_span(idx_P0_RES));
fprintf('RES 满站绝对峰值: %.4f%% @ t=%.2fh\n', PK_RES_max*100, t_span(idx_PK_RES));

%% 逐小时提取所有时间点的概率(用于绘表)
fprintf('\n--- 逐小时P(N=0)和P(N=K) ---\n');
for h = 0:23
    idx = find(t_span >= h, 1, 'first');
    p0_c = P_CBD(1, idx) * 100;
    pk_c = P_CBD(K_CBD+1, idx) * 100;
    p0_r = P_RES(1, idx) * 100;
    pk_r = P_RES(K_RES+1, idx) * 100;
    fprintf('%02d:00 | CBD: empty=%6.3f%% full=%6.3f%% | RES: empty=%6.3f%% full=%6.3f%%\n', ...
        h, p0_c, pk_c, p0_r, pk_r);
end

%% ============ K敏感性分析 ============
fprintf('\n\n=== K敏感性分析 ===\n');
fprintf('对不同K值重新运行CBD站ODE...\n');

load('C:/Users/33294/Desktop/paper_project/scripts/eda_results.mat');
load('C:/Users/33294/Desktop/paper_project/scripts/poisson_test_results.mat');

dt_ode = 0.005;
t_span = 0:dt_ode:24;
n_ode = length(t_span);

ode_hr = floor(t_span) + 1;
ode_hr(ode_hr > 24) = 24;
lam_ode = lambda_hourly(ode_hr) / 3600;
mu_ode  = mu_hourly(ode_hr) / 3600;

K_values = [40, 50, 60, 80];
fprintf('K    | max P(N=0)   | max P(N=K)   | mean N\n');
fprintf('-----|--------------|--------------|--------\n');

for K_test = K_values
    N0 = round(K_test / 2);
    P = zeros(K_test+1, n_ode);
    P(N0+1, 1) = 1;
    
    for j = 1:n_ode-1
        lam = lam_ode(j); mu = mu_ode(j);
        Pc = P(:,j);
        dP = zeros(K_test+1, 1);
        dP(1) = -lam*Pc(1) + mu*Pc(2);
        for i = 2:K_test
            dP(i) = lam*Pc(i-1) - (lam+mu)*Pc(i) + mu*Pc(i+1);
        end
        dP(K_test+1) = lam*Pc(K_test) - mu*Pc(K_test+1);
        Pn = Pc + dP*dt_ode;
        Pn = max(Pn, 0); Pn = Pn / sum(Pn);
        P(:,j+1) = Pn;
    end
    
    max_P0 = max(P(1,:)) * 100;
    max_PK = max(P(K_test+1,:)) * 100;
    mean_N = mean((0:K_test) * P);
    fprintf('%-4d | %11.4f%% | %11.4f%% | %7.2f\n', K_test, max_P0, max_PK, mean_N);
end

fprintf('\n=== 提取完成 ===\n');