# Reinforcement-Learning-Pacman

This a open-source project done by Firefade0329. Pacman is a well-known game since last century. 
This project includes a pacman game for human player, a AI controlled pacman game using path-finding algorithm, and an AI controlled pacman game trained by Reinforcement Learning.


This README file includes:
* Video of this profect
* Performance data of Reinforcement Learning
* Explanation of the source code

Videos
======
The first video shows the AI before training. Pacman is randomly exploring.


https://github.com/Firefade0329/Reinforcement-Learning-Pacman/assets/114788148/3c7b39aa-94f7-41d2-942f-c98d82e7d608


The second video shows the AI after training. Pacman is eating dots as fast as possible while keeping awway from the ghosts.


https://github.com/Firefade0329/Reinforcement-Learning-Pacman/assets/114788148/c8356845-2e2e-48bd-acde-a40b88940416



Reinforcement Learning Performance
=================================
The first figure shows the total rewards gaied in each game. Pacman can get more rewards as the training process goes. After 18 games, it can mantain a reward between 300 and 400 each game.
![reward](https://github.com/Firefade0329/Reinforcement-Learning-Pacman/assets/114788148/cfe6faa6-51a1-43b3-b288-99bc3b24876b)

The second figuer shows the rewards gained during a single game. Pacman is cumulating ots reward as quick as possible.
![step](https://github.com/Firefade0329/Reinforcement-Learning-Pacman/assets/114788148/004e0921-0fbe-4d08-8ab9-d3a9bd66c7a9)


How to run
==========
To run game for human player
```
Run Pacman.java
```
To run pacman with Dijkstra pathfinding algorithm
```
Run PacmanDijkstra.java
```
To run Reinforcement Learning AI
```
Run PAcmanRL.java
```
Parameters for training such as learning factor, decay rate. radom rate can be set in
```
ReinforcementLearning/Qlearning.java
```
To train from start, set the following
```
train = true
keepTrain = false
readQ = false
```
To continue training from exsisting model, set
```
train = true
keepTrain = true
readQ = false
```
To load a traned model, set
```
train = false
keepTrain = false
readQ = true
```
