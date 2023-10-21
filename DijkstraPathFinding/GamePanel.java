package DijkstraPathFinding;
import java.awt.*;
import javax.swing.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;

public class GamePanel extends JPanel implements ActionListener {
    public final int width = 800;
    public final int height = 600;
    public final int ghostNum = 0;

    public int blockSize;
    public int blockNum;

    public Game game;
    public int[][] map;
    public boolean win = false;
    public boolean lose = false;

    int agentDx = 0;
    int agentDy = 0;
    int agentDir = 0;

    int delay = 500;

    Timer timer;
    int goldSize = 5;

    JLabel scoreLabel;

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

        loadImages();

        start();

    }

    public void start() {
        timer = new Timer(delay, this);
        timer.start();
    }

    public void paintComponent(Graphics g) {
        super.paintComponent(g);
        draw(g);
    }

    public void loadImages() {
        ghostImage = new ImageIcon("Images/ghost.png").getImage();
        rightImage = new ImageIcon("Images/right.png").getImage();
        leftImage = new ImageIcon("Images/left.png").getImage();
        upImage = new ImageIcon("Images/up.png").getImage();
        downImage = new ImageIcon("Images/down.png").getImage();
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
        
        game.searchGold();
        game.eatGold();
        scoreLabel.setText("Score: " + game.getScore());
        gameCheck();
        game.moveGhost();
        gameCheck();

        if (win) {
            win = false;
            reinitialize();
        }

        if (lose) {
            lose = false;
            reinitialize();
        }

        repaint();


        agentDx = game.path.get(game.path.size()-2)[0] - game.agent.getIndexX();
        agentDy = game.path.get(game.path.size()-2)[1] - game.agent.getIndexY();
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

