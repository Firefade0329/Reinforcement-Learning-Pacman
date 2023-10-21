package ReinforcementLearning;
import java.awt.*;
import javax.swing.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;
import java.io.*;

public class GamePanel extends JPanel implements ActionListener {
    public final int width = 800;
    public final int height = 600;
    public final int ghostNum = 3;

    public int blockSize;
    public int blockNum;

    public Game game;
    public int[][] map;
    public boolean win = false;
    public boolean lose = false;

    int agentDx = 0;
    int agentDy = 0;
    int agentDir = 0;

    int delay = 100;

    Timer timer;
    int goldSize = 5;

    JLabel scoreLabel;

    QLearning learning;
    int iter = 0;
    int maxStep = 1000;

    int prevGhostDist = 0;

    Image ghostImage;
    Image rightImage, leftImage, upImage, downImage;

    public GamePanel() {

        this.setPreferredSize(new Dimension(width, height));
        this.setBackground(Color.black);
        this.setFocusable(true);
        this.addKeyListener(new MyKeyAdapter());

        game = new Game(width, height, ghostNum);
        map = game.getMap();
        blockSize = height / map.length;
        blockNum = (width / blockSize) * (height / blockSize);

        game.initAgent();
        game.initGhost();

        scoreLabel = new JLabel("Score: " + game.getScore());
        this.add(scoreLabel);

        learning = new QLearning();

        loadImages();

        start();

    }

    public void loadImages() {
        ghostImage = new ImageIcon("Images/ghost.png").getImage();
        rightImage = new ImageIcon("Images/right.png").getImage();
        leftImage = new ImageIcon("Images/left.png").getImage();
        upImage = new ImageIcon("Images/up.png").getImage();
        downImage = new ImageIcon("Images/down.png").getImage();
    }

    public void start() {
        timer = new Timer(delay, this);
        timer.start();
    }

    public void paintComponent(Graphics g) {
        super.paintComponent(g);
        draw(g);
    }

    public void draw(Graphics g) {
        // draw map
        g.setColor(Color.red);
        for (int i = 0; i < height / blockSize; i++) {
            for (int j = 0; j < width / blockSize; j++) {
                if (map[i][j] == 255) {
                    g.fillRect(j * blockSize, i * blockSize, blockSize, blockSize);
                }
            }
        }
        // draw agent
        switch (agentDir) {
            case 0:
                g.drawImage(rightImage, game.agent.getX(), game.agent.getY(), this);
                break;
            case 1:
                g.drawImage(rightImage, game.agent.getX(), game.agent.getY(), this);
                break;
            case 2:
                g.drawImage(upImage, game.agent.getX(), game.agent.getY(), this);
                break;
            case 3:
                g.drawImage(leftImage, game.agent.getX(), game.agent.getY(), this);
                break;
            case 4:
                g.drawImage(downImage, game.agent.getX(), game.agent.getY(), this);
                break;
        }
        // draw gold
        int countGold = 0;
        g.setColor(Color.yellow);
        for (int i = 0; i < height / blockSize; i++) {
            for (int j = 0; j < width / blockSize; j++) {
                if (map[i][j] == 1) {
                    g.fillOval(j * blockSize + blockSize / 2 - 1, i * blockSize + blockSize / 2 - 1, goldSize, goldSize);
                    countGold++;
                }
            }
        }
        game.updateRemainGold(countGold);
        // draw ghosts
        for (int i = 0; i < ghostNum; i++) {
            // g.setColor(Color.white);
            // g.fillOval(game.ghosts[i].getX(), game.ghosts[i].getY(), blockSize, blockSize);
            g.drawImage(ghostImage, game.ghosts[i].getX(), game.ghosts[i].getY(), this);
        }

        // draw path
        g.setColor(Color.gray);
        if (game.path != null) {
            for (int i = 1; i < game.path.size() - 1; i++) {
                g.fillOval(game.path.get(i)[0] * blockSize + blockSize / 2, game.path.get(i)[1] * blockSize + blockSize / 2, goldSize, goldSize);
            }
        }
        
    }


    public void actionPerformed(ActionEvent e) {

        int[] result = game.searchGold();
        int dir = result[0];
        int distance = result[1];

        int[] ghostDir = {0, 0, 0, 0};
        
        int ghostDist = 9999;
        int closestGhost = 0;
        for (int i = 0; i < game.ghostNum; i++) {
            result = game.searchGhost(i);
            if (result[1] < ghostDist) {
                ghostDist = result[1];
            }
            if (result[1] <= game.searchDistant) {
                closestGhost = result[0];
                ghostDir[result[0]] = 1;
            }
        }

        int state = learning.getState(dir);
        int[] position = {game.agent.getIndexX(), game.agent.getIndexY()};

        int action = learning.getAction(state, position, game.map);
        if (ghostDist > game.searchDistant) {
            if (action > 0) {
                agentDx = game.dirSet[action-1][0];
                agentDy = game.dirSet[action-1][1];
                game.agent.move(agentDx, agentDy);
                if (agentDx == 1) {
                    agentDir = 1;
                } else if (agentDy == -1) {
                    agentDir = 2;
                } else if (agentDx == -1) {
                    agentDir = 3;
                } else if (agentDy == 1) {
                    agentDir = 4;
                }
            } else {
                game.agent.move(0, 0);
            }
        } else {
            // dirSet = {{1,0}, {0,1}, {-1,0}, {0,-1}};
            int[] notWall = game.notWall(position);
            if (closestGhost == 0) {
                if (notWall[2] == 1) {
                    agentDx = -1;
                    agentDy = 0;
                } else {
                    if (notWall[1] == 1) {
                        agentDx = 0;
                        agentDy = 1;
                    } else {
                        agentDx = 0;
                        agentDy = -1;
                    }
                }
            } else if (closestGhost == 1) {
                if (notWall[1] == 1) {
                    agentDx = 0;
                    agentDy = 1;
                } else {
                    if (notWall[0] == 1) {
                        agentDx = 1;
                        agentDy = 0;
                    } else {
                        agentDx = -1;
                        agentDy = 0;
                    }
                }
            } else if (closestGhost == 2) {
                if (notWall[0] == 1) {
                    agentDx = 1;
                    agentDy = 0;
                } else {
                    if (notWall[1] == 1) {
                        agentDx = 0;
                        agentDy = 1;
                    } else {
                        agentDx = 0;
                        agentDy = -1;
                    }
                }
            } else if (closestGhost == 3) {
                if (notWall[3] == 1) {
                    agentDx = 0;
                    agentDy = -1;
                } else {
                    if (notWall[0] == 1) {
                        agentDx = 1;
                        agentDy = 0;
                    } else {
                        agentDx = -1;
                        agentDy = 0;
                    }
                }
            }
            game.agent.move(agentDx, agentDy);
            if (agentDx == 1) {
                agentDir = 1;
            } else if (agentDy == -1) {
                agentDir = 2;
            } else if (agentDx == -1) {
                agentDir = 3;
            } else if (agentDy == 1) {
                agentDir = 4;
            }
        }
        
        gameCheck();
        if (!lose) {
            if (game.remainGold > 1) {
                result = game.searchGold();
                int newDir = result[0];
                int newDistance = result[1];

                for (int i = 0; i < 4; i++){
                    ghostDir[i] = 0;
                }
                for (int i = 0; i < game.ghostNum; i++) {
                    result = game.searchGhost(i);
                    if (result[1] <= game.searchDistant) {
                        ghostDir[result[0]] = 1;
                    }
                }

                int nextState = learning.getState(newDir);

                int ghostX[] = new int[game.ghostNum];
                int ghostY[] = new int[game.ghostNum];
                for (int i = 0; i < game.ghostNum; i++) {
                    ghostX[i] = game.ghosts[i].getIndexX();
                    ghostY[i] = game.ghosts[i].getIndexY();
                }
                if (ghostDist > game.searchDistant) {
                    double newReward = learning.getReward(action, position, map, newDistance - distance, ghostX, ghostY, game.ghostNum);
                    learning.updateQ(state, action, nextState, newReward);
                }
            }
        }

        game.eatGold();
        scoreLabel.setText("Score: " + game.getScore());
        gameCheck();
        game.moveGhost();
        gameCheck();

        prevGhostDist = ghostDist;

        FileWriter file;
        if (learning.iter >= maxStep) {
            try {
                file = new FileWriter("Score.txt", true);
                BufferedWriter writer = new BufferedWriter(file);
                writer.write(String.valueOf(this.game.getScore()) + "\n");
                writer.close();
            }
            catch (IOException except)
            {
                except.printStackTrace();
            }
            System.out.println("Game#: " + iter);
            System.out.println("Step used: " + learning.iter);
            System.out.println("Reward: " + learning.totalReward);
            learning.printQ();
            iter++;
            learning.reset();
            reinitialize();
        }

        if (win) {
            try {
                file = new FileWriter("Score.txt", true);
                BufferedWriter writer = new BufferedWriter(file);
                writer.write(String.valueOf(this.game.getScore()) + "\n");
                writer.close();
            }
            catch (IOException except)
            {
                except.printStackTrace();
            }
            win = false;
            System.out.println("Game#: " + iter);
            System.out.println("Step used: " + learning.iter);
            System.out.println("Reward: " + learning.totalReward);
            learning.printQ();
            iter++;
            learning.reset();
            reinitialize();
        }

        if (lose) {
            try {
                file = new FileWriter("Score.txt", true);
                BufferedWriter writer = new BufferedWriter(file);
                writer.write(String.valueOf(this.game.getScore()) + "\n");
                writer.close();
            }
            catch (IOException except)
            {
                except.printStackTrace();
            }
            lose = false;
            System.out.println("Game#: " + iter);
            System.out.println("Step used: " + learning.iter);
            System.out.println("Reward: " + learning.totalReward);
            learning.printQ();
            iter++;
            learning.reset();
            reinitialize();
        }

        repaint();
    }

    public void gameCheck() {
        if (game.getRemainGold() == 0) {
            win = true;
        }

        for (int i = 0; i < ghostNum; i++) {
            if (game.agent.getX() == game.ghosts[i].getX() && game.agent.getY() == game.ghosts[i].getY()) {
                lose = true;
            }
        }
    }

    public void reinitialize() {
        game = new Game(width, height, ghostNum);
        map = game.getMap();
        game.initAgent();
        game.initGhost();
    }

    public class MyKeyAdapter extends KeyAdapter {
        public void keyPressed(KeyEvent e) {
            switch(e.getKeyCode()) {
                case KeyEvent.VK_LEFT:
                    agentDx = -1;
                    agentDy = 0;
                    break;
                case KeyEvent.VK_RIGHT:
                    agentDx = 1;
                    agentDy = 0;
                    break;
                case KeyEvent.VK_UP:
                    agentDx = 0;
                    agentDy = -1;
                    break;
                case KeyEvent.VK_DOWN:
                    agentDx = 0;
                    agentDy = 1;  
                    break; 
            }
        }
    }
}



