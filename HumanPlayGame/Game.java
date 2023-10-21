package HumanPlayGame;
import java.util.ArrayList;
import java.util.Random;

public class Game {
    //                1,   2,   3,   4,   5,   6,   7,   8,   9,  11,  11,  12,  13,  14,  15,  16,  17,  18,  19,  21,  21,  22,  23,  24,  25,  26,  27,  28,  29,  31,  31,  32
    int[][] map = {{255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255},
                    {255,   1,   1,   1,   1,   1, 255, 255, 255, 255, 255,   1,   1,   1, 255, 255, 255, 255,   1,   1,   1, 255, 255, 255, 255, 255,   1,   1,   1,   1,   1, 255},
                    {255,   1, 255, 255, 255,   1, 255,   1,   1,   1,   1,   1, 255,   1,   1,   1,   1,   1,   1, 255,   1,   1,   1,   1,   1, 255,   1, 255, 255, 255,   1, 255},
                    {255,   1, 255, 255, 255,   1, 255,   1, 255, 255, 255,   1, 255,   1, 255, 255,   1, 255,   1, 255,   1, 255, 255, 255,   1, 255,   1, 255, 255, 255,   1, 255},
                    {255,   1,   1,   1,   1,   1, 255,   1,   1,   1, 255,   1, 255,   1,   1,   1,   1,   1,   1, 255,   1, 255,   1,   1,   1, 255,   1,   1,   1,   1,   1, 255},
                    {255, 255,   1, 255, 255,   1,   1,   1, 255,   1, 255,   1,   1,   1, 255, 255,   1, 255,   1,   1,   1, 255,   1, 255,   1,   1,   1, 255, 255,   1, 255, 255},
                    {255, 255,   1, 255, 255,   1, 255,   1, 255,   1,   1,   1, 255,   1,   1,   1,   1,   1,   1, 255,   1,   1,   1, 255,   1, 255,   1, 255, 255,   1, 255, 255},
                    {255, 255,   1,   1,   1,   1,   1,   1, 255,   1, 255,   1, 255,   1, 255, 255, 255, 255,   1, 255,   1, 255,   1, 255,   1,   1,   1,   1,   1,   1, 255, 255},
                    {255, 255,   1, 255, 255,   1, 255,   1,   1,   1,   1,   1,   1,   1, 255, 255, 255, 255,   1,   1,   1,   1,   1,   1,   1, 255,   1, 255, 255,   1, 255, 255},
                    {255, 255,   1, 255, 255,   1, 255, 255,   1, 255,   1, 255, 255,   1,   1,   1,   1,   1,   1, 255, 255,   1, 255,   1, 255, 255,   1, 255, 255,   1, 255, 255},
                    {255, 255,   1, 255, 255,   1,   1,   1,   1, 255,   1,   1,   1,   1,   1, 255, 255,   1,   1,   1,   1,   1, 255,   1,   1,   1,   1, 255, 255,   1, 255, 255},
                    {255, 255,   1, 255, 255,   1, 255, 255,   1,   1,   1, 255, 255, 255,   1,   1,   1,   1, 255, 255, 255,   1,   1,   1, 255, 255,   1, 255, 255,   1, 255, 255},
                    {255, 255,   1, 255, 255,   1, 255, 255, 255, 255,   1,   1,   1,   1,   1, 255, 255,   1,   1,   1,   1,   1, 255, 255, 255, 255,   1, 255, 255,   1, 255, 255},
                    {255,   1,   1,   1,   1,   1,   1,   1,   1,   1, 255, 255,   1, 255,   1,   1,   1,   1, 255,   1, 255, 255,   1,   1,   1,   1,   1,   1,   1,   1,   1, 255},
                    {255,   1, 255, 255, 255, 255, 255,   1, 255,   1,   1,   1,   1,   1,   1, 255, 255,   1,   1,   1,   1,   1,   1, 255,   1, 255, 255, 255, 255, 255,   1, 255},
                    {255,   1, 255, 255,   1,   1,   1,   1,   1,   1, 255, 255, 255, 255,   1, 255, 255,   1, 255, 255, 255, 255,   1,   1,   1,   1,   1,   1, 255, 255,   1, 255},
                    {255,   1,   1,   1,   1, 255,   1, 255, 255,   1, 255, 255, 255, 255,   1,   1,   1,   1, 255, 255, 255, 255,   1, 255, 255,   1, 255,   1,   1,   1,   1, 255},
                    {255,   1, 255, 255, 255, 255,   1, 255, 255,   1,   1,   1,   1,   1,   1, 255, 255,   1,   1,   1,   1,   1,   1, 255, 255,   1, 255, 255, 255, 255,   1, 255},
                    {255,   1,   1,   1,   1,   1,   1,   1, 255, 255, 255, 255, 255, 255,   1,   1,   1,   1, 255, 255, 255, 255, 255, 255,   1,   1,   1,   1,   1,   1,   1, 255},
                    {255,   1, 255, 255,   1, 255, 255,   1,   1,   1,   1,   1,   1,   1,   1, 255, 255,   1,   1,   1,   1,   1,   1,   1,   1, 255, 255,   1, 255, 255,   1, 255},
                    {255,   1,   1, 255,   1,   1,   1,   1, 255, 255, 255, 255,   1, 255, 255, 255, 255, 255, 255,   1, 255, 255, 255, 255,   1,   1,   1,   1, 255,   1,   1, 255},
                    {255, 255,   1,   1, 255,   1, 255,   1,   1, 255, 255,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1, 255, 255,   1,   1, 255,   1, 255,   1,   1, 255, 255},
                    {255, 255, 255,   1,   1,   1, 255, 255,   1,   1,   1,   1, 255, 255, 255, 255, 255, 255, 255, 255,   1,   1,   1,   1, 255, 255,   1,   1,   1, 255, 255, 255},
                    {255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255}};
                
    int width;
    int height;
    int blockSize;

    Agent agent;
    Random random;
    int score;
    int remainGold;

    int ghostNum;
    Ghost[] ghosts;

    int[][] dirSet = {{1,0}, {0,1}, {-1,0}, {0,-1}};

    int difficulty = 5;

    public Game(int width, int height, int ghostNum) {
        this.width = width;
        this.height = height;
        this.blockSize = height / map.length;
        this.random = new Random();
        this.score = 0;
        this.remainGold = 9999;
        this.ghostNum = ghostNum;
        this.ghosts = new Ghost[ghostNum];
    }

    public int[][] getMap() {
        return map;
    }


    public void initAgent() {
        int indexX = 0;
        int indexY = 0;

        boolean positionLegal = false;

        while (!positionLegal) {
            indexX = random.nextInt((int) width / blockSize);
            indexY = random.nextInt((int) height / blockSize);
            if (map[indexY][indexX] != 255) {
                positionLegal = true;
                map[indexY][indexX] = 0;
            }
        }
        
        agent = new Agent(map, indexX * blockSize, indexY * blockSize, blockSize);
    }

    public void initGhost() {
        for (int i = 0; i < ghostNum; i++) {
            int indexX = 0;
            int indexY = 0;

            boolean positionLegal = false;
            while (!positionLegal) {
                indexX = random.nextInt((int) width / blockSize);
                indexY = random.nextInt((int) height / blockSize);
                if (map[indexY][indexX] != 255 && indexX * blockSize != agent.getX() && indexY * blockSize != agent.getY()) {
                    positionLegal = true;
                }
            }

            Ghost ghost = new Ghost(indexX * blockSize, indexY * blockSize, map, blockSize);
            ghosts[i] = ghost;
        }
    }

    public void updateRemainGold(int remainGold) {
        this.remainGold = remainGold;
    }

    public void eatGold() {
        if (map[agent.getY() / this.blockSize][agent.getX() / this.blockSize] == 1) {
            map[agent.getY() / this.blockSize][agent.getX() / this.blockSize] = 0;
            this.score++;
        }
    }

    public int getScore() {
        return this.score;
    }

    public int getRemainGold() {
        return this.remainGold;
    }
    
    public void moveGhost() {

        for (int i = 0; i < ghostNum; i++) {
            double minDist = 9999;
            int[] dir = {0,0};
            int numOutlet = 0;
            ArrayList<int[]> possibility = new ArrayList<int[]>();

            for (int j = 0; j < 4; j++) {
                if (map[ghosts[i].getY()/blockSize + dirSet[j][1]][ghosts[i].getX()/blockSize + dirSet[j][0]] != 255) {
                    if (-ghosts[i].getDir()[0] != dirSet[j][0] || -ghosts[i].getDir()[1] != dirSet[j][1]) {

                        double newDist = Math.pow(ghosts[i].getX()/blockSize + dirSet[j][0] - agent.getX()/blockSize, 2) + Math.pow(ghosts[i].getY()/blockSize + dirSet[j][1] - agent.getY()/blockSize, 2);

                        if (newDist < minDist) {
                            minDist = newDist;
                            dir = dirSet[j];
                        }

                        possibility.add(dirSet[j]);
                        numOutlet++;
                    }
                }
            }

            if (random.nextInt(10) > difficulty - 1) {
                dir = possibility.get(random.nextInt(numOutlet));
            }

            ghosts[i].updateDirection(dir);
            ghosts[i].updatePosition();


        }

    }

}
