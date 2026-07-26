package dev.pokepad.ui

import android.app.Activity
import android.content.Context
import android.text.InputType
import android.widget.EditText

/**
 * TRAINER VOICE — per-phone voice ownership. Two people, two phones, one room:
 * both mics hear the same names, so both phones react. Fix (no voice biometrics
 * needed — those aren't reliable on-device): each trainer picks a CALLSIGN, and
 * a phone only obeys a spoken command that includes its callsign. Say
 * "Ash — Charizard, Flamethrower!" and only the phone calibrated to "Ash" acts.
 *
 * Off by default: with no callsign set, a phone responds to anything (so
 * single-player and the 1-phone showcase are unchanged).
 */
object TrainerVoice {
    private const val KEY = "trainer_callsign"
    private fun prefs(ctx: Context) = ctx.getSharedPreferences("pokepad", Context.MODE_PRIVATE)

    fun callsign(ctx: Context): String = prefs(ctx).getString(KEY, "")?.trim().orEmpty()
    fun isSet(ctx: Context) = callsign(ctx).isNotEmpty()
    fun setCallsign(ctx: Context, name: String) = prefs(ctx).edit().putString(KEY, name.trim()).apply()
    fun label(ctx: Context) = if (isSet(ctx)) callsign(ctx) else "anyone"

    private fun norm(s: String) = s.lowercase().replace(Regex("[^a-z0-9]"), "")

    fun addressed(ctx: Context, hyps: List<String>): Boolean = matches(callsign(ctx), hyps)

    /** Should a phone with this callsign act on the utterance? True when no
     *  callsign is set, or the callsign is heard as its own WORD (or a near
     *  prefix like "Asher" for "Ash" — recognizer noise). Deliberately NOT a
     *  loose substring, so "Ash" doesn't fire on "Rock Sm-ash" or "Sm-ash". */
    fun matches(callsign: String, hyps: List<String>): Boolean {
        val cs = norm(callsign)
        if (cs.length < 2) return true                                    // not calibrated → obey anyone
        for (h in hyps) {
            val words = h.lowercase().split(Regex("[^a-z0-9]+")).map { norm(it) }.filter { it.isNotEmpty() }
            if (words.any { it == cs }) return true                       // whole word: "ash"
            if (words.any { it.startsWith(cs) && it.length - cs.length <= 2 }) return true  // "ashe"/"ashy"
            if (cs.length >= 4 && norm(h).contains(cs)) return true       // long callsign, run-together speech
        }
        return false
    }

    /** Calibrate dialog: type a trainer name (blank/Clear = respond to anyone). */
    fun promptCallsign(activity: Activity, onSet: (String) -> Unit) {
        val input = EditText(activity).apply {
            setText(callsign(activity)); hint = "e.g. Ash"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_WORDS
            setPadding(48, 32, 48, 32)
        }
        android.app.AlertDialog.Builder(activity)
            .setTitle("🎙 Calibrate Trainer Voice")
            .setMessage("Pick your trainer name. This phone will then only obey commands that include it — so your Pokémon answer to YOU, not the other trainer.\n\nExample: \"Ash — Pikachu, Thunderbolt!\"")
            .setView(input)
            .setPositiveButton("Save") { _, _ -> setCallsign(activity, input.text.toString()); onSet(callsign(activity)) }
            .setNeutralButton("Respond to anyone") { _, _ -> setCallsign(activity, ""); onSet("") }
            .setNegativeButton("Cancel", null)
            .show()
    }
}
