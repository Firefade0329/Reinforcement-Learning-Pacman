import java.awt.*;
import javax.swing.*;
import ReinforcementLearning.*;

public class PacmanRL extends JFrame {
    public PacmanRL() {
        this.add(new GamePanel());
        this.setTitle("Pacman Reinforcement Learning");
        this.setDefaultCloseOperation(EXIT_ON_CLOSE);
        this.setResizable(false);
        this.pack();
        this.setVisible(true);
    }

    public static void main(String[] args) {
        EventQueue.invokeLater(() -> {
            var game = new PacmanRL();
            game.setVisible(true);
        });
    }
}
