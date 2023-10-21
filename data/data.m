clear all
clc

file1 = fopen('Reward.txt', 'r');
formatSpec = '%f';
reward = fscanf(file1,formatSpec);

file2 = fopen('Score.txt', 'r');
score = fscanf(file2,formatSpec);

file3 = fopen('StepReward.txt', 'r');
step = fscanf(file3,formatSpec);

figure(1)
x = linspace(1, length(reward), length(reward));
plot(x, reward)
xlabel('Games')
ylabel('Reward')
title('Total Reward')

% figure(2)
% x = linspace(1, length(score), length(score));
% plot(x, score)
% xlabel('Games')
% ylabel('Score')
% title('Total Score')

figure(3)
x = linspace(1, 500, 500);
plot(x, step(1501:2000))
xlabel('Step')
ylabel('Reward')
title('Reward in One Game')


