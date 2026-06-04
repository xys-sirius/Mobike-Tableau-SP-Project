"""extract_ode_data.py - 从 .mat 文件提取真实 ODE 概率数据 (v2 - 修复时间向量)"""
import scipy.io as sio
import numpy as np
import os

BASE = r'C:\Users\33294\Desktop\paper_project\scripts'

sim = sio.loadmat(os.path.join(BASE, 'simulation_results.mat'))
print('simulation_results keys:', list(sim.keys()))

P_CBD = sim['P_CBD']  # (K+1, n_cbd)
P_RES = sim['P_RES']  # (K+1, n_res)
t_CBD = sim['t_ode_CBD'].flatten()
t_RES = sim['t_ode_RES'].flatten()
K_CBD = P_CBD.shape[0] - 1
K_RES = P_RES.shape[0] - 1

print(f'P_CBD: {P_CBD.shape}, t_CBD: {t_CBD.shape}, K_CBD={K_CBD}')
print(f'P_RES: {P_RES.shape}, t_RES: {t_RES.shape}, K_RES={K_RES}')

# 关键时间点概率
print('\n=== Table 3: Key Timepoint Probabilities ===')
print(f'{"Time":>5s} | {"CBD P(N=0)":>12s} | {"CBD P(N=K)":>12s} | {"RES P(N=0)":>12s} | {"RES P(N=K)":>12s}')
print('-' * 65)

for h in [0, 8, 12, 18, 23]:
    ic = np.searchsorted(t_CBD, h)
    ir = np.searchsorted(t_RES, h)
    p0c = P_CBD[0, ic] * 100
    pkc = P_CBD[K_CBD, ic] * 100
    p0r = P_RES[0, ir] * 100
    pkr = P_RES[K_RES, ir] * 100
    print(f' {h:02d}:00 | {p0c:11.4f}% | {pkc:11.4f}% | {p0r:11.4f}% | {pkr:11.4f}%')

# 峰值 (只用前 24 小时内的数据)
mask_c = t_CBD <= 24
mask_r = t_RES <= 24
t_c = t_CBD[mask_c]
t_r = t_RES[mask_r]
Pc = P_CBD[:, mask_c]
Pr = P_RES[:, mask_r]

ip0c = np.argmax(Pc[0, :])
ipkc = np.argmax(Pc[K_CBD, :])
ip0r = np.argmax(Pr[0, :])
ipkr = np.argmax(Pr[K_RES, :])

print('\n=== Peak Probabilities (t <= 24h) ===')
print(f'CBD empty peak: {Pc[0, ip0c]*100:.4f}% @ t={t_c[ip0c]:.2f}h')
print(f'CBD full  peak: {Pc[K_CBD, ipkc]*100:.4f}% @ t={t_c[ipkc]:.2f}h')
print(f'RES empty peak: {Pr[0, ip0r]*100:.4f}% @ t={t_r[ip0r]:.2f}h')
print(f'RES full  peak: {Pr[K_RES, ipkr]*100:.4f}% @ t={t_r[ipkr]:.2f}h')

# 逐小时表
print('\n=== Hourly Probabilities ===')
for h in range(24):
    ic = np.searchsorted(t_c, h)
    ir = np.searchsorted(t_r, h)
    p0c = Pc[0, ic] * 100
    pkc = Pc[K_CBD, ic] * 100
    p0r = Pr[0, ir] * 100
    pkr = Pr[K_RES, ir] * 100
    print(f'{h:02d}:00 CBD e={p0c:6.3f}% f={pkc:6.3f}% | RES e={p0r:6.3f}% f={pkr:6.3f}%')