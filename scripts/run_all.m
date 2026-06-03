% run_all.m
% 一键运行所有分析脚本
fprintf('========== 开始运行全部分析流程 ==========\n\n');

% Phase 1: 数据清洗与EDA
fprintf('>>> Phase 1: 数据清洗与EDA\n');
run('C:/Users/33294/Desktop/paper_project/scripts/step1_data_cleaning.m');

% Phase 2: NHPP统计推断
fprintf('\n>>> Phase 2: NHPP统计推断\n');
run('C:/Users/33294/Desktop/paper_project/scripts/step2_poisson_test.m');

% Phase 3: Gillespie仿真 + ODE
fprintf('\n>>> Phase 3: Gillespie仿真 + ODE\n');
run('C:/Users/33294/Desktop/paper_project/scripts/step3_gillespie_sim.m');

% Phase 4: 调度优化
fprintf('\n>>> Phase 4: 调度优化\n');
run('C:/Users/33294/Desktop/paper_project/scripts/step4_dispatch_optim.m');

fprintf('\n========== 全部分析流程完成 ==========\n');
