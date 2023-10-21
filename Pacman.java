import java.awt.*;
import javax.swing.*;
import HumanPlayGame.*;

public class Pacman extends JFrame {
    public Pacman() {
        this.add(new GamePanel());
        this.setTitle("Pacman");
        this.setDefaultCloseOperation(EXIT_ON_CLOSE);
        this.setResizable(false);
        this.pack();
        this.setVisible(true);
    }

    public static void main(String[] args) {
        EventQueue.invokeLater(() -> {
            var game = new Pacman();
            game.setVisible(true);
        });
    }
}
