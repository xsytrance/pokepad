package dev.pokepad.ui

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.GridLayout
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import dev.pokepad.core.Battle
import dev.pokepad.core.Director
import dev.pokepad.core.Ev
import dev.pokepad.core.Mon
import dev.pokepad.core.PokeData
import dev.pokepad.save.SaveData
import java.util.Random

/**
 * TRAINER MODE — a real turn-based battle. You give the command each turn (the
 * opponent's AI answers), the engine resolves it by true Gen-III mechanics, the
 * arena animates that turn, and you're prompted for the next move.
 *
 * Formats: 1v1 / 2v2 / 3v3 / LIMITLESS (your full party). Your team is your
 * loaded save party (lead first), padded with random challengers to fill the
 * format; the opponent gets a same-sized random squad. When your mon faints
 * YOU choose who goes next — the AI switches by matchup, like always.
 */
class TrainerActivity : AppCompatActivity() {

    private val BG = Color.parseColor("#0B1020")
    private val INK = Color.parseColor("#ECEAF6")
    private val DIM = Color.parseColor("#8A87A0")
    private val GOLD = Color.parseColor("#F5D246")
    private val rng = Random()

    private lateinit var arena: TrainerView
    private lateinit var prompt: TextView
    private lateinit var grid: GridLayout
    private lateinit var again: TextView
    private lateinit var fmtBtn: TextView
    private lateinit var mic: TextView
    private val moveBtns = ArrayList<TextView>()
    private val btnActions = arrayOfNulls<() -> Unit>(6)

    private lateinit var dex: dev.pokepad.core.Dex
    private lateinit var battle: Battle
    private var format = 1                    // 1/2/3, or 6 = LIMITLESS (full party)
    private val turnEvents = ArrayList<Ev>()
    private lateinit var commander: VoiceCommander

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        PokeData.ensure(this); SaveData.ensure(this); Sfx.ensure(this)
        dex = PokeData.dex()
        format = getSharedPreferences("pokepad", MODE_PRIVATE).getInt("format", 1)

        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setBackgroundColor(BG) }
        arena = TrainerView(this)
        root.addView(arena, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f))

        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; setBackgroundColor(Color.parseColor("#0E1430"))
            setPadding(dp(14), dp(12), dp(14), dp(18))
        }
        prompt = TextView(this).apply { setTextColor(INK); textSize = 15f; setTypeface(typeface, Typeface.BOLD) }
        panel.addView(prompt)
        grid = GridLayout(this).apply { columnCount = 2; rowCount = 3 }
        val cellW = (resources.displayMetrics.widthPixels - dp(40)) / 2
        repeat(6) { i ->
            val btn = TextView(this).apply {
                textSize = 15f; setTextColor(INK); gravity = Gravity.CENTER; setTypeface(typeface, Typeface.BOLD)
                isClickable = true; isFocusable = true
            }
            btn.setOnClickListener { btnActions[i]?.let { act -> Sfx.play("blip"); act() } }
            moveBtns.add(btn)
            grid.addView(btn, GridLayout.LayoutParams().apply {
                width = cellW; height = dp(58); setMargins(dp(4), dp(6), dp(4), dp(0))
            })
        }
        panel.addView(grid, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8); gravity = Gravity.CENTER_HORIZONTAL })
        commander = VoiceCommander(this,
            onStatus = { s -> runOnUiThread { if (s.isNotEmpty()) prompt.text = s } },
            onMove = { m -> runOnUiThread { onMove(m) } })
        mic = TextView(this).apply {
            text = "🎤  VOICE MODE: OFF"; setTextColor(GOLD); textSize = 14f; gravity = Gravity.CENTER
            setTypeface(typeface, Typeface.BOLD); setPadding(0, dp(12), 0, dp(12))
            background = GradientDrawable().apply { cornerRadius = dp(12).toFloat(); setColor(Color.parseColor("#182042")); setStroke(dp(1), GOLD) }
            isClickable = true; isFocusable = true; setOnClickListener { onMicToggle() }
        }
        panel.addView(mic, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(10) })
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        again = TextView(this).apply {
            text = "▶  NEW BATTLE"; setTextColor(INK); textSize = 16f; gravity = Gravity.CENTER
            setTypeface(typeface, Typeface.BOLD); visibility = View.GONE
            background = GradientDrawable().apply { cornerRadius = dp(14).toFloat(); setColor(Color.parseColor("#E23B3B")) }
            isClickable = true; isFocusable = true
            setOnClickListener { Sfx.play("blip"); prompt.setTextColor(INK); startBattle() }   // in-place, no flicker; voice mode survives
            setPadding(0, dp(14), 0, dp(14))
        }
        fmtBtn = TextView(this).apply {
            text = fmtLabel(); setTextColor(GOLD); textSize = 16f; gravity = Gravity.CENTER
            setTypeface(typeface, Typeface.BOLD); visibility = View.GONE
            background = GradientDrawable().apply { cornerRadius = dp(14).toFloat(); setColor(Color.parseColor("#182042")); setStroke(dp(1), GOLD) }
            isClickable = true; isFocusable = true
            setOnClickListener { Sfx.play("blip"); showFormatMenu() }
            setPadding(0, dp(14), 0, dp(14))
        }
        row.addView(again, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 2f))
        row.addView(fmtBtn, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { leftMargin = dp(8) })
        panel.addView(row, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
        root.addView(panel, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT))
        setContentView(root)
        Insets.padBottom(panel)   // arena stays full-bleed; menu clears the nav bar

        showFormatMenu()
    }

    private fun fmtLabel() = if (format >= 6) "∞ LIMITLESS" else "${format}V$format"

    // ── format / teams ────────────────────────────────────────────────────────
    private fun showFormatMenu() {
        setMenu(false); again.visibility = View.GONE; fmtBtn.visibility = View.GONE
        prompt.text = "Choose your battle format:"
        val opts = listOf(1 to "1V1\nclassic", 2 to "2V2\nback-up mon", 3 to "3V3\nhalf squad", 6 to "∞ LIMITLESS\nfull party")
        for (i in 0 until 6) {
            val btn = moveBtns[i]
            if (i < opts.size) {
                val (n, label) = opts[i]
                btn.text = label
                btn.background = GradientDrawable().apply {
                    cornerRadius = dp(12).toFloat()
                    setColor(if (n == format) Color.parseColor("#2A3A72") else Color.parseColor("#182042"))
                    setStroke(dp(1), if (n == format) GOLD else Color.parseColor("#33406A"))
                }
                btnActions[i] = {
                    format = n
                    getSharedPreferences("pokepad", MODE_PRIVATE).edit().putInt("format", n).apply()
                    startBattle()
                }
                btn.visibility = View.VISIBLE
            } else { btn.visibility = View.GONE; btnActions[i] = null }
        }
        grid.visibility = View.VISIBLE
    }

    private fun randomMon(exclude: Set<String>): Mon {
        val ids = PokeData.speciesIds
        var s = ids[rng.nextInt(ids.size)]
        while (s in exclude) s = ids[rng.nextInt(ids.size)]
        return Mon(dex, s, moves = Director.movesetFor(dex, s))
    }

    private fun myTeam(n: Int): List<Mon> {
        val team = ArrayList<Mon>()
        SaveData.battleLead?.let { team.add(SaveData.mon(it)) }
        SaveData.truth?.party?.filter { it.species != null }?.forEach { sm ->
            if (sm !== SaveData.battleLead && team.size < 6) team.add(SaveData.mon(sm))
        }
        // limitless = your party exactly as it stands; fixed n = party then random back-up
        if (n >= 6) return team.ifEmpty { listOf(randomMon(emptySet())) }
        while (team.size < n) team.add(randomMon(team.map { it.species.name }.toSet()))
        return team.take(n)
    }

    private fun startBattle() {
        val mine = myTeam(format)
        val used = mine.map { it.species.name }.toMutableSet()
        val theirs = ArrayList<Mon>()
        repeat(mine.size) { theirs.add(randomMon(used).also { used.add(it.species.name) }) }

        battle = Battle(dex, mine, theirs, seed = System.currentTimeMillis(), emit = { turnEvents.add(it) })
        battle.humanSides.add("L")

        setMenu(false); again.visibility = View.GONE; fmtBtn.visibility = View.GONE
        arena.verdictWin = null
        prompt.text = if (mine.size > 1) "${fmtLabel()} — ${theirs.size} foes ahead!" else "A wild ${battle.right.name} appeared!"
        turnEvents.clear(); battle.startInteractive()
        val reel = Director.renderEvents(dex, battle.left.species.name, battle.right.species.name, ArrayList(turnEvents),
            battle.left.maxHp.toFloat(), battle.right.maxHp.toFloat(),
            battle.left.maxHp.toFloat(), battle.right.maxHp.toFloat(), leftBack = true, bothOut = false)
        arena.play(reel) { afterReel() }
    }

    // ── turn loop ─────────────────────────────────────────────────────────────
    private fun onMove(move: String) {
        if (battle.awaitingSwitch("L") || battle.over) return
        setMenu(false)
        val hpBeforeL = battle.left.hp.toFloat(); val hpBeforeR = battle.right.hp.toFloat()
        val leftSp = battle.left.species.name; val rightSp = battle.right.species.name
        val maxL = battle.left.maxHp.toFloat(); val maxR = battle.right.maxHp.toFloat()
        turnEvents.clear(); battle.stepInteractive(move)
        val over = battle.over
        val winnerName = if (over) (battle.winner?.name ?: "") else ""
        val reel = Director.renderEvents(dex, leftSp, rightSp, ArrayList(turnEvents),
            hpBeforeL, hpBeforeR, maxL, maxR, leftBack = true, winnerName = winnerName, bothOut = true)
        arena.play(reel) { afterReel() }
    }

    private fun afterReel() {
        when {
            battle.over -> showResult()
            battle.awaitingSwitch("L") -> showSwitchMenu()
            else -> showMenu()
        }
    }

    private fun showSwitchMenu() {
        val choices = battle.switchChoices("L")
        val team = battle.team("L")
        prompt.text = "${battle.left.name} fainted! Who's next?"
        for (i in 0 until 6) {
            val btn = moveBtns[i]
            if (i < choices.size) {
                val m = team[choices[i]]
                val pct = (100 * m.hp / m.maxHp)
                btn.text = "${m.name}\nLv${m.level} · $pct%"
                btn.background = GradientDrawable().apply {
                    cornerRadius = dp(12).toFloat(); setColor(Color.parseColor("#1A2408")); setStroke(dp(1), GOLD)
                }
                val idx = choices[i]
                btnActions[i] = { onSwitch(idx) }
                btn.visibility = View.VISIBLE
            } else { btn.visibility = View.GONE; btnActions[i] = null }
        }
        grid.visibility = View.VISIBLE
        commander.menuHidden()
    }

    private fun onSwitch(idx: Int) {
        grid.visibility = View.GONE
        val rightSp = battle.right.species.name
        val hpR = battle.right.hp.toFloat(); val maxR = battle.right.maxHp.toFloat()
        turnEvents.clear(); battle.sendIn("L", idx)
        val reel = Director.renderEvents(dex, battle.left.species.name, rightSp, ArrayList(turnEvents),
            battle.left.hp.toFloat(), hpR, battle.left.maxHp.toFloat(), maxR, leftBack = true, bothOut = true)
        arena.play(reel) { afterReel() }
    }

    private fun teamStatus(): String {
        val mineLeft = battle.team("L").count { !it.fainted }
        val foesLeft = battle.team("R").count { !it.fainted }
        return if (battle.team("L").size > 1 || battle.team("R").size > 1) "   ($mineLeft left · $foesLeft foes)" else ""
    }

    private fun showMenu() {
        prompt.text = "What will ${battle.left.name} do?${teamStatus()}"
        val moves = battle.leftMoves()
        for (i in 0 until 6) {
            val btn = moveBtns[i]
            if (i < moves.size && i < 4) {
                val name = moves[i]; val mv = dex.moves[name]
                val disp = name.replace("-", " ").replaceFirstChar { it.uppercase() }
                btn.text = if ((mv?.power ?: 0) > 0) "$disp\n${mv?.type?.uppercase()} · ${mv?.power}" else "$disp\n${mv?.type?.uppercase()}"
                btnActions[i] = { onMove(name) }
                btn.background = GradientDrawable().apply { cornerRadius = dp(12).toFloat(); setColor(typeColor(mv?.type)); setStroke(dp(1), Color.parseColor("#00000040")) }
                btn.visibility = View.VISIBLE
            } else { btn.visibility = if (i < 4) View.INVISIBLE else View.GONE; btnActions[i] = null }
        }
        setMenu(true)
        commander.menuShown(listOf(battle.left.name, battle.left.species.name), moves)
    }

    private fun showResult() {
        val youWon = battle.winSide == "L"
        arena.showVerdict(youWon)
        prompt.text = if (youWon) "You won! ${battle.winner?.name ?: "Your team"} is victorious! 🏆"
                      else "You're out of Pokémon… ${battle.winner?.name ?: "the foe"} wins."
        prompt.setTextColor(if (youWon) GOLD else INK)
        setMenu(false); again.visibility = View.VISIBLE; fmtBtn.visibility = View.VISIBLE
        fmtBtn.text = fmtLabel()
    }

    private fun setMenu(show: Boolean) {
        grid.visibility = if (show) View.VISIBLE else View.GONE
        mic.visibility = if (show) View.VISIBLE else View.GONE
        if (!show) commander.menuHidden()
    }

    // ── voice mode ────────────────────────────────────────────────────────────
    private fun onMicToggle() {
        if (!Voice.available(this)) { toast("voice input isn't available on this device"); return }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), 7); return
        }
        val on = commander.toggle()
        mic.text = if (on) "🎤  VOICE MODE: ON" else "🎤  VOICE MODE: OFF"
        if (on && grid.visibility == View.VISIBLE)
            commander.menuShown(listOf(battle.left.name, battle.left.species.name), battle.leftMoves())
        else if (!on) prompt.text = "What will ${battle.left.name} do?${teamStatus()}"
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 7 && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) onMicToggle()
    }

    override fun onResume() { super.onResume(); Music.play(this, "music_battle") }
    override fun onPause() { super.onPause(); Music.stop() }
    override fun onDestroy() { super.onDestroy(); commander.stop() }

    private fun toast(s: String) = Toast.makeText(this, s, Toast.LENGTH_SHORT).show()

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
