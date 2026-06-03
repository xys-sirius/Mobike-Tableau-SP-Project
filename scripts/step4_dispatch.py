#!/usr/bin/env python3
# step4_dispatch.py - 双站点(s,S)动态阈值调度优化 (纯Python/numpy)
# 核心思路: 在每小时初评估风险，若触发阈值则调度重置，降低后续时段损失
# 模型: 比较"不调度继续"vs"调度后重置到S"的两条ODE轨迹期望成本差

import numpy as np
from scipy.io import loadmat, savemat
from scipy.integrate import solve_ivp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time, os

t0 = time.time()
print('=== Phase 4 (Python): (s,S) Dynamic Dispatch Optimization ===')

# ==================== 加载结果 ====================
sim = loadmat('C:/Users/33294/Desktop/paper_project/scripts/simulation_results.mat')

K_CBD = int(sim['K_CBD'][0,0])
K_RES = int(sim['K_RES'][0,0])
C_lost = float(sim['C_lost'][0,0])
C_pen_CBD = float(sim['C_penalty_CBD'][0,0])
C_pen_RES = float(sim['C_penalty_RES'][0,0])
lambda_h = sim['lambda_hourly'].flatten()
mu_h = sim['mu_hourly'].flatten()
lambda_h_RES = sim['lambda_hourly_RES'].flatten()
mu_h_RES = sim['mu_hourly_RES'].flatten()
t_ode_CBD = sim['t_ode_CBD'].flatten()
t_ode_RES = sim['t_ode_RES'].flatten()

cost_CBD_nodisp = float(sim['cost_CBD'][0,0])
cost_RES_nodisp = float(sim['cost_RES'][0,0])
total_nodisp = cost_CBD_nodisp + cost_RES_nodisp

C_dispatch = 5.0  # 每次调度成本(元)

fig_path = 'C:/Users/33294/Desktop/paper_project/figures/'
os.makedirs(fig_path, exist_ok=True)

print(f'K_CBD={K_CBD}, K_RES={K_RES}, C_lost={C_lost}, C_pen_CBD={C_pen_CBD}, C_disp={C_dispatch}')
print(f'Baseline (no dispatch): CBD={cost_CBD_nodisp:.2f}, RES={cost_RES_nodisp:.2f}, Total={total_nodisp:.2f}')

# ==================== 速率函数 ====================
def lam_CBD(t):
    h = min(int(t), 23)
    return lambda_h[h]
def mu_CBD(t):
    h = min(int(t), 23)
    return mu_h[h]
def lam_RES(t):
    h = min(int(t), 23)
    return lambda_h_RES[h]
def mu_RES(t):
    h = min(int(t), 23)
    return mu_h_RES[h]

# ==================== ODE辅助函数 ====================
def ode_KFE(t, P, K, lam_fn, mu_fn):
    """Physics: lam=借车(death,N->N-1), mu=还车(birth,N->N+1)
    Inflow to i: from i-1 via mu, from i+1 via lam"""
    lam = lam_fn(t)
    mu = mu_fn(t)
    dP = np.zeros(K + 1)
    dP[0]   = -mu * P[0] + lam * P[1]
    for i in range(1, K):
        dP[i] = mu * P[i-1] - (lam + mu) * P[i] + lam * P[i+1]
    dP[K]   = mu * P[K-1] - lam * P[K]
    return dP

def expected_loss_from_dist(P, K, lam, mu, C_lost_val, C_pen_val):
    """给定概率分布P（长度为K+1），计算瞬时期望损失率"""
    p0 = P[0]
    pk = P[K]
    return lam * p0 * C_lost_val + mu * pk * C_pen_val

def simulate_from_state(t_start, t_end, n_start, K, lam_fn, mu_fn):
    """从t_start时刻状态n_start开始，模拟到t_end的ODE轨迹，返回总期望成本"""
    P0_vec = np.zeros(K + 1)
    P0_vec[n_start] = 1.0
    if t_end <= t_start:
        return 0.0, P0_vec
    
    sol = solve_ivp(lambda t, P: ode_KFE(t, P, K, lam_fn, mu_fn),
                    [t_start, t_end], P0_vec, method='RK45', max_step=0.02,
                    rtol=1e-6, atol=1e-9)
    
    # 积分损失率
    total_loss = 0.0
    for i in range(len(sol.t)):
        t = sol.t[i]
        P = sol.y[:, i]
        lam = lam_fn(t)
        mu = mu_fn(t)
        if i < len(sol.t) - 1:
            dt = sol.t[i+1] - sol.t[i]
        else:
            dt = 0
        total_loss += expected_loss_from_dist(P, K, lam, mu, C_lost, C_pen_CBD) * dt
    
    return total_loss, sol.y[:, -1]  # 返回总损失和终态分布

# ==================== 1. 动态(s,S)调度策略 ====================
print('\n=== 1. Dynamic (s,S) Dispatch with Cost-Benefit Decision ===')

# 每小时初检查: N(t) < s → 考虑调度
# 若调度: 花费C_dispatch，库存重置到S，之后按ODE演化
# 若不调度: 维持当前概率分布，继续演化
# 实际中我们基于ODE概率分布评估: P(N < s)的概率中才触发

# 我们采用双层嵌套ODE仿真:
# - 外层: 24小时 × 每小时做一次决策
# - 内层: 仿真从[i, i+1]小时的演化，记录成本

def compute_dispatch_policy(K, N0, lambda_hourly, mu_hourly, C_lost_val, C_pen_val, C_disp):
    """
    对给定站点计算动态(s,S)策略的总期望成本。
    策略: 在每小时初评估，若当前期望库存 < s_threshold 则调度到S。
    对CBD站点使用基于净流量方向的动态阈值。
    """
    
    lam_fn = lambda t: lambda_hourly[min(int(t), 23)]
    mu_fn = lambda t: mu_hourly[min(int(t), 23)]
    
    # 确定动态(s,S): 基于λ/μ比率
    dyn_s = np.zeros(24, dtype=int)
    dyn_S = np.zeros(24, dtype=int)
    
    for h in range(24):
        lam = lambda_hourly[h]
        mu = mu_hourly[h]
        
        if abs(lam + mu) < 1e-10:
            exp_n = K // 2
        else:
            exp_n_raw = K * mu / (lam + mu)
            exp_n = np.clip(int(round(exp_n_raw)), 3, K - 3)
        
        # CBD是净流入站(μ>λ)，需要更多空位→ s偏小, S偏小
        if mu > lam * 1.2:  # 净流入
            s_val = max(2, exp_n - 10)
            S_val = max(s_val + 5, exp_n)
        elif lam > mu * 1.2:  # 净流出
            s_val = min(K - 3, exp_n)
            S_val = min(K, exp_n + 12)
        else:
            s_val = max(2, exp_n - 5)
            S_val = min(K, exp_n + 8)
        
        s_val = np.clip(s_val, 2, K - 5)
        S_val = np.clip(S_val, s_val + 3, K)
        
        dyn_s[h] = s_val
        dyn_S[h] = S_val
    
    # 仿真: 逐小时决策
    # 使用确定性期望值近似: E[N(t)]作为决策依据（而非完整概率分布）
    # 这避免了每步ODE积分的高昂代价，同时保持策略合理性
    
    total_cost = 0.0
    E_N_current = N0  # 当前期望库存
    
    for h in range(24):
        t_start = h
        t_end = h + 1.0
        lam = lambda_hourly[h]
        mu = mu_hourly[h]
        
        s_val = dyn_s[h]
        S_val = dyn_S[h]
        
        # 决策: 如果E[N] < s，考虑调度
        dispatch_this_hour = False
        if E_N_current < s_val:
            # 评估调度收益: 从s_val附近重置到S_val后，本时段损失的减少
            # 简化: 用流体近似 E[N] ≈ N + (μ-λ) 变化
            
            # 不调度的期望损失(粗略): 基于当前位置的P0/PK风险
            p0_risk = max(0, 1 - E_N_current / max(1, K * mu / (lam + mu + 1e-10)))
            p0_risk = min(1.0, p0_risk * 0.5)  # 粗估
            
            pk_risk = max(0, E_N_current / max(1, K) * (lam / (lam + mu + 1e-10)))
            pk_risk = min(1.0, pk_risk * 0.3)
            
            loss_no_dispatch = lam * p0_risk * C_lost_val + mu * pk_risk * C_pen_val
            
            # 调度后的期望: 从S_val出发
            E_after = S_val + (mu - lam) * 0.5  # 半小时间隔的平均
            E_after = np.clip(E_after, 0, K)
            
            p0_after = max(0, 1 - E_after / max(1, K * mu / (lam + mu + 1e-10)))
            p0_after = min(1.0, p0_after * 0.5)
            pk_after = max(0, E_after / max(1, K) * (lam / (lam + mu + 1e-10)))
            pk_after = min(1.0, pk_after * 0.3)
            
            loss_with_dispatch = C_disp + lam * p0_after * C_lost_val + mu * pk_after * C_pen_val
            
            if loss_with_dispatch < loss_no_dispatch:
                dispatch_this_hour = True
                E_N_current = S_val  # 调度重置
        
        # 本时段演化(E[N]的流体近似)
        # dE[N]/dt ≈ μ(t) - λ(t)，受边界约束
        dN = (mu - lam) * 1.0  # 1小时
        E_N_current += dN
        E_N_current = np.clip(E_N_current, 0, K)
        
        # 本时段损失
        if dispatch_this_hour:
            total_cost += C_disp
        
        # P0和PK的粗略估计（基于E[N]和λ/μ比）
        if abs(lam + mu) < 1e-10:
            p0, pk = 0, 0
        else:
            steady_n = K * mu / (lam + mu)
            var_approx = steady_n * (1 - steady_n / K) * 0.3  # 方差近似
            # P0近似: 正态分布尾部
            if E_N_current > 0:
                z0 = abs(E_N_current) / max(1, np.sqrt(max(var_approx, 0.1)))
                p0 = min(1.0, np.exp(-0.5 * z0**2) * 0.5)
            else:
                p0 = 0.5
            zk = abs(K - E_N_current) / max(1, np.sqrt(max(var_approx, 0.1)))
            pk = min(1.0, np.exp(-0.5 * zk**2) * 0.5)
        
        total_cost += lam * p0 * C_lost_val + mu * pk * C_pen_val
    
    return total_cost, dyn_s, dyn_S


# CBD dispatch
cost_CBD_dispatch, dyn_s_CBD, dyn_S_CBD = compute_dispatch_policy(
    K_CBD, K_CBD // 2, lambda_h, mu_h, C_lost, C_pen_CBD, C_dispatch)
saving_CBD = (cost_CBD_nodisp - cost_CBD_dispatch) / cost_CBD_nodisp * 100
print(f'CBD: no-dispatch={cost_CBD_nodisp:.2f} → dispatch={cost_CBD_dispatch:.2f} (saving {saving_CBD:.1f}%)')

# RES dispatch
cost_RES_dispatch, dyn_s_RES, dyn_S_RES = compute_dispatch_policy(
    K_RES, K_RES // 2, lambda_h_RES, mu_h_RES, C_lost, C_pen_RES, C_dispatch)
saving_RES = (cost_RES_nodisp - cost_RES_dispatch) / cost_RES_nodisp * 100
print(f'RES: no-dispatch={cost_RES_nodisp:.2f} → dispatch={cost_RES_dispatch:.2f} (saving {saving_RES:.1f}%)')

total_optimized = cost_CBD_dispatch + cost_RES_dispatch
total_saving = (total_nodisp - total_optimized) / total_nodisp * 100
print(f'TOTAL: {total_nodisp:.2f} → {total_optimized:.2f} (saving {total_saving:.1f}%)')

# ==================== 2. 成本对比表 ====================
print('\n=== 2. Cost Comparison Summary ===')
header = f'{"Strategy":<30}  {"Cost(RMB)":>10}  {"Save%":>8}'
sep = '-' * 52
print(header)
print(sep)
print(f'{"Baseline (no dispatch)":<30}  {total_nodisp:10.2f}  {"-":>8}')
print(f'{"Dynamic (s,S) dispatch":<30}  {total_optimized:10.2f}  {total_saving:7.1f}%')
print(f'{"CBD only":<30}  {cost_CBD_dispatch:10.2f}  {saving_CBD:7.1f}%')
print(f'{"RES only":<30}  {cost_RES_dispatch:10.2f}  {saving_RES:7.1f}%')

# ==================== 3. 画图 ====================
print('\nGenerating figures...')

# Fig 1: 动态阈值策略 (三面板)
fig2, axes = plt.subplots(3, 1, figsize=(12, 11))

ax = axes[0]
ax.plot(range(24), lambda_h, 'r-o', linewidth=2, markersize=5, label='λ(t)')
ax.plot(range(24), mu_h, 'b-s', linewidth=2, markersize=5, label='μ(t)')
ax.set_ylabel('Rate (per hour)'); ax.set_title('CBD Station: λ(t) / μ(t)')
ax.legend(); ax.grid(True); ax.set_xticks(range(24))

ax = axes[1]
ax.plot(range(24), dyn_s_CBD, 'g^-', linewidth=2, markersize=8, label='s*(t) trigger')
ax.plot(range(24), dyn_S_CBD, 'mo-', linewidth=2, markersize=8, label='S*(t) target')
ax.axhline(0, color='k', linestyle=':'); ax.axhline(K_CBD, color='k', linestyle=':')
ax.fill_between(range(24), dyn_s_CBD, dyn_S_CBD, color='lightgreen', alpha=0.3)
ax.set_xlabel('Hour'); ax.set_ylabel('Level')
ax.set_title(f'Dynamic (s(t), S(t)) Threshold Strategy (K={K_CBD})')
ax.legend(); ax.grid(True); ax.set_xticks(range(24))

ax = axes[2]
# 每小时节约成本（无调度损失 - 调度后损失）
hourly_saving = np.zeros(24)
for h in range(24):
    lam = lambda_h[h]; mu = mu_h[h]
    # 无调度损失（粗略）
    if abs(lam + mu) < 1e-10:
        p0_nodisp, pk_nodisp = 0, 0
    else:
        steady_n = K_CBD * mu / (lam + mu)
        var_approx = max(steady_n * (1 - steady_n / K_CBD) * 0.3, 0.1)
        mid_n = K_CBD // 2
        z0 = abs(mid_n) / np.sqrt(var_approx)
        zk = abs(K_CBD - mid_n) / np.sqrt(var_approx)
        p0_nodisp = min(1.0, np.exp(-0.5 * z0**2) * 0.5)
        pk_nodisp = min(1.0, np.exp(-0.5 * zk**2) * 0.5)
    
    # 调度后损失（S_val出发）
    if abs(lam + mu) < 1e-10:
        p0_disp, pk_disp = 0, 0
    else:
        z0d = abs(dyn_S_CBD[h]) / max(1, np.sqrt(var_approx))
        zkd = abs(K_CBD - dyn_S_CBD[h]) / max(1, np.sqrt(var_approx))
        p0_disp = min(1.0, np.exp(-0.5 * z0d**2) * 0.5)
        pk_disp = min(1.0, np.exp(-0.5 * zkd**2) * 0.5)
    
    loss_nodisp = lam * p0_nodisp * C_lost + mu * pk_nodisp * C_pen_CBD
    loss_disp = lam * p0_disp * C_lost + mu * pk_disp * C_pen_CBD
    hourly_saving[h] = loss_nodisp - loss_disp

colors = ['green' if s > 0 else 'red' for s in hourly_saving]
ax.bar(range(24), hourly_saving, color=colors, edgecolor='darkgray')
ax.axhline(0, color='k', linestyle='-')
ax.set_xlabel('Hour'); ax.set_ylabel('Saving (¥/hour)')
ax.set_title(f'Hourly Loss Reduction via Dynamic Dispatch\nTotal saving={cost_CBD_nodisp - cost_CBD_dispatch:.2f}¥ | CBD baseline loss={cost_CBD_nodisp:.2f}¥')
ax.grid(True, axis='y'); ax.set_xticks(range(24))

fig2.suptitle('Dynamic (s,S) Dispatch Optimization for CBD', fontsize=14)
fig2.tight_layout()
fig2.savefig(fig_path + 'dispatch_dynamic_threshold.png', dpi=300, bbox_inches='tight')
print('  dispatch_dynamic_threshold.png saved')

# Fig 2: 成本对比柱状图
fig3, ax = plt.subplots(figsize=(8, 6))
strategies = ['No Dispatch', 'Dynamic (s,S)']
costs = [total_nodisp, total_optimized]
colors = ['gray', 'green']
bars = ax.bar(strategies, costs, color=colors, edgecolor='black', linewidth=1.5)
for bar, c in zip(bars, costs):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3, f'{c:.2f}¥', ha='center', fontsize=13, fontweight='bold')
ax.set_ylabel('Expected Daily Cost (¥)')
ax.set_title(f'Cost Comparison: Baseline vs Dispatch (saving {total_saving:.1f}%)')
ax.grid(True, axis='y', alpha=0.3)
fig3.savefig(fig_path + 'dispatch_cost_comparison.png', dpi=300, bbox_inches='tight')
print('  dispatch_cost_comparison.png saved')

# ==================== 4. 详细动态阈值表 ====================
print('\n=== 4. CBD Hourly Dynamic Threshold Table ===')
print(f'{"Hour":>4}  {"λ":>6}  {"μ":>6}  {"Net":>7}  {"s*":>4}  {"S*":>4}')
for h in range(24):
    net = lambda_h[h] - mu_h[h]
    print(f'{h:4d}  {lambda_h[h]:6.1f}  {mu_h[h]:6.1f}  {net:+7.1f}  {dyn_s_CBD[h]:4d}  {dyn_S_CBD[h]:4d}')

# ==================== 5. 保存 ====================
savemat('C:/Users/33294/Desktop/paper_project/scripts/dispatch_results.mat', {
    'dyn_s_CBD': dyn_s_CBD, 'dyn_S_CBD': dyn_S_CBD,
    'dyn_s_RES': dyn_s_RES, 'dyn_S_RES': dyn_S_RES,
    'cost_CBD_nodisp': cost_CBD_nodisp, 'cost_CBD_dispatch': cost_CBD_dispatch,
    'cost_RES_nodisp': cost_RES_nodisp, 'cost_RES_dispatch': cost_RES_dispatch,
    'total_nodisp': total_nodisp, 'total_optimized': total_optimized,
    'total_saving': total_saving, 'saving_CBD': saving_CBD, 'saving_RES': saving_RES,
    'C_dispatch': C_dispatch, 'C_lost': C_lost, 'C_pen_CBD': C_pen_CBD, 'C_pen_RES': C_pen_RES
})

elapsed = time.time() - t0
print(f'\n=== Phase 4 Complete ({elapsed:.1f}s total) ===')
print(f'TOTAL saving: {total_saving:.1f}% ({total_nodisp:.2f} → {total_optimized:.2f})')
plt.close('all')