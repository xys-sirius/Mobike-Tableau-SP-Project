% extract_results.m - 提取所有步骤关键数值
diary result_report.txt;
try
    load('poisson_test_results.mat');
    fprintf('=== STEP2: Poisson Test ===\n');
    fprintf('CBD lam: %.1f ~ %.1f, mu: %.1f ~ %.1f\n', min(lambda_hourly), max(lambda_hourly), min(mu_hourly), max(mu_hourly));
    fprintf('RES lam: %.1f ~ %.1f, mu: %.1f ~ %.1f\n', min(lambda_hourly_RES), max(lambda_hourly_RES), min(mu_hourly_RES), max(mu_hourly_RES));
    fprintf('VMR = [%.1f %.1f %.1f %.1f %.1f %.1f]\n', VMR_all);
    fprintf('p   = [%.4f %.4f %.4f %.4f %.4f %.4f]\n', pval_all);
    fprintf('CBD cluster=%d, RES cluster=%d\n', cluster_CBD, cluster_RES);
catch e
    fprintf('step2 error: %s\n', e.message);
end

try
    load('simulation_results.mat');
    fprintf('\n=== STEP3: Simulation ===\n');
    fprintf('CBD K=%d N0=%d, RES K=%d N0=%d\n', K_CBD, N0_CBD, K_RES, N0_RES);
    fprintf('CBD cost=%.2f (empty=%.2f full=%.2f)\n', cost_CBD, cost_CBD_empty, cost_CBD_full);
    fprintf('RES cost=%.2f (empty=%.2f full=%.2f)\n', cost_RES, cost_RES_empty, cost_RES_full);
    fprintf('Total no-dispatch cost=%.2f\n', total_cost_no_dispatch);
    fprintf('Risk data:\n');
    for i=1:size(risk_data,1)
        fprintf('  H%02d: CBD EN=%.1f P0=%.2f%% PK=%.2f%% | RES EN=%.1f P0=%.2f%% PK=%.2f%%\n', ...
            risk_data(i,1), risk_data(i,2), risk_data(i,3), risk_data(i,4), ...
            risk_data(i,5), risk_data(i,6), risk_data(i,7));
    end
    fprintf('Cost params: C_lost=%.1f C_pen_CBD=%.1f C_pen_RES=%.1f C_dispatch=%.0f\n', ...
        C_lost, C_penalty_CBD, C_penalty_RES, C_dispatch);
catch e
    fprintf('step3 error: %s\n', e.message);
end

try
    load('dispatch_results.mat');
    fprintf('\n=== STEP4: Optimization ===\n');
    fprintf('Static saving: %.1f%%, Dynamic saving: %.1f%%\n', saving_static, saving_dynamic);
    fprintf('Dynamic daily cost=%.2f vs baseline=%.2f\n', daily_total_dynamic_CBD, total_cost_no_dispatch);
catch e
    fprintf('step4 error: %s\n', e.message);
end

diary off;
exit;