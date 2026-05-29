%% Algorithm 3 (MADDPG_FDec) 结果可视化脚本
clear; clc; close all;

% 设置全局绘图属性，确保图片清晰、专业
set(0, 'DefaultLineLineWidth', 2);
set(0, 'DefaultAxesFontSize', 12);
set(0, 'DefaultAxesFontWeight', 'bold');
set(0, 'DefaultFigureColor', [1 1 1]);

%% 1. 训练收敛情况 (Reward Convergence)
if exist('reward.mat', 'file')
    load('reward.mat'); % 数据维度通常为 [n_platoon, n_episode]
    avg_reward = mean(reward, 1); 
    
    figure('Name', 'Algo3 Reward');
    plot(avg_reward, 'Color', [0.9290 0.6940 0.1250]); % 橙黄色区分
    grid on;
    title('Algorithm 3: Training Convergence (Average Reward)');
    xlabel('Episode');
    ylabel('Local Reward Sum');
    saveas(gcf, 'Algo3_Result_1_Reward.png');
end

%% 3. AoI 累积分布函数 (CDF - 替换平均趋势图)
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
    
    saveas(gcf, 'Algo3_Result_2_AoI_CDF.png');
end

%% 3. 单周期内 V2V 任务完成度 (Demand Depletion)
if exist('demand.mat', 'file')
    load('demand.mat');
    % 提取最后 100 轮中最后一轮的 Demand 消耗曲线
    % demand 结构为 [n_platoon, 100, steps_per_episode]
    last_episode_demand = squeeze(mean(demand(:, end, :), 1));
    
    figure('Name', 'Algo3 Demand Flow');
    plot(last_episode_demand, 'Color', [0.4660 0.6740 0.1880], 'LineStyle', '--');
    grid on;
    title('Intra-Episode: V2V Demand Depletion Rate');
    xlabel('Step');
    ylabel('Remaining Data (bits)');
    saveas(gcf, 'Algo3_Result_3_Demand_Step.png');
end

%% 4. 实时 AoI 演进 (AoI Sawtooth Evolution)
if exist('AoI_evolution.mat', 'file')
    load('AoI_evolution.mat');
    % 展示最后 100 轮中最后一轮的实时波动
    last_aoi_evol = squeeze(mean(AoI_evolution(:, end, :), 1));
    
    figure('Name', 'Algo3 AoI Sawtooth');
    plot(last_aoi_evol, 'b');
    grid on;
    title('Intra-Episode: AoI Sawtooth Waveform (Real-time)');
    xlabel('Step');
    ylabel('Instantaneous AoI');
    saveas(gcf, 'Algo3_Result_4_AoI_Evolution.png');
end

%% 5. V2I 与 V2V 资源竞争分析 (Throughput)
if exist('V2I.mat', 'file') && exist('V2V.mat', 'file')
    load('V2I.mat');
    load('V2V.mat');
    
    % 计算平均吞吐量
    mean_v2i = squeeze(mean(mean(V2I, 1), 2));
    mean_v2v = squeeze(mean(mean(V2V, 1), 2));
    
    figure('Name', 'Algo3 Rate Comparison');
    set(gcf, 'Color', 'w'); % 设置背景为白色
    
    % 左轴设置
    yyaxis left
    plot(mean_v2i, '-', 'LineWidth', 1.5, 'DisplayName', 'V2I Rate (Cellular)');
    ylabel('V2I Rate (bps)');
    
    % 右轴设置
    yyaxis right
    plot(mean_v2v, ':', 'LineWidth', 2, 'DisplayName', 'V2V Rate (Platoon)');
    ylabel('V2V Rate (bps)');
    
    grid on;
    title('Algorithm 3: Multi-Link Rate Balancing');
    xlabel('Step');
    
    % --- 核心修改：图例放在下方外部，且横向排列 ---
    legend('Location', 'southoutside', 'Orientation', 'horizontal'); 
    % --------------------------------------------
    
    % 导出图片
    saveas(gcf, 'Algo3_Result_5_Rate_Comparison.png');
end

fprintf('Algorithm 3 所有指标可视化已完成并保存到当前文件夹。\n');