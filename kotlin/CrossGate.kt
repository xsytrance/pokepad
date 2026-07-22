/*
 * Cross-gate: assert the Kotlin Engine reproduces the Python spec's expected
 * values (fixtures/crossgate.tsv) bit-for-bit — "one rule-set, two engines".
 */
import java.io.File

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
            "STAT" -> check(Engine.statCalc(f[1].toInt(), f[2].toInt(), f[3].toInt(), f[4].toInt(),
                    f[5] == "1", f[6].toDouble()) == f[7].toInt(), "STAT ${f.drop(1)}")
            "EFF" -> check(Engine.typeEff(chart, f[1], f[2].split(",")) == f[3].toDouble(), "EFF ${f[1]} vs ${f[2]}")
            "DMG" -> check(Engine.damage(chart, f[1].toInt(), f[2].toInt(), f[3].toInt(), f[4].toInt(),
                    f[5].split(","), f[6], f[7].split(","), f[9].toInt(), f[10] == "1") == f[11].toInt(), "DMG ${f.drop(1)}")
            "STAGE" -> {
                check((1000 * Engine.stageMult(f[1].toInt())).toInt() == f[2].toInt(), "stageMult ${f[1]}")
                check((1000 * Engine.accMult(f[1].toInt())).toInt() == f[3].toInt(), "accMult ${f[1]}")
            }
            "RES" -> check(maxOf(1, f[1].toInt() / 8) == f[2].toInt(), "residual ${f[1]}")
            "TOX" -> check(maxOf(1, f[1].toInt() * f[2].toInt() / 16) == f[3].toInt(), "toxic ${f[1]}/${f[2]}")
            "PARA" -> check(f[1].toInt() / 4 == f[2].toInt(), "para ${f[1]}")
            "DMGX" -> check(Engine.damageStage(chart, f[1].toInt(), f[2].toInt(), f[3].toInt(), f[4].toInt(),
                    f[5].toInt(), f[6].toInt(), f[7] == "1", f[8] == "1",
                    f[9].split(","), f[10], f[11].split(","), f[12].toInt(), f[13] == "1") == f[14].toInt(), "DMGX ${f.drop(1)}")
        }
    }
    println("Kotlin cross-gate: $pass/$total match the Python spec  (chart ${chart.values.sumOf { it.size }} cells)")
    for (d in fails.take(10)) println("  ❌ $d")
    if (pass != total) kotlin.system.exitProcess(1)
    println("✅ Kotlin engine is bit-identical to the Python reference.")
}
