package dev.pokepad.ui

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import dev.pokepad.block.Host
import dev.pokepad.block.PokeballScene
import dev.pokepad.core.Director
import dev.pokepad.core.Mon
import dev.pokepad.core.PokeData
import dev.pokepad.save.SaveData
import java.util.Random

/**
 * 🔴 POKÉBALL SHOWCASE — the attract mode. The block (USB or Bluetooth MIDI)
 * sits closed as a Pokéball. Say a name — "Pika…" — and before you finish the
 * sentence the shell cracks open for a peek. Say "I CHOOSE YOU!" and it bursts
 * open: your REAL mon from your REAL save, shiny sparkle and all. Double-tap
 * the glass (or tap the card here) to page through its true stats; tap a move
 * to demo the attack on phone AND block. Say "return!" to close the ball.
 *
 * Works phone-only too — the ball just lives on screen instead of the glass.
 */
class ShowcaseActivity : AppCompatActivity() {

    private val BG = Color.parseColor("#0B1020")
    private val CARD = Color.parseColor("#141B33")
    private val INK = Color.parseColor("#ECEAF6")
    private val DIM = Color.parseColor("#8A87A0")
    private val GOLD = Color.parseColor("#F5D246")
    private val RED = Color.parseColor("#E23B3B")
    private val ui = Handler(Looper.getMainLooper())
    private val rng = Random()

    /** one showable mon, precomputed from the save (or a synth stand-in) */
    private class Entry(val label: String, val species: String, val level: Int,
                        val shiny: Boolean, val nature: String, val ability: String?,
                        val ot: String, val mon: Mon)

    private enum class St { BALL, PEEK, OPEN }
    private var st = St.BALL
    private var current: Entry? = null
    private var page = 0
    private var party: List<Entry> = emptyList()
    private var scene: PokeballScene? = null
    @Volatile private var listening = false
    @Volatile private var closed = false

    private lateinit var status: TextView
    private lateinit var ballArt: TextView
    private lateinit var card: LinearLayout
    private lateinit var sprite: ImageView
    private lateinit var title: TextView
    private lateinit var pageText: TextView
    private lateinit var movesRow: LinearLayout
    private lateinit var partyLine: TextView
    private lateinit var flash: View

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        PokeData.ensure(this); SaveData.ensure(this); Sfx.ensure(this)
        party = buildParty()

        val scroll = ScrollView(this).apply { setBackgroundColor(BG); isFillViewport = true }
        val frame = FrameLayout(this)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(24), dp(40), dp(24), dp(28))
        }
        root.addView(TextView(this).apply {
            text = "POKÉBALL SHOWCASE"; setTextColor(GOLD); textSize = 15f
            letterSpacing = 0.14f; setTypeface(typeface, Typeface.BOLD); gravity = Gravity.CENTER
        })
        status = TextView(this).apply {
            setTextColor(INK); textSize = 16f; gravity = Gravity.CENTER
            setTypeface(typeface, Typeface.BOLD)
        }
        root.addView(status, lp(14, width = dp(320)))

        ballArt = TextView(this).apply { text = "◓"; textSize = 110f; gravity = Gravity.CENTER; setTextColor(RED) }
        root.addView(ballArt, lp(6))

        card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_HORIZONTAL
            background = GradientDrawable().apply { cornerRadius = dp(20).toFloat(); setColor(CARD); setStroke(dp(1), Color.parseColor("#26314F")) }
            setPadding(dp(18), dp(18), dp(18), dp(18)); visibility = View.GONE
            isClickable = true; isFocusable = true
            setOnClickListener { Sfx.play("blip"); nextPage() }
        }
        sprite = ImageView(this)
        card.addView(sprite, LinearLayout.LayoutParams(dp(150), dp(150)))
        title = TextView(this).apply { setTextColor(INK); textSize = 19f; gravity = Gravity.CENTER; setTypeface(typeface, Typeface.BOLD) }
        card.addView(title, lp(8))
        pageText = TextView(this).apply { setTextColor(DIM); textSize = 14.5f; gravity = Gravity.CENTER }
        card.addView(pageText, lp(6))
        card.addView(TextView(this).apply {
            text = "tap card · or double-tap the block glass"; setTextColor(Color.parseColor("#55536A")); textSize = 11.5f; gravity = Gravity.CENTER
        }, lp(8))
        root.addView(card, lp(12, width = dp(320)))

        movesRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; visibility = View.GONE; gravity = Gravity.CENTER }
        root.addView(movesRow, lp(12, width = dp(330)))

        partyLine = TextView(this).apply { setTextColor(DIM); textSize = 12.5f; gravity = Gravity.CENTER }
        root.addView(partyLine, lp(18, width = dp(320)))

        root.addView(bigBtn("⤵  RETURN (close the ball)", CARD) { doReturn() }, lp(14, width = dp(300), height = dp(50)))

        frame.addView(root, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT))
        flash = View(this).apply { visibility = View.GONE }
        frame.addView(flash, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT))
        scroll.addView(frame)
        setContentView(scroll)
        Insets.pad(root)

        // the glass becomes the ball (if a block is linked — USB or BLE MIDI)
        if (Host.streamer?.isAlive == true) {
            val dex = PokeData.dex()
            scene = PokeballScene(
                monPx = { sp, t ->
                    dex.species[sp]?.let { s ->
                        val feats = dev.pokepad.core.FEATURES[sp] ?: dev.pokepad.core.autoFeatures(s.types)
                        dev.pokepad.core.Renderer.render(s.shape, s.types, feats, (t * 6).toInt(), false, sp).px
                    }
                },
                onPage = { p -> ui.post { page = p; Sfx.play("blip"); refresh() } })
                .also { Host.setScene(it) }
        }

        refresh()
        ensureMicThenListen()
    }

    private fun buildParty(): List<Entry> {
        val dex = PokeData.dex()
        val fromSave = SaveData.truth?.party?.filter { it.species != null }?.map { sm ->
            Entry(sm.nickname.ifBlank { cap(sm.species!!) }, sm.species!!, sm.level, sm.shiny,
                sm.nature, sm.ability, sm.otName, SaveData.mon(sm))
        } ?: emptyList()
        if (fromSave.isNotEmpty()) return fromSave
        // no save loaded — stock the ball with three random stand-ins
        val ids = PokeData.speciesIds
        return (0 until 3).map {
            val s = ids[rng.nextInt(ids.size)]
            Entry(cap(s), s, 50, false, "hardy", null, "?", Mon(dex, s, moves = Director.movesetFor(dex, s)))
        }
    }

    // ── the show ─────────────────────────────────────────────────────────────
    private fun star(e: Entry) = PokeballScene.Star(e.species, e.shiny, e.level, e.mon.stats, e.mon.types)

    private fun doPeek(e: Entry) {
        if (st == St.OPEN && current === e) return
        current = e; st = St.PEEK; page = 0
        Sfx.play("ack")
        scene?.peek(star(e))
        refresh()
    }

    private fun doReveal(e: Entry) {
        current = e; st = St.OPEN; page = 0
        Sfx.play("summon")
        scene?.reveal(star(e))
        refresh()
    }

    private fun doReturn() {
        if (st == St.BALL) return
        st = St.BALL; current = null; page = 0
        Sfx.play("faint")
        scene?.close()
        refresh()
    }

    private fun nextPage() {
        if (st != St.OPEN) return
        page = (page + 1) % (scene?.PAGES ?: 3)
        scene?.setPage(page)
        refresh()
    }

    private fun demoAttack(move: String) {
        val e = current ?: return
        val mv = PokeData.dex().moves[move] ?: return
        val col = typeColor(mv.type)
        Sfx.play(if (mv.power >= 90) "super" else "hit")
        scene?.attack(col and 0xFFFFFF)
        // phone: sprite lunges, screen washes in the move's type color
        sprite.animate().translationXBy(dp(30).toFloat()).setDuration(120).withEndAction {
            sprite.animate().translationXBy(-dp(30).toFloat()).setDuration(220).start()
        }.start()
        flash.setBackgroundColor(col); flash.alpha = 0.55f; flash.visibility = View.VISIBLE
        flash.animate().alpha(0f).setDuration(650).withEndAction { flash.visibility = View.GONE }.start()
        status.text = "⚡ ${disp(move)}!"
    }

    // ── voice: continuous, partial-aware ────────────────────────────────────
    private fun ensureMicThenListen() {
        if (!Voice.available(this)) { status.text = "voice unavailable — tap a name below"; return }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), 9); return
        }
        listenLoop()
    }

    override fun onRequestPermissionsResult(code: Int, perms: Array<out String>, res: IntArray) {
        super.onRequestPermissionsResult(code, perms, res)
        if (code == 9 && res.firstOrNull() == PackageManager.PERMISSION_GRANTED) listenLoop()
    }

    private fun names(e: Entry) = listOf(e.label, e.species)

    private fun listenLoop() {
        if (closed || listening) return
        listening = true
        Voice.listenPartial(this,
            onPartial = { hyps -> ui.post { onHeard(hyps, partial = true) } },
            onResult = { hyps ->
                ui.post {
                    listening = false
                    onHeard(hyps, partial = false)
                    ui.postDelayed({ listenLoop() }, 400)   // keep the mic hot
                }
            })
    }

    private fun onHeard(hyps: List<String>, partial: Boolean) {
        if (closed || hyps.isEmpty()) return
        val chooseSaid = hyps.any { it.lowercase().contains("choose") || it.lowercase().contains("chews") }
        val returnSaid = hyps.any { Regex("\\breturn\\b").containsMatchIn(it.lowercase()) }
        val named = party.firstOrNull { e -> Voice.match(hyps, names(e)) != null }

        when {
            // "…return!" — back into the ball (final results only, to be safe)
            !partial && returnSaid && st != St.BALL -> doReturn()
            // "<name>, I choose you!" in one breath — straight to the reveal
            chooseSaid && (named != null || current != null) ->
                doReveal(named ?: current!!)
            // a name mid-sentence — crack the shell before they finish talking
            named != null && st != St.OPEN -> doPeek(named)
            // move demo once revealed
            !partial && st == St.OPEN && current != null ->
                Voice.match(hyps, current!!.mon.moves)?.let { demoAttack(it) }
        }
    }

    // ── phone mirror ─────────────────────────────────────────────────────────
    private fun refresh() {
        val e = current
        partyLine.text = "in the ball: " + party.joinToString(" · ") { it.label } +
            (if (SaveData.truth == null) "   (no save loaded — stand-ins)" else "")
        when (st) {
            St.BALL -> {
                ballArt.visibility = View.VISIBLE; ballArt.text = "◓"; ballArt.setTextColor(RED)
                card.visibility = View.GONE; movesRow.visibility = View.GONE
                status.text = "say a Pokémon's name…"
            }
            St.PEEK -> {
                ballArt.visibility = View.VISIBLE; ballArt.text = "◒"; ballArt.setTextColor(GOLD)
                card.visibility = View.GONE; movesRow.visibility = View.GONE
                status.text = "⚡ ${e?.label?.uppercase()}?!  say “I CHOOSE YOU!”"
            }
            St.OPEN -> {
                ballArt.visibility = View.GONE
                card.visibility = View.VISIBLE
                e ?: return
                val bmp = Sprite.still(PokeData.dex(), e.species)
                sprite.setImageBitmap(Bitmap.createScaledBitmap(bmp, dp(150), dp(150), false))
                title.text = "${e.label}${if (e.shiny) " ✨" else ""}   Lv${e.level}"
                pageText.text = pageBody(e)
                fillMoves(e)
                status.text = "${e.label} — I choose you!"
            }
        }
    }

    private fun pageBody(e: Entry): String {
        val m = e.mon
        return when (page) {
            1 -> {
                val total = m.stats.values.sum()
                "POWER  $total\n(the block shows Lv + power bar)"
            }
            2 -> {
                val s = m.stats
                "HP ${s["hp"]}   ATK ${s["atk"]}   DEF ${s["def"]}\nSPA ${s["spa"]}   SPD ${s["spd"]}   SPE ${s["spe"]}"
            }
            else -> {
                val t = m.types.joinToString("/") { it.uppercase() }
                "$t · ${e.nature}${e.ability?.let { " · $it" } ?: ""}\nOT ${e.ot}"
            }
        }
    }

    private fun fillMoves(e: Entry) {
        movesRow.removeAllViews(); movesRow.visibility = View.VISIBLE
        val dex = PokeData.dex()
        for (mvName in e.mon.moves.take(4)) {
            val mv = dex.moves[mvName] ?: continue
            val b = TextView(this).apply {
                text = disp(mvName); setTextColor(INK); textSize = 12.5f; gravity = Gravity.CENTER
                setTypeface(typeface, Typeface.BOLD)
                background = GradientDrawable().apply { cornerRadius = dp(10).toFloat(); setColor(typeColor(mv.type)) }
                setPadding(dp(6), dp(10), dp(6), dp(10))
                isClickable = true; isFocusable = true
                setOnClickListener { demoAttack(mvName) }
            }
            movesRow.addView(b, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(3); marginEnd = dp(3)
            })
        }
    }

    override fun onResume() { super.onResume(); Music.play(this, "music_menu", 0.25f) }
    override fun onPause() { super.onPause(); Music.stop() }
    override fun onDestroy() {
        super.onDestroy()
        closed = true
        scene?.abort(); if (scene != null) Host.setScene(null)
    }

    private fun cap(s: String) = s.replaceFirstChar { it.uppercase() }
    private fun disp(m: String) = m.replace("-", " ").replaceFirstChar { it.uppercase() }
    private fun lp(top: Int, width: Int = LinearLayout.LayoutParams.WRAP_CONTENT,
                   height: Int = LinearLayout.LayoutParams.WRAP_CONTENT) =
        LinearLayout.LayoutParams(width, height).apply { topMargin = dp(top) }
    private fun bigBtn(label: String, bg: Int, onClick: () -> Unit) = TextView(this).apply {
        text = label; setTextColor(INK); textSize = 15f; setTypeface(typeface, Typeface.BOLD)
        gravity = Gravity.CENTER
        background = GradientDrawable().apply { cornerRadius = dp(16).toFloat(); setColor(bg); setStroke(dp(1), Color.parseColor("#26314F")) }
        isClickable = true; isFocusable = true; setOnClickListener { Sfx.play("blip"); onClick() }
    }
    private fun typeColor(type: String?): Int {
        val rgb = when (type) {
            "fire" -> 0xC85A2E; "water" -> 0x3A6AB0; "electric" -> 0xB89A1E; "grass" -> 0x3E8A34
            "ice" -> 0x4A8A96; "fighting" -> 0xA83E3E; "poison" -> 0x7A3A8A; "ground" -> 0x9A7A3E
            "flying" -> 0x5A6EA8; "psychic" -> 0xB03E6E; "bug" -> 0x6E8A28; "rock" -> 0x7A6A3E
            "ghost" -> 0x4E3E7A; "dragon" -> 0x4A4AA8; "dark" -> 0x4A3E3A; "steel" -> 0x5A6470
            else -> 0x445070
        }
        return (0xFF000000.toInt()) or rgb
    }
}
