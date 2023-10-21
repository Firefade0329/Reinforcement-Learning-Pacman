package ReinforcementLearning;
public class Agent {
    int[][] map;
    int x;
    int y;
    int blockSize;
    int score;

    public Agent(int[][] map, int x, int y, int blockSize) {
        this.map = map;
        this.x = x;
        this.y = y;
        this.blockSize = blockSize;
        this.score = 0;
    }

    public int getX() {
        return this.x;
    }

    public int getY() {
        return this.y;
    }

    public int getIndexX() {
        return this.x/blockSize;
    }

    public int getIndexY() {
        return this.y/blockSize;
    }

    public void move(int dx, int dy) {
        if (this.map[this.y/blockSize][this.x/blockSize + dx] != 255) {
            this.x += dx * blockSize;
        }
        if (this.map[this.y/blockSize + dy][this.x/blockSize] != 255) {
            this.y += dy * blockSize;
        }
    }
    
}
