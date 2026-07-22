/*
 * Poképad — Gen-III battle math in Kotlin (the on-device engine core).
 *
 * A faithful port of the Python reference spec (sim/engine.py). The harness in
 * main() reads fixtures/crossgate.tsv (expected values computed by Python) and
 * asserts this Kotlin implementation reproduces them BIT-FOR-BIT — the
 * "one rule-set, two engines, one gate" verification. When this engine moves
 * into the Android app to drive the blocks, this same fixture guards it.
 *
 * Gen-III on purpose: physical/special split by TYPE; integer damage formula;
 * STAB; type effectiveness; crits; the 0.85–1.00 roll; nature multipliers.
 */
import java.io.File

val PHYSICAL_TYPES = setOf("normal", "fighting", "flying", "ground", "rock", "bug", "ghost", "poison", "steel")

object Engine {
    /** Gen-III stat formula (natMul: 1.0 / 1.1 / 0.9). Matches Python int() truncation. */
    fun statCalc(base: Int, iv: Int, ev: Int, level: Int, isHp: Boolean, natMul: Double): Int {
        val inner = (2 * base + iv + ev / 4) * level / 100
        return if (isHp) inner + level + 10 else ((inner + 5) * natMul).toInt()
    }

    fun typeEff(chart: Map<String, Map<String, Double>>, moveType: String, defTypes: List<String>): Double {
        var m = 1.0
        for (dt in defTypes) m *= chart[moveType]?.get(dt) ?: 1.0
        return m
    }

    /** Gen-III single-hit damage (core formula, no abilities/stages). */
    fun damage(chart: Map<String, Map<String, Double>>, level: Int, power: Int, atk: Int, def: Int,
               atkTypes: List<String>, moveType: String, defTypes: List<String>,
               roll: Int, crit: Boolean): Int {
        val eff = typeEff(chart, moveType, defTypes)
        if (eff == 0.0) return 0
        var dmg = (2 * level / 5 + 2) * power * atk / def
        dmg = dmg / 50 + 2
        if (crit) dmg *= 2
        if (moveType in atkTypes) dmg = dmg * 3 / 2
        dmg = (dmg * eff).toInt()
        dmg = dmg * roll / 100
        return maxOf(1, dmg)
    }
}

fun main(args: Array<String>) {
    val path = if (args.isNotEmpty()) args[0] else "fixtures/crossgate.tsv"
    val chart = HashMap<String, HashMap<String, Double>>()
    data class Case(val kind: String, val f: List<String>)
    val cases = ArrayList<Case>()
    File(path).forEachLine { line ->
        if (line.isBlank()) return@forEachLine
        val f = line.split("\t")
        when (f[0]) {
            "CHART" -> chart.getOrPut(f[1]) { HashMap() }[f[2]] = f[3].toDouble()
            else -> cases.add(Case(f[0], f))
        }
    }

    var pass = 0; var total = 0; val fails = ArrayList<String>()
    fun check(ok: Boolean, desc: String) { total++; if (ok) pass++ else fails.add(desc) }

    for (c in cases) {
        val f = c.f
        when (c.kind) {
            "STAT" -> {
                val got = Engine.statCalc(f[1].toInt(), f[2].toInt(), f[3].toInt(), f[4].toInt(),
                        f[5] == "1", f[6].toDouble())
                check(got == f[7].toInt(), "STAT ${f.drop(1)} → $got != ${f[7]}")
            }
            "EFF" -> {
                val got = Engine.typeEff(chart, f[1], f[2].split(","))
                check(got == f[3].toDouble(), "EFF ${f[1]} vs ${f[2]} → $got != ${f[3]}")
            }
            "DMG" -> {  // fields: level power atk def atkTypes moveType defTypes phys roll crit expected
                val got = Engine.damage(chart, f[1].toInt(), f[2].toInt(), f[3].toInt(), f[4].toInt(),
                        f[5].split(","), f[6], f[7].split(","), f[9].toInt(), f[10] == "1")
                check(got == f[11].toInt(), "DMG ${f.drop(1)} → $got != ${f[11]}")
            }
        }
    }

    println("Kotlin cross-gate: $pass/$total match the Python spec  (chart ${chart.values.sumOf { it.size }} cells)")
    for (d in fails.take(10)) println("  ❌ $d")
    if (pass != total) kotlin.system.exitProcess(1)
    println("✅ Kotlin engine is bit-identical to the Python reference.")
}
