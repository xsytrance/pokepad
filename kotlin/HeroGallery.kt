import java.awt.Color
import java.awt.Font
import java.awt.image.BufferedImage
import java.io.File
import javax.imageio.ImageIO

private fun outline(px: IntArray): IntArray {
    val out = px.copyOf()
    fun on(x: Int, y: Int) = x in 0..14 && y in 0..14 && px[y * 15 + x] != 0
    for (y in 0 until 15) for (x in 0 until 15) if (!on(x, y)) {
        if (on(x - 1, y) || on(x + 1, y) || on(x, y - 1) || on(x, y + 1)) out[y * 15 + x] = 0x0A0A0F
    }
    return out
}

fun main() {
    val show = listOf("pikachu", "charmander", "squirtle", "bulbasaur",
        "gengar", "snorlax", "jigglypuff", "magikarp")
    val scale = 22; val cell = 15 * scale; val pad = 26
    val cols = 4; val rows = (show.size + cols - 1) / cols
    val cw = cell + pad; val ch = cell + pad + 24
    val img = BufferedImage(cols * cw, rows * ch, BufferedImage.TYPE_INT_RGB)
    val g = img.graphics
    g.color = Color(0x14141B); g.fillRect(0, 0, img.width, img.height)
    show.forEachIndexed { i, name ->
        val raw = HeroArt.px(name) ?: return@forEachIndexed
        val fr = outline(raw)
        val ox = (i % cols) * cw + pad / 2; val oy = (i / cols) * ch + pad / 2
        g.color = Color(0x0A0A0F); g.fillRect(ox, oy, cell, cell)
        for (y in 0 until 15) for (x in 0 until 15) {
            val c = fr[y * 15 + x]; if (c == 0) continue
            g.color = Color(c); g.fillRect(ox + x * scale, oy + y * scale, scale, scale)
        }
        g.color = Color(0xECEAF6); g.font = Font("SansSerif", Font.BOLD, 16)
        g.drawString(name.uppercase(), ox + 4, oy + cell + 20)
    }
    val out = File("build/hero_gallery.png"); out.parentFile.mkdirs()
    ImageIO.write(img, "png", out)
    println("wrote build/hero_gallery.png (${show.size} hero mon)")
}
