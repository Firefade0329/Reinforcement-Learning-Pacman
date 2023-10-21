package ReinforcementLearning;
import java.util.Random;
import java.util.ArrayList;
import java.lang.Math;
import java.io.*;

// State: | Closest Gold
//  0-15       right
//  16-31      up
//  32-47      left
//  48-63      down

// in each case of closest gold direction, there are 16 cases for ghost direction
// 1 represents there is a ghost on this direction, 0 for no
//        |  down | left |   up | right
//    0   |   0   |  0   |   0  |   0
//    1   |   0   |  0   |   0  |   1
//    2   |   0   |  0   |   1  |   0
//    3   |   0   |  0   |   1  |   1
//    4   |   0   |  1   |   0  |   0
//    5   |   0   |  1   |   0  |   1
//    6   |   0   |  1   |   1  |   0
//    7   |   0   |  1   |   1  |   1
//    8   |   1   |  0   |   0  |   0
//    9   |   1   |  0   |   0  |   1
//   10   |   1   |  0   |   1  |   0
//   11   |   1   |  0   |   1  |   1
//   12   |   1   |  1   |   0  |   0
//   13   |   1   |  1   |   0  |   1
//   14   |   1   |  1   |   1  |   0
//   15   |   1   |  1   |   1  |   1

// let dir = 0,1,2,3 for right, up, left, down
// state index = dir * 16 + index_of_ghost_table

// Actions:
// 0: None
// 1: (1,0)
// 2: (0,1)
// 3: (-1,0)
// 4: (0,-1)

public class QLearning {
    double[][] q;
    int numState = 4;
    int numAction = 5;
    double alpha = 1;
    double gamma = 0.8;
    double randomRate;
    double totalReward = 0;
    int[][] dirSet = {{1,0},{0,1},{-1,0},{0,-1}};
    Random random;
    int iter = 0;   // iteration
    FileWriter file;
    boolean train = false;
    boolean keepTrain = false;
    boolean readQ = true;
    int Qindex = 20;
    double eps = 0.0000001;

    public QLearning() {
        this.q = new double[numState][numAction];
        this.random = new Random();
        this.randomRate = 0.0;

        if (readQ) {
            train = false;
            keepTrain = false;
            ArrayList<String> contents = readFile();
            String QString = contents.get(Qindex);
            this.q = StringtoQ(QString);
            // printQ();
        }

        if (keepTrain) {
            ArrayList<String> contents = readFile();
            String QString = contents.get(contents.size() - 1);
            this.q = StringtoQ(QString);
            // printQ();
        }
    }

    public void updateQ(int state, int action, int nextState, double reward) {
        if (train) {
            double QValue = q[state][action];

            double maxQ = q[nextState][0];
            for (int i = 0; i < numAction; i++) {
                if (q[nextState][i] > maxQ) {
                    maxQ = q[nextState][i];
                }
            }

            double newQ = QValue + alpha * (reward + gamma * maxQ - QValue);
            q[state][action] = newQ;
            normalize(state);
            this.randomRate -= eps;
        } 

        FileWriter file;
        try
        {
            file = new FileWriter("data/StepReward.txt", true);
            BufferedWriter writer = new BufferedWriter(file);
            writer.write(String.valueOf(this.totalReward) + "\n");
            writer.close();
        }
        catch (IOException except)
        {
            except.printStackTrace();
        }

       
    }

    public void normalize(int state) {
        double sum = 0;
        for (int i = 0; i < numAction; i++) {
            sum = sum + q[state][i];
        }

        if (sum !=0) {
            for (int i = 0; i < numAction; i++) {
                q[state][i] = q[state][i] / sum;
            }
        }
    }

    // ghostDir = {if right has ghost, if up, if left, if down}. 1 represents yes, 0 represent no
    public int getState(int dir) {

        return dir;
    }

    public double getReward(int action, int[] position, int[][]map, int difference, int[] ghostX, int[] ghostY, int numGhost) {
        double reward = 0;
        int indexX;
        int indexY;
        if (action == 0) {
            indexX = position[0];
            indexY = position[1];
        } else {
            indexX = position[0] + dirSet[action - 1][0];
            indexY = position[1] + dirSet[action - 1][1];
        }

        boolean lose = false;
        for (int i = 0; i < numGhost; i++) {
            if (Math.abs(indexX - ghostX[i]) <= 1 && Math.abs(indexY - ghostY[i]) <= 1) {
                lose = true;
            }
        }

        if (lose) {
            reward = -100;
        } else if (map[indexY][indexX] == 1) {
            reward = 1;
        } else {
            if (difference < 0) {
                reward = 0.1;
            } else {
                reward = -0.1;
            }
        }

        totalReward = totalReward + reward;
        return reward;
    }

    public void reset() {
        if (train) {
            wrireFile(q);
        }
        totalReward = 0;
        iter = 0;
    }

    public void printQ() {
        System.out.println("Q-Table");
        for (int i= 0; i < numState; i++) {
            for (int j = 0; j < numAction; j++) {
                System.out.print(q[i][j] + " ");
            }
            System.out.println();
        }
        System.out.println();
    }

    public int getAction(int state, int[] position, int[][] map) {
        int action = 0;
        if (Math.random() < this.randomRate) {
            action = random.nextInt(numAction);
        } else {
            double sumQ = 0;
            for (int i = 0; i < numAction; i++) {
                sumQ = sumQ + q[state][i];
            }
            if (sumQ == 0) {
                action = random.nextInt(numAction);
            } else {
                double maxQ = -9999;
                for (int i = 0; i < numAction; i++) {
                    if (q[state][i] > maxQ) {
                        maxQ = q[state][i];
                        action = i;
                    }
                }
            }
        }

        iter++;
        return action;
    }

    public void wrireFile(double[][] q) {
        FileWriter file;
        FileWriter file2;
        try
        {
            file = new FileWriter("data/QTable.txt", true);
            BufferedWriter writer = new BufferedWriter(file);
            String table = QtoString(q);
            writer.write(table);
            writer.close();

            file2 = new FileWriter("data/Reward.txt", true);
            BufferedWriter writer2 = new BufferedWriter(file2);
            writer2.write(String.valueOf(this.totalReward) + "\n");
            writer2.close();
        }
        catch (IOException except)
        {
            except.printStackTrace();
        }
 
    }

    public ArrayList<String> readFile() {
        FileReader file;
        ArrayList<String> contents = new ArrayList<String>();

        try {
            file = new FileReader("data/QTable.txt");
            BufferedReader input = new BufferedReader(file);
        try {
            String line = null; 

            while (( line = input.readLine()) != null){
                contents.add(line);
            }
        }
        finally {
            input.close();
        }
        }
            catch (IOException ex){
            ex.printStackTrace();
        }
        return contents;
    }

    public String QtoString(double[][] q) {
        String QString = "";
        for (int i = 0; i < numState; i++) {
            for (int j = 0; j < numAction; j++) {
                QString = QString + q[i][j] + ",";
            }
        }
        QString = QString + "\n";
        return QString;
    }

    public double[][] StringtoQ(String QString) {
        double[][] q = new double[numState][numAction];
        String[] result = QString.split(",");
        for (int i = 0; i < numState; i++) {
            for (int j = 0; j < numAction; j++) {
                q[i][j] = Double.parseDouble(result[i*numAction + j]);
            }
        }
        return q;
    }
}
