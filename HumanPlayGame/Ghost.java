package HumanPlayGame;
public class Ghost {
    int x;
    int y;
    int[][] map;
    int blockSize;

    int[] dir = {0, 0};
    int[][] dirSet = {{1, 0}, {0, 1}, {-1, 0}, {0, -1}};

    public Ghost(int x, int y, int[][] map, int blockSize) {
        this.x = x;
        this.y = y;
        this.map = map;
        this.blockSize = blockSize;
    }

    public int getX() {
        return this.x;
    }

    public int getY() {
        return this.y;
    }

    public void updatePosition() {
        this.x = this.x + this.dir[0] * blockSize;
        this.y += this.dir[1] * blockSize;
    }

    public void updateDirection(int[] dir) {
        this.dir = dir;
    }

    public int[] getDir() {
        return this.dir;
    }
}
