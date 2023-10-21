package DijkstraPathFinding;
import java.util.ArrayList;

public class Dijkstra {

    int[][] dirSet = {{1,0}, {0,1}, {-1,0}, {0,-1}};

    public Dijkstra() {}

    public ArrayList<int[]> findpath(int[] currentPosition, ArrayList<int[]> openSetPosition, int[][] map) {
        ArrayList<int[]> path = new ArrayList<int[]>();
        ArrayList<int[]> openSet = new ArrayList<int[]>();
        ArrayList<Node> closeSet = new ArrayList<Node>();

        for (int i = 0; i < openSetPosition.size(); i++) {
            openSet.add(openSetPosition.get(i));
        }

        Node currentNode = new Node(currentPosition);

        for (int i = 0; i < openSet.size(); i++) {
            if (openSet.get(i)[0] == currentPosition[0] && openSet.get(i)[1] == currentPosition[1]) {
                openSet.remove(i);
                break;
            }
        }

        closeSet.add(currentNode);

        ArrayList<Node> currentLayer = new ArrayList<Node>();
        ArrayList<Node> nextLayer = new ArrayList<Node>();

        nextLayer.add(currentNode);
        Node node = null;

        boolean goldFound = false;

        while (!goldFound) {
            currentLayer = nextLayer;
            nextLayer = new ArrayList<Node>();
            for (int i = 0; i < currentLayer.size(); i++) {
                for (int j = 0; j < 4; j++) {
                    int[] newPosition = {currentLayer.get(i).position[0] + dirSet[j][0], currentLayer.get(i).position[1] + dirSet[j][1]};
                    for (int k = 0; k < openSet.size(); k++) {
                        if (openSet.get(k)[0] == newPosition[0] && openSet.get(k)[1] == newPosition[1]) {
                            node = new Node(newPosition);
                            openSet.remove(k);
                            node.previous = currentLayer.get(i);
                            closeSet.add(node);
                            nextLayer.add(node);

                            if (map[node.position[1]][node.position[0]] == 1) {
                                i = currentLayer.size();
                                j = 4;
                                goldFound = true;
                            }
                            k = openSet.size();
                        }
                    }
                }
            }
        }

        path.add(node.position);
        while (node.previous != null) {
            node = node.previous;
            path.add(node.position);
        }


        return path;
    }
    
}

class Node {
    int[] position;
    Node previous;
    public Node(int[] position) {
        this.position = position;
        this.previous = null;
    }
}
