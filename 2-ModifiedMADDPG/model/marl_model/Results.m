%% Algorithm 2 (Modified MADDPG) 结果可视化脚本
clear; clc; close all;

% 设置绘图风格
set(0, 'DefaultLineLineWidth', 1.5);
set(0, 'DefaultAxesFontSize', 12);
set(0, 'DefaultAxesFontWeight', 'bold');

%% 1. 奖励曲线 (Reward Convergence)
% 文件包含 [n_platoon, n_episode] 的奖励数据
if exist('reward.mat', 'file')
    load('reward.mat');
    avg_reward = mean(reward, 1); % 对所有车队取平均
    
    figure('Color', [1 1 1]);
    plot(avg_reward, 'Color', [0.8500 0.3250 0.0980]);
    grid on;
    title('Training Convergence: Average Reward');
    xlabel('Episode');
    ylabel('Local Reward');
    saveas(gcf, 'Result_1_Reward.png');
end

%% 2. AoI 累积分布函数 (CDF - 替换平均趋势图)
if exist('AoI.mat', 'file')
    load('AoI.mat'); % 假设变量名为 AoI [n_platoon, n_episode]
    
    % 为了体现收敛后的性能，我们取最后 100 个 Episode 的所有车队数据
    % 如果总 Episode 较少，可以根据实际情况调整，例如 AoI(:, end-50:end)
    if size(AoI, 2) >= 100
        stable_aoi_data = AoI(:, end-99:end);
    else
        stable_aoi_data = AoI;
    end
    
    % 将矩阵拉平为一维向量，用于计算分布
    aoi_vector = stable_aoi_data(:);
    
    % 计算经验累积分布函数 (Empirical CDF)
    [f, x] = ecdf(aoi_vector);
    
    figure('Name', 'AoI CDF');
    % 绘制曲线，设置粗细和颜色
    plot(x, f, 'LineWidth', 2, 'Color', [0 0.4470 0.7410]);
    grid on;
    
    % 装饰图表
    xlabel('Age of Information (AoI)');
    ylabel('Probability (P \leq x)');
    title('CDF of Average AoI (Last 100 Episodes)');
    
    % 设置坐标轴范围，方便观察（根据你数据的最大值微调）
    xlim([0 max(x)*1.1]);
    ylim([0 1.05]);
    
    % 添加一些辅助说明，比如 90% 的 AoI 都在多少以下
    p90 = prctile(aoi_vector, 90);
    line([p90 p90], [0 0.9], 'Color', 'r', 'LineStyle', '--');
    text(p90, 0.4, ['  90th Percentile: ', num2str(round(p90,2))], 'Color', 'r');
    
    saveas(gcf, 'Result_2_AoI_CDF.png');
end

%% 3. V2V 需求消耗过程 (V2V Demand Evolution)
% 结构为 [n_platoon, 100, n_step] 代表最后100轮的每步变化
if exist('demand.mat', 'file')
    load('demand.mat');
    % 取最后一轮 (last episode) 观察 Demand 如何随时间步降为 0
    last_episode_demand = squeeze(mean(demand(:, end, :), 1));
    
    figure('Color', [1 1 1]);
    plot(last_episode_demand, 'g', 'LineWidth', 2);
    grid on;
    title('Intra-Episode: V2V Demand Depletion (Last Episode)');
    xlabel('Step');
    ylabel('Remaining Demand (bits)');
    saveas(gcf, 'Result_3_Demand_Step.png');
end

%% 4. AoI 在一轮内的波动 (AoI Intra-Episode Evolution)
% 结构同上，展示 AoI 锯齿状更新过程
if exist('AoI_evolution.mat', 'file')
    load('AoI_evolution.mat');
    last_episode_aoi_evol = squeeze(mean(AoI_evolution(:, end, :), 1));
    
    figure('Color', [1 1 1]);
    plot(last_episode_aoi_evol, 'b');
    grid on;
    title('Intra-Episode: AoI Sawtooth Waveform (Last Episode)');
    xlabel('Step');
    ylabel('Instantaneous AoI');
    saveas(gcf, 'Result_4_AoI_Evolution.png');
end

%% 5. V2I 与 V2V 速率对比 (Throughput Comparison)
if exist('V2I.mat', 'file') && exist('V2V.mat', 'file')
    load('V2I.mat');
    load('V2V.mat');
    % 计算最后100轮的平均速率
    mean_v2i = squeeze(mean(mean(V2I, 1), 2));
    mean_v2v = squeeze(mean(mean(V2V, 1), 2));
    
    figure('Color', [1 1 1]);
    plot(mean_v2i, 'r', 'DisplayName', 'Inter-platoon (V2I)');
    hold on;
    plot(mean_v2v, 'k', 'DisplayName', 'Intra-platoon (V2V)');
    grid on;
    legend show;
    title('Average Transmission Rate Comparison');
    xlabel('Step');
    ylabel('Rate (bps)');
    saveas(gcf, 'Result_5_Rate_Comparison.png');
end

fprintf('所有可视化图表已保存至当前目录下！\n');