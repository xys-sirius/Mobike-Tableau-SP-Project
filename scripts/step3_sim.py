#!/usr/bin/env python3
# step3_sim.py - 双站点Gillespie仿真 + ODE (纯Python/numpy, 完全向量化)
# 速率: ~5-10秒完成全部计算

import numpy as np
from scipy.io import loadmat, savemat
from scipy.integrate import solve_ivp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time, os

t0 = time.time()
print('=== Phase 3 (Python): Dual Station Gillespie + ODE ===')

# ==================== 加载前序结果 ====================
pt = loadmat('C:/Users/33294/Desktop/paper_project/scripts/poisson_test_results.mat')

cluster_CBD = int(pt['cluster_CBD'][0,0])
cluster_RES = int(pt['cluster_RES'][0,0])
lambda_hourly = pt['lambda_hourly'].flatten()  # CBD到达率(借车)
mu_hourly = pt['mu_hourly'].flatten()          # CBD离开率(还车)
lambda_hourly_RES = pt['lambda_hourly_RES'].flatten()
mu_hourly_RES = pt['mu_hourly_RES'].flatten()

print(f'CBD: Cluster {cluster_CBD}, RES: Cluster {cluster_RES}')

# ==================== 参数设置 ====================
K_CBD, N0_CBD = 50, 25
K_RES, N0_RES = 80, 40
C_lost, C_penalty_CBD, C_penalty_RES = 2.0, 2.5, 1.0
T_total = 24.0
dt_gillespie = 15.0 / 3600  # 15秒步长 = 0.004167h
n_steps = int(T_total / dt_gillespie)  # 5760
n_sim = 200
time_h = np.arange(n_steps + 1) * dt_gillespie
hour_idx = np.minimum(np.floor(time_h[:n_steps]).astype(int), 23)  # 0-23

# ==================== 1. 批量Poisson随机数 ====================
print(f'\nGenerating Poisson random numbers ({n_sim}x{n_steps})...')
t1 = time.time()

lam_per_step_CBD = lambda_hourly[hour_idx] * dt_gillespie
mu_per_step_CBD  = mu_hourly[hour_idx] * dt_gillespie
lam_per_step_RES = lambda_hourly_RES[hour_idx] * dt_gillespie
mu_per_step_RES  = mu_hourly_RES[hour_idx] * dt_gillespie

# 完全向量化: 每行一个仿真
births_CBD = np.random.poisson(mu_per_step_CBD[np.newaxis, :], (n_sim, n_steps))   # n_sim x n_steps
deaths_CBD = np.random.poisson(lam_per_step_CBD[np.newaxis, :], (n_sim, n_steps))
births_RES = np.random.poisson(mu_per_step_RES[np.newaxis, :], (n_sim, n_steps))
deaths_RES = np.random.poisson(lam_per_step_RES[np.newaxis, :], (n_sim, n_steps))
print(f'  Poisson generation: {time.time()-t1:.1f}s')

# ==================== 2. 累积和轨迹 ====================
print('Computing trajectories...')
t1 = time.time()

delta_CBD = births_CBD - deaths_CBD
cum_CBD = np.cumsum(delta_CBD, axis=1)
traj_CBD = np.hstack([np.full((n_sim, 1), N0_CBD), N0_CBD + cum_CBD])
traj_CBD = np.clip(traj_CBD, 0, K_CBD)

delta_RES = births_RES - deaths_RES
cum_RES = np.cumsum(delta_RES, axis=1)
traj_RES = np.hstack([np.full((n_sim, 1), N0_RES), N0_RES + cum_RES])
traj_RES = np.clip(traj_RES, 0, K_RES)
print(f'  Trajectory computation: {time.time()-t1:.1f}s')

# ==================== 3. 统计量 ====================
mean_traj_CBD = np.mean(traj_CBD, axis=0)
std_traj_CBD = np.std(traj_CBD, axis=0, ddof=1)
ci_l_CBD = mean_traj_CBD - 1.96 * std_traj_CBD / np.sqrt(n_sim)
ci_u_CBD = mean_traj_CBD + 1.96 * std_traj_CBD / np.sqrt(n_sim)

mean_traj_RES = np.mean(traj_RES, axis=0)
std_traj_RES = np.std(traj_RES, axis=0, ddof=1)
ci_l_RES = mean_traj_RES - 1.96 * std_traj_RES / np.sqrt(n_sim)
ci_u_RES = mean_traj_RES + 1.96 * std_traj_RES / np.sqrt(n_sim)

empty_CBD = np.sum(traj_CBD == 0) / (n_sim * (n_steps + 1)) * 100
full_CBD  = np.sum(traj_CBD == K_CBD) / (n_sim * (n_steps + 1)) * 100
empty_RES = np.sum(traj_RES == 0) / (n_sim * (n_steps + 1)) * 100
full_RES  = np.sum(traj_RES == K_RES) / (n_sim * (n_steps + 1)) * 100
print(f'CBD: empty={empty_CBD:.2f}%, full={full_CBD:.2f}% | RES: empty={empty_RES:.2f}%, full={full_RES:.2f}%')

# ==================== 4. ODE数值解 (用solve_ivp) ====================
print('Solving ODE...')
t1 = time.time()

# 速率函数: 返回每小时速率（ODE时间单位为小时）
def lam_CBD_t(t):
    h = min(int(t), 23)
    return lambda_hourly[h]

def mu_CBD_t(t):
    h = min(int(t), 23)
    return mu_hourly[h]

def lam_RES_t(t):
    h = min(int(t), 23)
    return lambda_hourly_RES[h]

def mu_RES_t(t):
    h = min(int(t), 23)
    return mu_hourly_RES[h]

def ode_KFE(t, P, K, lam_fn, mu_fn):
    """Kolmogorov Forward Equations: dP/dt = P * Q
    Physics: lambda=借车率(death, N->N-1), mu=还车率(birth, N->N+1)
    Inflow to state i: from i-1 via 还车(mu), from i+1 via 借车(lam)
    Outflow from state i: via 还车(mu) to i+1, via 借车(lam) to i-1"""
    lam = lam_fn(t)
    mu = mu_fn(t)
    dP = np.zeros(K + 1)
    dP[0]   = -mu * P[0] + lam * P[1]           # 流出:还车(0->1), 流入:借车(1->0)
    for i in range(1, K):
        dP[i] = mu * P[i-1] - (lam + mu) * P[i] + lam * P[i+1]
    dP[K]   = mu * P[K-1] - lam * P[K]          # 流入:还车(K-1->K), 流出:借车(K->K-1)
    return dP

# 初始条件
P0_CBD = np.zeros(K_CBD + 1)
P0_CBD[N0_CBD] = 1.0
P0_RES = np.zeros(K_RES + 1)
P0_RES[N0_RES] = 1.0

# 用RK45求解
sol_CBD = solve_ivp(lambda t, P: ode_KFE(t, P, K_CBD, lam_CBD_t, mu_CBD_t),
                    [0, T_total], P0_CBD, method='RK45', max_step=0.02,
                    rtol=1e-6, atol=1e-9)
sol_RES = solve_ivp(lambda t, P: ode_KFE(t, P, K_RES, lam_RES_t, mu_RES_t),
                    [0, T_total], P0_RES, method='RK45', max_step=0.02,
                    rtol=1e-6, atol=1e-9)

t_ode_CBD = sol_CBD.t
P_CBD     = sol_CBD.y
t_ode_RES = sol_RES.t
P_RES     = sol_RES.y

E_N_CBD = np.sum(np.arange(K_CBD + 1)[:, np.newaxis] * P_CBD, axis=0)
P0_prob_CBD = P_CBD[0, :]
PK_prob_CBD = P_CBD[K_CBD, :]

E_N_RES = np.sum(np.arange(K_RES + 1)[:, np.newaxis] * P_RES, axis=0)
P0_prob_RES = P_RES[0, :]
PK_prob_RES = P_RES[K_RES, :]
print(f'  ODE solved: {time.time()-t1:.1f}s (CBD steps={len(t_ode_CBD)}, RES steps={len(t_ode_RES)})')

# ==================== 5. 经济学损失成本 ====================
# 插值到统一时间网格计算成本
t_uniform = np.linspace(0, T_total, 1001)
P0_CBD_interp = np.interp(t_uniform, t_ode_CBD, P0_prob_CBD)
PK_CBD_interp = np.interp(t_uniform, t_ode_CBD, PK_prob_CBD)
P0_RES_interp = np.interp(t_uniform, t_ode_RES, P0_prob_RES)
PK_RES_interp = np.interp(t_uniform, t_ode_RES, PK_prob_RES)

lam_CBD_samples = np.array([lam_CBD_t(t) for t in t_uniform])
mu_CBD_samples  = np.array([mu_CBD_t(t) for t in t_uniform])
lam_RES_samples = np.array([lam_RES_t(t) for t in t_uniform])
mu_RES_samples  = np.array([mu_RES_t(t) for t in t_uniform])

dt_cost = T_total / 1000
cost_CBD_empty = np.sum(lam_CBD_samples * P0_CBD_interp * C_lost * dt_cost)
cost_CBD_full  = np.sum(mu_CBD_samples * PK_CBD_interp * C_penalty_CBD * dt_cost)
cost_CBD = cost_CBD_empty + cost_CBD_full

cost_RES_empty = np.sum(lam_RES_samples * P0_RES_interp * C_lost * dt_cost)
cost_RES_full  = np.sum(mu_RES_samples * PK_RES_interp * C_penalty_RES * dt_cost)
cost_RES = cost_RES_empty + cost_RES_full
total_cost = cost_CBD + cost_RES

print(f'\nCBD cost: total={cost_CBD:.2f} (empty={cost_CBD_empty:.2f} + full={cost_CBD_full:.2f})')
print(f'RES cost: total={cost_RES:.2f} (empty={cost_RES_empty:.2f} + full={cost_RES_full:.2f})')
print(f'Total cost (no dispatch): {total_cost:.2f}')

# ==================== 6. 关键时段风险 ====================
print('\n=== Key Hour Risk ===')
key_hours = [0, 7, 8, 9, 12, 17, 18, 19, 23]
print(f'{"Hour":>4}  {"CBD_E[N]":>8}  {"CBD_P0%":>7}  {"CBD_PK%":>7}  {"RES_E[N]":>8}  {"RES_P0%":>7}  {"RES_PK%":>7}')
risk_data = []
for h in key_hours:
    e_c = np.interp(h, t_ode_CBD, E_N_CBD)
    p0c = np.interp(h, t_ode_CBD, P0_prob_CBD) * 100
    pkc = np.interp(h, t_ode_CBD, PK_prob_CBD) * 100
    e_r = np.interp(h, t_ode_RES, E_N_RES)
    p0r = np.interp(h, t_ode_RES, P0_prob_RES) * 100
    pkr = np.interp(h, t_ode_RES, PK_prob_RES) * 100
    risk_data.append([h, e_c, p0c, pkc, e_r, p0r, pkr])
    print(f'{h:4d}  {e_c:8.1f}  {p0c:7.2f}  {pkc:7.2f}  {e_r:8.1f}  {p0r:7.2f}  {pkr:7.2f}')
risk_data = np.array(risk_data)

# ==================== 7. 画图 ====================
fig_path = 'C:/Users/33294/Desktop/paper_project/figures/'
os.makedirs(fig_path, exist_ok=True)
print('\nGenerating figures...')

# Fig 1: 双站点存量轨迹
fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
for sim in range(min(5, n_sim)):
    ax1.plot(time_h, traj_CBD[sim, :], color=[0.8, 0.6, 0.6], linewidth=0.5)
ax1.plot(time_h, mean_traj_CBD, 'r-', linewidth=2.5)
ax1.fill_between(time_h, ci_l_CBD, ci_u_CBD, color='r', alpha=0.15)
ax1.axhline(0, color='k', linestyle='--')
ax1.axhline(K_CBD, color='k', linestyle='--')
ax1.set_title(f'CBD (Cluster {cluster_CBD}) K={K_CBD}')
ax1.set_xlabel('Hour'); ax1.set_ylabel('N(t)')
ax1.set_xlim(0, 24); ax1.grid(True)

for sim in range(min(5, n_sim)):
    ax2.plot(time_h, traj_RES[sim, :], color=[0.6, 0.6, 0.8], linewidth=0.5)
ax2.plot(time_h, mean_traj_RES, 'b-', linewidth=2.5)
ax2.fill_between(time_h, ci_l_RES, ci_u_RES, color='b', alpha=0.15)
ax2.axhline(0, color='k', linestyle='--')
ax2.axhline(K_RES, color='k', linestyle='--')
ax2.set_title(f'RES (Cluster {cluster_RES}) K={K_RES}')
ax2.set_xlabel('Hour'); ax2.set_ylabel('N(t)')
ax2.set_xlim(0, 24); ax2.grid(True)
fig1.suptitle('Dual Station Inventory Trajectories: CBD vs RES')
fig1.savefig(fig_path + 'dual_inventory_trajectories.png', dpi=300, bbox_inches='tight')
print('  dual_inventory_trajectories.png saved')

# Fig 2: ODE vs Gillespie
fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
ax1.plot(time_h, mean_traj_CBD, 'r-', linewidth=2, label='Gillespie')
ax1.plot(t_ode_CBD, E_N_CBD, 'r--', linewidth=2, label='ODE')
ax1.axhline(0, color='k', linestyle=':'); ax1.axhline(K_CBD, color='k', linestyle=':')
ax1.set_title(f'CBD K={K_CBD}: ODE vs Gillespie')
ax1.set_xlabel('Hour'); ax1.set_ylabel('E[N(t)]')
ax1.legend(); ax1.grid(True)

ax2.plot(time_h, mean_traj_RES, 'b-', linewidth=2, label='Gillespie')
ax2.plot(t_ode_RES, E_N_RES, 'b--', linewidth=2, label='ODE')
ax2.axhline(0, color='k', linestyle=':'); ax2.axhline(K_RES, color='k', linestyle=':')
ax2.set_title(f'RES K={K_RES}: ODE vs Gillespie')
ax2.set_xlabel('Hour'); ax2.set_ylabel('E[N(t)]')
ax2.legend(); ax2.grid(True)
fig2.suptitle('ODE vs Gillespie: Expected Inventory')
fig2.savefig(fig_path + 'dual_ode_vs_gillespie.png', dpi=300, bbox_inches='tight')
print('  dual_ode_vs_gillespie.png saved')

# Fig 3: 风险概率
fig3, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
ax1.plot(t_ode_CBD, P0_prob_CBD * 100, 'r-', linewidth=2, label='CBD empty')
ax1.plot(t_ode_CBD, PK_prob_CBD * 100, 'r--', linewidth=2, label='CBD full')
ax1.plot(t_ode_RES, P0_prob_RES * 100, 'b-', linewidth=2, label='RES empty')
ax1.plot(t_ode_RES, PK_prob_RES * 100, 'b--', linewidth=2, label='RES full')
ax1.set_xlabel('Hour'); ax1.set_ylabel('Probability (%)')
ax1.set_title('P(N=0) vs P(N=K)')
ax1.legend(); ax1.grid(True)

# 每小时快照
hours_snap = np.arange(24)
P0c_snap = np.array([np.interp(h, t_ode_CBD, P0_prob_CBD) * 100 for h in hours_snap])
PKc_snap = np.array([np.interp(h, t_ode_CBD, PK_prob_CBD) * 100 for h in hours_snap])
P0r_snap = np.array([np.interp(h, t_ode_RES, P0_prob_RES) * 100 for h in hours_snap])
PKr_snap = np.array([np.interp(h, t_ode_RES, PK_prob_RES) * 100 for h in hours_snap])
w = 0.35
ax2.bar(hours_snap - w/2, P0c_snap, w, color='r', label='CBD empty')
ax2.bar(hours_snap - w/2, PKc_snap, w, color=[1, 0.4, 0.4], label='CBD full', bottom=P0c_snap)
ax2.bar(hours_snap + w/2, P0r_snap, w, color='b', label='RES empty')
ax2.bar(hours_snap + w/2, PKr_snap, w, color=[0.4, 0.4, 1], label='RES full', bottom=P0r_snap)
ax2.set_xlabel('Hour'); ax2.set_ylabel('Probability (%)')
ax2.set_title('Hourly Risk Snapshot')
ax2.legend(); ax2.grid(True)
fig3.suptitle('Dual Station Risk Probabilities')
fig3.savefig(fig_path + 'dual_risk_probabilities.png', dpi=300, bbox_inches='tight')
print('  dual_risk_probabilities.png saved')

# Fig 4: 概率分布热力图
fig4, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
hp_CBD = np.zeros((K_CBD + 1, 24))
for h in range(24):
    for n in range(K_CBD + 1):
        hp_CBD[n, h] = np.interp(h, t_ode_CBD, P_CBD[n, :], right=P_CBD[n, -1])
hp_CBD[hp_CBD < 1e-6] = 0
im1 = ax1.imshow(hp_CBD, aspect='auto', origin='lower', extent=[0, 24, 0, K_CBD], cmap='viridis')
plt.colorbar(im1, ax=ax1)
ax1.set_title(f'CBD K={K_CBD}: P(N(t)=n)')
ax1.set_xlabel('Hour'); ax1.set_ylabel('n')

hp_RES = np.zeros((K_RES + 1, 24))
for h in range(24):
    for n in range(K_RES + 1):
        hp_RES[n, h] = np.interp(h, t_ode_RES, P_RES[n, :], right=P_RES[n, -1])
hp_RES[hp_RES < 1e-6] = 0
im2 = ax2.imshow(hp_RES, aspect='auto', origin='lower', extent=[0, 24, 0, K_RES], cmap='viridis')
plt.colorbar(im2, ax=ax2)
ax2.set_title(f'RES K={K_RES}: P(N(t)=n)')
ax2.set_xlabel('Hour'); ax2.set_ylabel('n')
fig4.suptitle('Dual Station Transient Probability Heatmaps')
fig4.savefig(fig_path + 'dual_prob_heatmap.png', dpi=300, bbox_inches='tight')
print('  dual_prob_heatmap.png saved')

# ==================== 8. 保存结果 (.mat) ====================
print('\nSaving results...')
savemat('C:/Users/33294/Desktop/paper_project/scripts/simulation_results.mat', {
    'K_CBD': K_CBD, 'K_RES': K_RES,
    'N0_CBD': N0_CBD, 'N0_RES': N0_RES,
    'C_lost': C_lost, 'C_penalty_CBD': C_penalty_CBD, 'C_penalty_RES': C_penalty_RES,
    'lambda_hourly': lambda_hourly, 'mu_hourly': mu_hourly,
    'lambda_hourly_RES': lambda_hourly_RES, 'mu_hourly_RES': mu_hourly_RES,
    'all_traj_CBD': traj_CBD, 'all_traj_RES': traj_RES,
    'mean_traj_CBD': mean_traj_CBD, 'mean_traj_RES': mean_traj_RES,
    'P_CBD': P_CBD, 'P_RES': P_RES,
    'E_N_CBD': E_N_CBD, 'E_N_RES': E_N_RES,
    'P0_CBD': P0_prob_CBD, 'PK_CBD': PK_prob_CBD,
    'P0_RES': P0_prob_RES, 'PK_RES': PK_prob_RES,
    'cost_CBD': cost_CBD, 'cost_RES': cost_RES,
    'cost_CBD_empty': cost_CBD_empty, 'cost_CBD_full': cost_CBD_full,
    'cost_RES_empty': cost_RES_empty, 'cost_RES_full': cost_RES_full,
    'total_cost': total_cost,
    'risk_data': risk_data, 'key_hours': key_hours,
    't_span': t_uniform, 'time_h': time_h,
    't_ode_CBD': t_ode_CBD, 't_ode_RES': t_ode_RES,
    'cluster_CBD': cluster_CBD, 'cluster_RES': cluster_RES
})

elapsed = time.time() - t0
print(f'\n=== Phase 3 Complete ({elapsed:.1f}s total) ===')
print(f'CBD cost={cost_CBD:.2f}, RES cost={cost_RES:.2f}, Total={total_cost:.2f}')
print('Next: Run step4 for dispatch optimization')
plt.close('all')