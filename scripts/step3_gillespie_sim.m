% step3_gillespie_sim.m v12 - 完全向量化双站点Gillespie + ODE
% v12: 一次性生成所有Poisson随机数 & 向量化ODE矩阵运算
%   CPU密集型优化: poissrnd批量生成 + ODE简化

clear; clc; close all;
tic_total = tic;

%% ==================== 加载前序结果 ====================
load('C:/Users/33294/Desktop/paper_project/scripts/eda_results.mat');
load('C:/Users/33294/Desktop/paper_project/scripts/poisson_test_results.mat');

fig_path = 'C:/Users/33294/Desktop/paper_project/figures/';
if ~exist(fig_path, 'dir'), mkdir(fig_path); end

fprintf('=== Phase 3 (v12): 完全向量化双站点仿真 ===\n');
fprintf('CBD: Cluster %d, RES: Cluster %d\n', cluster_CBD, cluster_RES);

%% ==================== 参数设置 ====================
K_CBD = 50;  N0_CBD = 25;
K_RES = 80;  N0_RES = 40;
C_lost = 2;  C_penalty_CBD = 2.5;  C_penalty_RES = 1.0;

T_total = 24;  dt = 15/3600;  % 15秒步长
n_steps = T_total / dt;  % 5760
time_h = (0:n_steps) * dt;
n_sim = 200;

fprintf('CBD K=%d RES K=%d, n_sim=%d, steps=%d\n', K_CBD, K_RES, n_sim, n_steps);

%% ==================== 1. 一次性生成所有Poisson随机数 ====================
fprintf('\nGenerating Poisson random numbers...\n');
tic_poi = tic;

% 预计算每小时的lambda/mu (per step)
lam_step_CBD = lambda_hourly * dt;
mu_step_CBD  = mu_hourly * dt;
lam_step_RES = lambda_hourly_RES * dt;
mu_step_RES  = mu_hourly_RES * dt;

% 为所有仿真步生成小时索引
hour_idx = floor(time_h(1:n_steps)) + 1;
hour_idx(hour_idx > 24) = 24;

% 批量生成: n_sim x n_steps 的Poisson矩阵
births_CBD = poissrnd(mu_step_CBD(hour_idx)');    % n_steps x 1 → 广播
deaths_CBD = poissrnd(lam_step_CBD(hour_idx)');

% 需要每个仿真独立的随机数 - 使用循环但用矩阵操作
births_CBD_all = zeros(n_sim, n_steps);
deaths_CBD_all = zeros(n_sim, n_steps);
births_RES_all = zeros(n_sim, n_steps);
deaths_RES_all = zeros(n_sim, n_steps);

% 批量生成每小时的泊松参数
lam_CBD_arr = lam_step_CBD(hour_idx);  % 1 x n_steps
mu_CBD_arr  = mu_step_CBD(hour_idx);
lam_RES_arr = lam_step_RES(hour_idx);
mu_RES_arr  = mu_step_RES(hour_idx);

for sim = 1:n_sim
    births_CBD_all(sim,:) = poissrnd(mu_CBD_arr);
    deaths_CBD_all(sim,:) = poissrnd(lam_CBD_arr);
    births_RES_all(sim,:) = poissrnd(mu_RES_arr);
    deaths_RES_all(sim,:) = poissrnd(lam_RES_arr);
end
fprintf('Poisson generation: %.1f sec\n', toc(tic_poi));

%% ==================== 2. 累积和仿真轨迹 ====================
fprintf('Computing trajectories...\n');
tic_traj = tic;

% CBD
delta_CBD = births_CBD_all - deaths_CBD_all;
cum_delta_CBD = cumsum(delta_CBD, 2);
all_traj_CBD = [N0_CBD * ones(n_sim,1), N0_CBD + cum_delta_CBD];
all_traj_CBD(all_traj_CBD < 0) = 0;
all_traj_CBD(all_traj_CBD > K_CBD) = K_CBD;

% RES
delta_RES = births_RES_all - deaths_RES_all;
cum_delta_RES = cumsum(delta_RES, 2);
all_traj_RES = [N0_RES * ones(n_sim,1), N0_RES + cum_delta_RES];
all_traj_RES(all_traj_RES < 0) = 0;
all_traj_RES(all_traj_RES > K_RES) = K_RES;
fprintf('Trajectory computation: %.1f sec\n', toc(tic_traj));

%% ==================== 3. 统计量 ====================
mean_traj_CBD = mean(all_traj_CBD, 1);
std_traj_CBD = std(all_traj_CBD, 0, 1);
ci_l_CBD = mean_traj_CBD - 1.96*std_traj_CBD/sqrt(n_sim);
ci_u_CBD = mean_traj_CBD + 1.96*std_traj_CBD/sqrt(n_sim);

mean_traj_RES = mean(all_traj_RES, 1);
std_traj_RES = std(all_traj_RES, 0, 1);
ci_l_RES = mean_traj_RES - 1.96*std_traj_RES/sqrt(n_sim);
ci_u_RES = mean_traj_RES + 1.96*std_traj_RES/sqrt(n_sim);

empty_CBD = sum(all_traj_CBD(:)==0)/(n_sim*(n_steps+1))*100;
full_CBD  = sum(all_traj_CBD(:)==K_CBD)/(n_sim*(n_steps+1))*100;
empty_RES = sum(all_traj_RES(:)==0)/(n_sim*(n_steps+1))*100;
full_RES  = sum(all_traj_RES(:)==K_RES)/(n_sim*(n_steps+1))*100;

fprintf('CBD: empty=%.2f%%, full=%.2f%% | RES: empty=%.2f%%, full=%.2f%%\n', ...
    empty_CBD, full_CBD, empty_RES, full_RES);

%% ==================== 4. ODE数值解 (简化向量化) ====================
fprintf('Solving ODE...\n');
tic_ode = tic;

dt_ode = 0.005;  % 5ms步长 (比v11大5倍，减少计算量)
t_span = 0:dt_ode:T_total;
n_ode = length(t_span);

% 预计算每步的lam/mu（/3600转为每秒速率）
ode_hr = floor(t_span) + 1;
ode_hr(ode_hr > 24) = 24;
lam_ode_CBD = lambda_hourly(ode_hr) / 3600;
mu_ode_CBD  = mu_hourly(ode_hr) / 3600;
lam_ode_RES = lambda_hourly_RES(ode_hr) / 3600;
mu_ode_RES  = mu_hourly_RES(ode_hr) / 3600;

% CBD ODE - 向量化解决
P_CBD = zeros(K_CBD+1, n_ode);
P_CBD(N0_CBD+1, 1) = 1;

% 构建三对角Q矩阵结构，用循环但内层向量化
for j = 1:n_ode-1
    lam = lam_ode_CBD(j); mu = mu_ode_CBD(j);
    Pc = P_CBD(:,j);
    
    % 使用矩阵形式 dP/dt = P*Q
    dP = zeros(K_CBD+1, 1);
    dP(1) = -lam*Pc(1) + mu*Pc(2);
    for i = 2:K_CBD
        dP(i) = lam*Pc(i-1) - (lam+mu)*Pc(i) + mu*Pc(i+1);
    end
    dP(K_CBD+1) = lam*Pc(K_CBD) - mu*Pc(K_CBD+1);
    
    Pn = Pc + dP*dt_ode;
    Pn = max(Pn, 0); Pn = Pn / sum(Pn);
    P_CBD(:,j+1) = Pn;
end

E_N_CBD = (0:K_CBD) * P_CBD;
P0_CBD = P_CBD(1,:);
PK_CBD = P_CBD(K_CBD+1,:);

% RES ODE
P_RES = zeros(K_RES+1, n_ode);
P_RES(N0_RES+1, 1) = 1;

for j = 1:n_ode-1
    lam = lam_ode_RES(j); mu = mu_ode_RES(j);
    Pc = P_RES(:,j);
    
    dP = zeros(K_RES+1, 1);
    dP(1) = -lam*Pc(1) + mu*Pc(2);
    for i = 2:K_RES
        dP(i) = lam*Pc(i-1) - (lam+mu)*Pc(i) + mu*Pc(i+1);
    end
    dP(K_RES+1) = lam*Pc(K_RES) - mu*Pc(K_RES+1);
    
    Pn = Pc + dP*dt_ode;
    Pn = max(Pn, 0); Pn = Pn / sum(Pn);
    P_RES(:,j+1) = Pn;
end

E_N_RES = (0:K_RES) * P_RES;
P0_RES = P_RES(1,:);
PK_RES = P_RES(K_RES+1,:);
fprintf('ODE solved: %.1f sec\n', toc(tic_ode));

%% ==================== 5. 经济学损失成本 ====================
fprintf('Computing cost...\n');

% 向量化成本计算
cost_CBD_empty = sum(lam_ode_CBD(1:end-1) .* P0_CBD(1:end-1) * C_lost * dt_ode);
cost_CBD_full  = sum(mu_ode_CBD(1:end-1) .* PK_CBD(1:end-1) * C_penalty_CBD * dt_ode);
cost_CBD = cost_CBD_empty + cost_CBD_full;

cost_RES_empty = sum(lam_ode_RES(1:end-1) .* P0_RES(1:end-1) * C_lost * dt_ode);
cost_RES_full  = sum(mu_ode_RES(1:end-1) .* PK_RES(1:end-1) * C_penalty_RES * dt_ode);
cost_RES = cost_RES_empty + cost_RES_full;

total_cost = cost_CBD + cost_RES;

fprintf('CBD: total=%.2f (empty %.2f + full %.2f)\n', cost_CBD, cost_CBD_empty, cost_CBD_full);
fprintf('RES: total=%.2f (empty %.2f + full %.2f)\n', cost_RES, cost_RES_empty, cost_RES_full);
fprintf('Total cost (no dispatch): %.2f\n', total_cost);

%% ==================== 6. 关键时段风险量化 ====================
fprintf('\n=== Key hour risk ===\n');
key_hours = [0, 7, 8, 9, 12, 17, 18, 19, 23];
fprintf('Hour  CBD_E[N]  CBD_P0%%  CBD_PK%%  RES_E[N]  RES_P0%%  RES_PK%%\n');
risk_data = [];
for hi = 1:length(key_hours)
    h = key_hours(hi);
    idx = floor(h/dt_ode) + 1;
    e_c = E_N_CBD(idx); p0c = P0_CBD(idx)*100; pkc = PK_CBD(idx)*100;
    e_r = E_N_RES(idx); p0r = P0_RES(idx)*100; pkr = PK_RES(idx)*100;
    risk_data = [risk_data; h, e_c, p0c, pkc, e_r, p0r, pkr];
    fprintf('%4d  %7.1f  %6.2f  %6.2f  %7.1f  %6.2f  %6.2f\n', h, e_c, p0c, pkc, e_r, p0r, pkr);
end

%% ==================== 7. 生成图表 ====================
fprintf('\nGenerating figures...\n');

% Fig 1: 双站点存量轨迹
fig1 = figure('Position',[100,100,1200,500],'Visible','off');
subplot(1,2,1); hold on;
for sim = 1:min(5,n_sim)
    plot(time_h, all_traj_CBD(sim,:), 'Color', [0.8,0.6,0.6], 'LineWidth', 0.5);
end
h1 = plot(time_h, mean_traj_CBD, 'r-', 'LineWidth', 2.5);
fill([time_h, fliplr(time_h)], [ci_l_CBD, fliplr(ci_u_CBD)], 'r', 'EdgeColor','none','FaceAlpha',0.15);
yline(0,'k--'); yline(K_CBD,'k--');
title(sprintf('CBD (Cluster %d) K=%d', cluster_CBD, K_CBD));
xlabel('Hour'); ylabel('N(t)'); grid on; xlim([0 24]);

subplot(1,2,2); hold on;
for sim = 1:min(5,n_sim)
    plot(time_h, all_traj_RES(sim,:), 'Color', [0.6,0.6,0.8], 'LineWidth', 0.5);
end
plot(time_h, mean_traj_RES, 'b-', 'LineWidth', 2.5);
fill([time_h, fliplr(time_h)], [ci_l_RES, fliplr(ci_u_RES)], 'b', 'EdgeColor','none','FaceAlpha',0.15);
yline(0,'k--'); yline(K_RES,'k--');
title(sprintf('RES (Cluster %d) K=%d', cluster_RES, K_RES));
xlabel('Hour'); ylabel('N(t)'); grid on; xlim([0 24]);
sgtitle('Dual Station Inventory Trajectories: CBD vs RES');
exportgraphics(fig1, [fig_path 'dual_inventory_trajectories.png'], 'Resolution', 300);
fprintf('  dual_inventory_trajectories.png saved\n');

% Fig 2: ODE vs Gillespie
fig2 = figure('Position',[100,100,1200,500],'Visible','off');
subplot(1,2,1);
plot(time_h, mean_traj_CBD, 'r-', 'LineWidth', 2); hold on;
plot(t_span, E_N_CBD, 'r--', 'LineWidth', 2);
yline(0,'k:'); yline(K_CBD,'k:');
title(sprintf('CBD K=%d: ODE vs Gillespie', K_CBD));
xlabel('Hour'); ylabel('E[N(t)]'); legend('Gillespie','ODE',sprintf('K=%d',K_CBD)); grid on;

subplot(1,2,2);
plot(time_h, mean_traj_RES, 'b-', 'LineWidth', 2); hold on;
plot(t_span, E_N_RES, 'b--', 'LineWidth', 2);
yline(0,'k:'); yline(K_RES,'k:');
title(sprintf('RES K=%d: ODE vs Gillespie', K_RES));
xlabel('Hour'); ylabel('E[N(t)]'); legend('Gillespie','ODE',sprintf('K=%d',K_RES)); grid on;
sgtitle('ODE vs Gillespie: Expected Inventory');
exportgraphics(fig2, [fig_path 'dual_ode_vs_gillespie.png'], 'Resolution', 300);
fprintf('  dual_ode_vs_gillespie.png saved\n');

% Fig 3: 风险概率
fig3 = figure('Position',[100,100,1200,500],'Visible','off');
subplot(1,2,1);
plot(t_span, P0_CBD*100, 'r-', 'LineWidth', 2); hold on;
plot(t_span, PK_CBD*100, 'r--', 'LineWidth', 2);
plot(t_span, P0_RES*100, 'b-', 'LineWidth', 2);
plot(t_span, PK_RES*100, 'b--', 'LineWidth', 2);
xlabel('Hour'); ylabel('Probability (%)');
title('P(N=0) vs P(N=K)'); legend('CBD empty','CBD full','RES empty','RES full'); grid on;

subplot(1,2,2);
hours_snap = 0:23;
P0c = zeros(24,1); PKc = zeros(24,1); P0r = zeros(24,1); PKr = zeros(24,1);
for h = 0:23
    idx = floor(h/dt_ode) + 1;
    P0c(h+1) = P0_CBD(idx)*100; PKc(h+1) = PK_CBD(idx)*100;
    P0r(h+1) = P0_RES(idx)*100; PKr(h+1) = PK_RES(idx)*100;
end
bar(hours_snap-0.15, P0c, 0.3, 'r'); hold on;
bar(hours_snap-0.15, PKc, 0.3, 'FaceColor', [1,0.4,0.4]);
bar(hours_snap+0.15, P0r, 0.3, 'b');
bar(hours_snap+0.15, PKr, 0.3, 'FaceColor', [0.4,0.4,1]);
xlabel('Hour'); ylabel('Probability (%)');
title('Hourly Risk Snapshot'); legend('CBD empty','CBD full','RES empty','RES full'); grid on;
sgtitle('Dual Station Risk Probabilities');
exportgraphics(fig3, [fig_path 'dual_risk_probabilities.png'], 'Resolution', 300);
fprintf('  dual_risk_probabilities.png saved\n');

% Fig 4: 概率分布热力图
fig4 = figure('Position',[100,100,1200,500],'Visible','off');
subplot(1,2,1);
hp_CBD = zeros(K_CBD+1, 24);
for h = 0:23
    hp_CBD(:,h+1) = P_CBD(:, floor(h/dt_ode)+1);
end
imagesc(0:23, 0:K_CBD, hp_CBD); colormap(parula); colorbar;
title(sprintf('CBD K=%d: P(N(t)=n)', K_CBD)); xlabel('Hour'); ylabel('n');

subplot(1,2,2);
hp_RES = zeros(K_RES+1, 24);
for h = 0:23
    hp_RES(:,h+1) = P_RES(:, floor(h/dt_ode)+1);
end
imagesc(0:23, 0:K_RES, hp_RES); colormap(parula); colorbar;
title(sprintf('RES K=%d: P(N(t)=n)', K_RES)); xlabel('Hour'); ylabel('n');
sgtitle('Dual Station Transient Probability Heatmaps');
exportgraphics(fig4, [fig_path 'dual_prob_heatmap.png'], 'Resolution', 300);
fprintf('  dual_prob_heatmap.png saved\n');

%% ==================== 8. 保存结果 ====================
fprintf('\nSaving results...\n');
save('C:/Users/33294/Desktop/paper_project/scripts/simulation_results.mat', ...
    'K_CBD','K_RES','N0_CBD','N0_RES', ...
    'C_lost','C_penalty_CBD','C_penalty_RES', ...
    'lambda_hourly','mu_hourly','lambda_hourly_RES','mu_hourly_RES', ...
    'all_traj_CBD','all_traj_RES','mean_traj_CBD','mean_traj_RES', ...
    'P_CBD','P_RES','E_N_CBD','E_N_RES','P0_CBD','PK_CBD','P0_RES','PK_RES', ...
    'cost_CBD','cost_RES','cost_CBD_empty','cost_CBD_full','cost_RES_empty','cost_RES_full', ...
    'total_cost','risk_data','key_hours','t_span','time_h','dt_ode', ...
    'cluster_CBD','cluster_RES');

fprintf('\n=== Phase 3 (v12) Complete (%.1f sec total) ===\n', toc(tic_total));
fprintf('CBD cost=%.2f, RES cost=%.2f, Total=%.2f\n', cost_CBD, cost_RES, total_cost);
fprintf('Next: Run step4 for joint dispatch optimization\n');