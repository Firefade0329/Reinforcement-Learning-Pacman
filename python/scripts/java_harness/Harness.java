package ReinforcementLearning;
import java.awt.image.BufferedImage;

public class Harness {
    public static void main(String[] a) throws Exception {
        int games = Integer.parseInt(a[0]);
        GamePanel p = new GamePanel();
        p.timer.stop();
        BufferedImage img = new BufferedImage(800, 600, BufferedImage.TYPE_INT_RGB);
        while (p.iter < games) {
            p.paintComponent(img.getGraphics());   // updates remainGold like a real repaint
            p.actionPerformed(null);
        }
        System.exit(0);
    }
}
