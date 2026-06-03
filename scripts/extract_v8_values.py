"""从simulation_results_v8.mat提取关键数值"""
import scipy.io as sio
import numpy as np

data = sio.loadmat('C:/Users/33294/Desktop/paper_project/scripts/simulation_results_v8.mat')

print("=== KEY VALUES (v8) ===")
for key in ['K', 'N0', 'n_stations', 's_optimal', 'min_cost', 
            'total_expected_cost', 'w_max_per_user', 'subsidy_upper',
            'total_expected_lost_users', 'C_lost', 'C_penalty', 'C_dispatch']:
    if key in data:
        val = data[key]
        if hasattr(val, '__iter__') and val.size == 1:
            val = val.item()
        elif hasattr(val, '__iter__') and val.size > 1:
            val = val.flatten()[0]
        print(f"{key} = {val}")
    else:
        print(f"{key} = NOT_FOUND")

# 全天统计
all_traj = data.get('all_trajectories')
if all_traj is not None:
    n_sim, T_min = all_traj.shape
    total_empty_frac = np.sum(all_traj == 0) / (n_sim * T_min)
    total_full_frac = np.sum(all_traj == data['K'].item()) / (n_sim * T_min)
    print(f"\ntotal_empty_frac = {total_empty_frac}")
    print(f"total_full_frac = {total_full_frac}")

# 动态阈值
if 'dynamic_s' in data:
    ds = data['dynamic_s'].flatten()
    print(f"\ndynamic_s = {ds.tolist()}")

# 每小时成本率
if 'hourly_cost_rate' in data:
    hcr = data['hourly_cost_rate']
    if hcr.ndim == 2:
        hcr = hcr.flatten()
    print(f"\nhourly_cost_rate = {hcr.tolist()}")

# 关键时段风险
if 'expected_N_ode' in data:
    en = data['expected_N_ode'].flatten()
    dt = data.get('dt_ode', np.array([0.001])).item() if 'dt_ode' in data else 0.001
    P_t = data.get('P_t')
    K = int(data['K'].item())
    
    print(f"\n=== 关键时段风险 ===")
    for h in [0, 8, 12, 18, 23]:
        idx = int(h / dt)
        if idx < len(en):
            n_val = en[idx]
            p_empty = P_t[0, idx] if P_t is not None else 'N/A'
            p_full = P_t[K, idx] if P_t is not None else 'N/A'
            print(f"Hour {h}: E[N]={n_val:.2f}, P(empty)={p_empty}, P(full)={p_full}")

# 早高峰详情
if 'lambda_hourly' in data:
    lh = data['lambda_hourly'].flatten()
    mh = data['mu_hourly'].flatten()
    print(f"\nlambda_hourly = {lh.tolist()}")
    print(f"mu_hourly = {mh.tolist()}")
    print(f"lambda(8)={lh[8]}, mu(8)={mh[8]}")

print("\n=== DONE ===")