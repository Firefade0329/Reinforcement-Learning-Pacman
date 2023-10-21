import java.awt.*;
import javax.swing.*;
import DijkstraPathFinding.*;

public class PacmanDijkstra extends JFrame {
    public PacmanDijkstra() {
        this.add(new GamePanel());
        this.setTitle("Pacman Dijkstra");
        this.setDefaultCloseOperation(EXIT_ON_CLOSE);
        this.setResizable(false);
        this.pack();
        this.setVisible(true);
    }

    public static void main(String[] args) {
        EventQueue.invokeLater(() -> {
            var game = new PacmanDijkstra();
            game.setVisible(true);
        });
    }
}
